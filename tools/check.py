#!/usr/bin/env python3
"""Compara a ROM reconstruida com a original e mostra a primeira diferenca."""
import hashlib, sys
built, orig = (open(p, "rb").read() for p in sys.argv[1:3])
if built == orig:
    print(f"OK: reconstrucao identica ao original ({len(orig)} bytes, sha1 {hashlib.sha1(orig).hexdigest()})")
    sys.exit(0)
n = min(len(built), len(orig))
first = next((i for i in range(n) if built[i] != orig[i]), n)
print(f"DIFERENTE: tamanho {len(built)} vs {len(orig)}; primeira diferenca no offset 0x{first:X} (vram 0x{0x100000+first:08X})")
sys.exit(1)
