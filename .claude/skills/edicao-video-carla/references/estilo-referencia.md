# Estilo do vídeo de referência (medido)

Medidas tiradas quadro a quadro do vídeo de referência, em 1080x1920 e 30 quadros por segundo. As constantes estão em `edicao-video/ferramentas/`: legendas e efeitos de imagem em `render.py`, entradas, efeitos sonoros automáticos e enquadramento em `plan_tool2.py`, padrões das transições em `transitions.py`, UI em `ui_elements.py`, cor em `lut_teal.py`, trilha e efeitos em `synth.py`, mixagem em `mix.py`. Os ajustes próprios da Carla ficam no plano (`style`, `levels`, `grade`, `top_gap` do gancho). Este arquivo existe para você entender o que cada número significa antes de mudar algum. O estudo completo está no documento "Estudo do vídeo de referência para a edição da Carla" (https://claude.ai/artifact/KCfZzqJuRp3d4kGobsxpuG).

## Sumário

1. Legenda laranja (linha corrida)
2. Cartões brancos
3. Gancho
4. Entradas e saídas das legendas
5. Cortes e enquadramento
6. Transição de silhueta
7. Momento em preto e branco
8. Cor
9. Trilha, efeitos sonoros e mixagem
10. Ajustes próprios da Carla (não existem na referência)

## 1. Legenda laranja

- Instrument Sans Bold, cerca de 84 px, espaçamento entre letras de -4,38 px.
- Cor #FC7D01; no gancho, #F76405.
- Linha de base em y = 991 na referência; na Carla, 1258 (ver seção 10).
- Espaço entre palavras: 1,6 + 37,7 x k px. Em pouco mais da metade dos cartões com várias palavras, um único vão fica largo (k de 3 a 8), perto de x = 570. É estilo, não tem relação com as mãos; `gaps.py` aplica.
- Fica por cima da pessoa, sem recorte: não há legenda atrás do corpo.

## 2. Cartões brancos

- Bebas Neue, #FAFAFA, brilho difuso (desfoque de 8 px, opacidade 0,45).
- Uma linha: altura de maiúscula 225 px, largura máxima 1041 px.
- Duas linhas: as linhas têm a mesma largura (bloco de cerca de 890 px), com vão de 18 px, 35 px se a linha de baixo tiver acento agudo ou circunflexo e 53 px se tiver til.
- Modo "equal": duas palavras do mesmo tamanho, uma sobre a outra (usado em "NESSA / VIDA.").
- Cartão branco e laranja nunca aparecem juntos: um substitui o outro.

## 3. Gancho

Primeiros segundos: palavras brancas grandes no topo da área de legenda (as duas primeiras palavras da fala) e, logo abaixo, a continuação da frase em laranja, esticada para a mesma largura. Um efeito de "glitch" sonoro acompanha a entrada da linha laranja.

## 4. Entradas e saídas

- Corte seco: o cartão aparece inteiro.
- Entrada B (laranja): sobe cerca de 110 px em 6 quadros, com o primeiro quadro já levemente visível.
- Entrada A (laranja, só nos primeiros 8 s): palavra por palavra, com brilho em 81% e salto para 100%.
- Branco deslizando da direita em 4 a 5 quadros, primeiro quadro com cerca de 74% de opacidade.
- A segunda linha de um cartão branco entra cerca de 0,1 s antes de a palavra ser dita.
- Toda saída é corte seco. A troca de cartão acontece no início da primeira palavra do cartão seguinte.

## 5. Cortes e enquadramento

- Pausas reduzidas a cerca de 90 ms (mediana da referência), ritmo de umas 200 palavras por minuto. Na Carla as pausas ficam em cerca de 115 ms (45 ms antes da palavra seguinte e 70 ms depois da anterior), porque com menos folga finais de palavra ficavam raspados; o ritmo dela, naturalmente mais calmo, fica em torno de 150 palavras por minuto.
- Três tamanhos de plano trocados nos cortes. Na referência: 1,00, 1,17 e 1,30; na Carla, 1,08, 1,20 e 1,32, porque o enquadramento original dela já é fechado.
- Em cerca de dois terços dos cortes o tamanho muda; nos demais o plano desliza para o lado.
- Trechos curtos demais para parecer plano novo (menos de 0,5 s, ou menos de 0,9 s desde a última troca) mantêm o enquadramento: viram corte seco simples.

## 6. Transição de silhueta

O plano que entra aparece alguns quadros antes do corte como recorte da pessoa sobre o plano que sai, piscando por estados, e termina em quadro branco cheio. A legenda nova aparece já no quadro branco.

| Padrão | Quadros | Sequência |
| --- | --- | --- |
| T1 | 7 | branco, semi, normal, quente, normal, branco cheio, branco cheio |
| T2 | 7 | branco, semi 70%, frio, quente, normal, branco cheio, branco cheio |
| T3 | 5 | brilho, normal, preto, normal, branco cheio |
| T4 | 4 | branco, preto, normal, branco cheio |

Quatro transições por vídeo, uma de cada padrão, espalhadas (na Carla: cerca de 9%, 30%, 55% e 70% da duração), sempre no início de uma frase nova depois de uma pausa. A primeira não tem som; as outras têm "glitch".

## 7. Momento em preto e branco

Cerca de 22 quadros na referência (na Carla, cerca de 30, nas duas palavras de "nessa vida"), cedo no vídeo, numa frase de peso: dessatura e escurece com curva (sem desfoque), com efeito sonoro de impacto grave. Começa sempre num corte e nunca invade o plano seguinte.

## 8. Cor

LUT teal e laranja (`lut_teal.py`): pretos fechados, altas luzes sem estourar, fundo e tons neutros puxados para o ciano, pele protegida. Na Carla a pele e o cabelo loiro saturavam sob a luz quente do escritório, por isso `skin_sat` 0,80 e `skin_warm` 0.

## 9. Trilha, efeitos e mixagem

- Trilha ambiente original em sol menor (i, VII, VI, V, 4 s por acorde), introdução mais vazia e crescimento por volta de 30% do vídeo, cerca de 15 a 18 dB abaixo da voz, sem abaixar quando ela fala, final seco.
- Efeitos: impacto grave e "boom" nos cartões brancos que deslizam e no preto e branco; "glitch" nas transições 2 a 4 e no gancho; clique duplo em alguns cartões brancos entre 62% e 86% do vídeo.
- Voz feminina: corta graves abaixo de 120 Hz, reforça presença, controla sibilância, comprime e normaliza.
- Final em -14 LUFS e pico máximo de -1 dBTP; AAC 256 kb/s no arquivo mestre.

## 10. Ajustes próprios da Carla

A Carla grava em selfie fechada (rosto entre 24% e 54% da altura), com as mãos na altura do peito. Por isso:

- `style.dy` 267: todas as legendas descem 267 px, para o peito, deixando o rosto livre.
- Cartões de duas linhas menores (`max_cap` 210, `block_w` 820, `block_max` 900; "equal" com 215 e centro em 1250).
- Sombra suave atrás do laranja (`shadow_k` 0,55, desfoque 6 px, 3 px para baixo): sem ela o laranja some quando passa sobre as mãos. A referência não tem essa sombra.
- Faixa de UI entre 70% e 83% da altura, logo abaixo da linha laranja. É mais baixa que o padrão do código (68%), por escolha consciente: com as legendas no peito, não sobra espaço acima, e essa faixa ainda fica acima da área de texto do Reels.

Se ela gravar em outro lugar, com outra luz ou mais longe da câmera, esses valores precisam ser recalibrados com `preview.py` antes do render.
