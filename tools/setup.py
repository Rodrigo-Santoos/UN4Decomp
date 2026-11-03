#!/usr/bin/env python3
"""Extrai o executavel da SUA ISO do Naruto Shippuden: Ultimate Ninja 4 (USA) e prepara o projeto.

Uso: python3 tools/setup.py "/caminho/Naruto Shippuden - Ultimate Ninja 4 (USA) (En,Fr).iso"
"""
import hashlib, struct, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ELF_SHA256 = "fefb3b546e41e80e829faee107a73f7599167a1446f781207ae69310e5105407"
TEXT_OFFSET, TEXT_SIZE = 0x180, 0x509500   # segmento carregado em 0x00100000

def iso_dir(f, lba, size):
    f.seek(lba * 2048); d = f.read(size); i = 0; out = {}
    while i < len(d):
        n = d[i]
        if n == 0:
            i = (i // 2048 + 1) * 2048; continue
        ext, sz = struct.unpack("<I", d[i+2:i+6])[0], struct.unpack("<I", d[i+10:i+14])[0]
        name = d[i+33:i+33+d[i+32]].decode("latin1").split(";")[0]
        if name not in ("\x00", "\x01"):
            out[name] = (ext, sz, bool(d[i+25] & 2))
        i += n
    return out

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    base = ROOT / "baserom"; base.mkdir(exist_ok=True)
    with open(sys.argv[1], "rb") as f:
        f.seek(16 * 2048); pvd = f.read(2048)
        root = iso_dir(f, struct.unpack("<I", pvd[158:162])[0], struct.unpack("<I", pvd[166:170])[0])
        ext, sz, _ = root["SLUS_218.62"]
        f.seek(ext * 2048); (base / "SLUS_218.62").write_bytes(f.read(sz))
        pext, psz, _ = root["PRG"]
        for name, (e, s, d) in iso_dir(f, pext, psz).items():
            if not d:
                f.seek(e * 2048); (base / name).write_bytes(f.read(s))
    elf = (base / "SLUS_218.62").read_bytes()
    if hashlib.sha256(elf).hexdigest() != ELF_SHA256:
        sys.exit("O executavel nao e o esperado (precisa ser o Ultimate Ninja 4 USA, SLUS-21862).")
    (base / "SLUS_218.62.rom").write_bytes(elf[TEXT_OFFSET:TEXT_OFFSET + TEXT_SIZE])
    print("Executavel conferido. Gerando o assembly com o splat...")
    (ROOT / "config/auto").mkdir(parents=True, exist_ok=True)
    (ROOT / "build").mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "splat", "split", "config/SLUS_218.62.yaml"], cwd=ROOT, check=True)
    print("Pronto. Rode 'make' para conferir a reconstrucao.")

if __name__ == "__main__":
    main()
