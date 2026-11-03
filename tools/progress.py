#!/usr/bin/env python3
"""Mostra quanto do executavel principal ja foi decompilado."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
funcs = {}
for s in (ROOT / "asm").rglob("*.s"):
    for name, size in re.findall(r"^nonmatching (\S+), (0x[0-9A-Fa-f]+)", s.read_text(), re.M):
        funcs[name] = int(size, 16)
lst = ROOT / "config/matched.txt"
done = [f for f in (lst.read_text().split() if lst.exists() else []) if f in funcs]
tb, db = sum(funcs.values()), sum(funcs[f] for f in done)
print(f"Funcoes: {len(done)} de {len(funcs)} ({100*len(done)/max(1,len(funcs)):.2f}%)")
print(f"Codigo:  {db} de {tb} bytes ({100*db/max(1,tb):.3f}%)")
