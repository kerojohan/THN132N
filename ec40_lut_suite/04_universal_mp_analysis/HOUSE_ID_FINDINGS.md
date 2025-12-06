# Descobriments sobre P i House ID

## Investigació: Dependència de P respecte House ID

### Resultats Clau

#### 1. Transformacions XOR entre Houses

**Descobriment**: Algunes parelles de Houses tenen XOR constant!

```
House   3 XOR House 247 = 0x0  (n=35 punts) ✅
House  96 XOR House 247 = 0x0  (n=13 punts) ✅
```

**Implicació**: Houses 3, 96 i 247 **comparteixen la mateixa LUT de P**!

#### 2. Verificació Empírica

Comprovació directa de P per mateix (temperatura, nib7):

| Temp | Nib7 | P(247) | P(3) | Match |
|------|------|--------|------|-------|
| 13.5°C | 0x2 | 0xF | 0xF | ✅ |
| 14.0°C | 0x2 | 0x8 | 0x8 | ✅ |
| 18.0°C | 0x1 | 0x9 | 0x9 | ✅ |
| 23.0°C | 0x1 | 0xE | 0xE | ✅ |
| 25.5°C | 0x1 | 0xC | 0xC | ✅ |

**Resultat**: 35/35 punts comuns tenen P idèntic (100%)

#### 3. Causa dels Errors de Verificació

**NO és problema de House ID diferent**, sinó de **cobertura de LUT**!

Anàlisi d'errors House 3:
- Total errors: 52
- Tots els errors: Diferència d'1 nibble en P
- Causa: Temperatures NO presents a la LUT

Exemples:
- 18.7°C → idx=587 → **NO a LUT** ❌
- 23.0°C → idx=630 → **NO a LUT** ❌  
- 25.5°C → idx=655 → **NO a LUT** ❌

Però:
- 23.0°C amb Nib7=0x1 **SÍ funciona** quan està a captures originals ✅

### Conclusions

1. **P NO depèn del House ID** per Houses 3, 96, 247
   - Comparteixen la mateixa LUT
   - XOR = 0x0 entre ells

2. **Errors de verificació** són per:
   - Temperatures fora de rang LUT (-20°C a -16.5°C)
   - Temperatures dins rang però sense entrada específica
   - LUT té 405 punts, dataset té ~1000 temperatures úniques

3. **Solució**:
   - Ampliar LUT amb més captures
   - Interpolar valors per temperatures no capturades
   - O acceptar ~85% precisió com a límit pràctic

### Estadístiques Finals

- **Cobertura LUT**: 405 punts de temperatura
- **Rang LUT**: -16.0°C a +61.4°C
- **Temperatures dataset dins rang**: 1449/1769 (81.9%)
- **Temperatures dataset fora rang**: 320/1769 (18.1%)

### Properes Passes

1. ✅ Confirmat: Houses 3, 96, 247 usen mateixa LUT
2. ⏳ Investigar altres Houses (173, 132, etc.)
3. ⏳ Ampliar LUT amb interpolació
4. ⏳ Documentar transformacions XOR descobertes

---

**Data**: 2025-12-06  
**Script**: `investigate_house_xor.py`  
**Dataset**: 1769 trames úniques, 28 House IDs diferents
