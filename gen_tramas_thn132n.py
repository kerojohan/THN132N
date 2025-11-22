#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import csv
import argparse

# ---------- Tablas P[d] y M[e] (ya deducidas) ----------

P_TABLE = [
    0x000, 0x075, 0x0EA, 0x09F, 0x0B5,
    0x0C0, 0x05F, 0x02A, 0x06B, 0x01E,
]

M_TABLE = {
    -16: 0x2A1, -15: 0x252, -14: 0x203, -13: 0x2B5,
    -12: 0x2E4, -11: 0x217, -10: 0x246,  -9: 0x29A,
     -8: 0x2CB,  -7: 0x2F7,  -6: 0x2A6,  -5: 0x255,
     -4: 0x204,  -3: 0x2B2,  -2: 0x2E3,  -1: 0x210,
      0: 0x2C2,   1: 0x148,   2: 0x1BB,   3: 0x1EA,
      4: 0x15C,   5: 0x10D,   6: 0x1FE,   7: 0x1AF,
      8: 0x193,   9: 0x1C2,  10: 0x11E,  11: 0x14F,
     12: 0x1BC,  13: 0x236,  14: 0x280,  15: 0x10A,
     16: 0x1F9,  17: 0x1A8,  18: 0x194,  19: 0x866,
     20: 0x2CC,  21: 0x146,  22: 0x1B5,  23: 0x1E4,
     24: 0x152,  25: 0x103,  26: 0x1F0,  27: 0x1A1,
     28: 0x246,  29: 0x1CC,  30: 0x110,  31: 0x141,
     32: 0x1B2,  33: 0x1E3,  34: 0x8F6,  35: 0x8A7,
     36: 0x854,  37: 0x805,  38: 0x839,  39: 0x868,
     40: 0x8C6,  41: 0x897,  42: 0x864,  43: 0x835,
     44: 0x883,  45: 0x8D2,  46: 0x821,  47: 0x870,
     48: 0x84C,  49: 0x81D,  50: 0x162,  51: 0x133,
     52: 0x863,  53: 0x191,  54: 0x884,
}

M_MIN_E = min(M_TABLE.keys())
M_MAX_E = max(M_TABLE.keys())

BASE_RAW_HEX = "555555559995a5a6aa6a5aaaa9a9aa9aaaa65a6555"

# ---------- util bits ----------

def hex_to_bits(hexstr: str):
    bits = []
    for i in range(0, len(hexstr), 2):
        b = int(hexstr[i:i+2], 16)
        for bit in range(7, -1, -1):
            bits.append((b >> bit) & 1)
    return bits

def bits_to_hex(bits):
    out_bytes = []
    for i in range(0, len(bits), 8):
        chunk = bits[i:i+8]
        while len(chunk) < 8:
            chunk.append(0)
        val = 0
        for j, bit in enumerate(chunk):
            val |= (bit << (7 - j))
        out_bytes.append(f"{val:02X}")
    return "".join(out_bytes)

BASE_BITS = hex_to_bits(BASE_RAW_HEX)
HEADER_BITS = BASE_BITS[:40]  # preámbulo+sync

# ---------- temperatura → e,d,R12 ----------

def temp_to_e_d(temp_c: float):
    e = int(temp_c)
    absT = abs(temp_c)
    t10 = int(round(absT * 10.0))
    abs_e = abs(e)
    d = t10 - abs_e * 10
    return e, d

def calc_R12(temp_c: float) -> int:
    e, d = temp_to_e_d(temp_c)
    if e < M_MIN_E:
        e = M_MIN_E
    if e > M_MAX_E:
        e = M_MAX_E
    P = P_TABLE[d]
    M = M_TABLE[e]
    return (P ^ M) & 0x0FFF

def temp_to_bcd_bytes(temp_c: float):
    sign_bit = 0
    if temp_c < 0:
        sign_bit = 1
        temp_c = -temp_c

    t10 = int(round(temp_c * 10.0))
    d0 = t10 % 10
    ent = t10 // 10
    u = ent % 10
    d1 = (ent // 10) % 10

    msg4 = (d0 << 4) | (u & 0x0F)

    hundreds = 0
    low_nibble = (sign_bit << 3) | (hundreds & 0x07)
    msg5 = ((d1 & 0x0F) << 4) | low_nibble
    return msg4, msg5

def calc_os21_checksum(msg):
    s = 0
    for i in range(6):
        b = msg[i]
        s += (b >> 4) + (b & 0x0F)
    s &= 0xFF
    high = (s & 0xF0) >> 4
    low  = (s & 0x0F)
    return (low << 4) | high

def reflect_nibbles(buf: bytes) -> bytes:
    return bytes(((b & 0x0F) << 4) | (b >> 4) for b in buf)

# ---------- EC40 post-reflect ----------

def build_ec40_post(temp_c: float,
                    channel: int = 1,
                    device_id: int = 247) -> bytes:
    msg = [0] * 8
    msg[0] = 0xEC
    msg[1] = 0x40

    id_low  = device_id & 0x0F
    id_high = device_id & 0xF0

    msg[2] = ((channel & 0x0F) << 4) | id_low
    msg[3] = id_high

    msg[4], msg[5] = temp_to_bcd_bytes(temp_c)

    r12 = calc_R12(temp_c)
    msg[3] = (msg[3] & 0xF0) | ((r12 >> 8) & 0x0F)
    msg[7] = r12 & 0xFF

    msg[6] = calc_os21_checksum(msg)
    return bytes(msg)

# ---------- Manchester + RAW ----------

def build_raw_from_ec40_post(ec40_post: bytes) -> str:
    ec40_pre = reflect_nibbles(ec40_post)

    data_bits = []
    for byte in ec40_pre:
        for j in range(8):
            data_bits.append((byte >> j) & 1)  # LSB-first

    mc_bits = []
    for bit in data_bits:
        if bit == 0:
            mc_bits.extend([1, 0])
        else:
            mc_bits.extend([0, 1])

    all_bits = HEADER_BITS + mc_bits
    return bits_to_hex(all_bits)

# ---------- main CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description='Genera tramas Oregon Scientific THN132N en formato CSV'
    )
    parser.add_argument(
        '--device-id',
        type=int,
        default=247,
        help='Device ID (House Code), rango 0-255 (default: 247)'
    )
    parser.add_argument(
        '--channel',
        type=int,
        default=1,
        choices=[1, 2, 3],
        help='Canal del sensor (1, 2 o 3, default: 1)'
    )
    parser.add_argument(
        '--temp-min',
        type=float,
        default=-20.0,
        help='Temperatura mínima en °C (default: -20.0)'
    )
    parser.add_argument(
        '--temp-max',
        type=float,
        default=50.0,
        help='Temperatura máxima en °C (default: 50.0)'
    )
    parser.add_argument(
        '--temp-step',
        type=float,
        default=0.5,
        help='Incremento de temperatura en °C (default: 0.5)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default='tramas_thn132n.csv',
        help='Archivo de salida CSV (default: tramas_thn132n.csv)'
    )
    
    args = parser.parse_args()
    
    # Validación de parámetros
    if args.device_id < 0 or args.device_id > 255:
        print("Error: device_id debe estar entre 0 y 255", file=sys.stderr)
        sys.exit(1)
    
    if args.temp_min >= args.temp_max:
        print("Error: temp_min debe ser menor que temp_max", file=sys.stderr)
        sys.exit(1)
    
    if args.temp_step <= 0:
        print("Error: temp_step debe ser mayor que 0", file=sys.stderr)
        sys.exit(1)
    
    # Generar tramas
    tramas = []
    temp = args.temp_min
    
    while temp <= args.temp_max:
        ec40 = build_ec40_post(temp, args.channel, args.device_id)
        raw_hex = build_raw_from_ec40_post(ec40)
        
        tramas.append({
            'temperatura': f"{temp:.1f}",
            'device_id': args.device_id,
            'channel': args.channel,
            'ec40_hex': ec40.hex().upper(),
            'raw_hex': raw_hex
        })
        
        temp += args.temp_step
    
    # Escribir CSV
    with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['temperatura', 'device_id', 'channel', 'ec40_hex', 'raw_hex']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for trama in tramas:
            writer.writerow(trama)
    
    print(f"✓ Generadas {len(tramas)} tramas")
    print(f"✓ Device ID: {args.device_id}")
    print(f"✓ Canal: {args.channel}")
    print(f"✓ Rango de temperatura: {args.temp_min}°C a {args.temp_max}°C (paso: {args.temp_step}°C)")
    print(f"✓ Archivo guardado: {args.output}")

if __name__ == "__main__":
    main()

