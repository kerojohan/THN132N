// Emisión bit a bit de una trama capturada THN132N real, repetida 2 veces como exige el protocolo V2.1
// Trama: 555555559995a5a6aa9aaa9aaaa6a96aaa559aa969
// Codificación ya es Manchester capturada, se emite como OOK crudo

#include "driver/rmt.h"
#include "driver/gpio.h"

#define TX_GPIO GPIO_NUM_4
#define T_UNIT 488  // microsegundos por semibit

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
      items[idx].level0 = 1;
      items[idx].duration0 = T_UNIT;
      items[idx].level1 = 0;
      items[idx].duration1 = T_UNIT;
    } else {
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

void setup() {
  setup_rmt();
}

void loop() {
  rmt_item32_t items[512];
  int len = 0;
  const char* hexframe = "555555559995a5a6aa9aaa9aaaa6a96aaa559aa969";
  build_raw_ook_frame(hexframe, items, len);

  // Emitir dos veces con pausa de ~4 ms entre ambas
  rmt_write_items(RMT_CHANNEL_0, items, len, true);
  delayMicroseconds(4096);
  rmt_write_items(RMT_CHANNEL_0, items, len, true);

  delay(30000);  // repetir cada 30 s como sensor real
}
