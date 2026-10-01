# Edição de vídeo no estilo da referência (Carla Bittencourt)

Motor de edição que aplica, num vídeo bruto de fala, o estilo medido no vídeo de referência: legenda em duas camadas (linha laranja corrida e cartões brancos em Bebas Neue), cortes sem pausas com três tamanhos de plano, transição de silhueta com quadro branco, momento em preto e branco, correção de cor teal e laranja com pele protegida, elementos de UI ligados à fala, trilha ambiente original em tom menor e efeitos sonoros sintetizados, com entrega a -14 LUFS.

O estudo completo, com todas as medidas, está no documento "Estudo do vídeo de referência para a edição da Carla". O passo a passo para editar um vídeo novo da Carla, com as regras de conferência e os erros já cometidos, está na skill `.claude/skills/edicao-video-carla`, que o Claude carrega sozinho quando recebe um vídeo dela.

Esta pasta contém apenas scripts. Nenhum vídeo, modelo ou fonte é versionado aqui, e nada nesta pasta faz parte do site.

## Preparação

```bash
export EDV_HOME=~/edicao-video-dados      # pasta de dados (modelos, fontes, trabalhos)
./ferramentas/setup.sh                     # instala dependências e baixa modelos e fontes
```

## Fluxo

1. **Entrada do vídeo bruto.** `ferramentas/intake.sh <id ou link do arquivo> <nome>` baixa o vídeo do Drive, normaliza (HDR do iPhone para SDR, 30 quadros por segundo, 1080x1920) e transcreve com dois modelos (Parakeet com tempo por palavra e Whisper para conferir o texto).
2. **Plano de edição.** Escreve-se um `plan.json` com índices de palavras: trechos mantidos, cartões laranja e brancos, gancho, momento em preto e branco, transições, elementos de UI e trilha. O formato está descrito no topo de `ferramentas/plan_tool2.py`. Com `snap_energy`, os cortes só acontecem onde o áudio está de fato em silêncio e cada pausa real é reduzida para cerca de 90 ms, como na referência; `hard` fixa cortes exatos em trechos com palavra recomeçada, e só depois de `asr_clip.py` confirmar que o trecho que termina no corte é reconhecido com a última palavra inteira. A chave `style` desloca as legendas para baixo quando o rosto ocupa a parte alta do quadro (no vídeo da Carla, `dy` de 267 px) e ativa a sombra suave do laranja.
3. **Conferência.** `ferramentas/preview.py` compõe legendas e UI sobre a base em instantes escolhidos e gera uma folha de quadros, para validar posição e leitura antes do render completo.
4. **Render.** `ferramentas/run_chain.sh <pasta do trabalho> [preset]` executa, em ordem: plano para linha do tempo, enquadramento pelo rosto, montagem com cor, vãos largos das legendas, transições com recorte de pessoa, mixagem e composição final.
5. **Controle de qualidade e entrega.** `ferramentas/qa_cortes.py <pasta>` reconhece o áudio final em volta de cada corte para achar palavra cortada; `ferramentas/entrega.sh <pasta>` gera a versão abaixo de 30 MB para o chat, divide o arquivo mestre em partes e monta a folha de quadros das transições.

## Arquivos

| Arquivo | Função |
| --- | --- |
| `intake.sh` | Baixa do Drive, normaliza e transcreve |
| `prep.py` | Normaliza a fonte (HDR, rotação, taxa de quadros, resolução) |
| `asr_parakeet.py`, `asr_whisper.py` | Transcrição com tempo por palavra e conferência do texto |
| `asr_clip.py` | Reconhece trechos curtos da fonte para decidir pontos de corte exatos |
| `preview.py` | Folha de quadros com legendas e UI para conferência antes do render |
| `plan_tool2.py` | Aplica as regras da referência ao plano e gera a linha do tempo |
| `facecenter.py` | Centraliza cada enquadramento no rosto |
| `assemble.py` | Corta, reenquadra e aplica a cor |
| `lut_teal.py` | Gera a LUT teal e laranja com proteção de pele |
| `gaps.py` | Abre o vão largo em parte dos cartões laranja |
| `matte.py`, `transitions.py` | Recorte de pessoa e preparação das transições de silhueta |
| `render.py`, `ui_elements.py` | Composição das legendas, efeitos e elementos de UI |
| `synth.py`, `mix.py` | Trilha e efeitos originais, tratamento da voz e loudness |
| `run_chain.sh` | Executa o fluxo inteiro |
| `qa_cortes.py` | Confere no vídeo final se alguma palavra ficou cortada |
| `entrega.sh` | Versão de entrega abaixo de 30 MB, mestre em partes e quadros das transições |
