# Plano: Naruto Shippuden: Ultimate Ninja 4 rodando nativo no PC (e depois no Vita)

Ordem combinada: **1) o jogo abre → 2) intro → 3) menu → 4) luta → 5) modo história por último.**

## Os dois caminhos, trabalhando juntos

| | Recompilação (PS2Recomp) | Decompilação (este projeto) |
|---|---|---|
| O que é | Tradução **automática** de cada instrução MIPS para C++ | Reescrever cada função à mão, em C legível |
| Velocidade | O jogo inteiro de uma vez (9.878 funções em ~10 s) | Função por função |
| Resultado | Código ilegível, lento nas partes gráficas (VU/GS) | Código entendível, fácil de portar e otimizar |
| Papel aqui | **Fazer o jogo abrir no PC cedo** | **Ir substituindo o código recompilado** com o tempo |

A ideia é usar a recompilação para ver o jogo funcionando no PC o quanto antes, e a
decompilação para ir trocando, aos poucos, as partes recompiladas por código de verdade,
começando pelo que estiver travando ou lento.

## Fase 1: o jogo abre no PC (recompilação)

- [x] Executável recompilado inteiro para C++ (9.878 funções, 1 instrução não suportada).
- [x] 722 funções das bibliotecas da Sony identificadas pelo nome (gráfico, DMA, controle,
      CD, memory card, som, vídeo MPEG). O runtime do PS2Recomp substitui várias delas.
- [x] Script de montagem: `recomp/build.sh`.
- [ ] Compilar e rodar no PC pela primeira vez, e anotar até onde o boot chega (`recomp/run.log`).
- [ ] Corrigir os bloqueios em ordem: função não encontrada → syscall faltando → arquivo não lido.

## Fase 2: intro

- A abertura é um vídeo `.PSS` (MPEG2 da Sony, pasta `PSS/`). O jogo usa a `libipu`/`libmpeg`;
  o vídeo precisa da decodificação do IPU no runtime.
- Os dados ficam em arquivos `.CVM` (sistema de arquivos ROFS da CRI) e `.AFS`; a leitura deles
  precisa funcionar no runtime.

## Fase 3: menu

- O menu principal provavelmente está no módulo `HOME.BIN` (carregado em `0x006B8200`).
- Precisa: desenho 2D (GS), controle (`libpad`), memory card (`libmc`), som (`libsdr` + CRI ADX).

## Fase 4: luta

- Módulo `BATTLE.BIN` (~4.200 funções), carregado no mesmo endereço do `HOME.BIN`.
- Aqui entra o peso: modelos 3D desenhados pelo microcódigo VU1 do jogo. O PS2Recomp avisa que
  essa parte é muito lenta; é onde a decompilação e um renderizador próprio fazem diferença.
- **Reaproveitar a base do port do BT3** (Tenkaichi3Decomp): ele já substitui as mesmas
  bibliotecas da Sony, **na mesma versão 3.1.0** que o UN4 usa (gráfico, controle, CD,
  memory card, som), e tem um renderizador do GS para Vulkan/OpenGL e para o Vita (vitaGL).

## Fase 5: modo história

- Módulo `RPG.BIN` (~3.300 funções). Por último, como combinado.

## Depois: Vita

- O PS2Recomp já tem suporte inicial a Vita, mas o código recompilado é pesado demais para o
  hardware do Vita. Para o Vita, a parte do jogo que roda o tempo todo (luta, gráficos) precisa
  estar decompilada e otimizada, como foi feito no BT3.

## Números de referência

- Executável: 9.878 funções; 722 são bibliotecas da Sony; **9.156 são código do jogo**.
- Código alcançado diretamente a partir do boot: ~4.000 funções do jogo (sem contar ponteiros
  de função e os módulos `.BIN`).
- Decompiladas com 100%: veja `make progress`.
