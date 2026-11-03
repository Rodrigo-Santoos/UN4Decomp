# Funcoes em andamento

Estas funcoes ainda **nao** batem 100%. O C esta logicamente certo, mas o codigo gerado
difere do original em um ponto: o jogo salva os registradores `s0`/`s1` com `sd` (64 bits),
e todas as versoes do Metrowerks testadas salvam com `sq` (128 bits). Tambem preenchem
os "delay slots" (otimizacao com scheduling), ao contrario das funcoes ja decompiladas.

Hipotese: esta parte do jogo foi compilada com outro compilador ou outra configuracao
(candidato forte: EE-GCC 2.96 da Sony, cuja assinatura "GCC2096" aparece no executavel).
Descobrir isso e o proximo passo importante do projeto.

Melhor resultado ate agora (Metrowerks 3.0.1b205, -O3):

| funcao | match |
|---|---|
| func_0012E398 | 80.4% |
| func_001377E0 | 45.7% |
| func_00124970 | 45.0% |
| func_0011D020 | 28.0% |
| func_0013B168 | 67.8% (Metrowerks 2.4, -O3) |

Para testar: copie o arquivo para `src/main/` e rode `make match FUNC=func_XXXXXXXX`.
