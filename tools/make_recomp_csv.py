#!/usr/bin/env python3
"""Gera recomp/build/funcs.csv (limites e nomes das funcoes) a partir do asm do splat."""
import re
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from split_alabels import find_entries, split  # noqa: E402

funcs = []
texts = []
for s in ("asm/main/text.s", "asm/main/late_text.s"):
    pending = None
    text = (ROOT / s).read_text()
    texts.append(text)
    for line in text.splitlines():
        m = re.match(r"nonmatching (\S+), (0x[0-9A-Fa-f]+)", line)
        if m:
            pending = (m.group(1), int(m.group(2), 16))
            continue
        if pending:
            a = re.match(r"\s+/\* [0-9A-F]+ ([0-9A-F]{8}) ", line)
            if a:
                funcs.append((pending[0], int(a.group(1), 16), pending[1]))
                pending = None

# palavras do executavel original (para conferir o fim de trecho antes de cada rotulo)
elf = (ROOT / "baserom/SLUS_218.62").read_bytes()
phoff = struct.unpack_from("<I", elf, 28)[0]
_, off, vaddr, _, filesz = struct.unpack_from("<IIIII", elf, phoff)


def word_at(addr):
    i = addr - vaddr + off
    if addr < vaddr or i + 4 > off + filesz:
        return None
    return struct.unpack_from("<I", elf, i)[0]


funcs, added = split(funcs, find_entries(texts, word_at))

# Funcoes da libvu0 (matrizes/vetores do VU0): o PS2Recomp troca qualquer funcao com o mesmo nome de um
# "stub" do runtime pela versao dele em C++, e algumas dessas versoes estao erradas (sceVu0MulMatrix
# multiplica na ordem trocada; _sceVu0ecossin nem usa a mesma convencao de registradores). Isso deixava
# toda a geometria do VU1 fora da tela (titulo e opcoes do menu invisiveis). Renomeando, o codigo
# original do jogo e recompilado e usado no lugar.
KEEP_ORIGINAL = re.compile(r"^_?sceVu0")
funcs = [(("un4_" + n) if KEEP_ORIGINAL.match(n) else n, a, z) for n, a, z in funcs]
out = ROOT / "recomp/build/funcs.csv"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("Name,Start,End,Size\n" + "".join(f"{n},0x{a:08X},0x{a + z:08X},{z}\n" for n, a, z in funcs))
extra = f" (+{len(added)} entradas separadas: {', '.join(hex(a) for a in added)})" if added else ""
print(f"{len(funcs)} funcoes -> {out.relative_to(ROOT)}{extra}")
