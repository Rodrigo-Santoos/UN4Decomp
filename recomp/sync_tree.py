#!/usr/bin/env python3
"""Ajuda o build.sh a nao recompilar o que nao mudou.

O build.sh volta os arquivos do PS2Recomp ao original e aplica os patches de novo a cada build, e
gera de novo todo o codigo C++ do jogo. Isso muda a data de todos os arquivos, e o ninja recompila
tudo (~10 mil arquivos). Este script guarda a data dos arquivos cujo conteudo nao mudou:

  snapshot RAIZ LISTA DIR...   anota caminho, data e hash dos arquivos em RAIZ/DIR...
  restore  RAIZ LISTA          arquivo com o mesmo conteudo da anotacao volta para a data antiga
  sync --dst D --src S [--src S2] --pattern P [--pattern P2] --manifest M
                               copia S/P para D so quando o conteudo mudou; apaga de D o que
                               foi copiado num build anterior e nao existe mais
"""
import argparse
import fnmatch
import hashlib
import os
import shutil
import sys


def digest(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_snapshot(root, listfile, dirs):
    count = 0
    with open(listfile + ".tmp", "w", encoding="utf-8") as out:
        for d in dirs:
            base = os.path.join(root, d)
            for dirpath, _, files in os.walk(base):
                for name in files:
                    full = os.path.join(dirpath, name)
                    try:
                        st = os.stat(full)
                    except OSError:
                        continue
                    rel = os.path.relpath(full, root)
                    out.write(f"{st.st_mtime_ns}\t{digest(full)}\t{rel}\n")
                    count += 1
    os.replace(listfile + ".tmp", listfile)
    print(f"   datas anotadas: {count} arquivos")


def cmd_restore(root, listfile):
    if not os.path.exists(listfile):
        return
    kept = 0
    with open(listfile, encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t", 2)
            if len(parts) != 3:
                continue
            mtime_ns, sha, rel = int(parts[0]), parts[1], parts[2]
            full = os.path.join(root, rel)
            try:
                st = os.stat(full)
            except OSError:
                continue
            if st.st_mtime_ns == mtime_ns:
                kept += 1
                continue
            if digest(full) == sha:
                os.utime(full, ns=(st.st_atime_ns, mtime_ns))
                kept += 1
    print(f"   arquivos sem mudanca (data mantida): {kept}")


def cmd_sync(dst, srcs, patterns, manifest):
    os.makedirs(dst, exist_ok=True)
    previous = set()
    if os.path.exists(manifest):
        with open(manifest, encoding="utf-8") as f:
            previous = {l.strip() for l in f if l.strip()}
    current = {}
    for s in srcs:
        if not os.path.isdir(s):
            continue
        for name in sorted(os.listdir(s)):
            if any(fnmatch.fnmatch(name, p) for p in patterns):
                current[name] = os.path.join(s, name)
    copied = same = removed = 0
    for name, src in current.items():
        target = os.path.join(dst, name)
        if os.path.exists(target) and os.path.getsize(target) == os.path.getsize(src) and digest(target) == digest(src):
            same += 1
            continue
        shutil.copyfile(src, target)
        copied += 1
    stale = previous - set(current)
    if not previous:
        # primeiro build com este script: apaga codigo gerado antigo (o build.sh antigo apagava func_*/ovl*)
        for name in os.listdir(dst):
            if name not in current and (fnmatch.fnmatch(name, "func_*.cpp") or fnmatch.fnmatch(name, "ovl*.cpp")):
                stale.add(name)
    for name in stale:
        try:
            os.remove(os.path.join(dst, name))
            removed += 1
        except OSError:
            pass
    with open(manifest, "w", encoding="utf-8") as f:
        for name in sorted(current):
            f.write(name + "\n")
    print(f"   {dst}: {copied} atualizados, {same} iguais, {removed} removidos")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    mode = sys.argv[1]
    if mode == "snapshot":
        cmd_snapshot(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif mode == "restore":
        cmd_restore(sys.argv[2], sys.argv[3])
    elif mode == "sync":
        ap = argparse.ArgumentParser()
        ap.add_argument("--dst", required=True)
        ap.add_argument("--src", action="append", default=[])
        ap.add_argument("--pattern", action="append", default=[])
        ap.add_argument("--manifest", required=True)
        a = ap.parse_args(sys.argv[2:])
        cmd_sync(a.dst, a.src, a.pattern, a.manifest)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
