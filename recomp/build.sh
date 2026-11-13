#!/usr/bin/env bash
# Monta a versao recompilada do UN4 para PC (experimental), usando o PS2Recomp.
# Uso (dentro do Ubuntu/WSL, na pasta do projeto):
#   bash recomp/build.sh "/mnt/c/.../Naruto Shippuden - Ultimate Ninja 4 (USA) (En,Fr).iso"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
R="$ROOT/recomp"
ISO="${1:-}"
# guarda o caminho da ISO para o run.sh (o jogo le o disco direto da ISO, com os setores reais)
[ -n "$ISO" ] && realpath "$ISO" > "$(cd "$(dirname "$0")" && pwd)/.iso_path"
PS2RECOMP_COMMIT=e5636981a1c9de368f6b71e819c3dc188dfedbf4
JOBS="${JOBS:-$(nproc)}"

echo "== 1/6 dependencias do sistema"
sudo apt-get install -y build-essential cmake git ninja-build \
  libx11-dev libxrandr-dev libxinerama-dev libxcursor-dev libxi-dev \
  libgl1-mesa-dev libasound2-dev libpulse-dev pkg-config \
  libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libswscale-dev

echo "== 2/6 arquivos do jogo (da sua ISO)"
if [ ! -f "$R/game/SLUS_218.62" ]; then
  [ -n "$ISO" ] || { echo "passe o caminho da ISO: bash recomp/build.sh /caminho/jogo.iso"; exit 1; }
  python3 "$ROOT/tools/extract_iso.py" "$ISO" "$R/game"
fi
sha256sum "$R/game/SLUS_218.62" | grep -q fefb3b546e41e80e829faee107a73f7599167a1446f781207ae69310e5105407 \
  || { echo "executavel inesperado: precisa ser o UN4 USA (SLUS-21862)"; exit 1; }

echo "== 3/6 PS2Recomp"
if [ ! -d "$R/PS2Recomp" ]; then
  git clone https://github.com/ran-j/PS2Recomp.git "$R/PS2Recomp"
fi
git -C "$R/PS2Recomp" checkout -q "$PS2RECOMP_COMMIT"
git -C "$R/PS2Recomp" submodule update --init --recursive
# ajustes do UN4Decomp no runtime, no IOP e no recompilador: volta os arquivos ao original e aplica todos os patches de novo
# (assim um patch atualizado substitui a versao antiga sem conflito)
# sync_tree.py guarda a data dos arquivos que nao mudaram, para o ninja so recompilar o que mudou de verdade
mkdir -p "$R/build"
SNAP="$R/build/.datas_ps2recomp"
PATCHED_DIRS="ps2xRuntime/src/lib ps2xRuntime/include ps2xIOP ps2xRecomp/src ps2xRecomp/include"
python3 "$R/sync_tree.py" snapshot "$R/PS2Recomp" "$SNAP" $PATCHED_DIRS
git -C "$R/PS2Recomp" checkout -q -- $PATCHED_DIRS
git -C "$R/PS2Recomp" clean -fdq -- $PATCHED_DIRS
for p in "$R"/*.patch; do
  [ -f "$p" ] || continue
  echo "   patch: $(basename "$p")"
  git -C "$R/PS2Recomp" apply "$p"
done
python3 "$R/sync_tree.py" restore "$R/PS2Recomp" "$SNAP"
cmake -S "$R/PS2Recomp" -B "$R/PS2Recomp/out/tools" -G Ninja -DCMAKE_BUILD_TYPE=Release \
  -DPS2X_BUILD_RUNTIME=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF
cmake --build "$R/PS2Recomp/out/tools" -j "$JOBS"

echo "== 4/6 recompilando o codigo do jogo para C++"
python3 "$ROOT/tools/make_recomp_csv.py"
rm -rf "$R/build/output"; mkdir -p "$R/build/output"
(cd "$R" && "$R/PS2Recomp/out/tools/ps2xRecomp/ps2_recomp" config.toml | tail -3)
echo "== 4b/6 recompilando os modulos HOME/BATTLE/RPG/TEXT (overlays)"
python3 "$R/overlays.py" 2>&1 | grep -v "\[warning\]"

# medidor de funcoes (diagnostico do boot); desligue com UN4_PROFILE=0
if [ "${UN4_PROFILE:-1}" != "0" ]; then
  python3 "$R/profile_inject.py" "$R/build/output" "$R/build/ovl_output"
fi

echo "== 5/6 compilando o runtime + jogo (o 1o build demora: sao ~10 mil arquivos; depois so o que mudou)"
RUN="$R/PS2Recomp/ps2xRuntime"
# copia o codigo gerado so quando o conteudo mudou (arquivo igual mantem a data e nao e recompilado)
python3 "$R/sync_tree.py" sync --dst "$RUN/src/runner" --src "$R/build/output" --src "$R/build/ovl_output" \
  --pattern '*.cpp' --pattern '*.h' --manifest "$R/build/.arquivos_runner"
python3 "$R/sync_tree.py" sync --dst "$RUN/include" --src "$R/build/output" --src "$R/build/ovl_output" \
  --pattern '*.h' --manifest "$R/build/.arquivos_include"
python3 "$R/sync_tree.py" restore "$R/PS2Recomp" "$SNAP"
# GCC precisa das instrucoes SSE4/AVX ligadas (no Windows o MSVC usa /arch:AVX2).
# RelWithDebInfo sem -g: otimizado, mas sem LTO (LTO em ~10 mil arquivos estoura a memoria).
OPT="-O2 -DNDEBUG -march=native"
cmake -S "$R/PS2Recomp" -B "$R/PS2Recomp/out/game" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_C_FLAGS_RELWITHDEBINFO="$OPT" -DCMAKE_CXX_FLAGS_RELWITHDEBINFO="$OPT" \
  -DPS2X_BUILD_RECOMP=OFF -DPS2X_BUILD_ANALYZER=OFF -DPS2X_BUILD_TEST=OFF -DPS2X_BUILD_STUDIO=OFF \
  -DPS2X_ENABLE_AGRESSIVE_LOGS=OFF -DPS2X_STRICT_RETURN_DIAGNOSTICS=ON \
  -DCMAKE_EXE_LINKER_FLAGS="-rdynamic"
# cada arquivo gerado usa bastante memoria para compilar; limite com JOBS=4 se o WSL travar
cmake --build "$R/PS2Recomp/out/game" -j "$JOBS"

echo "== 6/6 pronto"
EXE="$(find "$R/PS2Recomp/out/game" -name ps2EntryRunner -type f | head -1)"
echo "Para rodar:  bash recomp/run.sh"
