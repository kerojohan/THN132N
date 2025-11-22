// Emisión bit a bit de una trama capturada THN132N real, repetida 2 veces como exige el protocolo V2.1
// Trama: 555555559995a5a6aa6a5655aa6a56aaaa655a96a5 (Temp 7.1°C)
// Codificación Manchester: cada bit hex → 2 semibits alternando HIGH/LOW

#include "driver/rmt.h"
#include "driver/gpio.h"

#define TX_GPIO GPIO_NUM_4
#define T_UNIT 488  // microsegundos por semibit (del sensor original promedio 976/2)

void hex_string_to_bits(const char* hex, bool* bits, int& bitlen) {
  bitlen = 0;
  while (*hex && *(hex + 1)) {
    char byte_str[3] = {hex[0], hex[1], 0};
    uint8_t byte = strtol(byte_str, nullptr, 16);
    for (int i = 7; i >= 0; i--) {
      bits[bitlen++] = (byte >> i) & 0x01;
    }
    hex += 2;
  }
}

void build_raw_ook_frame(const char* hexstr, rmt_item32_t* items, int& length) {
  bool bits[512];
  int bitlen = 0;
  hex_string_to_bits(hexstr, bits, bitlen);

  int idx = 0;
  for (int i = 0; i < bitlen; i++) {
    if (bits[i]) {
      // Bit 1: HIGH + LOW
      items[idx].level0 = 1;
      items[idx].duration0 = T_UNIT;
      items[idx].level1 = 0;
      items[idx].duration1 = T_UNIT;
    } else {
      // Bit 0: LOW + HIGH
      items[idx].level0 = 0;
      items[idx].duration0 = T_UNIT;
      items[idx].level1 = 1;
      items[idx].duration1 = T_UNIT;
    }
    idx++;
  }
  length = idx;
}

void setup_rmt() {
  rmt_config_t config = RMT_DEFAULT_CONFIG_TX(TX_GPIO, RMT_CHANNEL_0);
  config.clk_div = 80; // 1us por tick
  ESP_ERROR_CHECK(rmt_config(&config));
  ESP_ERROR_CHECK(rmt_driver_install(config.channel, 0, 0));
}

// Array de tramas con diferentes temperaturas
const char* TEMP_FRAMES[] = {
  "555555559995A5A6AA6A56559A6AA66AAA655A5566",  // 14.1°C
  "555555559995A5A6AA6A56559A9AA66AAA955A9699",  // 14.2°C
  "555555559995A5A6AA6A56559A5AA66AAA555A6A55",  // 14.3°C
  "555555559995A5A6AA6A56559AA6A66AAAAAA65A66",  // 14.4°C
  "555555559995A5A6AA6A56559A66A66AAA6AA6A6AA",  // 14.5°C
  "555555559995A5A6AA6A56559A96A66AAA9AA66555",  // 14.6°C
  "555555559995A5A6AA6A56559A56A66AAA5AA69999",  // 14.7°C
  "555555559995A5A6AA6A56559AA9A66AAAA6A69559",  // 14.8°C
  "555555559995A5A6AA6A56559A69A66AAA66A66995"   // 14.9°C
};

const int NUM_FRAMES = 9;
int current_frame_index = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("Oregon Scientific THN132N Transmitter");
  Serial.println("Using RMT for precise timing");
  Serial.println("Cycling through temperatures 14.1°C - 14.9°C");
  setup_rmt();
}

void loop() {
  rmt_item32_t items[512];
  int len = 0;
  
  // Seleccionar trama actual del array
  const char* hexframe = TEMP_FRAMES[current_frame_index];
  build_raw_ook_frame(hexframe, items, len);

  Serial.print("Transmitting packet (2x) - Temp: 14.");
  Serial.print(current_frame_index + 1);
  Serial.println("°C");
  
  // Emitir dos veces con pausa de ~9.8 ms entre ambas (del sensor original)
  rmt_write_items(RMT_CHANNEL_0, items, len, true);
  delayMicroseconds(9800);
  rmt_write_items(RMT_CHANNEL_0, items, len, true);

  // Incrementar índice para siguiente transmisión (ciclar al inicio si llega al final)
  current_frame_index = (current_frame_index + 1) % NUM_FRAMES;

  Serial.println("Waiting 30s...");
  delay(30000);  // repetir cada 30 s como sensor real
}