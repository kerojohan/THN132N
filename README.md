# THN132N - Oregon Scientific Emulator

Proyecto de emulación del sensor de temperatura Oregon Scientific THN132N (código EC40) para microcontroladores. Permite transmitir datos de temperatura compatibles con receptores Oregon Scientific en la banda de 433 MHz.

## 📚 Documentación

### 📂 `/Docs`

Contiene documentación técnica obtenida mediante ingeniería inversa:

- **`Oregon_THN132N_BAR206.pdf`**: Documentación del sensor Oregon Scientific THN132N y protocolo BAR206 extraída mediante reverse engineering. Incluye:
  - Análisis del protocolo de comunicación RF 433 MHz
  - Estructura de la trama Oregon Scientific v2.1
  - Decodificación del formato EC40
  - Tablas P[d] y M[e] para el cálculo del rolling code R12
  - Codificación Manchester y timing OOK

Esta documentación fue creada mediante el análisis de tramas reales capturadas con rtl_433 y sirve como referencia para el desarrollo del emulador.

## 📁 Estructura del Proyecto

```
Antigravity/
├── esp32/                        # Código para ESP32
│   ├── oregon_transmitter.ino    # Transmisor Oregon THN132N con RMT
│   └── 184funcionaTX.ino         # Test básico de transmisión
├── attiny/                       # Código para ATtiny85
│   └── attiny85THN132N.ino       # Emulador Oregon con sensor DS18B20
├── Docs/                         # Documentación técnica
│   └── Oregon_THN132N_BAR206.pdf # Análisis de protocolo (reverse engineering)
├── gen_tramas_thn132n.py         # Generador de tramas en Python
└── tramas_thn132n.csv            # Tramas pre-calculadas
```

---

## 💾 Código para Microcontroladores

### 🔧 ATtiny85: `attiny/attiny85THN132N.ino`
**Plataforma:** ATtiny85 (Digispark Kickstarter)  
**Descripción:** Firmware completo para emular un sensor Oregon THN132N usando un ATtiny85.

**Características:**
- Lee temperatura real desde un sensor DS18B20 (OneWire)
- Construye payload EC40 post-reflect con tablas P y M validadas
- Genera trama RAW Oregon Scientific v2.1 con codificación Manchester
- Transmite por RF 433 MHz mediante módulo FS1000A (OOK)
- LED indicador que parpadea durante cada transmisión
- Periodo de transmisión: cada 39 segundos

**Configuración de Pines:**
- `PB0 (Pin 0)`: FS1000A DATA (transmisor RF 433 MHz)
- `PB1 (Pin 1)`: LED indicador de transmisión
- `PB2 (Pin 2)`: DS18B20 DQ (sensor de temperatura OneWire)

**Conexiones Hardware:**

*DS18B20:*
- VCC → 5V
- GND → GND
- DQ → PB2 + resistencia pull-up 4.7kΩ a VCC

*FS1000A:*
- VCC → 5V
- GND → GND
- DATA → PB0

*LED:*
- Ánodo (+) → PB1 (con resistencia 220-330Ω)
- Cátodo (-) → GND

**Parámetros Configurables:**
```cpp
const uint32_t PERIOD_SEC = 39;    // Segundos entre transmisiones
uint8_t g_channel         = 2;     // Canal 1-3
uint8_t g_device_id       = 34;    // House Code (0-255)
const uint16_t T_UNIT_US  = 500;   // Microsegundos por semibit
```

**Compilación:**
- Requiere ATTinyCore para Arduino IDE
- Librería: OneWire (para DS18B20)
- Board: Digispark (Default - 16.5 MHz)

---

### 🖥️ ESP32: `esp32/oregon_transmitter.ino`
**Plataforma:** ESP32  
**Descripción:** Generador completo de tramas Oregon THN132N para ESP32 con transmisión mediante RMT.

**Características:**
- Port directo del script Python `gen_tramas_thn132n.py`
- Implementa tablas P y M, cálculo R12, checksum Oregon v2.1
- Usa hardware RMT del ESP32 para timing preciso (488 µs/semibit)
- Genera payload EC40 post-reflect y trama RAW hexadecimal
- Transmisión por módulo FS1000A conectado a GPIO4
- Salida por Serial para debugging

**Configuración:**
```cpp
#define TX_GPIO   GPIO_NUM_4     // Pin RF del ESP32
#define T_UNIT    488            // µs por semibit (≈976 µs/bit)
static float   TEMP_C     = 10.7f;
static uint8_t CHANNEL    = 2;    // 1-3
static uint8_t DEVICE_ID  = 34;   // 0-255
```

**Hardware:**
- ESP32 (cualquier modelo)
- FS1000A conectado a GPIO4
- Alimentación 5V para módulo RF

**Uso:**
- Periodo de transmisión: cada 30 segundos
- Monitor Serial a 115200 bps muestra EC40 y RAW hex generados
- Modifica `TEMP_C`, `CHANNEL` y `DEVICE_ID` según necesites

---

### 🐍 `gen_tramas_thn132n.py`
**Plataforma:** Python 3  
**Descripción:** Script para generar tramas Oregon THN132N en formato CSV para cualquier rango de temperaturas.

**Características:**
- Implementa tablas P[d] y M[e] validadas para calcular R12
- Codificación Manchester (0→10, 1→01)
- Genera payload EC40 (post-reflect) y trama RAW hexadecimal
- Checksum Oregon Scientific v2.1
- Exporta a CSV con todos los parámetros configurables

**Uso:**
```bash
python3 gen_tramas_thn132n.py --help

# Ejemplo: generar tramas de -20°C a 50°C, paso 0.5°C
python3 gen_tramas_thn132n.py \
  --device-id 247 \
  --channel 1 \
  --temp-min -20.0 \
  --temp-max 50.0 \
  --temp-step 0.5 \
  --output tramas_thn132n.csv
```

**Parámetros:**
- `--device-id`: House Code (0-255, default: 247)
- `--channel`: Canal del sensor (1, 2 o 3, default: 1)
- `--temp-min`: Temperatura mínima en °C (default: -20.0)
- `--temp-max`: Temperatura máxima en °C (default: 50.0)
- `--temp-step`: Incremento de temperatura (default: 0.5)
- `--output`: Archivo CSV de salida (default: tramas_thn132n.csv)

**Salida CSV:**
- `temperatura`: Temperatura en °C
- `device_id`: ID del dispositivo
- `channel`: Canal configurado
- `ec40_hex`: Payload EC40 post-reflect (16 caracteres hex)
- `raw_hex`: Trama RAW completa con Manchester (42 caracteres hex)

---

### 📊 `tramas_thn132n.csv`
**Descripción:** Archivo CSV generado por `gen_tramas_thn132n.py` con tramas pre-calculadas.

**Formato:**
```csv
temperatura,device_id,channel,ec40_hex,raw_hex
-20.0,247,1,EC407F7002148BCA,555555559955AA9AA69AA6A5A5AAA9A65A55956A6A
10.0,247,1,EC407F7000010065,555555559955AA9AA69AA6A5A599A96A5A96956A95
...
```

**Uso:**
- Útil para validación y testing
- Permite pre-cargar tramas en memoria de sistemas embebidos
- Compatible con rtl_433 para verificación de formato

---

## 🔬 Protocolo Oregon Scientific v2.1

### Estructura de la trama THN132N (EC40):

**Payload EC40 (8 bytes post-reflect):**
```
[0] = 0xEC          - Tipo de sensor (THN132N)
[1] = 0x40          - Subtipo
[2] = Canal + ID    - Canal (nibble alto) + Device ID (nibble bajo)
[3] = ID + R12_H    - Device ID (nibble alto) + R12 bits 11-8
[4] = Temp BCD      - d0 (decimales) + u (unidades)
[5] = Temp BCD      - d1 (decenas) + signo
[6] = Checksum      - Checksum Oregon v2.1
[7] = R12_L         - R12 bits 7-0
```

**Trama RAW completa (42 hex chars = 168 bits):**
- Header: `5555555599` (40 bits de preámbulo + sync)
- Datos: 8 bytes EC40 pre-reflect codificados en Manchester (128 bits)

### Cálculo R12 (Rolling Code):
```
R12 = P[d] XOR M[e]  (12 bits)

donde:
  e = parte entera de la temperatura (con signo)
  d = primer decimal (0-9)
  P[d] = tabla P de 10 valores
  M[e] = tabla M de 71 valores (rango -16 a 54°C)
```

### Codificación Manchester:
- Bit 0 → `10`
- Bit 1 → `01`
- LSB-first (bit menos significativo primero)

---

## 🛠️ Notas de Implementación

### Tablas P y M
Las tablas P[d] y M[e] fueron extraídas mediante reverse engineering de tramas reales capturadas con rtl_433. Estas tablas son idénticas en los tres archivos para garantizar compatibilidad.

**Caso especial 10.0°C:**  
M[10] = 0x100 (corregido del valor original 0x14F)

### Timing OOK (On-Off Keying)
- **Semibit:** ~488-500 µs
- **Bit completo:** ~976-1000 µs
- **Pausa entre tramas:** ~10 ms

### Deep Sleep (Futuro)
El código ATtiny85 puede ser extendido con:
- Watchdog Timer para sleep profundo
- Reducción de consumo < 1 µA en standby
- Despertar cada 39s para leer sensor y transmitir

---

## 📡 Compatibilidad

**Receptores compatibles:**
- Oregon Scientific oficiales (¡obviamente!)
- rtl_433 con RTL-SDR
- RFLink
- Otros receptores 433 MHz con decodificador Oregon v2.1

**Verificación con rtl_433:**
```bash
rtl_433 -f 433920000 -R 75 -F json
```

Deberías ver:
```json
{
  "model": "Oregon-THN132N",
  "id": 34,
  "channel": 2,
  "temperature_C": 21.5,
  ...
}
```

---

## 📝 Licencia

Proyecto de código abierto para propósitos educativos y de experimentación.

---

## 👨‍💻 Autor

Joan - Oregon Scientific Reverse Engineering  
Basado en análisis de tramas reales con rtl_433

---

## 🔗 Referencias

- [rtl_433 - Oregon Scientific decoder](https://github.com/merbanan/rtl_433)
- [ATTinyCore](https://github.com/SpenceKonde/ATTinyCore)
- [ESP32 RMT Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/peripherals/rmt.html)
