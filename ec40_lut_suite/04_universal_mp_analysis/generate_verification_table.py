#!/usr/bin/env python3
"""
Genera un document de verificació detallat comparant captures vs generador.
PROCESСА TOTS els CSVs de captures de la carpeta ec40_lut_suite.
"""

import csv
import sys
from pathlib import Path
import glob

# Afegir el path de Docs per importar la LUT
sys.path.insert(0, str(Path(__file__).parent / "Docs"))

from oregon_p_lut_complete import get_p

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = Path(__file__).parent / "Docs"

# TOTS els CSVs de captures (exclou verification_table.csv i env/)
CSV_FILES = [
    BASE_DIR / "ec40_capturas_merged.csv",
    BASE_DIR / "ec40_capturas_merged_clean.csv",
    BASE_DIR / "ec40_live.csv",
    BASE_DIR / "ec40_live_1.csv",
    BASE_DIR / "01_data_capture" / "tramas_thn132n.csv",
]

def generate_frame(house_id, channel, temp_celsius, rolling_code=0x2):
    """Genera trama completa de 15 nibbles."""
    nibbles = []
    
    # 1. ID (EC40)
    nibbles.extend([0xE, 0xC, 0x4, 0x0])
    
    # 2. Channel
    nibbles.append(channel & 0xF)
    
    # 3. House
    nibbles.append(house_id & 0xF)
    nibbles.append((house_id >> 4) & 0xF)
    
    # 4. Rolling code
    nibbles.append(rolling_code & 0xF)
    
    # 5. Temperatura BCD
    temp_abs = abs(temp_celsius)
    temp_int = int(round(temp_abs * 10))
    nibbles.append(temp_int % 10)
    nibbles.append((temp_int // 10) % 10)
    nibbles.append((temp_int // 100) % 10)
    
    # 6. Flags
    flags = 0x0 if temp_celsius >= 0 else 0x8
    nibbles.append(flags)
    
    # 7. R1, M (checksum senzill)
    total_sum = sum(nibbles)
    checksum_byte = total_sum & 0xFF
    r1 = checksum_byte & 0xF
    m = (checksum_byte >> 4) & 0xF
    nibbles.extend([r1, m])
    
    # 8. P (LUT + XOR transform)
    p = get_p(temp_celsius, rolling_code)
    nibbles.append(p)
    
    return nibbles

def load_all_captures():
    """Carrega TOTES les captures de tots els CSVs."""
    
    all_captures = []
    csv_stats = {}
    
    for csv_file in CSV_FILES:
        if not csv_file.exists():
            print(f"⚠️  Saltant {csv_file.name} (no existeix)")
            continue
        
        count = 0
        print(f"📊 Processant {csv_file.name}...", end=" ")
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        # Intentar llegir amb diferents formats de columnes
                        house = int(row.get('house', row.get('House', 0)))
                        channel = int(row.get('channel', row.get('Channel', 1)))
                        temp_c = float(row.get('temperature_C', row.get('Temperature', 0)))
                        timestamp = row.get('timestamp', row.get('Timestamp', ''))
                        captured_hex = row.get('payload64_hex', row.get('Payload', ''))
                        
                        if not captured_hex or len(captured_hex) < 15:
                            continue
                        
                        all_captures.append({
                            'source': csv_file.name,
                            'timestamp': timestamp,
                            'house': house,
                            'channel': channel,
                            'temp': temp_c,
                            'payload': captured_hex
                        })
                        count += 1
                        
                    except (ValueError, KeyError):
                        continue
            
            csv_stats[csv_file.name] = count
            print(f"{count} trames")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n📊 Total captures carregades: {len(all_captures)}")
    for name, count in csv_stats.items():
        print(f"   - {name}: {count}")
    
    return all_captures

def create_verification_table():
    """Crea taula de verificació completa."""
    
    print("=" * 60)
    print("VERIFICACIÓ AMB TOTES LES CAPTURES")
    print("=" * 60)
    
    # Carregar totes les captures
    all_captures = load_all_captures()
    
    if not all_captures:
        print("❌ No s'han trobat captures!")
        return []
    
    print(f"\nGenerant trames per {len(all_captures)} captures...")
    
    results = []
    total = 0
    matches = 0
    
    for capture in all_captures:
        try:
            house = capture['house']
            channel = capture['channel']
            temp_c = capture['temp']
            timestamp = capture['timestamp']
            captured_hex = capture['payload']
            
            # Nibbles capturats
            captured_nibbles = [int(c, 16) for c in captured_hex]
            nib7 = captured_nibbles[7] if len(captured_nibbles) > 7 else 0x2
            
            # Generar trama
            generated_nibbles = generate_frame(house, channel, temp_c, nib7)
            
            # Comparar (primers 15 nibbles)
            captured_15 = captured_nibbles[:15]
            match = (generated_nibbles == captured_15)
            
            total += 1
            if match:
                matches += 1
            
            # Identificar diferències nibble a nibble
            diffs = []
            for i in range(min(15, len(captured_15))):
                if i < len(generated_nibbles) and captured_15[i] != generated_nibbles[i]:
                    diffs.append({
                        'pos': i,
                        'captured': captured_15[i],
                        'generated': generated_nibbles[i]
                    })
            
            results.append({
                'source': capture['source'],
                'timestamp': timestamp,
                'house': house,
                'channel': channel,
                'temp': temp_c,
                'nib7': nib7,
                'captured': ''.join(f'{n:x}' for n in captured_15),
                'generated': ''.join(f'{n:x}' for n in generated_nibbles),
                'match': match,
                'diffs': diffs
            })
            
        except (ValueError, KeyError, IndexError) as e:
            continue
    
    print(f"\n{'='*60}")
    print(f"RESULTATS GENERALS")
    print(f"{'='*60}")
    print(f"Total trames processades: {total}")
    print(f"Matches: {matches} ({matches/total*100:.2f}%)")
    print(f"Errors: {total-matches} ({(total-matches)/total*100:.2f}%)")
    print(f"{'='*60}\n")
    
    return results


def generate_markdown_table(results, output_file):
    """Genera taula en format Markdown."""
    
    with open(output_file, 'w') as f:
        f.write("# Taula de Verificació - Captures vs Generador\n\n")
        f.write(f"**Total trames**: {len(results)}\n")
        
        matches = sum(1 for r in results if r['match'])
        f.write(f"**Matches**: {matches} ({matches/len(results)*100:.2f}%)\n")
        f.write(f"**Errors**: {len(results)-matches}\n\n")
        
        # Estadístiques per font CSV
        from collections import defaultdict, Counter
        
        by_source = defaultdict(list)
        for r in results:
            by_source[r['source']].append(r['match'])
        
        f.write("## Estadístiques per Font de Dades\n\n")
        f.write("| Font CSV | Total | Matches | Errors | Precisió |\n")
        f.write("|----------|-------|---------|--------|----------|\n")
        
        for source in sorted(by_source.keys()):
            total_s = len(by_source[source])
            matches_s = sum(by_source[source])
            errors_s = total_s - matches_s
            pct = matches_s / total_s * 100
            
            status = "✅" if pct > 99 else "⚠️" if pct > 90 else "❌"
            f.write(f"| {source} | {total_s} | {matches_s} | {errors_s} | {pct:.1f}% {status} |\n")
        
        # Estadístiques per House
        by_house = defaultdict(list)
        for r in results:
            by_house[r['house']].append(r['match'])
        
        f.write("\n## Estadístiques per House\n\n")
        f.write("| House | Total | Matches | Errors | Precisió |\n")
        f.write("|-------|-------|---------|--------|----------|\n")
        
        for house in sorted(by_house.keys()):
            total_h = len(by_house[house])
            matches_h = sum(by_house[house])
            errors_h = total_h - matches_h
            pct = matches_h / total_h * 100
            
            status = "✅" if pct > 99 else "⚠️" if pct > 90 else "❌"
            f.write(f"| {house} | {total_h} | {matches_h} | {errors_h} | {pct:.1f}% {status} |\n")
        
        # Estadístiques per Nib7
        by_nib7 = defaultdict(list)
        for r in results:
            by_nib7[r['nib7']].append(r['match'])
        
        f.write("\n## Estadístiques per Rolling Code (Nib7)\n\n")
        f.write("| Nib7 | Total | Matches | Errors | Precisió |\n")
        f.write("|------|-------|---------|--------|----------|\n")
        
        for nib7 in sorted(by_nib7.keys()):
            total_n = len(by_nib7[nib7])
            matches_n = sum(by_nib7[nib7])
            errors_n = total_n - matches_n
            pct = matches_n / total_n * 100
            
            status = "✅" if pct > 99 else "⚠️" if pct > 90 else "❌"
            f.write(f"| 0x{nib7:X} | {total_n} | {matches_n} | {errors_n} | {pct:.1f}% {status} |\n")
        
        # Anàlisi d'errors
        errors_only = [r for r in results if not r['match']]
        
        if errors_only:
            f.write(f"\n## Anàlisi d'Errors ({len(errors_only)} total)\n\n")
            
            # Errors per posició
            error_positions = Counter()
            for r in errors_only:
                for diff in r['diffs']:
                    error_positions[diff['pos']] += 1
            
            f.write("### Errors per Posició de Nibble\n\n")
            f.write("| Posició | Descripció | Errors | % |\n")
            f.write("|---------|------------|--------|---|\n")
            
            position_names = {
                0: "ID (E)", 1: "ID (C)", 2: "ID (4)", 3: "ID (0)",
                4: "Channel", 5: "House LSN", 6: "House MSN",
                7: "Rolling Code", 8: "Temp LSN", 9: "Temp Mid",
                10: "Temp MSN", 11: "Flags", 12: "R1", 13: "M", 14: "P"
            }
            
            for pos in sorted(error_positions.keys()):
                count = error_positions[pos]
                pct = count / len(errors_only) * 100
                name = position_names.get(pos, f"Pos {pos}")
                f.write(f"| {pos} | {name} | {count} | {pct:.1f}% |\n")
            
            # Mostrar primers 10 errors
            f.write("\n### Primers 10 Errors Detallats\n\n")
            f.write("| # | Font | House | Ch | Temp | Nib7 | Capturada | Generada | Diferències |\n")
            f.write("|---|------|-------|----|------|------|-----------|----------|-------------||\n")
            
            for i, r in enumerate(errors_only[:10], 1):
                diffs_str = ", ".join([f"pos{d['pos']}:{d['captured']:X}→{d['generated']:X}" for d in r['diffs']])
                f.write(f"| {i} | {r['source']} | {r['house']} | {r['channel']} | {r['temp']:.1f}°C | 0x{r['nib7']:X} | `{r['captured']}` | `{r['generated']}` | {diffs_str} |\n")
        
        f.write("\n---\n\n")
        f.write("**Generador**: `generate_verification_table.py` amb `oregon_p_lut_complete.py`\n")
        if results:
            f.write(f"**Data**: {results[0]['timestamp'].split()[0] if results[0]['timestamp'] else 'N/A'}")
            f.write(f" - {results[-1]['timestamp'].split()[0] if results[-1]['timestamp'] else 'N/A'}\n")
        f.write(f"**Fonts**: {len(by_source)} fitxers CSV processats\n")

    """Genera taula en format Markdown."""
    
    with open(output_file, 'w') as f:
        f.write("# Taula de Verificació - Captures vs Generador\n\n")
        f.write(f"**Total trames**: {len(results)}\n")
        
        matches = sum(1 for r in results if r['match'])
        f.write(f"**Matches**: {matches} ({matches/len(results)*100:.2f}%)\n")
        f.write(f"**Errors**: {len(results)-matches}\n\n")
        
        # Estadístiques per House
        from collections import defaultdict, Counter
        
        by_house = defaultdict(list)
        for r in results:
            by_house[r['house']].append(r['match'])
        
        f.write("## Estadístiques per House\n\n")
        f.write("| House | Total | Matches | Errors | Precisió |\n")
        f.write("|-------|-------|---------|--------|----------|\n")
        
        for house in sorted(by_house.keys()):
            total_h = len(by_house[house])
            matches_h = sum(by_house[house])
            errors_h = total_h - matches_h
            pct = matches_h / total_h * 100
            
            status = "✅" if pct > 99 else "⚠️" if pct > 90 else "❌"
            f.write(f"| {house} | {total_h} | {matches_h} | {errors_h} | {pct:.1f}% {status} |\n")
        
        # Estadístiques per Nib7
        by_nib7 = defaultdict(list)
        for r in results:
            by_nib7[r['nib7']].append(r['match'])
        
        f.write("\n## Estadístiques per Rolling Code (Nib7)\n\n")
        f.write("| Nib7 | Total | Matches | Errors | Precisió |\n")
        f.write("|------|-------|---------|--------|----------|\n")
        
        for nib7 in sorted(by_nib7.keys()):
            total_n = len(by_nib7[nib7])
            matches_n = sum(by_nib7[nib7])
            errors_n = total_n - matches_n
            pct = matches_n / total_n * 100
            
            status = "✅" if pct > 99 else "⚠️" if pct > 90 else "❌"
            f.write(f"| 0x{nib7:X} | {total_n} | {matches_n} | {errors_n} | {pct:.1f}% {status} |\n")
        
        # Anàlisi d'errors
        errors_only = [r for r in results if not r['match']]
        
        if errors_only:
            f.write(f"\n## Anàlisi d'Errors ({len(errors_only)} total)\n\n")
            
            # Errors per posició
            error_positions = Counter()
            for r in errors_only:
                for diff in r['diffs']:
                    error_positions[diff['pos']] += 1
            
            f.write("### Errors per Posició de Nibble\n\n")
            f.write("| Posició | Descripció | Errors | % |\n")
            f.write("|---------|------------|--------|---|\n")
            
            position_names = {
                0: "ID (E)", 1: "ID (C)", 2: "ID (4)", 3: "ID (0)",
                4: "Channel", 5: "House LSN", 6: "House MSN",
                7: "Rolling Code", 8: "Temp LSN", 9: "Temp Mid",
                10: "Temp MSN", 11: "Flags", 12: "R1", 13: "M", 14: "P"
            }
            
            for pos in sorted(error_positions.keys()):
                count = error_positions[pos]
                pct = count / len(errors_only) * 100
                name = position_names.get(pos, f"Pos {pos}")
                f.write(f"| {pos} | {name} | {count} | {pct:.1f}% |\n")
            
            # Mostrar primers 10 errors
            f.write("\n### Primers 10 Errors Detallats\n\n")
            f.write("| # | House | Ch | Temp | Nib7 | Capturada | Generada | Diferències |\n")
            f.write("|---|-------|----|----|------|-----------|----------|-------------|\n")
            
            for i, r in enumerate(errors_only[:10], 1):
                diffs_str = ", ".join([f"pos{d['pos']}:{d['captured']:X}→{d['generated']:X}" for d in r['diffs']])
                f.write(f"| {i} | {r['house']} | {r['channel']} | {r['temp']:.1f}°C | 0x{r['nib7']:X} | `{r['captured']}` | `{r['generated']}` | {diffs_str} |\n")
        
        f.write("\n---\n\n")
        f.write("**Generador**: `oregon_optimized_generator.py` amb `oregon_p_lut_complete.py`\n")
        f.write(f"**Data**: {results[0]['timestamp'].split()[0]} - {results[-1]['timestamp'].split()[0]}\n")

def generate_csv_table(results, output_file):
    """Genera taula en format CSV."""
    
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Capçalera
        writer.writerow([
            'Timestamp', 'House', 'Channel', 'Temp_C', 'Nib7',
            'Captured', 'Generated', 'Match', 'Diffs'
        ])
        
        # Dades
        for r in results:
            diffs_str = ';'.join([f"{d['pos']}:{d['captured']:X}→{d['generated']:X}" for d in r['diffs']])
            
            writer.writerow([
                r['timestamp'],
                r['house'],
                r['channel'],
                f"{r['temp']:.1f}",
                f"0x{r['nib7']:X}",
                r['captured'],
                r['generated'],
                'OK' if r['match'] else 'ERROR',
                diffs_str if diffs_str else '-'
            ])

if __name__ == "__main__":
    # Crear taula de verificació
    results = create_verification_table()
    
    # Generar documents
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    md_file = OUTPUT_DIR / "verification_table.md"
    csv_file = OUTPUT_DIR / "verification_table.csv"
    
    print(f"\nGenerant documents...")
    generate_markdown_table(results, md_file)
    generate_csv_table(results, csv_file)
    
    print(f"\n✅ Documents generats:")
    print(f"   - {md_file}")
    print(f"   - {csv_file}")
