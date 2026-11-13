#!/usr/bin/env python3
"""Compila src/main/<FUNC>.c com o Metrowerks e compara com a funcao original.

Uso: python3 tools/match.py func_00123456 [--flags "-O2"] [--compiler 3.0.1b205-051227]

O compilador e as flags padrao foram descobertos testando funcoes do proprio jogo:
Metrowerks 3.0.1 build 205 (dez/2005) com -O2 reproduz o codigo original.
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tools/bin"
AS = BIN / "binutils/mips-ps2-decompals-as"
WIBO = BIN / "wibo"
MWCC_DIR = BIN / "compilers"
OBJDIFF = BIN / "objdiff-cli"
ASFLAGS = ["-EL", "-march=r5900", "-mabi=eabi", "-G0", "-no-pad-sections", "-I", str(ROOT / "include")]
DEFAULT_FLAGS = "-O2"
DEFAULT_COMPILER = "3.0.1b205-051227"

def find_asm(func: str) -> str:
    """Recorta a funcao do asm gerado pelo splat (asm/main/*.s)."""
    for s in sorted((ROOT / "asm").rglob("*.s")):
        text = s.read_text()
        m = re.search(rf"^nonmatching {re.escape(func)}, .*?$", text, re.M)
        if not m:
            continue
        nxt = re.search(r"^(/\* Handwritten function \*/\n)?nonmatching ", text[m.end():], re.M)
        body = text[m.start(): m.end() + (nxt.start() if nxt else len(text) - m.end())]
        return body
    sys.exit(f"funcao {func} nao encontrada em asm/")

def run(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        sys.exit(f"falhou: {Path(str(cmd[0])).name}")
    return r

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("func")
    ap.add_argument("--flags", default=DEFAULT_FLAGS)
    ap.add_argument("--compiler", default=DEFAULT_COMPILER)
    a = ap.parse_args()
    out = ROOT / "build/match" / a.func
    out.mkdir(parents=True, exist_ok=True)

    # objeto esperado (original)
    target_s = out / "target.s"
    target_s.write_text('.include "macro.inc"\n.set noat\n.set noreorder\n.section .text, "ax"\n\n'
                        + find_asm(a.func) + "\n")
    run([AS, *ASFLAGS, "-o", out / "target.o", target_s])

    # objeto compilado a partir do C
    src = ROOT / "src/main" / f"{a.func}.c"
    if not src.exists():
        sys.exit(f"crie {src.relative_to(ROOT)} primeiro")
    cdir = MWCC_DIR / a.compiler
    if a.compiler.startswith("ee-gcc"):
        # EE-GCC da Sony (binario Linux 32 bits: precisa de libc6:i386, veja tools/setup_eegcc.sh)
        gcc = cdir / "bin/ee-gcc"
        libdirs = [p for p in (cdir / "lib/gcc-lib/ee").glob("*") if p.is_dir()]
        bflags = [f"-B{cdir / 'bin'}/"] + [f"-B{d}/" for d in libdirs]
        flags = a.flags.split() if a.flags != DEFAULT_FLAGS else ["-O2", "-G0"]
        run([gcc, *bflags, "-c", *flags, "-I" + str(ROOT / "include"), "-o", out / "base.o", src], cwd=ROOT)
    else:
        run([WIBO, cdir / "mwccps2.exe", "-c", "-lang", "c", "-nostdinc", *a.flags.split(),
             "-I" + str(ROOT / "include"), "-o", out / "base.o", src], cwd=ROOT)

    r = run([OBJDIFF, "diff", "-1", out / "target.o", "-2", out / "base.o", "-o", "-", "--format", "json", a.func])
    data = json.loads(r.stdout)
    pct = None
    for side in ("right", "left"):
        for sym in (data.get(side) or {}).get("symbols", []):
            if sym.get("name") == a.func and "match_percent" in sym:
                pct = sym["match_percent"]
    if pct is None:
        print(json.dumps(data)[:2000]); sys.exit("nao achei o resultado do objdiff")
    print(f"{a.func}: {pct:.2f}% igual ao original")
    if pct >= 100.0:
        lst = ROOT / "config/matched.txt"
        done = set(lst.read_text().split()) if lst.exists() else set()
        if a.func not in done:
            done.add(a.func)
            lst.write_text("\n".join(sorted(done)) + "\n")
            print("  -> marcada como decompilada em config/matched.txt")
    sys.exit(0 if pct >= 100.0 else 1)

if __name__ == "__main__":
    main()
