# Edição de vídeo no estilo da referência (Carla Bittencourt)

Motor de edição que aplica, num vídeo bruto de fala, o estilo medido no vídeo de referência: legenda em duas camadas (linha laranja corrida e cartões brancos em Bebas Neue), cortes sem pausas com três tamanhos de plano, transição de silhueta com quadro branco, momento em preto e branco, correção de cor teal e laranja com pele protegida, elementos de UI ligados à fala, trilha ambiente original em tom menor e efeitos sonoros sintetizados, com entrega a -14 LUFS.

O estudo completo, com todas as medidas, está no documento "Estudo do vídeo de referência para a edição da Carla".

Esta pasta contém apenas scripts. Nenhum vídeo, modelo ou fonte é versionado aqui, e nada nesta pasta faz parte do site.

## Preparação

```bash
export EDV_HOME=~/edicao-video-dados      # pasta de dados (modelos, fontes, trabalhos)
./ferramentas/setup.sh                     # instala dependências e baixa modelos e fontes
```

## Fluxo

1. **Entrada do vídeo bruto.** `ferramentas/intake_carla.sh` baixa o vídeo da Carla do Drive, normaliza (HDR do iPhone para SDR, 30 quadros por segundo, 1080x1920) e transcreve com dois modelos (Parakeet com tempo por palavra e Whisper para conferir o texto).
2. **Plano de edição.** Escreve-se um `plan.json` com índices de palavras: trechos mantidos, cartões laranja e brancos, gancho, momento em preto e branco, transições, elementos de UI e trilha. O formato está descrito no topo de `ferramentas/plan_tool2.py`.
3. **Render.** `ferramentas/run_chain.sh <pasta do trabalho> [preset]` executa, em ordem: plano para linha do tempo, enquadramento pelo rosto, montagem com cor, vãos largos das legendas, transições com recorte de pessoa, mixagem e composição final.

## Arquivos

| Arquivo | Função |
| --- | --- |
| `prep.py` | Normaliza a fonte (HDR, rotação, taxa de quadros, resolução) |
| `asr_parakeet.py`, `asr_whisper.py` | Transcrição com tempo por palavra e conferência do texto |
| `plan_tool2.py` | Aplica as regras da referência ao plano e gera a linha do tempo |
| `facecenter.py` | Centraliza cada enquadramento no rosto |
| `assemble.py` | Corta, reenquadra e aplica a cor |
| `lut_teal.py` | Gera a LUT teal e laranja com proteção de pele |
| `gaps.py` | Abre o vão largo em parte dos cartões laranja |
| `matte.py`, `transitions.py` | Recorte de pessoa e preparação das transições de silhueta |
| `render.py`, `ui_elements.py` | Composição das legendas, efeitos e elementos de UI |
| `synth.py`, `mix.py` | Trilha e efeitos originais, tratamento da voz e loudness |
| `run_chain.sh` | Executa o fluxo inteiro |
