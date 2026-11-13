#!/usr/bin/env python3
"""Mostra quanto do executavel principal ja foi decompilado."""
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
funcs = {}
for s in (ROOT / "asm").rglob("*.s"):
    for name, size in re.findall(r"^nonmatching (\S+), (0x[0-9A-Fa-f]+)", s.read_text(), re.M):
        funcs[name] = int(size, 16)
libs = set((ROOT / "config/sony_libs.txt").read_text().split()) & set(funcs)
game = {n: s for n, s in funcs.items() if n not in libs}
lst = ROOT / "config/matched.txt"
done = [f for f in (lst.read_text().split() if lst.exists() else []) if f in game]
tb, db = sum(game.values()), sum(game[f] for f in done)
print(f"Bibliotecas da Sony identificadas: {len(libs)} funcoes (nao precisam ser decompiladas)")
print(f"Codigo do jogo: {len(done)} de {len(game)} funcoes ({100*len(done)/max(1,len(game)):.2f}%)")
print(f"                {db} de {tb} bytes ({100*db/max(1,tb):.3f}%)")
