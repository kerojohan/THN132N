#!/usr/bin/env python3
"""
Normalitza TOTS els CSVs de captures a un format estàndard.
Format estàndard: timestamp,house,channel,temperature_C,payload64_hex
"""

import csv
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent

# Fitxers d'entrada i sortida
CSV_SOURCES = {
    'ec40_capturas_merged.csv': {
        'path': BASE_DIR / 'ec40_capturas_merged.csv',
        'columns': {
            'timestamp': 'timestamp',
            'house': 'house',
            'channel': 'channel',
            'temperature_C': 'temperature_C',
            'payload64_hex': 'payload64_hex'
        }
    },
    'ec40_live.csv': {
        'path': BASE_DIR / 'ec40_live.csv',
        'columns': None  # Detectar automàticament
    },
    'ec40_live_1.csv': {
        'path': BASE_DIR / 'ec40_live_1.csv',
        'columns': None  # Detectar automàticament
    },
    'tramas_thn132n.csv': {
        'path': BASE_DIR / '01_data_capture' / 'tramas_thn132n.csv',
        'columns': None  # Detectar automàticament
    }
}

OUTPUT_FILE = BASE_DIR / 'ec40_all_captures_normalized.csv'

def detect_column_mapping(header):
    """Detecta el mapatge de columnes segons les capçaleres."""
    
    # Possibles noms per cada camp
    mappings = {
        'timestamp': ['timestamp', 'time', 'datetime', 'date'],  # Optional
        'house': ['house', 'house_id', 'house_code', 'device_id', 'id'],
        'channel': ['channel', 'ch', 'canal'],
        'temperature_C': ['temperatura', 'temperature_C', 'temperature', 'temp', 'temp_c'],
        'payload64_hex': ['ec40_hex', 'payload64_hex', 'payload', 'data', 'frame', 'hex', 'raw64']
    }
    
    result = {}
    header_lower = [h.lower().strip() for h in header]
    
    print(f"   Capçaleres trobades: {header}")
    
    for std_name, possible_names in mappings.items():
        for possible in possible_names:
            for i, col in enumerate(header_lower):
                if possible.lower() == col or possible.lower() in col:
                    result[std_name] = header[i]
                    print(f"   {std_name} -> {header[i]}")
                    break
            if std_name in result:
                break
    
    # Timestamp és opcional
    required_fields = ['house', 'channel', 'temperature_C', 'payload64_hex']
    missing = [f for f in required_fields if f not in result]
    
    if missing:
        print(f"   ⚠️  Camps obligatoris que falten: {missing}")
        return None
    
    print(f"   ✅ Mapatge detectat correctament ({len(result)} camps)")
    return result

def normalize_csv(source_file, column_mapping):
    """Normalitza un CSV al format estàndard."""
    
    if not source_file.exists():
        return []
    
    normalized_rows = []
    
    try:
        with open(source_file, 'r') as f:
            # Cas especial: ec40_live_1.csv no té header
            if source_file.name == 'ec40_live_1.csv':
                # Format: timestamp,raw168,raw64,temp,channel,house,battery,sensor_type_hex,rolling_code_hex,checksum_hex
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 7:
                        try:
                            normalized_rows.append({
                                'timestamp': parts[0],
                                'house': parts[5],
                                'channel': parts[4],
                                'temperature_C': parts[3],
                                'payload64_hex': parts[2]
                            })
                        except:
                            continue
                return normalized_rows
            
            reader = csv.DictReader(f)
            
            # Si no tenim mapping, detectar-lo
            if column_mapping is None:
                column_mapping = detect_column_mapping(reader.fieldnames)
                if column_mapping is None:
                    return []
            
            for row in reader:
                try:
                    # Cas especial: ec40_live.csv usa 'raw64' per payload
                    payload_key = column_mapping.get('payload64_hex', '')
                    payload = row.get(payload_key, '')
                    
                    # Si detectem sensor_type_hex, realment volem raw64
                    if 'sensor_type_hex' in payload_key and 'raw64' in row:
                        payload = row['raw64']
                    
                    # Extreure dades segons mapping
                    normalized_row = {
                        'timestamp': row.get(column_mapping.get('timestamp', ''), datetime.now().isoformat()),
                        'house': row.get(column_mapping.get('house', ''), '0'),
                        'channel': row.get(column_mapping.get('channel', ''), '1'),
                        'temperature_C': row.get(column_mapping.get('temperature_C', ''), '0.0'),
                        'payload64_hex': payload
                    }
                    
                    # Netejar timestamp si està buit
                    if not normalized_row['timestamp'] or normalized_row['timestamp'] == '':
                        normalized_row['timestamp'] = datetime.now().isoformat()
                    
                    # Validar que tenim dades mínimes
                    if normalized_row['payload64_hex'] and len(normalized_row['payload64_hex']) >= 15:
                        normalized_rows.append(normalized_row)
                        
                except (ValueError, KeyError):
                    continue
    
    except Exception as e:
        print(f"❌ Error processant {source_file.name}: {e}")
    
    return normalized_rows

def merge_and_normalize_all():
    """Fusiona i normalitza tots els CSVs."""
    
    print("=" * 60)
    print("NORMALITZACIÓ DE TOTS ELS CSVs")
    print("=" * 60)
    
    all_rows = []
    stats = {}
    
    for name, config in CSV_SOURCES.items():
        source_path = config['path']
        column_map = config['columns']
        
        print(f"\n📊 Processant {name}...")
        
        if not source_path.exists():
            print(f"   ⚠️  No existeix")
            stats[name] = 0
            continue
        
        rows = normalize_csv(source_path, column_map)
        stats[name] = len(rows)
        all_rows.extend(rows)
        
        print(f"   ✅ {len(rows)} trames normalitzades")
    
    # Eliminar duplicats (mateix payload)
    seen_payloads = set()
    unique_rows = []
    
    for row in all_rows:
        if row['payload64_hex'] not in seen_payloads:
            seen_payloads.add(row['payload64_hex'])
            unique_rows.append(row)
    
    print(f"\n{'='*60}")
    print(f"RESUM")
    print(f"{'='*60}")
    print(f"Total trames carregades: {len(all_rows)}")
    print(f"Duplicats eliminats: {len(all_rows) - len(unique_rows)}")
    print(f"Trames úniques: {len(unique_rows)}")
    print(f"\nPer font:")
    for name, count in stats.items():
        print(f"  - {name}: {count}")
    
    # Guardar CSV normalitzat
    if unique_rows:
        with open(OUTPUT_FILE, 'w', newline='') as f:
            fieldnames = ['timestamp', 'house', 'channel', 'temperature_C', 'payload64_hex']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            
            writer.writeheader()
            writer.writerows(unique_rows)
        
        print(f"\n✅ Fitxer normalitzat creat:")
        print(f"   {OUTPUT_FILE}")
        print(f"   {len(unique_rows)} trames úniques")
    else:
        print("\n❌ No s'han trobat trames vàlides")
    
    return len(unique_rows)

if __name__ == "__main__":
    count = merge_and_normalize_all()
    print(f"\n{'='*60}")
    print(f"Procés completat: {count} trames normalitzades")
    print(f"{'='*60}")
