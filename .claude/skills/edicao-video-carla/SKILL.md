---
name: edicao-video-carla
description: Edita vídeos de fala da Carla (cliente da Havanna) no estilo do vídeo de referência já estudado, com legenda laranja corrida, cartões brancos em Bebas Neue, cortes sem pausas com três tamanhos de plano, transições de silhueta com quadro branco, momento em preto e branco, cor teal com pele protegida, elementos de UI ligados à fala, trilha e efeitos originais, entregando o vídeo pronto no chat. Use sempre que o usuário mandar um link do Drive ou um arquivo de vídeo da Carla para editar, pedir "edita esse vídeo", "mesmo estilo do anterior", "faz igual ao último da Carla", ou pedir ajuste num vídeo da Carla já editado (palavra cortada, legenda, transição, cor), mesmo sem citar a palavra skill.
---

# Edição de vídeo da Carla no estilo da referência

Esta skill transforma um vídeo bruto de fala da Carla em um Reels pronto, no mesmo estilo do primeiro vídeo entregue e aprovado (plano em `edicao-video/planos/carla_plan.json`). As ferramentas estão em `edicao-video/ferramentas/` e o README daquela pasta descreve cada uma.

Separe sempre duas coisas. **O estilo é fixo e já está no código**: fontes, cores, animações, transições, preto e branco, trilha, efeitos e mixagem. **As decisões editoriais são de cada vídeo e são suas**: o que cortar, quais frases viram cartão branco, onde entram gancho, preto e branco, transições e UI. Foi nas decisões, e não no código, que aconteceram os erros do primeiro vídeo; por isso a maior parte desta skill trata de como decidir e conferir.

As medidas do estilo estão em `references/estilo-referencia.md`. Leia antes de mexer em qualquer constante ou se o vídeo novo tiver enquadramento diferente.

## Comunicação com o usuário

- Escreva sempre em português do Brasil, inclusive nas descrições das ferramentas, que o usuário também lê. As regras de escrita dele valem para tudo o que é visível: "para", nunca "pra" ou "pro"; sem reticências; sem travessão no lugar de vírgula; sem emojis; pontuação formal.
- Trabalhe até a entrega sem parar para pedir aprovação no meio. Ajustes vêm depois que ele assistir.
- Dê atualizações curtas durante as esperas longas (montagem, render), dizendo em que etapa está.

## Ambiente

A sessão roda num contêiner de nuvem temporário: modelos, fontes e vídeos somem quando ela termina. Prepare tudo numa pasta de dados dentro do scratchpad:

```bash
export EDV_HOME=<scratchpad>/edv                                   # pasta de dados; exporte em todo comando que usar as ferramentas
F=$(git rev-parse --show-toplevel)/edicao-video/ferramentas        # caminho absoluto das ferramentas
bash $F/setup.sh                                                   # alguns minutos: modelos de fala, recorte de pessoa, fontes, OpenCV 4
```

- O ffmpeg vem do pacote imageio e não há `ffprobe`; para ler duração e trilhas use `ffmpeg -hide_banner -i arquivo`.
- O download do Drive precisa que a rede do ambiente libere `drive.usercontent.google.com`. Se vier bloqueado, explique e peça para o usuário ajustar a rede do ambiente. Não contorne a política de rede por outros serviços: uma tentativa assim já foi barrada.
- `git push` exige o app do Claude instalado na organização HavannaBrasil. Já foi instalado; se voltar o erro 403, oriente reinstalar por https://claude.ai/connect-github.

## Passo 1: localizar e baixar o vídeo

O usuário costuma mandar o link de uma **pasta** do Drive. Use o conector do Google Drive (`search_files` dentro da pasta) para achar o arquivo de vídeo e o ID dele. O download pelo próprio conector tem limite de uns 10 MB, então baixe com o script:

```bash
bash $F/intake.sh <id ou link do arquivo> <nome-do-trabalho>
```

Ele baixa, converte o HDR do iPhone para SDR, normaliza para 1080x1920 a 30 quadros por segundo e transcreve com dois modelos: Parakeet, com tempo por palavra (`words.json`), e Whisper, para conferir o texto. Tudo fica em `$EDV_HOME/work/<nome>`.

## Passo 2: ler a fala e decidir o que sai

Leia as duas transcrições e marque recomeços (no primeiro vídeo: "e querer provar para o mundo, que tá querendo provar para o mundo"), frases abandonadas e vícios. Os trechos que saem são faixas de palavras fora de `keep`.

**Regra de conferência, a mais importante desta skill.** Antes de tirar um trecho ou de forçar um ponto de corte com `hard`, prove com o reconhecimento de fala que nenhuma palavra fica pela metade:

```bash
cd $EDV_HOME/work/<nome> && python3 $F/asr_clip.py mezz.mov 14.30:15.00 14.30:15.48
```

- Reconheça o trecho que **termina exatamente no corte planejado, sozinho**. A última palavra precisa sair completa. Foi esse teste, feito tarde, que revelou "ninho" no lugar de "ninguém" e "maturi" no lugar de "maturidade".
- O juiz é o Parakeet. O Whisper inventa repetições ("Maturidade. Maturidade. Mat") e serve só para conferir o texto.
- Não confie em teste de emenda, em que dois trechos são colados e reconhecidos juntos: o modelo completa a palavra truncada pelo contexto ("maturi" + "é você" vira "maturidade é você").
- Um silêncio de 40 a 80 ms dentro de uma palavra é o fechamento de uma consoante (g, d, t, p, k), não o fim dela. Fim de palavra de verdade tem pelo menos uns 150 ms de silêncio. Os dois erros do primeiro vídeo foram exatamente isso: "nin|guém" e "maturi|dade".
- Se o reconhecimento mostrar uma palavra solta logo depois de outra ("Quem?" depois de "ninguém"), suspeite primeiro que é a segunda metade da palavra anterior, e só depois que é um vício de fala.

Prefira o modo por energia (`snap_energy: true`), que corta só onde o áudio está de fato em silêncio. Use `hard` só para recomeços sem pausa, e sempre conferido.

## Passo 3: escrever o plano

Copie `edicao-video/planos/carla_plan.json` como ponto de partida; o formato está no topo de `edicao-video/ferramentas/plan_tool2.py`. Mantenha `src`, `style`, `levels`, `grade`, `snap_energy`, `min_pause` 0,20, `silence_db` -45, `keep_pause_out` 0,07, `framing`, `sfx` e `music`, que foram calibrados para a Carla. Troque `out` pelo nome do trabalho e refaça do zero tudo o que é deste vídeo: `keep`, `hard`, `text`, `breath`, `cut_at`, `cards`, `bw`, `transitions` e `ui`, porque os índices de palavra do plano antigo não valem para outra fala. Gere a LUT dentro da pasta do trabalho, com o mesmo nome que o plano usa: `python3 $F/lut_teal.py carla.cube 1.0 0.07 0.90 0.0 1.0 0.80`.

Critérios para as legendas, vindos da referência:

- **Gancho** nas duas primeiras palavras, em branco grande, com a continuação da frase em laranja embaixo.
- **Cartões brancos** nas palavras de impacto, um a cada 3 a 5 s em média, de uma ou duas linhas curtas. Alterne entradas por corte e deslizando. Use "equal" uma vez, no preto e branco.
- **Laranja** no resto, de 2 a 5 palavras por cartão, quebrando nas unidades de sentido da frase.
- **Preto e branco** uma vez, cedo (entre 5 e 8 s), numa frase de peso.
- **Quatro transições** (T1, T2, T3 e T4), por volta de 9%, 30%, 55% e 70% da duração, sempre no início de uma frase nova depois de uma pausa.
- **`cut_at`** nas frases longas sem pausa, para ter troca de plano a cada 2 s, mais ou menos.
- **Texto na norma culta:** "tá" vira "está" e "pra" ou "pro" viram "para" ou "para o", seguindo a regra do usuário. Avise na entrega, porque ele pode preferir fiel à fala. Esconda o "aí" de apoio com `""`.

Elementos de UI só quando a fala pede, nunca como enfeite:

- **Lista em linha** (`checklist` com `layout: row`) quando ela enumera; cada item marca no momento em que é dito.
- **Comparação** (`versus` com `reveal`) quando ela contrapõe dois conceitos; o lado direito só aparece quando ela fala dele.
- **Botão** (`cta`) quando ela chama para o link ou para a comunidade.
- Use `y` 0,70 a 0,705 e `max_bottom` 0,80 a 0,83. O fim é cortado automaticamente antes de cada transição.

Rode `plan_tool2.py` e leia a lista de trechos. Espere cerca de 40 a 50 trechos para 80 s de vídeo. Centenas de trechos indicam que o modo por energia não está ligado.

## Passo 4: conferir antes do render

Monte a base e gere uma folha de quadros antes de gastar o render completo:

```bash
cd $EDV_HOME/work/<nome>
python3 $F/plan_tool2.py words.json plan.json .
python3 $F/facecenter.py edl_raw.json edl.json
python3 $F/assemble.py edl.json base.mp4 base.wav       # cerca de 4 min
python3 $F/gaps.py timeline.json
python3 $F/preview.py timeline.json plan.json pv.png 0.3 1.5 3.3 6.2 10.6 17.5 33.2 46.5 50.5 65.6
```

Veja a folha e confira:

- o rosto fica livre;
- o laranja está legível sobre as mãos;
- os cartões de duas linhas não sobem no queixo;
- a UI não encosta nos cartões brancos e não sai pela borda.

Se a Carla tiver gravado em outro lugar, com outra luz ou mais longe da câmera, recalibre `style.dy`, `levels`, a LUT e a faixa de UI aqui, com novas folhas, até ficar certo.

## Passo 5: render

```bash
bash $F/run_chain.sh $EDV_HOME/work/<nome> slow > chain.log 2>&1   # em segundo plano
```

O processo leva uns 20 minutos (montagem 4, transições 1, mixagem 1, composição 13). Se a base já foi montada no passo 4, rode só as etapas seguintes (transições, mixagem e render), como em `run_chain.sh`. Para esperar, use `until grep -q CHAIN_DONE chain.log; do sleep 15; done` em segundo plano. Nunca use `pgrep -f` com um padrão que também aparece no próprio comando de espera, porque ele acha a si mesmo e nunca termina.

## Passo 6: controle de qualidade

```bash
python3 $F/qa_cortes.py $EDV_HOME/work/<nome>
bash $F/entrega.sh $EDV_HOME/work/<nome>
```

- `qa_cortes.py` reconhece o áudio do vídeo final em volta de cada corte e mostra o que o plano diz ao lado do que foi ouvido. É triagem, porque janelas curtas geram leituras ruidosas ("exalo" no lugar de "exausta"). Para cada caso suspeito, confira na fonte com `asr_clip.py`, como no passo 2.
- Na `qa_transicoes.png`, o quadro n-1 de cada transição precisa mostrar a legenda nova sobre o branco.
- Confira se o volume integrado está a até 1 LU de -14 LUFS e o pico em torno de -1 dBTP.
- Para ver um quadro exato, extraia por índice (`select='eq(n\,K)'`). `-ss` não garante o quadro certo.
- Numa selfie fechada, a pessoa do plano que entra cobre uns 70% do quadro, e a transição parece um corte colorido. É o esperado; não é falha.

## Passo 7: entrega

- Envie `<nome>_entrega.mp4`, em HEVC abaixo de 30 MB, com `SendUserFile`. O chat não aceita arquivo maior que 30 MB.
- Diga que o arquivo em qualidade máxima só existe no contêiner temporário. Se o usuário quiser, envie as partes de `mestre/` com o comando para juntar no Mac (está no topo de `entrega.sh`). Você não tem acesso ao Mac dele e não consegue gravar direto na mesa.
- No resumo, conte o que foi feito e liste as decisões que ele deve conferir: trechos removidos, norma culta nas legendas e qualquer desvio da referência.
- Salve o plano em `edicao-video/planos/<nome>.json`, faça commit das mudanças nas ferramentas e envie. Nunca coloque vídeo no repositório.

## Ajustes depois da entrega

O usuário aponta problemas pela minutagem do vídeo final. Para achar a palavra, use `timeline.json`: cada item de `segments` tem `t0` e `t1` no vídeo final, `in` e `out` na fonte e `first` e `last` com os índices das palavras. Corrija o plano e confira o novo corte com `asr_clip.py` antes de renderizar.

- Mudou um ponto de corte: é preciso montar de novo.
- Mudou só legenda ou UI, com os mesmos trechos: confira que `edl_raw.json` não mudou e reaproveite `base.mp4`.

Depois do render, rode o passo 6 de novo.

## Erros já cometidos e como não repetir

| Erro | Causa | O que fazer |
| --- | --- | --- |
| "ninguém" e "maturidade" cortadas pela metade | Corte forçado no silêncio de uma consoante; leitura errada de "Quem?" e de uma suposta repetição | Regra de conferência do passo 2 |
| 134 cortes picotando a fala | Pausas falsas criadas pelos tempos estimados do reconhecedor | `snap_energy` com `min_pause` 0,20 |
| Laranja ilegível sobre as mãos | Mãos da Carla na altura da legenda | Sombra do laranja em `style.ORANGE` |
| Pele e cabelo alaranjados | Luz quente do escritório somada à saturação da LUT | `skin_sat` 0,80, `skin_warm` 0 |
| UI de letra pequena | Tamanhos pensados para tela grande | Tamanhos atuais (lista 50, comparação 52/36, botão 56) |
| Legenda um quadro atrasada na transição | Arredondamento de tempo | Corrigido no `render.py`, que agora compara quadros inteiros |
| UI invadindo a transição | Fim calculado depois do corte | Corrigido no `plan_tool2.py` |
| Arquivo de 180 MB recusado no chat | Limite de 30 MB | `entrega.sh` |
