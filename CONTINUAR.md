# Como continuar de onde parou (depois de formatar o PC ou clonar em outra máquina)

Este arquivo é o "ponto de retomada" do projeto: o que precisa instalar, como montar o jogo de novo,
em que pé cada coisa está e qual é o próximo passo. **Atualize a seção "Situação" sempre que algo mudar.**

O repositório **não tem nada do jogo**. Você precisa da sua ISO do
*Naruto Shippuden: Ultimate Ninja 4* (USA, SLUS-21862). Guarde a ISO fora do repositório (e faça
backup dela antes de formatar).

## 1. Do zero até o jogo abrir

1. **Windows:** instale o WSL com Ubuntu (PowerShell como administrador) e reinicie:
   ```powershell
   wsl --install -d Ubuntu
   ```
2. **Dentro do Ubuntu**, clone o projeto na pasta do Linux (não em `/mnt/c/...`, que é lento e
   não deixa as ferramentas rodarem):
   ```bash
   sudo apt update && sudo apt install -y git python3-pip make
   cd ~ && git clone https://github.com/SEU_USUARIO/UN4Decomp.git && cd UN4Decomp
   ```
3. **Monte a versão de PC** (passe o caminho da sua ISO; só precisa na primeira vez):
   ```bash
   bash recomp/build.sh "/mnt/c/Users/<você>/.../Naruto Shippuden - Ultimate Ninja 4 (USA) (En,Fr).iso"
   ```
   O script instala as dependências, extrai o jogo da ISO para `recomp/game/` (~3,7 GB), baixa o
   PS2Recomp no commit certo, aplica todos os `recomp/*.patch`, traduz o jogo para C++ e compila.
   **O primeiro build demora bastante** (~10 mil arquivos). Se o WSL travar por falta de memória:
   `JOBS=4 bash recomp/build.sh ...`
4. **Rode:**
   ```bash
   bash recomp/run.sh
   ```
   Nas próximas vezes: `bash recomp/build.sh "$(cat recomp/.iso_path)"` e `bash recomp/run.sh`.

## 2. Controles e teclas

- **Controle:** qualquer controle XInput (Xbox 360/One) ligado no Windows. O WSL não enxerga USB,
  então o `run.sh` abre o `recomp/pad_bridge.ps1` no Windows, que lê o controle e manda para o jogo
  pela porta 28862. A=X, B=bolinha, X=quadrado, Y=triângulo, LB/RB=L1/R1, gatilhos=L2/R2.
  O teclado continua funcionando.
- **F9:** grava um quadro para diagnóstico (imagem do GS, memória do jogo, amostra do VU1).
- **F10:** imagem esticada / 4:3. **F11:** tela cheia / janela.
- Variáveis: `UN4_FULLSCREEN=1`, `UN4_STRETCH=0`, `UN4_SOM=0` (sem som), `UN4_VU1_LENTO=1`
  (interpretador antigo do VU1), `UN4_PROFILE=0` no build (sem medidor de funções).

## 3. As duas pastas (importante para trabalhar com o Claude)

- **Pasta do Windows** (`Documentos\UN4Decomp`, ligada ao Claude): é onde o Claude grava os
  patches novos e de onde ele lê os resultados dos testes.
- **Pasta do WSL** (`~/UN4Decomp`): é onde o jogo é compilado e rodado.

Fluxo de cada teste:
1. O Claude grava um `recomp/un4_*.patch` (ou script) na pasta do Windows.
2. Leve as novidades para o WSL e compile (ajuste o caminho se o seu for outro):
   ```bash
   cp -ru /mnt/c/Users/<você>/OneDrive/Documentos/UN4Decomp/recomp/. ~/UN4Decomp/recomp/
   bash recomp/build.sh "$(cat recomp/.iso_path)" && bash recomp/run.sh
   ```
3. Jogue até o ponto do problema, aperte **F9** se for coisa de imagem, e **feche o jogo**.
4. O `run.sh` copia sozinho o log (`run_log.gz`) e as capturas (`gsdump/`) para a pasta do Windows
   (caminho em `UN4_WINDIR`; o padrão está no `run.sh`). O Claude lê de lá.

Para retomar com o Claude numa conversa nova: ligue a pasta do Windows na conversa e peça para ele
ler este arquivo e o `ROADMAP.md`.

## 4. Como os patches funcionam

O `build.sh` volta o PS2Recomp ao original e aplica **todos** os `recomp/*.patch` em ordem
alfabética (por isso os nomes com `z`, `zz`, ... : os mais novos vêm depois). Para desfazer uma
mudança, apague o patch e compile de novo.

| Grupo | Patches | O que faz |
|---|---|---|
| Boot e sistema | `un4_fix_branch64`, `callback_stack`, `invocation_stacks`, `priority`, `spin_yield`, `zsched_*`, `zheap_layout`, `zvblank_catchup` | Erros de tradução e de threads que travavam o boot |
| Disco | `un4_fix_cd_image`, `iop_ioman`, `iop_heap_reuse` | Leitura direto da ISO, arquivos CVM/AFS |
| Vídeo da intro | `un4_fix_mpeg_callbacks`, `mpeg_lead`, `field_weave` | Vídeo PSS |
| Imagem (GS/VIF/VU) | `un4_fix_gs_*`, `gif_dma_madr`, `vif_image`, `vu0_*`, `vu1_minmax`, `zvu0_qdiv`, `zvif_tags`, `zperf_gs` | Menus e luta desenhando certo; `zvif_tags` = lista de desenho da luta tem ~12 mil tags |
| Matemática | `un4_fix_hle_math`, `zzzzzzz_fpu_sqrt_cvt`, `zzzzzzzz_mmi_phmadh` | Funções e instruções do processador traduzidas errado (câmera, som, vozes) |
| Controle e tela | `un4_fix_pad_pressure`, `zzz_pad_tela` | Controle pelo Windows, janela esticada |
| Som | `un4_fix_iop_libsd`, `zzzzzz_som` | Música e vozes (fluxo ADX/AHX → saída de áudio) |
| Desempenho | `zzzzz_vu1_rapido` | Interpretador rápido do VU1 |
| Diagnóstico (podem sair no fim) | `un4_debug*`, `un4_profile`, `zgsdump`, `zthread_diag`, `zvu1_diag`, `zvif_spr`, `zzf9_ram`, `zzzz_perf_diag` | Logs, F9, medidores |

## 5. Situação (atualizado em 13/11/2026)

**Funciona:** boot, vídeo da intro (sem som), título, menus, MODE SELECT, seleção de personagem,
luta com cenário + personagens + HUD, controle, janela esticada, música.

**Problemas conhecidos:**
- **Voz chiando** (Naruto falando no MODE SELECT): causa achada (instrução `PHMADH`), correção em
  `un4_zzzzzzzz_mmi_phmadh.patch`, **falta confirmar no teste**.
- **Sem efeitos sonoros** (golpes, cursor) e **sem som no vídeo da intro**: ainda não feito.
- **HUD da luta errado:** ícones dos itens trocados e a vida do jogador 2 aparece como a do jogador 1.
- **FPS baixo na luta** (~11 de 60; o jogo fica em câmera lenta). A thread do jogo está saturada:
  ~35% no VU1, ~31% no desenho do GS por software.

**Próximos passos, na ordem combinada:**
1. Som: confirmar a voz → efeitos sonoros → som da intro.
2. HUD da luta.
3. FPS: (a) dividir o desenho do GS entre os núcleos parados; (b) tirar VIF1/VU1/GS da thread do
   jogo; (c) traduzir o microcódigo do VU1 em vez de interpretar (necessário para chegar a 60).
4. Widescreen de verdade, limpeza dos patches de diagnóstico.
5. Modo história (`RPG.BIN`) por último. Depois: Vita.

## 6. Anotações técnicas úteis

- PS2Recomp fixado no commit `e5636981` (está no `build.sh`).
- `$gp = 0x60EF70`. Gerente da luta: ponteiro em `0x609794`; jogadores em `+0x104` e `+0x108`.
- O recompilador troca por versões prontas toda função cujo nome está na lista de bibliotecas;
  várias dessas versões estavam erradas (`sceVu0*`, `sin/cos/atan/floor/fabs`), por isso o
  `un4_fix_hle_math` manda recompilar o código real do jogo.
- Som: o jogo decodifica ADX/AHX no processador principal e manda PCM para o IOP
  (`sceSdBlockTrans`, 48 kHz, 16 bits, blocos de 512 bytes esquerda/direita).
- Mexer em `ps2_runtime.h`, `ps2_runtime_macros.h`, `un4_profile.h` ou `ps2_vu1.h` recompila os
  ~10 mil arquivos; mudanças em `.cpp` não.
