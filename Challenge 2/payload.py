#!/usr/bin/env python3
"""
Derive the Master_GW id and the card-forge write, using ONLY:
  - a dump_eeprom dump (encoded DB), and
  - the gateway MAC (get_mac).
No firmware needed.

Usage: python3 payload.py              # uses the values baked in below
       edit MAC and DUMP to match your board, or pipe your own.
"""

# --- paste from get_mac ---
MAC = [0x34, 0x98, 0x7A, 0x84, 0x3A, 0x14]

# --- paste from dump_eeprom: the encoded bytes starting at offset 0x10 ---
DUMP_HEX = """
78 F7 18 E6 43 4B 73 CF 7A 84 3A 14 24 B8 4A 85
75 72 52 F1 19 E1 65 53 63 98 7A 84 BE 2E 20 9A
3C E8 55 7B 46 A9 25 C3 6D 14 34 98 3E D1 5C 17
72 F4 15 EB 48 26 6B DF 2D 84 3A 14 43 10 E3 87
69 71 46 EE 1F F6 65 53 63 98 7A 84 B2 8D 9E 9D
29 F0 55 66 55 FF 1F DB 7D 43 34 98 6B A6 09 15
79 F9 09 F0 5F 66 6B DF 2D 84 3A 14 6C 82 DC 1D
7D 75 46 F9 1D E1 65 53 63 98 7A 84 E4 B9 8A 9A
3D E5 48 70 51 F6 25 C3 6D 14 34 98 2F E2 4D 15
62 F9 0F E8 4E 4B 73 CF 7A 84 3A 14 CA 75 80 94
"""  # 0x10 .. 0xAF  (the DB region; the 0xB0+ tail is a separate addr^0x3C fill)

enc = [int(x, 16) for x in DUMP_HEX.split()]
# DB keystream is MAC repeated: plaintext[i] = enc[i] ^ MAC[i % 6]
db = bytes(enc[i] ^ MAC[i % 6] for i in range(len(enc)))

# records are 16 bytes: name[12] + id[3] + level[1]
print("decoded gateway roster (per-board):")
master = None
for off in range(0, len(db), 16):
    rec = db[off:off+16]
    if len(rec) < 16:
        break
    name = rec[:12].split(b'\x00')[0].decode('latin1', 'replace')
    gid = rec[12:15]
    level = rec[15]
    tag = "  <-- MASTER (level 0x99)" if level == 0x99 else ""
    print(f"  {name:12s} id={gid.hex(' ')} level=0x{level:02x}{tag}")
    if level == 0x99:
        master = gid

if master:
    ids = master.hex().upper()
    print(f"\nTarget id (Master_GW) = {master.hex(' ').upper()}")
    print(f"Forge:  write_block 5 {ids}99000000000000000000000000")
else:
    print("\nNo level-0x99 gateway found — check MAC/dump alignment.")
