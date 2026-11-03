#!/usr/bin/env python3
"""Baixa as ferramentas usadas pelo projeto para tools/bin/ (Linux x86-64 ou WSL)."""
import hashlib, io, os, stat, tarfile, urllib.request


def make_exec(p):
    try:
        p.chmod(p.stat().st_mode | stat.S_IEXEC)
    except PermissionError:
        raise SystemExit(
            "Nao consegui marcar as ferramentas como executaveis nesta pasta.\n"
            "Isso acontece em pastas do Windows/OneDrive (/mnt/c/...).\n"
            "Copie o projeto para dentro do Linux e rode de la, por exemplo:\n"
            "  cp -r \"$PWD\" ~/UN4Decomp && cd ~/UN4Decomp && rm -rf tools/bin && python3 tools/setup_tools.py")
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIN = ROOT / "tools/bin"
GH = "https://github.com"
FILES = {
    "wibo": (f"{GH}/decompals/wibo/releases/download/1.2.0/wibo-x86_64",
             "13f86a2d618f0dbe67179d349625345eabf9b46450295cb4c904e49f6aff85af"),
    "objdiff-cli": (f"{GH}/encounter/objdiff/releases/download/v3.8.0/objdiff-cli-linux-x86_64",
                    "bc1e047126f9c6914bd1695798175234642ab9eaf45e886f841b59a4231e1a81"),
}
TARS = {
    "binutils": f"{GH}/decompals/binutils-mips-ps2-decompals/releases/latest/download/binutils-mips-ps2-decompals-linux-x86-64.tar.gz",
    "compilers/3.0.1b205-051227": f"{GH}/decompme/compilers/releases/download/compilers/mwcps2-3.0.1b205-051227.tar.gz",
    "compilers/2.4-001213": f"{GH}/decompme/compilers/releases/download/compilers/mwcps2-2.4-001213.tar.gz",
}

def get(url):
    print("baixando", url)
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def main():
    BIN.mkdir(parents=True, exist_ok=True)
    for name, (url, sha) in FILES.items():
        p = BIN / name
        if not p.exists():
            data = get(url)
            if hashlib.sha256(data).hexdigest() != sha:
                raise SystemExit(f"hash errado para {name}")
            p.write_bytes(data)
            make_exec(p)
    for name, url in TARS.items():
        d = BIN / name
        if not d.exists():
            d.mkdir(parents=True)
            tarfile.open(fileobj=io.BytesIO(get(url))).extractall(d)
            for f in d.iterdir():
                make_exec(f)
    print("Ferramentas prontas em tools/bin/")

if __name__ == "__main__":
    main()
