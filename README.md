# Oregon Scientific THN132N - Universal Emulator

**Generador universal per Oregon Scientific THN132N basat en reverse engineering exhaustiu**

[![Version](https://img.shields.io/badge/version-1.0-blue)]()
[![Accuracy](https://img.shields.io/badge/accuracy-86.79%25-green)]()
[![Memory](https://img.shields.io/badge/memory-83%25_reduction-brightgreen)]()

---

## 🎯 Què és aquest projecte?

Un **generador universal** per al protocol de sensors Oregon Scientific THN132N (ID: EC40), desenvolupat mitjançant reverse engineering complet del protocol amb >20,000 proves algorísmiques.

**Resultats clau**:
- ✅ Fórmules universals per checksums R1 i M (100% precisió)
- ✅ Transformacions XOR constants per checksum P
- ✅ Reducció del 83% en memòria necessària
- ✅ 86.79% precisió global verificada (2196 trames)
- ✅ Funciona per qualsevol House ID

---

## 🚀 Inici Ràpid

### Opció 1: Arduino/ESP32 (Recomanat)

```cpp
// Fitxer: esp32/oregon_transmitter_universal.ino
#define DEVICE_ID  247    // House Code (0-255)
#define CHANNEL    1      // Canal (1-3)
#define ROLLING_CODE 0x2  // Rolling code (0,1,2,8)

// Compilar i pujar a ESP32
// Connectar DS18B20 al pin configurat
```

### Opció 2: Python

```python
from ec40_lut_suite.Docs.oregon_p_lut_complete import get_p

# Obtenir checksum P per temperatura i rolling code
p = get_p(temp_celsius=20.5, nib7=0x2)
```

---

## 📊 Descobriments Principals

### 1. Nibble 7: Rolling Code Variable

**Descobriment crític**: El que es pensava fix NO ho és!

```
Valors possibles: 0x0, 0x1, 0x2, 0x8
Comportament: Rolling code anti-replay o session ID
```

### 2. R1 i M: Fórmules Universals (100%)

```python
# Suma simple dels primers 12 nibbles
total_sum = sum(nibbles[0:12])  # Inclou nibble 7!
r1 = (total_sum & 0xFF) & 0xF
m = (total_sum & 0xFF) >> 4
```

### 3. P: Transformacions XOR Constants (100%)

```python
# Només necessitem 1 LUT base + 3 constants XOR
P(1) = P(0) XOR 0xB
P(2) = P(0) XOR 0x6
P(8) = P(2) XOR 0x7

# Reducció memòria: 2400 → 409 bytes (83%)
```

---

## 📁 Estructura del Projecte

```
├── esp32/
│   └── oregon_transmitter_universal.ino    ⭐ GENERADOR ARDUINO
│
├── ec40_lut_suite/
│   ├── ec40_capturas_merged.csv           📊 Dataset (2196 trames)
│   └── 04_universal_mp_analysis/
│       ├── Docs/ ⭐                         📚 DOCUMENTACIÓ COMPLETA
│       │   ├── README.md                      Guia tècnica
│       │   ├── TESIS_MASTER_COMPLETA.md       Treball acadèmic
│       │   ├── METODOLOGIA_DETALLADA.md       Metodologia
│       │   ├── oregon_p_lut_complete.py       LUT funcional
│       │   └── verification_table.md          Verificació
│       └── investigation_scripts/          🔬 Scripts proves (>50)
│
├── README.md                               📖 Aquesta pàgina
└── ESTRUCTURA_PROYECTO.md                  🗺️ Mapa complet
```

---

## 📖 Documentació

### Documentació Tècnica
- **[Docs/README.md](ec40_lut_suite/04_universal_mp_analysis/Docs/README.md)** - Guia tècnica completa
- **[ESTRUCTURA_PROYECTO.md](ESTRUCTURA_PROYECTO.md)** - Navegació pel projecte

### Documentació Acadèmica
- **[TESIS_MASTER_COMPLETA.md](ec40_lut_suite/04_universal_mp_analysis/Docs/TESIS_MASTER_COMPLETA.md)** - Treball estil màster (~8,500 paraules)
- **[METODOLOGIA_DETALLADA.md](ec40_lut_suite/04_universal_mp_analysis/Docs/METODOLOGIA_DETALLADA.md)** - Metodologia científica

### Verificació
- **[verification_table.md](ec40_lut_suite/04_universal_mp_analysis/Docs/verification_table.md)** - 2196 trames verificades
- **[p_algorithm_tests.md](ec40_lut_suite/04_universal_mp_analysis/Docs/p_algorithm_tests.md)** - >20,000 proves documentades

---

## 🔬 Metodologia

### Dataset
- **2196 trames** capturades
- **8 House IDs** diferents
- **Rang**: -16.0°C a +61.4°C
- **Període**: 13 dies (20 nov - 3 des 2025)

### Proves Realitzades
- **CRC variants**: 512 proves (256 polinomis × 2 inits)
- **Checksums**: Fletcher, Adler, Luhn
- **Hash functions**: Multiplicatius, XOR shift
- **Combinacions**: >19,000 variants
- **TOTAL**: >20,000 proves documentades

### Resultats
- **R1/M**: 100% precisió amb fórmula universal
- **P**: 86.79% precisió amb LUT optimitzada
- **Memòria**: Reducció 83% (2400 → 409 bytes)

---

## 🎓 Payload Complet (16 nibbles)

```
Pos  Nibble   Descripció
─────────────────────────────────────
0-3  EC40     ID del sensor
4    1-3      Channel
5-6  XX       House Code (LSN, MSN)
7    0,1,2,8  Rolling Code ⚠️ VARIABLE
8-10 XXX      Temperatura BCD
11   0/8      Flags (signe temp)
12   X        R1 (fórmula universal)
13   X        M (fórmula universal)
14   X        P (LUT + XOR transform)
15   X        Postamble
```

---

## 🛠️ Implementació

### Arduino/ESP32

**Hardware necessari**:
- ESP32 DevKit
- Sensor DS18B20 (lectura temperatura)
- Transmissor FS1000A (433 MHz)

**Pins**:
- DS18B20: GPIO 5
- FS1000A: GPIO 4

**Configuració**: Editar a `oregon_transmitter_universal.ino`
```cpp
static uint8_t CHANNEL    = 1;
static uint8_t DEVICE_ID  = 247;
static uint8_t ROLLING_CODE = 0x2;
```

### Python

**Instal·lació**:
```bash
# Copiar LUT
cp ec40_lut_suite/04_universal_mp_analysis/Docs/oregon_p_lut_complete.py .

# Usar
python3
>>> from oregon_p_lut_complete import get_p
>>> p = get_p(20.5, 0x2)
```

---

## 📈 Verificació

| Mètrica | Valor |
|---------|-------|
| Total trames testades | 2196 |
| Matches | 1906 |
| **Precisió global** | **86.79%** |
| Precisió R1 | 100% |
| Precisió M | 100% |
| Precisió P (dins rang LUT) | 90.0% |

**Verificació per House ID**:
- House 247: 87.4% (n=1534)
- House 3: 84.3% (n=472)
- House 92: 87.8% (n=90)

---

## 🤝 Contribucions

Aquest projecte és resultat de:
- 13 dies d'investigació
- >20,000 proves algorísmiques
- Reverse engineering exhaustiu
- Documentació científica completa

**Ús lliure** amb atribució. Si utilitzes aquest treball, referencia:
```
Oregon Scientific THN132N Universal Emulator
https://github.com/kerojohan/THN132N-emulator
```

---

## 📚 Referències

### Eines Utilitzades
- **rtl_433**: Decodificador SDR
- **Python 3.x**: Anàlisi de dades
- **Arduino IDE**: Implementació ESP32

### Protocol
- **Oregon Scientific v2.1**: Protocol base
- **THN132N**: Model específic (ID: EC40)
- **Freqüència**: 433.92 MHz (OOK)

---

## 📞 Contacte

**Repositori**: [GitHub - THN132N-emulator](https://github.com/kerojohan/THN132N-emulator)  
**Documentació**: Veure carpeta `Docs/`

---

## 📝 Llicència

Investigació i implementació original.

---

**Versió**: 1.0 Final (Desembre 2025)  
**Commit**: 5b5f52d  
**Autor**: Investigació amb Antigravity AI  
**Dataset**: 2196 trames verificades  
**Precisió**: 86.79%

---

⭐ **Si aquest projecte t'ha estat útil, dona-li una estrella!**
