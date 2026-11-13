#!/usr/bin/env bash
# Roda o UN4 recompilado. Uso: bash recomp/run.sh [/caminho/da/iso]
# - usa a placa de video (no WSL, pelo driver d3d12)
# - le o disco direto da ISO, com os setores reais (precisa para o som e para o processador de audio)
set -euo pipefail
R="$(cd "$(dirname "$0")" && pwd)"
ISO="${1:-$(cat "$R/.iso_path" 2>/dev/null || true)}"
[ -n "$ISO" ] && [ -f "$ISO" ] || { echo "passe o caminho da ISO: bash recomp/run.sh /caminho/jogo.iso"; exit 1; }
realpath "$ISO" > "$R/.iso_path"
EXE="$(find "$R/PS2Recomp/out/game" -name ps2EntryRunner -type f | head -1)"
[ -n "$EXE" ] || { echo "rode antes: bash recomp/build.sh"; exit 1; }
export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
export PS2X_CD_IMAGE="$ISO"
# gravacoes de quadros do GS (tecla F9 no jogo, e algumas automaticas): ficam em recomp/gsdump
export UN4_GSDUMP_DIR="$R/gsdump"
mkdir -p "$UN4_GSDUMP_DIR"
rm -f "$UN4_GSDUMP_DIR"/gsdump_*.bin "$UN4_GSDUMP_DIR"/eeram_*.bin "$UN4_GSDUMP_DIR"/vu1cap_*.bin "$UN4_GSDUMP_DIR"/sdraw.bin "$UN4_GSDUMP_DIR"/eeprof.bin
# tela: abre em janela, com a imagem esticada na janela toda. F11 = tela cheia/janela, F10 = esticada/4:3.
# Para abrir em tela cheia: UN4_FULLSCREEN=1 bash recomp/run.sh
export UN4_FULLSCREEN="${UN4_FULLSCREEN:-0}"
export UN4_STRETCH="${UN4_STRETCH:-1}"
# controle: o WSL nao enxerga o controle USB, entao um script do lado do Windows le o controle (XInput,
# ex.: Xbox 360) e manda para o jogo. Ele fecha sozinho quando o jogo fecha.
WIN="${UN4_WINDIR:-/mnt/c/Users/rodri/OneDrive/Documentos/UN4Decomp}"
if [ -f "$WIN/recomp/pad_bridge.ps1" ] && command -v powershell.exe >/dev/null 2>&1; then
  (powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$(wslpath -w "$WIN/recomp/pad_bridge.ps1")" >/dev/null 2>&1 &) || true
fi
# Ctrl+C no terminal fecha so o jogo; o script continua e copia o log mesmo assim
trap 'echo; echo "(Ctrl+C: jogo fechado, copiando o log...)"' INT
"$EXE" "$R/game/SLUS_218.62" 2>&1 | (trap '' INT; exec tee "$R/run.log") || true
trap - INT

# copia um resumo compactado do log para a pasta do projeto no Windows (para o Claude ler direto)
if [ -d "$WIN" ]; then
  grep -v "BACKPRESSURE" "$R/run.log" | head -c 400000000 | gzip -c > "$WIN/run_log.gz" || true
  echo "log copiado para: $WIN/run_log.gz ($(du -h "$WIN/run_log.gz" | cut -f1))"
  # copia as gravacoes do GS (compactadas) para a pasta do projeto no Windows
  if ls "$UN4_GSDUMP_DIR"/gsdump_*.bin >/dev/null 2>&1; then
    mkdir -p "$WIN/gsdump"
    rm -f "$WIN/gsdump"/gsdump_*.bin.gz
    for f in "$UN4_GSDUMP_DIR"/gsdump_*.bin; do
      gzip -1 -c "$f" > "$WIN/gsdump/$(basename "$f").gz" || true
    done
    echo "gravacoes do GS copiadas para: $WIN/gsdump ($(du -sh "$WIN/gsdump" | cut -f1))"
  fi
  # copia da memoria do EE gravada pelo diagnostico da camera (quando a matriz chega com lixo)
  rm -f "$WIN/gsdump"/eeram_*.bin.gz "$WIN/gsdump"/vu1cap_*.bin.gz 2>/dev/null || true
  if ls "$UN4_GSDUMP_DIR"/eeram_*.bin >/dev/null 2>&1 || ls "$UN4_GSDUMP_DIR"/vu1cap_*.bin >/dev/null 2>&1; then
    mkdir -p "$WIN/gsdump"
    for f in "$UN4_GSDUMP_DIR"/eeram_*.bin "$UN4_GSDUMP_DIR"/vu1cap_*.bin; do
      [ -f "$f" ] || continue
      gzip -1 -c "$f" > "$WIN/gsdump/$(basename "$f").gz" || true
    done
    echo "memoria do EE copiada para: $WIN/gsdump"
  fi
  # amostra crua do som (diagnostico)
  if [ -f "$UN4_GSDUMP_DIR/sdraw.bin" ]; then
    mkdir -p "$WIN/gsdump"
    gzip -1 -c "$UN4_GSDUMP_DIR/sdraw.bin" > "$WIN/gsdump/sdraw.bin.gz" || true
  fi
  # perfil de CPU da thread do jogo (ultimo intervalo) + tabela de simbolos do executavel
  if [ -f "$UN4_GSDUMP_DIR/eeprof.bin" ]; then
    mkdir -p "$WIN/gsdump"
    cp "$UN4_GSDUMP_DIR/eeprof.bin" "$WIN/gsdump/eeprof.bin" || true
    nm -n --defined-only "$EXE" 2>/dev/null | gzip -c > "$WIN/gsdump/syms.txt.gz" || true
  fi
fi
