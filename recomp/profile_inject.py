#!/usr/bin/env python3
"""UN4Decomp: liga o medidor de funcoes (un4_profile.h) no codigo C++ gerado pelo PS2Recomp.

Troca o bloco de log de entrada de cada funcao (desligado no build normal) por UN4_PROFILE("nome"),
que so soma 1 num contador. Uso: python3 profile_inject.py pasta1 [pasta2 ...]
"""
import re
import sys
from pathlib import Path

PAT = re.compile(r'#ifdef PS2_FUNCTION_LOG_TRACKER\n(\s*)PS_LOG_ENTRY\(("[^"\n]*")\);\n#endif')

# funcoes que tambem registram argumentos e o objeto apontado por a0 (diagnostico do desenho 2D)
TRACE = ("func_001C4AA0", "func_001C4750", "func_001C4A50", "func_00110850", "func_00110760", "func_001C5D80")


# pontos exatos (endereco da instrucao) onde registrar o estado do sprite
PEEKS = {"func_001C4AA0": ("1c5248", "1c5320", "1c53d8", "1c5840", "1c5aa0", "1c5a78", "1c5c90", "1c5ca8", "1c5cc0")}


# pontos onde registrar um texto (caminho de arquivo) apontado por um registrador: (endereco, registrador)
# func_001206A0 = busca de caminho do ROFS (RFDIR_SearchPath); s4 (r20) = caminho pedido, s3 (r19) = caminho tratado
STRS = {"func_001206A0": (("1207e4", 20), ("1207e4", 19), ("120814", 20), ("120728", 20), ("120770", 20))}


def add_strs(name, text):
    for addr, reg in STRS.get(name, ()):
        text = re.sub(rf"(\n(\s*)// 0x{addr}: [^\n]*)", rf'\1\n\2UN4_STR("{addr}", {reg});', text, count=1)
    return text


def add_peeks(name, text):
    for addr in PEEKS.get(name, ()):
        text = re.sub(rf"(\n(\s*)// 0x{addr}: [^\n]*)", rf'\1\n\2UN4_PEEK("{addr}");', text, count=1)
    return text


def repl(m):
    out = f'{m.group(1)}UN4_PROFILE({m.group(2)});'
    if m.group(2).strip('"').split("_0x")[0] in TRACE:
        out += f'\n{m.group(1)}UN4_TRACE({m.group(2)});'
    return out

total = 0
for folder in sys.argv[1:]:
    for path in Path(folder).glob("*.cpp"):
        text = path.read_text(encoding="utf-8", errors="surrogateescape")
        new, n = PAT.subn(repl, text)
        for name in PEEKS:
            if path.name.startswith(name + "_"):
                new = add_peeks(name, new)
        for name in STRS:
            if path.name.startswith(name + "_"):
                new = add_strs(name, new)
        if n:
            new = '#include "un4_profile.h"\n' + new
            path.write_text(new, encoding="utf-8", errors="surrogateescape")
            total += n
print(f"   medidor de funcoes ligado em {total} funcoes")
