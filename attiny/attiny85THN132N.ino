/*
 * ATtiny85 + DS18B20 -> Emulador Oregon THN132N (EC40)
 *
 * - Lee temperatura desde un DS18B20 (OneWire)
 * - Construye payload EC40 (post-reflect) con tus tablas P y M
 * - Genera RAW OS v2.1 (header + Manchester) en un array de bits
 * - Envía por 433 MHz usando un pin digital -> OOK (bit 1 = HIGH, bit 0 = LOW)
 *
 * NOTA:
 *  - Esto está pensado para Arduino + ATTinyCore.
 *  - Más adelante se puede añadir deep sleep y watchdog.
 */

#include <Arduino.h>
#include <OneWire.h>

// ---------------------------------------------------------------------------
// CONFIGURACIÓN DE PINES
// ---------------------------------------------------------------------------

const uint8_t RF_PIN       = 0;   // PB0 -> DATA módulo TX 433 MHz
const uint8_t ONEWIRE_PIN  = 2;   // PB2 -> DS18B20 DQ

// Periodo entre emisiones (segundos)
const uint32_t PERIOD_SEC = 39;

// Tiempo semibit (µs) para OOK Oregon V2.1 (ajustado según sensor real)
// Sensor real: ~984µs HIGH, ~964µs LOW → promedio ~974µs → semibit ~487µs
const uint16_t T_UNIT_US = 488;

// ---------------------------------------------------------------------------
// OneWire para DS18B20
// ---------------------------------------------------------------------------

OneWire ds(ONEWIRE_PIN);

// ---------------------------------------------------------------------------
// TABLAS P[d] y M[e] (ya validadas, con el fix de 10.0 ºC -> M[10] = 0x100)
// ---------------------------------------------------------------------------

// P[d] para d = 0..9
const uint16_t P_TABLE[10] PROGMEM = {
  0x000, 0x075, 0x0EA, 0x09F, 0x0B5,
  0x0C0, 0x05F, 0x02A, 0x06B, 0x01E
};

// M[e] para e = -16..54  -> index = e + 16 (0..70)
const int8_t  M_MIN_E = -16;
const int8_t  M_MAX_E =  54;

const uint16_t M_TABLE[71] PROGMEM = {
  0x2A1, 0x252, 0x203, 0x2B5, 0x2E4, 0x217, 0x246, 0x29A, // -16..-9
  0x2CB, 0x2F7, 0x2A6, 0x255, 0x204, 0x2B2, 0x2E3, 0x210, // -8..-1
  0x2C2, 0x148, 0x1BB, 0x1EA, 0x15C, 0x10D, 0x1FE, 0x1AF, // 0..7
  0x193, 0x1C2, 0x100, 0x14F, 0x1BC, 0x236, 0x280, 0x10A, // 8..15 (M[10]=0x100)
  0x1F9, 0x1A8, 0x194, 0x866, 0x2CC, 0x146, 0x1B5, 0x1E4, // 16..23
  0x152, 0x103, 0x1F0, 0x1A1, 0x246, 0x1CC, 0x110, 0x141, // 24..31
  0x1B2, 0x1E3, 0x8F6, 0x8A7, 0x854, 0x805, 0x839, 0x868, // 32..39
  0x8C6, 0x897, 0x864, 0x835, 0x883, 0x8D2, 0x821, 0x870, // 40..47
  0x84C, 0x81D, 0x162, 0x133, 0x863, 0x191, 0x884          // 48..54
};

// ---------------------------------------------------------------------------
// Parámetros Oregon del "sensor emulado"
// ---------------------------------------------------------------------------

uint8_t g_channel   = 1;   // Canal 1..3
uint8_t g_device_id = 10;  // House code (ID)


// ---------------------------------------------------------------------------
// DS18B20: lectura simple (bloqueante, pero suficiente para 39s periodo)
// ---------------------------------------------------------------------------

bool readDS18B20(float &tempC)
{
  byte addr[8];

  if (!ds.search(addr)) {
    ds.reset_search();
    return false;
  }

  // Comprobar tipo (0x28 = DS18B20)
  if (addr[0] != 0x28) {
    return false;
  }

  // CRC
  if (OneWire::crc8(addr, 7) != addr[7]) {
    return false;
  }

  // Convert T
  ds.reset();
  ds.select(addr);
  ds.write(0x44, 1); // convertir, alimentación parasita ON

  // Esperar conversión (12 bits ~ 750ms). Puedes bajar resolución luego.
  delay(750);

  // Leer scratchpad
  ds.reset();
  ds.select(addr);
  ds.write(0xBE); // Read Scratchpad

  byte data[9];
  for (byte i = 0; i < 9; i++) {
    data[i] = ds.read();
  }

  // CRC scratchpad opcional
  if (OneWire::crc8(data, 8) != data[8]) {
    return false;
  }

  int16_t raw = (int16_t)((data[1] << 8) | data[0]);
  tempC = (float)raw / 16.0f;  // 0.0625 steps

  return true;
}

// ---------------------------------------------------------------------------
// temp_to_e_d y R12 (igual que en tu Python corregido)
// ---------------------------------------------------------------------------

void temp_to_e_d(float temp_c, int &e, int &d)
{
  int sign = (temp_c < 0.0f) ? -1 : 1;
  float absT = fabsf(temp_c);
  int t10 = (int)roundf(absT * 10.0f); // 9.9999 -> 100

  int ent = t10 / 10;
  e = sign * ent;
  d = t10 - ent * 10;
}

uint16_t calc_R12(float temp_c)
{
  int e, d;
  temp_to_e_d(temp_c, e, d);

  if (e < M_MIN_E) e = M_MIN_E;
  if (e > M_MAX_E) e = M_MAX_E;
  if (d < 0)       d = 0;
  if (d > 9)       d = 9;

  uint16_t P = pgm_read_word(&P_TABLE[d]);
  uint16_t M = pgm_read_word(&M_TABLE[e - M_MIN_E]);
  return (P ^ M) & 0x0FFF;
}

// ---------------------------------------------------------------------------
// temp_to_bcd_bytes (msg[4], msg[5]) – misma lógica que Python
// ---------------------------------------------------------------------------

void temp_to_bcd_bytes(float temp_c, uint8_t &msg4, uint8_t &msg5)
{
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

// ---------------------------------------------------------------------------
// Checksum OS v2.1 (sobre msg[0..5])
// ---------------------------------------------------------------------------

uint8_t calc_os21_checksum(const uint8_t msg[6])
{
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
// reflect_nibbles
// ---------------------------------------------------------------------------

void reflect_nibbles(const uint8_t *in, uint8_t *out, size_t len)
{
  for (size_t i = 0; i < len; ++i) {
    uint8_t b = in[i];
    out[i] = (uint8_t)(((b & 0x0F) << 4) | (b >> 4));
  }
}

// ---------------------------------------------------------------------------
// build_ec40_post (EC40 post-reflect, 8 bytes) – igual que en Python
// ---------------------------------------------------------------------------

void build_ec40_post(float temp_c, uint8_t channel, uint8_t device_id,
                     uint8_t msg[8])
{
  msg[0] = 0xEC;
  msg[1] = 0x40;

  uint8_t id_low  = device_id & 0x0F;
  uint8_t id_high = device_id & 0xF0;

  msg[2] = (uint8_t)(((channel & 0x0F) << 4) | id_low);
  msg[3] = id_high;

  temp_to_bcd_bytes(temp_c, msg[4], msg[5]);

  uint16_t r12 = calc_R12(temp_c);
  msg[3] = (uint8_t)((msg[3] & 0xF0) | ((r12 >> 8) & 0x0F));
  msg[7] = (uint8_t)(r12 & 0xFF);

  msg[6] = calc_os21_checksum(msg);
}

// ---------------------------------------------------------------------------
// EC40 post -> bitstream OS v2.1 (168 bits) directo
// ---------------------------------------------------------------------------
//
//  - Header de 5 bytes: 0x55 0x55 0x55 0x55 0x99  (40 bits)
//  - Datos: 8 bytes EC40_pre (pre-reflect)
//      * se recorre byte a byte, bit LSB-first
//      * cada bit -> Manchester (0 -> 10, 1 -> 01)
//      * eso añade 16 bits por byte -> 128 bits
//  - Total = 40 + 128 = 168 bits
//
//  all_bits[i] = 0 o 1, donde 1->HIGH semibit, 0->LOW semibit.
//  Luego convertimos cada bit a pulso OOK de T_UNIT_US.

void build_osv21_bits_from_ec40_post(const uint8_t ec40_post[8],
                                     uint8_t all_bits[168])
{
  uint8_t ec40_pre[8];
  reflect_nibbles(ec40_post, ec40_pre, 8);

  const uint8_t header_bytes[5] = { 0x55, 0x55, 0x55, 0x55, 0x99 };

  int idx = 0;

  // Header (40 bits)
  for (int i = 0; i < 5; ++i) {
    uint8_t b = header_bytes[i];
    for (int bit = 7; bit >= 0; --bit) {
      all_bits[idx++] = (uint8_t)((b >> bit) & 0x01);
    }
  }

  // Datos (8 bytes, LSB-first + Manchester)
  for (int bi = 0; bi < 8; ++bi) {
    uint8_t byte = ec40_pre[bi];
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

  // idx debería ser 168
}

// ---------------------------------------------------------------------------
// Envío físico: bitstream OS v2.1 -> OOK en RF_PIN
// ---------------------------------------------------------------------------

void send_bits_ook(const uint8_t *bits, int n_bits)
{
  for (int i = 0; i < n_bits; ++i) {
    if (bits[i]) {
      // 1 -> HIGH luego LOW
      digitalWrite(RF_PIN, HIGH);
      delayMicroseconds(T_UNIT_US);
      digitalWrite(RF_PIN, LOW);
      delayMicroseconds(T_UNIT_US);
    } else {
      // 0 -> LOW luego HIGH
      digitalWrite(RF_PIN, LOW);
      delayMicroseconds(T_UNIT_US);
      digitalWrite(RF_PIN, HIGH);
      delayMicroseconds(T_UNIT_US);
    }
  }
  // IMPORTANTE: Asegurar que terminamos con RF en LOW
  digitalWrite(RF_PIN, LOW);
}

// Envía una trama EC40 post-reflect por RF (2 veces, como el sensor real)
void sendOregonFrame(const uint8_t ec40_post[8])
{
  uint8_t bits[168];
  build_osv21_bits_from_ec40_post(ec40_post, bits);

  // Primera ráfaga (~164 ms con T_UNIT=488µs)
  send_bits_ook(bits, 168);

  // Gap entre ráfagas: ~8.8 ms (como el sensor real THN132N)
  // Sensor real: ~8788 µs. Compensamos overhead del código (~520µs)
  // Delay ajustado: 8300µs → gap real ≈ 8800µs
  delayMicroseconds(8300);

  // Segunda ráfaga (~164 ms)
  send_bits_ook(bits, 168);
}

// ---------------------------------------------------------------------------
// SETUP / LOOP
// ---------------------------------------------------------------------------

void setup()
{
  pinMode(RF_PIN, OUTPUT);
  digitalWrite(RF_PIN, LOW);

  // En ATtiny normalmente no usas Serial, pero lo dejo comentado:
  // Serial.begin(9600);
}

void loop()
{
  static uint32_t last_ms = 0;
  static float last_valid_temp = 20.0; // Temperatura por defecto
  uint32_t now = millis();

  if (now - last_ms >= PERIOD_SEC * 1000UL) {
    last_ms = now;

    float tempC;
    if (readDS18B20(tempC)) {
      // Si leemos correctamente, guardamos la temperatura
      tempC = roundf(tempC * 10.0f) / 10.0f;
      last_valid_temp = tempC;
    } else {
      // Si falla el DS18B20, usar la última válida
      tempC = last_valid_temp;
    }

    uint8_t ec40[8];
    build_ec40_post(tempC, g_channel, g_device_id, ec40);

    // SIEMPRE transmitir, incluso si el sensor falló
    sendOregonFrame(ec40);
  }
}
