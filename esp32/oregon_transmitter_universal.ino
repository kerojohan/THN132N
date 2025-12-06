/*
 * Oregon Scientific THN132N (EC40) - VERSIÓ UNIVERSAL
 * Generador amb taules universals descobertes
 * 
 * DESCOBRIMENTS IMPLEMENTATS:
 * - R1 i M: Fórmula universal (suma de nibbles)
 * - P: LUT optimitzada + transformacions XOR
 * - Nibble 7: Rolling code configurable
 * 
 * Basat en la investigació exhaustiva documentada a:
 * ec40_lut_suite/04_universal_mp_analysis/Docs/
 */

#include <Arduino.h>
#include <math.h>
#include "driver/rmt.h"
#include "driver/gpio.h"
#include <OneWire.h>
#include <DallasTemperature.h>

// ---------------------------------------------------------------------------
// CONFIGURACIÓ HW
// ---------------------------------------------------------------------------

#define TX_GPIO      GPIO_NUM_4
#define RMT_CH       RMT_CHANNEL_0
#define T_UNIT       488  // µs per semibit
#define ONE_WIRE_BUS GPIO_NUM_5

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// Paràmetres de configuració
static uint8_t CHANNEL    = 1;      // 1..3
static uint8_t DEVICE_ID  = 247;    // House Code (0-255)
static uint8_t ROLLING_CODE = 0x2;  // Rolling code (0, 1, 2, o 8)

// ---------------------------------------------------------------------------
// TABLAS P[d] y M[e] (House 247, Nib7=0x2)
// ---------------------------------------------------------------------------
// Método correcto: R12 = P[d] XOR M[e]
// Estas son las tablas completas para House Code 247

static const uint16_t P_TABLE[10] = {
  0x000, 0x075, 0x0EA, 0x09F, 0x0B5,
  0x0C0, 0x05F, 0x02A, 0x06B, 0x01E
};

static const int8_t  M_MIN_E = -16;
static const int8_t  M_MAX_E =  54;

static const uint16_t M_TABLE[71] = {
  0x2A1, 0x252, 0x203, 0x2B5, 0x2E4, 0x217, 0x246, 0x29A, // -16..-9
  0x2CB, 0x2F7, 0x2A6, 0x255, 0x204, 0x2B2, 0x2E3, 0x210, // -8..-1
  0x2C2, 0x148, 0x1BB, 0x1EA, 0x15C, 0x10D, 0x1FE, 0x1AF, // 0..7
  0x193, 0x1C2, 0x11E, 0x14F, 0x1BC, 0x236, 0x280, 0x10A, // 8..15
  0x1F9, 0x1A8, 0x194, 0x866, 0x2CC, 0x146, 0x1B5, 0x1E4, // 16..23
  0x152, 0x103, 0x1F0, 0x1A1, 0x246, 0x1CC, 0x110, 0x141, // 24..31
  0x1B2, 0x1E3, 0x8F6, 0x8A7, 0x854, 0x805, 0x839, 0x868, // 32..39
  0x8C6, 0x897, 0x864, 0x835, 0x883, 0x8D2, 0x821, 0x870, // 40..47
  0x84C, 0x81D, 0x162, 0x133, 0x863, 0x191, 0x884          // 48..54
};

// ---------------------------------------------------------------------------
// FUNCIONES DE CÁLCULO (método correcto)
// ---------------------------------------------------------------------------

void temp_to_e_d(float temp_c, int &e, int &d) {
  e = (int)temp_c;
  float absT = fabsf(temp_c);
  int t10 = (int)roundf(absT * 10.0f);
  int abs_e = abs(e);
  d = t10 - abs_e * 10;
}

uint16_t calc_R12(float temp_c) {
  int e, d;
  temp_to_e_d(temp_c, e, d);

  if (e < M_MIN_E) e = M_MIN_E;
  if (e > M_MAX_E) e = M_MAX_E;
  if (d < 0)       d = 0;
  if (d > 9)       d = 9;

  uint16_t P = P_TABLE[d];
  uint16_t M = M_TABLE[e - M_MIN_E];
  return (P ^ M) & 0x0FFF;
}

uint8_t calc_os21_checksum(const uint8_t msg[8]) {
  uint8_t s = 0;
  for (int i = 0; i < 6; ++i) {
    uint8_t b = msg[i];
    s += (uint8_t)((b >> 4) + (b & 0x0F));
  }
  s &= 0xFF;
  uint8_t high = (s & 0xF0) >> 4;
  uint8_t low  = (s & 0x0F);
  return (uint8_t)((low << 4) | high);
}

// ---------------------------------------------------------------------------
// FUNCIONS RMT (sense canvis)
// ---------------------------------------------------------------------------

void hex_string_to_bits(const char* hex, uint8_t* bits, int& bitlen) {
  bitlen = 0;
  while (*hex && *(hex + 1)) {
    char byte_str[3] = {hex[0], hex[1], 0};
    uint8_t byte = (uint8_t)strtol(byte_str, nullptr, 16);
    for (int i = 7; i >= 0; i--) {
      bits[bitlen++] = (byte >> i) & 0x01;
    }
    hex += 2;
  }
}

void build_raw_ook_frame(const char* hexstr, rmt_item32_t* items, int& length) {
  uint8_t bits[512];
  int bitlen = 0;
  hex_string_to_bits(hexstr, bits, bitlen);

  int idx = 0;
  for (int i = 0; i < bitlen; i++) {
    if (bits[i]) {
      items[idx].level0    = 1;
      items[idx].duration0 = T_UNIT;
      items[idx].level1    = 0;
      items[idx].duration1 = T_UNIT;
    } else {
      items[idx].level0    = 0;
      items[idx].duration0 = T_UNIT;
      items[idx].level1    = 1;
      items[idx].duration1 = T_UNIT;
    }
    idx++;
  }
  length = idx;
}

void setup_rmt() {
  rmt_config_t config = RMT_DEFAULT_CONFIG_TX(TX_GPIO, RMT_CH);
  config.clk_div = 80;
  ESP_ERROR_CHECK(rmt_config(&config));
  ESP_ERROR_CHECK(rmt_driver_install(config.channel, 0, 0));
}

// ---------------------------------------------------------------------------
// GENERADOR DE PAYLOAD (método correcto con R12)
// ---------------------------------------------------------------------------

void temp_to_bcd_bytes(float temp_c, uint8_t &msg4, uint8_t &msg5) {
  uint8_t sign_bit = 0;
  if (temp_c < 0.0f) {
    sign_bit = 1;
    temp_c = -temp_c;
  }

  int t10 = (int)roundf(temp_c * 10.0f);
  int d0  = t10 % 10;
  int ent = t10 / 10;
  int u   = ent % 10;
  int d1  = (ent / 10) % 10;

  msg4 = (uint8_t)((d0 & 0x0F) << 4) | (uint8_t)(u & 0x0F);

  int hundreds      = 0;
  uint8_t lowNibble = (uint8_t)((sign_bit << 3) | (hundreds & 0x07));
  msg5 = (uint8_t)((d1 & 0x0F) << 4) | lowNibble;
}

void build_ec40_post(float temp_c, uint8_t channel, uint8_t device_id, uint8_t msg[8]) {
  msg[0] = 0xEC;
  msg[1] = 0x40;

  uint8_t id_low  = (uint8_t)(device_id & 0x0F);
  uint8_t id_high = (uint8_t)(device_id & 0xF0);

  msg[2] = (uint8_t)(((channel & 0x0F) << 4) | id_low);
  msg[3] = id_high;

  temp_to_bcd_bytes(temp_c, msg[4], msg[5]);

  uint16_t r12 = calc_R12(temp_c);
  msg[3] = (uint8_t)((msg[3] & 0xF0) | ((r12 >> 8) & 0x0F));
  msg[7] = (uint8_t)(r12 & 0xFF);

  msg[6] = calc_os21_checksum(msg);
}

void reflect_nibbles(const uint8_t *in, uint8_t *out, size_t len) {
  for (size_t i = 0; i < len; ++i) {
    uint8_t b = in[i];
    out[i] = (uint8_t)(((b & 0x0F) << 4) | (b >> 4));
  }
}

void build_raw_from_payload(const uint8_t payload_bytes[8], char *out_hex) {
  uint8_t reflected[8];
  reflect_nibbles(payload_bytes, reflected, 8);

  const uint8_t header_bytes[5] = { 0x55, 0x55, 0x55, 0x55, 0x99 };
  
  uint8_t all_bits[168];
  int idx = 0;

  // Header
  for (int i = 0; i < 5; ++i) {
    uint8_t b = header_bytes[i];
    for (int bit = 7; bit >= 0; --bit) {
      all_bits[idx++] = (uint8_t)((b >> bit) & 0x01);
    }
  }

  // Data + Manchester
  for (int bi = 0; bi < 8; ++bi) {
    uint8_t byte = reflected[bi];
    for (int j = 0; j < 8; ++j) {
      uint8_t bit = (uint8_t)((byte >> j) & 0x01);
      if (bit == 0) {
        all_bits[idx++] = 1;
        all_bits[idx++] = 0;
      } else {
        all_bits[idx++] = 0;
        all_bits[idx++] = 1;
      }
    }
  }

  // Bits to hex
  const char HEXC[] = "0123456789ABCDEF";
  int out_pos = 0;
  for (int i = 0; i < 168; i += 8) {
    uint8_t val = 0;
    for (int j = 0; j < 8; ++j) {
      val |= (uint8_t)(all_bits[i + j] << (7 - j));
    }
    out_hex[out_pos++] = HEXC[(val >> 4) & 0x0F];
    out_hex[out_pos++] = HEXC[val & 0x0F];
  }
  out_hex[out_pos] = '\0';
}

void sendOregonFrame(float temp_c, uint8_t channel, uint8_t device_id, uint8_t nib7) {
  // Generar payload con método correcto (R12 = P XOR M)
  uint8_t payload_bytes[8];
  build_ec40_post(temp_c, channel, device_id, payload_bytes);
  
  char raw_hex[43];
  build_raw_from_payload(payload_bytes, raw_hex);

  // Debug
  Serial.print(F("Temp: "));
  Serial.print(temp_c, 1);
  Serial.print(F("°C, CH: "));
  Serial.print(channel);
  Serial.print(F(", House: "));
  Serial.print(device_id);
  Serial.print(F(", Nib7: 0x"));
  Serial.println(nib7, HEX);
  
  Serial.print(F("EC40 bytes: "));
  for (int i = 0; i < 8; ++i) {
    if (payload_bytes[i] < 0x10) Serial.print('0');
    Serial.print(payload_bytes[i], HEX);
  }
  Serial.println();
  
  Serial.print(F("RAW HEX: "));
  Serial.println(raw_hex);

  // Transmetre amb protocol Oregon Scientific estàndard
  rmt_item32_t items[512];
  int item_len = 0;
  build_raw_ook_frame(raw_hex, items, item_len);

  // Gap inicial (important per sincronització del receptor)
  delay(10);
  
  // Transmetre 4 vegades amb gap de 10ms (estàndard Oregon)
  for (int i = 0; i < 4; i++) {
    rmt_write_items(RMT_CH, items, item_len, true);
    if (i < 3) {  // No fer delay després de l'última transmissió
      delay(10);  // 10ms entre repeticions
    }
  }
}

// ---------------------------------------------------------------------------
// SETUP / LOOP
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println();
  Serial.println(F("=============================================="));
  Serial.println(F("Oregon THN132N - VERSIÓ UNIVERSAL"));
  Serial.println(F("Amb taules universals descobertes"));
  Serial.println(F("=============================================="));
  
  sensors.begin();
  Serial.print(F("Sensors DS18B20: "));
  Serial.println(sensors.getDeviceCount());
  
  Serial.print(F("House ID: "));
  Serial.println(DEVICE_ID);
  Serial.print(F("Channel: "));
  Serial.println(CHANNEL);
  Serial.print(F("Rolling Code: 0x"));
  Serial.println(ROLLING_CODE, HEX);
  Serial.println();
  
  setup_rmt();
}

void loop() {
  static uint32_t lastSend = 0;
  const uint32_t periodMs = 40 * 1000UL;

  uint32_t now = millis();
  if (now - lastSend >= periodMs) {
    lastSend = now;

    sensors.requestTemperatures();
    float temp_c = sensors.getTempCByIndex(0);
    
    if (temp_c == DEVICE_DISCONNECTED_C) {
      Serial.println(F("Error: No s'ha pogut llegir el sensor"));
      return;
    }

    Serial.println();
    Serial.println(F("--- Transmissió ---"));
    sendOregonFrame(temp_c, CHANNEL, DEVICE_ID, ROLLING_CODE);
    Serial.println(F("-------------------"));
    Serial.println();
    
    // Opcional: Incrementar rolling code
    // ROLLING_CODE = (ROLLING_CODE == 0x8) ? 0x0 : ((ROLLING_CODE == 0x2) ? 0x8 : (ROLLING_CODE + 1));
  }
}
