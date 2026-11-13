#!/usr/bin/env python3
"""Recompila os modulos de codigo do UN4 (overlays "MWo3" da Metrowerks) para o PS2Recomp.

O jogo carrega HOME.BIN / RPG.BIN / BATTLE.BIN no MESMO endereco (0x006B8200) e
TEXTENG.BIN / TEXTFRN.BIN em 0x0086A000, trocando conforme o modo de jogo. O PS2Recomp
so conhece o executavel principal, entao este script:

  1. le o cabecalho MWo3 de cada .BIN (endereco, tamanho do codigo, construtores);
  2. desmonta cada um com o splat para achar os limites das funcoes;
  3. gera um ELF "falso" com o .BIN no endereco certo e recompila com o ps2_recomp;
  4. renomeia as funcoes de cada overlay (prefixo ovN_) para nao colidirem;
  5. gera ovl_dispatch.cpp: quando o jogo chama um endereco de overlay, o despachante
     olha o id no cabecalho que esta na memoria (base+4) e chama a funcao do overlay
     que esta carregado naquele momento;
  6. aumenta a tabela de funcoes do executavel principal para cobrir esses enderecos.

Uso: python3 recomp/overlays.py   (depois do passo 4 do recomp/build.sh)
"""
import re, shutil, struct, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from split_alabels import find_entries, split  # noqa: E402
R = ROOT / "recomp"
GAME = R / "game/PRG"
WORK = R / "build/ovl"
MAIN_OUT = R / "build/output"
RECOMP = R / "PS2Recomp/out/tools/ps2xRecomp/ps2_recomp"
OVERLAYS = ["HOME", "BATTLE", "RPG", "TEXTENG", "TEXTFRN"]
TABLE_BASE = 0x100000
TABLE_END = 0x8A0000          # cobre o executavel principal + as duas areas de overlay


def header(d):
    magic, ov_id, base, text_size, data_size, bss, ctor0, ctor1 = struct.unpack("<4s7I", d[:32])
    assert magic == b"MWo3", "nao e um overlay MWo3"
    return dict(id=ov_id, base=base, text_end=0x40 + text_size, bss=bss, ctor=ctor0 - base)


def words(d):
    return struct.unpack("<%dI" % (len(d) // 4), d[: len(d) // 4 * 4])


def code_ranges(d, h):
    """Codigo normal logo apos o cabecalho + codigo de inicializacao perto do fim (antes dos construtores)."""
    w = words(d)
    ranges = []
    if any(x == 0x03E00008 for x in w[0x40 // 4: h["text_end"] // 4]):
        ranges.append((0x40, h["text_end"]))
    late = [i * 4 for i, x in enumerate(w) if i * 4 >= h["text_end"] and (x >> 16) == 0x27BD and x & 0x8000]
    if late and late[0] < h["ctor"]:
        ranges.append((late[0], h["ctor"] & ~0xF))
    return ranges


def make_elf(data, vaddr, memsz, out, entry):
    ehsz, phsz, shsz = 52, 32, 40
    shstr = b"\0.text\0.shstrtab\0"
    off_data = 0x1000
    off_shstr = off_data + len(data)
    off_sh = (off_shstr + len(shstr) + 3) & ~3
    eh = b"\x7fELF" + bytes([1, 1, 1, 0]) + b"\0" * 8
    eh += struct.pack("<HHIIIIIHHHHHH", 2, 8, 1, entry, ehsz, off_sh, 0x20924001, ehsz, phsz, 1, shsz, 3, 2)
    ph = struct.pack("<IIIIIIII", 1, off_data, vaddr, vaddr, len(data), memsz, 7, 0x10)
    sh = b"\0" * 40
    sh += struct.pack("<IIIIIIIIII", 1, 1, 6, vaddr, off_data, len(data), 0, 0, 16, 0)
    sh += struct.pack("<IIIIIIIIII", 7, 3, 0, 0, off_shstr, len(shstr), 0, 0, 1, 0)
    f = bytearray(eh + ph)
    f += b"\0" * (off_data - len(f)) + data + shstr
    f += b"\0" * (off_sh - len(f)) + sh
    out.write_bytes(f)


def splat_functions(name, d, h, wdir):
    """Roda o splat no overlay e devolve [(nome, inicio, tamanho)]."""
    segs, pos = [], 0
    for i, (a, b) in enumerate(code_ranges(d, h)):
        if a > pos:
            segs.append(f"      - [0x{pos:X}, bin, {name.lower()}/data_{pos:X}]")
        segs.append(f"      - [0x{a:X}, asm, {name.lower()}/code_{a:X}]")
        pos = b
    if pos < len(d):
        segs.append(f"      - [0x{pos:X}, bin, {name.lower()}/data_{pos:X}]")
    (wdir / f"{name}.bin").write_bytes(d)
    cfg = f"""name: {name}
options:
  basename: {name}
  target_path: {name}.bin
  base_path: .
  platform: ps2
  compiler: MWCCPS2
  asm_path: asm
  src_path: src
  build_path: build
  asset_path: assets
  ld_script_path: build/{name}.ld
  find_file_boundaries: False
  undefined_funcs_auto_path: auto_funcs.txt
  undefined_syms_auto_path: auto_syms.txt
  symbol_addrs_path: []
segments:
  - name: {name.lower()}
    type: code
    start: 0x0
    vram: 0x{h['base']:08X}
    subalign: null
    subsegments:
{chr(10).join(segs)}
  - [0x{len(d):X}]
"""
    (wdir / f"{name}.yaml").write_text(cfg)
    subprocess.run([sys.executable, "-m", "splat", "split", f"{name}.yaml"], cwd=wdir, check=True,
                   stdout=subprocess.DEVNULL)
    funcs = []
    texts = []
    for s in sorted((wdir / "asm").rglob("*.s")):
        pending = None
        text = s.read_text()
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
    # entradas de tarefa/callback que o splat deixou como rotulo no meio de outra funcao
    base = h["base"]

    def word_at(addr):
        i = addr - base
        if i < 0 or i + 4 > len(d):
            return None
        return int.from_bytes(d[i:i + 4], "little")

    funcs, added = split(funcs, find_entries(texts, word_at))
    if added:
        print(f"   {name}: +{len(added)} entradas separadas ({', '.join(hex(x) for x in added)})")
    return funcs


def recompile(name, wdir, funcs):
    csv = wdir / "funcs.csv"
    csv.write_text("Name,Start,End,Size\n" + "".join(f"{n},0x{a:08X},0x{a+s:08X},{s}\n" for n, a, s in funcs))
    out = wdir / "output"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    (wdir / "config.toml").write_text(f"""[general]
input = "{name}.elf"
ghidra_output = "funcs.csv"
output = "output/"
single_file_output = false
patch_syscalls = false
patch_cop0 = true
patch_cache = true
stubs = []
skip = []
""")
    r = subprocess.run([str(RECOMP), "config.toml"], cwd=wdir, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stdout[-3000:] + r.stderr[-3000:])
        sys.exit(f"ps2_recomp falhou no {name}")
    return out


def rename(name, ov_id, out, dest):
    """Prefixa as funcoes do overlay e devolve {endereco: nome_da_funcao}."""
    prefix = f"ov{ov_id}_"
    decl = (out / "ps2_recompiled_functions.h").read_text()
    names = set(re.findall(r"^void (\w+)\(uint8_t\* rdram", decl, re.M))
    pat = re.compile(r"\b(" + "|".join(sorted(map(re.escape, names), key=len, reverse=True)) + r")\b") if names else None
    hdr_f, hdr_s = f"ps2_ovl{ov_id}_functions.h", f"ps2_ovl{ov_id}_stubs.h"
    slots = {}
    for line in (out / "register_functions.cpp").read_text().splitlines():
        m = re.search(r"= (\w+); // 0x([0-9a-f]+)", line)
        if m:
            slots[int(m.group(2), 16)] = prefix + m.group(1)
    for f in out.iterdir():
        if f.name == "register_functions.cpp":
            continue
        text = f.read_text()
        if pat:
            text = pat.sub(lambda m: prefix + m.group(1), text)
        text = text.replace("ps2_recompiled_functions.h", hdr_f).replace("ps2_recompiled_stubs.h", hdr_s)
        text = text.replace("PS2_RECOMPILED_FUNCTIONS_H", f"PS2_OVL{ov_id}_FUNCTIONS_H")
        target = {"ps2_recompiled_functions.h": hdr_f, "ps2_recompiled_stubs.h": hdr_s}.get(f.name, f"ovl{ov_id}_{f.name}")
        (dest / target).write_text(text)
    return slots


def write_dispatch(dest, groups):
    lines = ['#include "ps2_runtime.h"', '#include <cstring>', "#include <iostream>", ""]
    by_base = {}
    for ov in groups:
        by_base.setdefault(ov["base"], []).append(ov)
    for ov in groups:
        lines.append(f'#include "ps2_ovl{ov["id"]}_functions.h"')
    lines += ["", "namespace {", "struct OvlEntry { uint32_t addr; PS2Runtime::RecompiledFunction fn; };"]
    for ov in groups:
        lines.append(f"const OvlEntry kOvl{ov['id']}[] = {{")
        lines += [f"    {{0x{a:08X}u, {fn}}}," for a, fn in sorted(ov["slots"].items())]
        lines.append("};")
    lines.append("")
    lines.append("PS2Runtime::RecompiledFunction findIn(const OvlEntry *t, size_t n, uint32_t addr) {")
    lines.append("    size_t lo = 0, hi = n;")
    lines.append("    while (lo < hi) { size_t mid = (lo + hi) / 2; if (t[mid].addr < addr) lo = mid + 1; else hi = mid; }")
    lines.append("    return (lo < n && t[lo].addr == addr) ? t[lo].fn : nullptr;")
    lines.append("}")
    lines.append("")
    lines.append("void ovlDispatch(uint8_t *rdram, R5900Context *ctx, PS2Runtime *runtime) {")
    lines.append("    const uint32_t pc = ctx->pc;")
    lines.append("    PS2Runtime::RecompiledFunction fn = nullptr;")
    lines.append("    uint32_t loaded = 0;")
    for base, members in by_base.items():
        end = max(m["base"] + m["size"] for m in members)
        lines.append(f"    if (pc >= 0x{base:08X}u && pc < 0x{end:08X}u) {{")
        lines.append(f"        std::memcpy(&loaded, rdram + 0x{base:08X}u + 4u, 4);")
        lines.append("        switch (loaded) {")
        for m in members:
            lines.append(f"        case {m['id']}: fn = findIn(kOvl{m['id']}, sizeof(kOvl{m['id']}) / sizeof(OvlEntry), pc); break;")
        lines.append("        default: break;")
        lines.append("        }")
        lines.append("    }")
    lines.append("    if (fn == nullptr) {")
    lines.append('        std::cerr << "[ovl] sem funcao para 0x" << std::hex << pc << " (overlay carregado id=" << std::dec << loaded << ")" << std::endl;')
    lines.append('        runtime->reportMissingFunction(rdram, ctx, pc, 0u, PS2Runtime::GuestBranchKind::IndirectJump, "overlay");')
    lines.append("        return;")
    lines.append("    }")
    lines.append("    fn(rdram, ctx, runtime);")
    lines.append("}")
    lines.append("")
    lines.append("struct OvlInit {")
    lines.append("    OvlInit() {")
    addrs = sorted({a for ov in groups for a in ov["slots"]})
    lines.append(f"        static const uint32_t kAddrs[] = {{{', '.join(f'0x{a:X}u' for a in addrs)}}};")
    lines.append("        for (uint32_t a : kAddrs) g_ps2RecompiledFunctionTable[(a - g_ps2RecompiledFunctionTableBase) >> 2] = ovlDispatch;")
    lines.append("    }")
    lines.append("};")
    lines.append("const OvlInit g_ovlInit;")
    lines.append("}")
    text = "\n".join(lines) + "\n"
    text = text.replace('#include "ps2_runtime.h"',
                        '#include "ps2_runtime.h"\nextern const uint32_t g_ps2RecompiledFunctionTableBase;\n'
                        'extern PS2Runtime::RecompiledFunction g_ps2RecompiledFunctionTable[];', 1)
    (dest / "ovl_dispatch.cpp").write_text(text)
    return len(addrs)


def widen_main_table():
    reg = MAIN_OUT / "register_functions.cpp"
    s = reg.read_text()
    slots = (TABLE_END - TABLE_BASE) >> 2
    s = re.sub(r"g_ps2RecompiledFunctionTableEnd = 0x[0-9a-fA-F]+u;", f"g_ps2RecompiledFunctionTableEnd = 0x{TABLE_END:x}u;", s)
    s = re.sub(r"g_ps2RecompiledFunctionTableSlotCount = \d+u;", f"g_ps2RecompiledFunctionTableSlotCount = {slots}u;", s)
    s = re.sub(r"g_ps2RecompiledFunctionTable\[\d+u\] = \{\};", f"g_ps2RecompiledFunctionTable[{slots}u] = {{}};", s)
    assert f"0x{TABLE_BASE:x}u" in s, "a tabela principal nao comeca em 0x100000"
    reg.write_text(s)


def main():
    dest = R / "build/ovl_output"
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    groups = []
    for name in OVERLAYS:
        d = (GAME / f"{name}.BIN").read_bytes()
        h = header(d)
        wdir = WORK / name
        shutil.rmtree(wdir, ignore_errors=True)
        wdir.mkdir(parents=True)
        funcs = splat_functions(name, d, h, wdir)
        make_elf(d, h["base"], len(d) + h["bss"], wdir / f"{name}.elf", min(a for _, a, _ in funcs))
        out = recompile(name, wdir, funcs)
        slots = rename(name, h["id"], out, dest)
        groups.append(dict(id=h["id"], base=h["base"], size=len(d), slots=slots))
        print(f"{name}: id={h['id']} base=0x{h['base']:08X} {len(funcs)} funcoes, {len(slots)} pontos de entrada")
    n = write_dispatch(dest, groups)
    widen_main_table()
    print(f"ovl_dispatch.cpp: {n} enderecos de overlay roteados; tabela principal ate 0x{TABLE_END:08X}")


if __name__ == "__main__":
    main()
