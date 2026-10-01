---
name: edicao-video-carla
description: Edita vídeos de fala da Carla (cliente da Havanna) no estilo do vídeo de referência já estudado, com legenda laranja corrida, cartões brancos em Bebas Neue, cortes sem pausas com três tamanhos de plano, transições de silhueta com quadro branco, momento em preto e branco, cor teal com pele protegida, elementos de UI ligados à fala, trilha e efeitos originais, entregando o vídeo pronto no chat. Use sempre que o usuário mandar um link do Drive ou um arquivo de vídeo da Carla para editar, pedir "edita esse vídeo", "mesmo estilo do anterior", "faz igual ao último da Carla", ou pedir ajuste num vídeo da Carla já editado (palavra cortada, legenda, transição, cor), mesmo sem citar a palavra skill.
---

# Edição de vídeo da Carla no estilo da referência

Esta skill transforma um vídeo bruto de fala da Carla num Reels pronto, no mesmo estilo do primeiro vídeo entregue e aprovado, cujo plano está em `edicao-video/planos/carla_plan.json`. As ferramentas estão em `edicao-video/ferramentas/` e o README daquela pasta descreve cada uma.

Separe sempre duas coisas:

- **O estilo é fixo.** Fontes, cores, animações, transições, preto e branco, trilha, efeitos, mixagem e tamanhos da UI estão no código. Os ajustes próprios da Carla ficam no plano (`style`, `levels`, `grade` e o `top_gap` do gancho) e são copiados dele.
- **As decisões editoriais são de cada vídeo e são suas.** O que cortar, quais frases viram cartão branco, onde entram gancho, preto e branco, transições e UI.

Os erros do primeiro vídeo aconteceram nas decisões, não no código. Por isso a maior parte desta skill trata de como decidir e conferir.

As medidas do estilo estão em `references/estilo-referencia.md`. Leia antes de mexer em qualquer constante, ou se o vídeo novo tiver enquadramento diferente.

## Comunicação com o usuário

- Escreva sempre em português do Brasil, inclusive nas descrições das ferramentas, que ele também lê.
- As regras de escrita dele valem para tudo o que é visível: "para", nunca "pra" ou "pro"; sem reticências; sem travessão no lugar de vírgula; sem emojis; pontuação formal.
- Trabalhe até a entrega sem parar para pedir aprovação no meio. Ajustes vêm depois que ele assistir.
- Nas esperas longas, dê atualizações curtas dizendo em que etapa está.

## Ambiente

A sessão roda num contêiner de nuvem temporário: modelos, fontes e vídeos somem quando ela termina.

- **Espaço:** os modelos ocupam uns 2 GB e cada trabalho uns 1,5 GB. Confira com `df -h` antes de começar e apague trabalhos antigos se faltar.
- **Rede:** o ambiente precisa liberar:
  - github.com e objects.githubusercontent.com (modelos);
  - pypi.org e files.pythonhosted.org (pacotes);
  - fonts.googleapis.com e fonts.gstatic.com (fontes);
  - drive.usercontent.google.com (vídeo).

  Se algo vier bloqueado, explique e peça ao usuário para ajustar a rede do ambiente. Não contorne a política de rede por outros serviços: uma tentativa assim já foi barrada.

**Cada chamada de shell começa sem as variáveis da anterior; só o diretório atual continua.** Por isso o setup grava os caminhos absolutos num arquivo, e todo comando desta skill começa carregando esse arquivo:

```bash
# uma vez, em segundo plano: baixa uns 2 GB e passa do tempo limite de um comando comum
EDV_HOME=<scratchpad>/edv bash <raiz do repositório>/edicao-video/ferramentas/setup.sh > <scratchpad>/setup.log 2>&1
# em todo comando seguinte; define EDV_HOME e F (pasta das ferramentas), já absolutos
source <scratchpad>/edv/env.sh && ...
```

Rode em segundo plano (`run_in_background`) tudo o que passa de 2 minutos: setup, entrada do vídeo, montagem e render. Espere o aviso de término da própria ferramenta, que chega também quando o comando falha, e então leia o fim do log. Não monte laços de espera com `pgrep -f`: o padrão casa com o próprio comando de espera, que nunca termina.

O ffmpeg vem do pacote imageio e não há `ffprobe`; para ler duração e trilhas, use `ffmpeg -hide_banner -i arquivo`.

## Passo 1: localizar e baixar o vídeo

O usuário costuma mandar o link de uma **pasta** do Drive (`.../folders/<id da pasta>`).

1. Carregue as ferramentas do conector do Google Drive com ToolSearch; elas não vêm carregadas.
2. Liste o conteúdo com `search_files`, usando a consulta `'<id da pasta>' in parents`, e escolha o vídeo bruto.
3. Confira com `get_file_permissions` se o arquivo está compartilhado para qualquer pessoa com o link.
   - O download é feito por `curl`, sem a autenticação do conector, e só funciona assim.
   - Se não estiver, peça ao usuário que compartilhe. Não mude o compartilhamento por conta própria.
4. Baixe com o script, em segundo plano. O download pelo próprio conector tem limite de uns 10 MB.

```bash
source <scratchpad>/edv/env.sh && bash $F/intake.sh <id ou link do arquivo> <nome> > $EDV_HOME/intake_<nome>.log 2>&1
```

O script baixa o vídeo, converte o HDR do iPhone para SDR, normaliza para 1080x1920 a 30 quadros por segundo e transcreve com dois modelos:

- **Parakeet**, com tempo por palavra, em `words.json`;
- **Whisper**, só para conferir o texto.

Tudo fica em `$EDV_HOME/work/<nome>`, a pasta do trabalho, de onde partem todos os comandos seguintes. Se o log disser que o Drive devolveu uma página, o problema é compartilhamento ou rede.

## Passo 2: ler a fala e decidir o que sai

```bash
source <scratchpad>/edv/env.sh && cd $EDV_HOME/work/<nome> && python3 $F/inspecionar.py palavras
```

A saída lista cada palavra com índice e tempos. O plano é todo escrito em índices de palavra. Leia também `transcript_whisper.txt` e marque:

- recomeços (no primeiro vídeo: "e querer provar para o mundo, que tá querendo provar para o mundo");
- frases abandonadas;
- vícios de fala.

Os trechos que saem são as faixas de palavras que ficam fora de `keep`.

**Regra de conferência, a mais importante desta skill.** Nenhuma palavra pode ficar pela metade num corte. Prove isso com o reconhecimento de fala antes de renderizar:

```bash
python3 $F/asr_clip.py mezz.mov 14.30:15.00 14.30:15.48      # trechos da fonte, em segundos
python3 $F/inspecionar.py energia 15.0 0.15                   # envelope de 10 ms em volta de 15,0 s; '.' é silêncio
```

- **Trecho que termina no corte:** reconheça-o sozinho, terminando exatamente no ponto de corte. A última palavra precisa sair inteira. Foi esse teste, feito tarde demais, que revelou "ninho" no lugar de "ninguém" e "maturi" no lugar de "maturidade".
- **Trecho que começa no corte:** reconheça-o também. A primeira palavra não pode perder a consoante inicial.
- **Juiz:** o Parakeet. O Whisper inventa repetições ("Maturidade. Maturidade. Mat") e serve só para conferir o texto.
- **Teste de emenda não vale.** Ao colar dois trechos e reconhecer junto, o modelo completa a palavra truncada pelo contexto: "maturi" seguido de "é você" vira "maturidade é você".
- **Silêncio curto dentro da palavra:** 40 a 80 ms (4 a 8 pontos no envelope) é o fechamento de uma consoante (g, d, t, p, k), não o fim da palavra. Fim de verdade tem pelo menos uns 150 ms de silêncio. Os dois erros do primeiro vídeo foram exatamente isso: "nin|guém" e "maturi|dade".
- **Palavra solta logo depois de outra** ("Quem?" depois de "ninguém"): suspeite primeiro que é a segunda metade da palavra anterior, e só depois que é vício de fala.

Prefira o modo por energia (`snap_energy: true`), que corta só onde o áudio está de fato em silêncio. Use `hard` só para recomeços sem pausa, e sempre conferido.

## Passo 3: escrever o plano

```bash
source <scratchpad>/edv/env.sh && cd $EDV_HOME/work/<nome> && cp <raiz do repositório>/edicao-video/planos/carla_plan.json plan.json && python3 $F/lut_teal.py carla.cube 1.0 0.07 0.90 0.0 1.0 0.80
```

O comando copia o plano de exemplo e gera a LUT que ele usa, na pasta do trabalho. A lista de chaves está no topo de `$F/plan_tool2.py`.

- **Mantenha** `src`, `grade`, `crf`, `style`, `levels`, `framing`, `snap_energy`, `min_pause` (0,20), `silence_db` (-45), `keep_pause`, `keep_pause_out` (0,07), `pad_before`, `pad_after`, `max_gap`, `sfx` e `music`.
- **Troque** `out` por `"<nome>.mp4"`. O `entrega.sh` deriva dele o nome do arquivo de entrega.
- **Refaça** tudo o que é deste vídeo: `keep`, `hard`, `text`, `breath`, `cut_at`, `cards`, `bw`, `transitions` e `ui`. Os índices de palavra do plano antigo não valem para outra fala.
- **Use como molde** o cartão `hook` e os itens de `ui` do plano antigo. Troque palavras, textos, ícones e índices (`at`, `until`, `items[].at`, `left_at`, `right_at`), mas mantenha `top_gap`, `y`, `max_bottom` e `tail`.

Critérios para as legendas, vindos da referência:

- **Gancho:** as duas primeiras palavras em branco grande, com a continuação da frase em laranja embaixo.
- **Cartões brancos:**
  - nas palavras de impacto, um a cada 3 a 5 s em média, de uma ou duas linhas curtas;
  - alterne entrada por corte e entrada deslizando;
  - use "equal" uma vez, no preto e branco.
- **Laranja:** no resto, de 2 a 5 palavras por cartão, quebrando nas unidades de sentido.
- **Preto e branco:** uma vez, cedo (entre 5 e 8 s), em uma ou duas palavras de peso, por cerca de 1 s.
- **Transições:** quatro, nos padrões T1, T2, T3 e T4, por volta de 9%, 30%, 55% e 70% da duração, sempre no início de uma frase nova depois de uma pausa.
- **`cut_at`:** nas frases longas sem pausa, para ter troca de plano mais ou menos a cada 2 s.
- **Norma culta no texto:** "tá" vira "está", e "pra" ou "pro" viram "para" ou "para o", seguindo a regra do usuário. Avise na entrega, porque ele pode preferir fiel à fala.
- **"Aí" de apoio:** esconda com `""`.

Elementos de UI só quando a fala pede, nunca como enfeite:

- **Lista em linha** (`checklist` com `layout: "row"`), quando ela enumera. Cada item marca no momento em que é dito.
- **Comparação** (`versus` com `reveal: true`), quando ela contrapõe dois conceitos. O lado direito só aparece quando ela fala dele.
- **Botão** (`cta`), quando ela chama para o link ou para a comunidade.

Nenhuma transição pode cair entre o `at` e o `until` de um elemento. O corte automático só protege a transição logo depois do fim.

## Passo 4: prévia antes do render

```bash
source <scratchpad>/edv/env.sh && bash $F/run_chain.sh $EDV_HOME/work/<nome> slow previa > $EDV_HOME/work/<nome>/previa.log 2>&1
```

Rode em segundo plano; leva uns 6 min. O modo `previa`:

1. gera a linha do tempo;
2. enquadra;
3. monta a base com a cor (cerca de 4 min);
4. prepara as transições;
5. para e grava `previa.png`.

A `previa.png` é uma folha com os instantes que importam: o gancho, cada cartão branco, o preto e branco, cada elemento de UI e alguns cartões laranja. Confira na folha:

- se o rosto fica livre;
- se o laranja está legível sobre as mãos;
- se os cartões de duas linhas não sobem no queixo;
- se a UI não encosta nos cartões brancos nem sai pela borda.

Depois leia a lista de trechos em `timeline.json` (`segments`). Espere de 40 a 50 trechos para 80 s de vídeo; centenas indicam que o modo por energia não está ligado. Então rode `python3 $F/inspecionar.py cortes`. Ele lista todos os cortes que removem áudio e já imprime o comando do `asr_clip.py` com os dois trechos de cada corte. Rode esse comando e confira cada linha como no passo 2.

Se a Carla tiver gravado em outro lugar, com outra luz ou mais longe da câmera, recalibre aqui `style.dy`, `levels`, a LUT e a faixa de UI, com novas prévias até ficar certo.

- Mudanças em `levels` ou na LUT fazem a montagem rodar de novo sozinha.
- `WHITE.equal_cy` é um valor absoluto: se mudar `dy`, mude esse valor junto.

## Passo 5: render

```bash
source <scratchpad>/edv/env.sh && bash $F/run_chain.sh $EDV_HOME/work/<nome> slow > $EDV_HOME/work/<nome>/chain.log 2>&1
```

Rode em segundo plano. Se cortes, transições e LUT não mudaram desde a última montagem, o script reaproveita a base e as transições. Depois da prévia, então, ele só refaz vãos, mixagem e composição, em uns 15 min. O log termina em `CHAIN_DONE`, ou em `CHAIN_FAILED na etapa: <etapa>`.

## Passo 6: controle de qualidade

```bash
source <scratchpad>/edv/env.sh && cd $EDV_HOME/work/<nome> && python3 $F/qa_cortes.py .
source <scratchpad>/edv/env.sh && bash $F/entrega.sh $EDV_HOME/work/<nome> > $EDV_HOME/work/<nome>/entrega.log 2>&1
```

Rode o `entrega.sh` em segundo plano; leva uns 4 min.

- **`qa_cortes.py`:** reconhece o áudio do vídeo final em volta de cada corte e mostra, lado a lado, o que o plano diz e o que foi ouvido. É triagem, porque janelas curtas geram leituras ruidosas ("exalo" no lugar de "exausta"). Para cada caso suspeito, confira na fonte com `asr_clip.py` e `inspecionar.py energia`.
- **`qa_transicoes.png`:** o quadro n-1 de cada transição precisa mostrar a legenda nova sobre o branco.
- **Volume:** no `entrega.log`, o integrado deve estar a até 1 LU de -14 LUFS e o pico em torno de -1 dBTP.
- **Quadro exato:** extraia por índice (`select='eq(n\,K)'`); `-ss` não garante o quadro certo.
- **Transição em selfie fechada:** a pessoa do plano que entra cobre uns 70% do quadro, e a transição parece um corte colorido. É o esperado, não é falha.

## Passo 7: entrega

- **Envio:** mande `<nome>_entrega.mp4`, em HEVC abaixo de 30 MB, com `SendUserFile`. O chat não aceita arquivo maior que 30 MB. Se a ferramenta não aparecer, procure com ToolSearch; se não existir, avise o usuário e combine outra forma de envio.
- **Arquivo mestre:** o arquivo em qualidade máxima só existe no contêiner temporário; diga isso ao usuário. Se ele quiser, envie as partes de `mestre/` com o comando para juntar no Mac, que está no topo de `entrega.sh`. Você não tem acesso ao Mac dele e não consegue gravar direto na mesa.
- **Resumo:** conte o que foi feito e liste as decisões que ele deve conferir: trechos removidos, norma culta nas legendas e qualquer desvio da referência.
- **Repositório:**
  - salve o plano em `edicao-video/planos/<nome>.json`;
  - faça commit das mudanças nas ferramentas;
  - envie para o branch indicado pela sessão;
  - nunca coloque vídeo no repositório.

  Se o envio falhar com 403, consulte `read_documentation` no tópico `github.access`.

## Ajustes depois da entrega

O usuário aponta problemas pela minutagem do vídeo final. Para achar a palavra, use `timeline.json`. Cada item de `segments` tem:

- `t0` e `t1`: tempos no vídeo final;
- `in` e `out`: tempos na fonte;
- `first` e `last`: índices das palavras.

Corrija o plano e confira o novo corte com `asr_clip.py` antes de renderizar. Depois rode o passo 5, que decide sozinho se precisa montar de novo, e repita os passos 6 e 7.

## Erros já cometidos e como não repetir

| Erro | Causa | O que fazer |
| --- | --- | --- |
| "ninguém" e "maturidade" cortadas pela metade | Corte forçado no silêncio de uma consoante, mais a leitura errada de "Quem?" e de uma suposta repetição | Regra de conferência do passo 2 |
| 134 cortes picotando a fala | Pausas falsas criadas pelos tempos estimados do reconhecedor | `snap_energy` com `min_pause` 0,20 |
| Laranja ilegível sobre as mãos | Mãos da Carla na altura da legenda | Sombra do laranja em `style.ORANGE` |
| Pele e cabelo alaranjados | Luz quente do escritório somada à saturação da LUT | LUT com `skin_sat` 0,80 e `skin_warm` 0 |
| UI de letra pequena | Tamanhos pensados para tela grande | Os tamanhos novos já são o padrão do código |
| Legenda um quadro atrasada na transição | Arredondamento de tempo | Corrigido no `render.py`, que compara quadros inteiros |
| UI invadindo a transição | Fim calculado depois do corte | Corrigido no `plan_tool2.py`; ver também o fim do passo 3 |
| Arquivo de 180 MB recusado no chat | Limite de 30 MB | `entrega.sh` |
| Espera do render que nunca terminava | `pgrep -f` achando o próprio comando de espera | Rodar em segundo plano e esperar o aviso da ferramenta |
