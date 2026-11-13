# UN4Decomp — decompilação do Naruto Shippuden: Ultimate Ninja 4

Projeto para transformar o executável do **Naruto Shippuden: Ultimate Ninja 4** (PS2, versão
americana, SLUS-21862) de volta em código C. A decompilação é o primeiro degrau para um port
nativo, do mesmo jeito que o BT3 chegou ao PS Vita: decompilação → port para PC → port para Vita.

**Este projeto não contém nada do jogo.** O executável sai da sua própria ISO, e as pastas
`baserom/`, `asm/` e `build/` nunca devem ser publicadas (já estão no `.gitignore`).

## Situação atual

| Etapa | Situação |
|---|---|
| Executável extraído e conferido (sha256) | ✅ |
| Desmontado com o splat (9.875 funções, 3,1 MB de código) | ✅ |
| Reconstrução **byte a byte idêntica** ao original a partir do assembly | ✅ |
| Fluxo de decompilação função por função (`make match`) | ✅ |
| Funções decompiladas com 100% de igualdade | 4 |
| 722 funções das bibliotecas da Sony identificadas pelo nome | ✅ |
| Jogo inteiro recompilado automaticamente para C++ (PS2Recomp) | ✅ |
| **Versão de PC:** boot, intro, menus e luta abrindo, com controle e música | ✅ (lento na luta, som incompleto) |
| Módulo `RPG.BIN` (modo história) | ⏳ por último |

**Vai continuar o projeto em outro PC ou depois de formatar? Leia [CONTINUAR.md](CONTINUAR.md).**

## O que já descobrimos sobre o jogo

- **Mapa do executável principal** (carregado em `0x00100000`):
  - `0x00100000–0x003F6180`: código principal (9.855 funções)
  - `0x003F6180–0x005D9000`: dados e microcódigo das unidades vetoriais (VU) do PS2
  - `0x005D9000–0x005EAA00`: código de inicialização (construtores estáticos, 20 funções)
  - `0x005EAA00–0x00609500`: dados
  - `0x00609500–0x0089D980`: memória zerada (bss)
  - `$gp = 0x0060EF70`
- **Módulos de código** carregados sob demanda no endereço `0x006B8200`: `BATTLE.BIN`
  (luta, ~4.200 funções), `RPG.BIN` (modo história, ~3.300) e `HOME.BIN`. Os textos
  (`TEXTENG.BIN`/`TEXTFRN.BIN`) vão para `0x0086A000`.
- **Compilador:** parte do código bate exatamente com o **Metrowerks CodeWarrior para PS2,
  versão 3.0.1 (build 205, dez/2005) com `-O2`**. O executável foi gerado em 22/02/2006.
- **Outra parte ainda não bate** com nenhuma versão do Metrowerks: ela salva registradores
  com instruções de 64 bits (`sd`) onde o Metrowerks usa 128 bits (`sq`). Suspeita principal:
  essa parte foi compilada com o EE-GCC 2.96 da Sony. Veja `src/wip/LEIA.md`.
- **Mesmo motor do Ultimate Ninja 5:** os módulos de luta e história dos dois jogos têm 2.259
  textos internos idênticos (nomes de animação, modelo, câmera, formato `.ccs` da CyberConnect2).
  Existe uma decompilação do UN5 em andamento:
  https://github.com/MiguelQueiroz010/Decomp-no-Me-UN5Decomp

O plano completo (abrir → intro → menu → luta → história) está em **[ROADMAP.md](ROADMAP.md)**.

## Como usar

O projeto roda em **Linux** ou no **WSL** do Windows (Ubuntu). No Windows: `wsl --install -d Ubuntu`
no PowerShell. **Trabalhe com o projeto dentro do Linux** (por exemplo `~/UN4Decomp`), não em
`/mnt/c/...`: pastas do Windows/OneDrive não deixam as ferramentas rodarem e são bem mais lentas.

```bash
sudo apt install python3-pip make
pip install -r requirements.txt          # splat, spimdisasm
python3 tools/setup_tools.py             # baixa compilador, montador, objdiff para tools/bin/
python3 tools/setup.py "/mnt/c/Users/<você>/OneDrive/Documentos/PS2/Naruto Shippuden - Ultimate Ninja 4 (USA) (En,Fr).iso"
make                                     # reconstrói e confere: deve dizer "OK: reconstrucao identica"
```

Depois de mudar `config/SLUS_218.62.yaml` ou `config/symbol_addrs.txt`, rode `make split` e `make`.

### Rodar a versão recompilada no PC (experimental)

```bash
bash recomp/build.sh "/mnt/c/Users/<você>/OneDrive/Documentos/PS2/Naruto Shippuden - Ultimate Ninja 4 (USA) (En,Fr).iso"
```

O script instala as dependências, extrai os arquivos do jogo da sua ISO para `recomp/game/`
(~3,7 GB), baixa e compila o [PS2Recomp](https://github.com/ran-j/PS2Recomp), traduz o código do
jogo para C++ e compila tudo. A compilação é longa (são ~10 mil arquivos). No fim ele mostra o
comando para rodar; o log da execução (`recomp/run.log`) mostra até onde o jogo chegou.

### Testar o compilador da Sony (EE-GCC 2.96)

```bash
bash tools/setup_eegcc.sh
```

Testa as funções de `src/wip/` com o EE-GCC. Se alguma bater 100%, achamos o segundo compilador.

### Decompilar uma função

1. Escolha uma função em `asm/main/text.s` (comece pelas pequenas).
2. Escreva o C dela em `src/main/func_XXXXXXXX.c`.
3. Rode `make match FUNC=func_XXXXXXXX`. Se der **100%**, ela entra em `config/matched.txt`.
4. Veja o progresso com `make progress`.

`tools/match.py` aceita `--compiler` e `--flags` para testar outras combinações
(as versões disponíveis ficam em `tools/bin/compilers/`).

## Próximos passos

1. **Rodar a versão recompilada** (`recomp/build.sh`) e anotar até onde o boot chega.
2. **Identificar o compilador da segunda parte do código** (`tools/setup_eegcc.sh`).
3. Configurar `BATTLE.BIN` no splat como overlay em `0x006B8200`: é o coração do modo luta.
4. Dar nomes às funções e estruturas conforme forem entendidas (`config/symbol_addrs.txt`).
5. Conversar com o autor da decompilação do UN5 para dividir descobertas sobre o motor.
6. Ligar as funções já decompiladas na reconstrução do executável (hoje a reconstrução usa
   só o assembly; o `make match` confere cada função isoladamente).

## Estrutura

```
config/SLUS_218.62.yaml   configuração do splat (mapa do executável)
config/symbol_addrs.txt   nomes de funções/variáveis já identificados
config/matched.txt        funções que já batem 100%
config/sony_libs.txt      funções das bibliotecas da Sony (não precisam ser decompiladas)
recomp/                   configuração e script da versão recompilada (PS2Recomp)
src/main/                 funções decompiladas
src/wip/                  funções em andamento
tools/setup.py            extrai e confere o executável da sua ISO
tools/setup_tools.py      baixa as ferramentas
tools/match.py            compila uma função e compara com o original
tools/check.py            confere a reconstrução byte a byte
tools/progress.py         mostra o progresso
tools/extract_iso.py      extrai todos os arquivos da ISO
tools/make_recomp_csv.py  gera a lista de funções para o PS2Recomp
tools/setup_eegcc.sh      instala e testa o EE-GCC 2.96
```

## Créditos das ferramentas

[splat](https://github.com/ethteck/splat), [spimdisasm](https://github.com/Decompollaborate/spimdisasm),
[objdiff](https://github.com/encounter/objdiff), [wibo](https://github.com/decompals/wibo),
[binutils-mips-ps2-decompals](https://github.com/decompals/binutils-mips-ps2-decompals) e os
compiladores preservados pelo [decomp.me](https://github.com/decompme/compilers).
