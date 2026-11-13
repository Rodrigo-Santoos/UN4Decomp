#!/usr/bin/env bash
# Instala o EE-GCC 2.96 da Sony (suspeito de ser o 2o compilador do jogo) e testa nas funcoes de src/wip.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$ROOT/tools/bin/compilers/ee-gcc2.96"
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get install -y libc6:i386
if [ ! -x "$D/bin/ee-gcc" ]; then
  mkdir -p "$D"
  curl -L https://github.com/decompme/compilers/releases/download/compilers/ee-gcc2.96.tar.xz | tar xJ -C "$D"
fi
cd "$ROOT"
mkdir -p build/eegcc-test; : > build/eegcc-test/resultado.txt
for c in src/wip/func_*.c; do
  f=$(basename "$c" .c)
  cp "$c" src/main/
  ok=0
  for flags in "-O2 -G0" "-O1 -G0" "-O3 -G0" "-O2 -G8"; do
    r=$(python3 tools/match.py "$f" --compiler ee-gcc2.96 --flags "$flags" 2>&1 | grep -m1 "igual\|falhou" || true)
    printf '%-16s %-10s %s\n' "$f" "$flags" "$r" | tee -a build/eegcc-test/resultado.txt
    case "$r" in *"100.00%"*) ok=1; break;; esac
  done
  if [ "$ok" = 1 ]; then rm "$c"; echo "  -> $f bateu 100% com o EE-GCC!"; else rm "src/main/$f.c"; fi
done
echo "Resultado salvo em build/eegcc-test/resultado.txt"
