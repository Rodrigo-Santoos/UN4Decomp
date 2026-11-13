"""UN4Decomp: separa em funcoes proprias os pontos de entrada que o splat deixou como rotulo
("alabel") dentro de outra funcao.

O jogo passa esses enderecos como ponteiro de funcao (por exemplo, a entrada de uma tarefa criada
com func_001C6340). Se eles ficam no meio de outra funcao, o PS2Recomp nao acha uma funcao nesse
endereco e a thread nunca comeca a rodar (foi o que travou o boot na tela de idioma).

Regra: o rotulo precisa ser referenciado com %lo(...) no codigo e vir logo depois do fim de um
trecho (jr $ra, j ou b incondicional, pulando nops de alinhamento).
"""
import re

ALABEL = re.compile(r"alabel (D_([0-9A-F]{8}))\b")


def _is_end(word):
    return word == 0x03E00008 or (word >> 26) == 2 or (word >> 16) == 0x1000


def find_entries(asm_texts, word_at):
    text = "\n".join(asm_texts)
    entries = []
    for name, hexaddr in sorted(set(ALABEL.findall(text))):
        if f"%lo({name})" not in text:
            continue
        addr = int(hexaddr, 16)
        p = addr - 4
        for _ in range(8):
            w = word_at(p)
            if w is None or w != 0:
                break
            p -= 4
        w = word_at(p)
        prev = word_at(p - 4)
        if w is None:
            continue
        # fim de trecho: a instrucao de desvio fica antes do delay slot
        if (prev is not None and _is_end(prev)) or _is_end(w):
            entries.append(addr)
    return entries


def split(funcs, entries):
    """funcs: lista de (nome, inicio, tamanho). Devolve a lista com as entradas separadas."""
    out = list(funcs)
    added = []
    for addr in entries:
        for i, (n, a, s) in enumerate(out):
            if a < addr < a + s:
                out[i] = (n, a, addr - a)
                out.insert(i + 1, (f"func_{addr:08X}", addr, a + s - addr))
                added.append(addr)
                break
    out.sort(key=lambda f: f[1])
    return out, added
