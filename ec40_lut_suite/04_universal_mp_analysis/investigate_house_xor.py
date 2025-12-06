#!/usr/bin/env python3
"""
Investiga si hi ha transformacions XOR constants de P entre diferents House IDs.
Similar a com vam descobrir les transformacions per Nib7.
"""

import csv
from collections import defaultdict

# Carregar totes les captures
captures_by_key = defaultdict(list)

print("Carregant captures...")
with open('../ec40_all_captures_normalized.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        temp_c = float(row['temperature_C'])
        house = int(row['house'])
        payload = row['payload64_hex']
        
        if len(payload) >= 15:
            nibbles = [int(c, 16) for c in payload]
            p = nibbles[14]
            nib7 = nibbles[7]
            
            # Clau: (temperatura, nib7)
            temp_idx = int(round((temp_c + 40) * 10))
            key = (temp_idx, nib7)
            
            captures_by_key[key].append({
                'house': house,
                'p': p,
                'temp_c': temp_c
            })

print(f"Total claus (temp, nib7): {len(captures_by_key)}")

# Buscar temperatures comunes entre parelles de houses
print("\n" + "="*80)
print("ANÀLISI DE TRANSFORMACIONS XOR ENTRE HOUSE IDs")
print("="*80)

# Trobar parelles de houses amb dades comunes
house_pairs_xors = defaultdict(list)

for key, captures in captures_by_key.items():
    # Agrupar per house
    by_house = defaultdict(list)
    for c in captures:
        by_house[c['house']].append(c['p'])
    
    # Si tenim múltiples houses per aquesta (temp, nib7)
    if len(by_house) >= 2:
        houses = sorted(by_house.keys())
        
        # Provar totes les parelles
        for i in range(len(houses)):
            for j in range(i+1, len(houses)):
                h1, h2 = houses[i], houses[j]
                
                # Agafar primer valor P de cada house
                p1 = by_house[h1][0]
                p2 = by_house[h2][0]
                
                xor_val = p1 ^ p2
                
                house_pairs_xors[(h1, h2)].append({
                    'temp_idx': key[0],
                    'nib7': key[1],
                    'p1': p1,
                    'p2': p2,
                    'xor': xor_val
                })

# Analitzar quines parelles tenen XOR constant
print(f"\nParelles de Houses trobades: {len(house_pairs_xors)}")
print("\nParelles amb XOR CONSTANT (>= 5 punts):\n")

constant_pairs = []

for (h1, h2), xors_data in sorted(house_pairs_xors.items()):
    if len(xors_data) >= 5:  # Mínim 5 punts per considerar-ho
        xor_values = [d['xor'] for d in xors_data]
        
        # Comprovar si tots els XORs són iguals
        if len(set(xor_values)) == 1:
            xor_constant = xor_values[0]
            constant_pairs.append((h1, h2, xor_constant, len(xors_data)))
            
            print(f"House {h1:3} XOR House {h2:3} = 0x{xor_constant:X} (n={len(xors_data)} punts) ✅")
            
            # Mostrar alguns exemples
            print(f"  Exemples:")
            for example in xors_data[:3]:
                temp_c = (example['temp_idx'] - 400) / 10
                print(f"    Temp={temp_c:5.1f}°C, Nib7=0x{example['nib7']:X}: P({h1})=0x{example['p1']:X}, P({h2})=0x{example['p2']:X}, XOR=0x{example['xor']:X}")

print(f"\n{'='*80}")
print(f"RESUM: {len(constant_pairs)} parelles amb XOR constant trobades")
print(f"{'='*80}")

# Analitzar si podem construir una xarxa de transformacions
if constant_pairs:
    print("\n" + "="*80)
    print("XARXA DE TRANSFORMACIONS")
    print("="*80)
    
    # Crear grafo de transformacions
    transformations = {}
    for h1, h2, xor_val, count in constant_pairs:
        if h1 not in transformations:
            transformations[h1] = {}
        if h2 not in transformations:
            transformations[h2] = {}
        
        transformations[h1][h2] = xor_val
        transformations[h2][h1] = xor_val  # Simètric
    
    # Mostrar xarxa
    print("\nHouses connectades:")
    for house in sorted(transformations.keys()):
        connections = transformations[house]
        if connections:
            conn_str = ", ".join([f"{h}(XOR 0x{x:X})" for h, x in sorted(connections.items())])
            print(f"  House {house:3}: {conn_str}")
    
    # Intentar trobar un House "base" ben connectat
    print("\nConnectivitat:")
    for house in sorted(transformations.keys()):
        print(f"  House {house:3}: {len(transformations[house])} connexions")

# Guardar resultats
output_file = 'house_xor_transformations.txt'
with open(output_file, 'w') as f:
    f.write("TRANSFORMACIONS XOR ENTRE HOUSE IDs\n")
    f.write("="*80 + "\n\n")
    
    for h1, h2, xor_val, count in constant_pairs:
        f.write(f"House {h1} XOR House {h2} = 0x{xor_val:X} (n={count})\n")

print(f"\n✅ Resultats guardats a: {output_file}")
