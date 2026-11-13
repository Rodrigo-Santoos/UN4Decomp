#!/usr/bin/env python3
"""Extrai todos os arquivos de uma ISO (ISO9660) para uma pasta. Uso: extract_iso.py jogo.iso pasta/"""
import struct, sys
from pathlib import Path

def entries(f, lba, size):
    f.seek(lba * 2048); d = f.read(size); i = 0
    while i < len(d):
        n = d[i]
        if n == 0:
            i = (i // 2048 + 1) * 2048; continue
        ext, sz = struct.unpack("<I", d[i+2:i+6])[0], struct.unpack("<I", d[i+10:i+14])[0]
        name = d[i+33:i+33+d[i+32]].decode("latin1").split(";")[0]
        if name not in ("\x00", "\x01"):
            yield name, ext, sz, bool(d[i+25] & 2)
        i += n

def walk(f, lba, size, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for name, ext, sz, is_dir in entries(f, lba, size):
        if is_dir:
            walk(f, ext, sz, out / name)
        else:
            f.seek(ext * 2048); left = sz
            with open(out / name, "wb") as o:
                while left:
                    chunk = f.read(min(left, 1 << 24)); o.write(chunk); left -= len(chunk)

def main():
    iso, dest = sys.argv[1], Path(sys.argv[2])
    with open(iso, "rb") as f:
        f.seek(16 * 2048); pvd = f.read(2048)
        walk(f, struct.unpack("<I", pvd[158:162])[0], struct.unpack("<I", pvd[166:170])[0], dest)
    print("extraido em", dest)

if __name__ == "__main__":
    main()
