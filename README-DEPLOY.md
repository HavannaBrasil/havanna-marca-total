# Havanna · Social Listening Marca Total — Deploy na Cloudflare Pages

Dashboard interativo de social listening da Havanna Brasil, marca total, últimos 12 meses. Arquivo único e autossuficiente, com tela de login da marca e proteção por sessão assinada.

## Arquivos desta pasta

| Arquivo | Função |
|---|---|
| `index.html` | O dashboard completo, autossuficiente. Dados embutidos, gráficos via Chart.js, importação e exportação de CSV, impressão. |
| `_worker.js` | Tela de login com a logo Havanna e controle de acesso por sessão assinada (HMAC). Roda no modo avançado da Cloudflare Pages. |
| `robots.txt` | Bloqueia indexação por buscadores. |
| `README-DEPLOY.md` | Este guia. |

## Como subir na Cloudflare Pages (Direct Upload)

1. Acesse o painel da Cloudflare e entre em **Workers & Pages**.
2. Clique em **Create application**, depois na aba **Pages**, depois em **Upload assets**.
3. Dê um nome ao projeto, por exemplo `havanna-marca-total`.
4. Arraste os arquivos desta pasta, ou seja `index.html`, `_worker.js` e `robots.txt`, para a área de upload. Suba os três no mesmo projeto.
5. Clique em **Deploy site**. Em alguns segundos o endereço `https://havanna-marca-total.pages.dev` fica no ar.
6. A presença do `_worker.js` na raiz ativa automaticamente o modo avançado, e a tela de login passa a proteger todo o site.

## Credenciais e variáveis de ambiente

O `_worker.js` lê as credenciais de variáveis de ambiente. Enquanto elas não forem definidas, ele usa um padrão de fallback para que o site funcione logo após o deploy.

**Padrão de fallback:** usuário `nuts.havanna`, senha `MarcaTotal2026`.

Para definir as suas, vá em **Settings**, depois **Variables and secrets**, e cadastre:

| Nome | Tipo | Função |
|---|---|---|
| `USERNAME` | Texto | Usuário de acesso. |
| `PASSWORD` | Secret | Senha de acesso. |
| `SESSION_SECRET` | Secret | Chave usada para assinar a sessão. Use uma frase longa e aleatória. |

Após salvar as variáveis, faça um novo deploy ou um retry do deploy para que o worker passe a lê-las. Sem o `SESSION_SECRET` próprio, a sessão usa uma chave padrão conhecida, portanto defina o seu para produção.

## Como atualizar os dados

O dashboard nasce com os últimos 12 meses já embutidos. Para atualizar sem reabrir o código:

1. No topo do dashboard, clique em **Importar CSV**.
2. Escolha um arquivo com estas colunas exatas, na primeira linha: `date, platform, type, title, url, reach, views, likes, comments, shares, interactions, theme, sentiment, source`.
3. O dashboard recalcula KPIs, gráficos e listas na hora.

O campo `platform` aceita os valores `instagram`, `tiktok`, `facebook`, `imprensa`, `reclame` e `ugc`. A camada interna, ou seja Instagram, TikTok e Facebook, sai do Reportei. A camada externa, ou seja imprensa, Reclame Aqui e UGC, vem de pesquisa e curadoria.

Para gerar um recorte de período e compartilhar, use **Exportar CSV** ou **Imprimir**.

## Observações

- O arquivo `index.html` depende de dois CDNs públicos, ou seja Chart.js e PapaParse, além das fontes do Google. Mantenha o ambiente com acesso a esses domínios.
- A logo no topo e na tela de login é uma reconstrução vetorial nas cores oficiais da marca, Pantone 185 vermelho e Pantone 116 amarelo. Para trocar pela arte oficial, basta substituir o bloco `<svg class="shield">` no `index.html` e no `_worker.js`.

Produto desenvolvido e mantido pela Nuts & Co.
