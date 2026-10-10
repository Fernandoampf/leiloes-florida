# DIÁRIO DE MUDANÇAS — Claude ↔ Grok

Arquivo compartilhado entre os dois agentes que mexem neste site. **Público**: só informação técnica (nada de caixa, plano ou decisão de compra).

## Regra de trabalho
1. **Início de toda sessão:** `git pull` e ler este diário + os commits do outro desde a última entrada.
2. **Fim de toda sessão:** uma linha neste diário por mudança (data, quem, o quê, por quê, como testou) + commit começando com **[Claude]** ou **[Grok]** + `git push`.
3. **Grok:** depois de regerar o site, anotar "no ar desde hh:mm ET, N testes ok". **Claude:** depois de conferir no ar, anotar "conferido pelo Claude".
4. **Ninguém desfaz o trabalho do outro.** Discordou → escrever como **PROPOSTA** aqui; o Fernando decide.
5. Mudança de regra de cálculo → atualizar o README ("Regras do Fernando") e os testes.
6. Papéis: **Grok** = coleta de dados, condados, montagem do site, testes. **Claude** = regras e cálculo, conferência no ar, checagens (FEMA, área alagada, cadastro), análise.

## Registro
Formato: `dd/mm hh:mm ET · QUEM · commit · o quê · por quê · teste/estado`

### 09/10/2026
- 06:26 · Grok · 8b2af8f · refresh diário das listas RealAuction · rotina · no ar
- 13:05 · Grok · 5650a57 · veredito por espaço de lance (SEM ESPAÇO/DISPUTADO/FLIP/CONSIDERAR), título promulgado FL, fechamento US$ 1 mil, posse 5/3 · pedido do Fernando · no ar
- 13:47 · Grok · 297d865 · valor de venda local (comps por subdivisão), avaliações manuais, termos com tooltip · pedido do Fernando · no ar
- 15:11 · Grok · 7bbddc3 · selo "conflito de tipo" (lote com sinais de construção) · qualidade · no ar
- 16:08 · Grok · aa9e9d4 · oferta/absorção de lotes, construtoras ativas, view Builders, links diretos · pedido do Fernando · no ar
- 16:54 · Claude · 30e37bc · regras do Fernando: escada de retorno para lotes (40/25/17%), NET ≥ US$ 25 mil em casa, estresse ARV −10%, premissas de compra às cegas, custo do capital 8%, Cash to Close real, teto da nota · pedido do Fernando · testado nos dados de 09/10; Grok regerou (a2df563/511fafb), testes ok · conferido pelo Claude
- 17:32 · Grok · 5ef6090 · Lake/Osceola presenciais pelas listas oficiais do clerk · cobertura · no ar · conferido pelo Claude (188 foreclosures, 0 com julgamento)
- 18:28 · Grok · 82ad650 · favoritos padrão do plano (data/favoritos.json fora do git) · pedido do Fernando · no ar
- 19:33 · Claude · 4d9465d · oferta alta sem pontos extras na escada (supAdd 0), filtro "Dar lance (proxy no teto)", sem filtro de caixa · pedido do Fernando · Grok regerou 19:39 (f20b80c), 214 testes ok · conferido pelo Claude
- 20:03 · Claude · e1ffcdf · ROI/ano, vista 📦 Pacotes, +2 meses de título (qtm 2) · pedido do Fernando · Grok regerou 20:08 (c72f29c), 214 testes ok · conferido pelo Claude
- 20:11 · Claude · d0a120f · Pacotes abrem na Flórida toda · pedido do Fernando · aguardando próxima montagem
- 20:21 · Grok · 8e1a1b2 · Sumter: tax deed presencial pela lista do clerk · cobertura (prioridade 1) · no ar
- 20:38 · Grok · a72f7a9 · Collier tax deed presencial, conferência no clerk (Citrus/Hernando: opening bid e resgatados), endereço pelo DOR, alerta homestead, regra de pagamento de Hillsborough · correções pedidas · no ar 20:39 · conferido pelo Claude (Collier 35 tax deeds)
- 20:55 · Grok · 432ec41 · Gulf presencial, clerks 1×/dia, saintjohns.realforeclose, selo de lote abaixo do mínimo do zoneamento, comps sem outliers · cobertura/qualidade · no ar
- PROPOSTA · Claude · cruzar a geometria de cada lote com o mapa de áreas alagadas (USFWS NWI) e consultar a zona FEMA em vários pontos; excluir dos vereditos FLIP/CONSIDER lote com área alagada relevante ou zona A/AE/AH/VE (caso Collier TD 26136: ~71% alagado + AH) · regra do Fernando "área alagada não" · **feito em 115fd6e**
- 22:19 · Grok · 115fd6e · lotes: % de área úmida (USFWS NWI) e % de zona FEMA medidos sobre o POLÍGONO da parcela (cadastro estadual DOR); badge + drawer; sai de FLIP/CONSIDER com área úmida ≥ 20% ou FEMA A/AE/AH/AO/VE ≥ 10% do lote (premissas wetMax/floodMat, ajustáveis); cache 90 dias, até 600 lotes novos por dia · regra do Fernando (Collier TD 26136 = 70,9% NWI + 100% AH, confere) · polígono em 1.092 de 1.197 lotes; 257 acima de um dos limites; no ar desde 22:20 ET, todos os testes ok
- 22:40 · Claude · — · conferido no ar: checagem de área alagada/FEMA pela parcela (TD 26136 = 70,9% alagado e 100% AH; lotes acompanhados em 0% e zona X) · resposta do Fernando às 2 perguntas: (1) limite de 10% para área alagada E para zona de inundação; abaixo de 10% só selo, sem tirar do veredito; (2) sim à releitura semanal além de 7 dias, só dos candidatos (FLIP, CONSIDER, 'Dar lance', favoritos), com acessos espalhados no dia · **feito pelo Grok em b9d05a5 + cron do box**
- 23:17 · Grok · b9d05a5 · regra do Fernando: área úmida E inundação FEMA com limite de 10% (≥ 10% tira de FLIP/CONSIDER; abaixo só selo para revisar); premissa salva com 20% migra para 10% · decisão do Fernando 09/10 · 261 lotes excluídos, 30 só com selo; no ar desde 23:18 ET, todos os testes ok
- 23:17 · Grok · (fora do git, box) · releitura semanal das listas RealAuction de leilões a mais de 7 dias, SÓ datas com candidatos (FLIP, CONSIDER, Dar lance, favoritos), 20–60 min aleatórios entre datas, para no 1º bloqueio; cron do box domingo 01:13 ET (/workspace/auc/statewide/weekly_reread.py) · decisão do Fernando 09/10 · teste a seco: 1.472 candidatos, 6 datas a reler

## 2026-10-09 23:5x ET — Grok: Levy (tax deed presencial) no ar
- Novo leitor genérico `fetch_taxsmart` em inperson.py (clerks no produto TaxSmartWeb: busca por data de leilão + grid JSON; cache diário; offline usa o último cache). Config `TAXSMART = {county: url}` — basta uma linha por condado novo.
- Levy: 26 processos listados p/ 09/11/2026 (19 SALE, 7 REDEEMED descartados). Leilão presencial seg. 10h, Government Center, Bronson. 14 dos 19 são terrenos sem endereço no cadastro DOR (identificados pela parcela).
- Rolos NAL baixados p/ Levy, Hardee, DeSoto, Bradford, Union, Columbia, Dixie, Lafayette, Madison, Jefferson, Liberty, Holmes, Wakulla, Gadsden.
- Teste novo (Levy) + todos os testes OK.

## 2026-10-10 00:3x ET — Grok: Wakulla (tax deed presencial) no ar; Hardee/DeSoto/Bradford/Glades/Union sem fonte automatizável
- Wakulla: tabela do clerk (wakullaclerk.org/official_records/tax_deed_sales.php, cache diário) + aviso em PDF por processo (baixado uma vez, cache permanente) → parcela, opening bid estatutário, credor, certificado. 4 à venda em 21/10/2026 (6 resgatados fora). Quartas 10h, saguão do fórum, inscrição até 9h45.
- Hardee, DeSoto, Bradford, Glades: clerk não publica lista de parcelas online (só edital em jornal). Union: site do clerk responde 403 ao box — não contornado.
- NoticeRegistry: termos (seção 7) proíbem raspagem/download sistemático → não usado. floridapublicnotices.com: termos não proíbem, mas só via API interna não documentada → não usado sem aprovação.
- Columbia: página do clerk sem leilões agendados agora (reler quando houver).

## 2026-10-10 ET — Grok: editais de tax deed (floridapublicnotices.com) para condados sem lista online — aprovado pelo Fernando
- notices.py: busca JSON do próprio site (POST / com keywords="tax deed" + paper=<jornal do condado>), 1 busca por jornal por dia (cache), PDF/imagem de cada edital baixado uma vez (cache permanente; imagens via OCR tesseract), 3 s entre requisições, para tudo em 403/429/5xx. Sem contorno.
- Extrai parcela, data/hora/local, certificado, credor, proprietário, endereço e opening bid (quando o edital traz). Sem parcela mas com endereço → parcela única no rolo DOR. Sem opening bid → badge "Sem Opening Bid" (nobid). Resgates não são publicados: aviso no drawer para confirmar com o clerk.
- Publicado condado a condado:
  - 10/10 00:00 Hardee: 10 itens
  - 10/10 00:09 DeSoto: 11 itens
  - 10/10 00:15 Bradford (+Glades/Union: 0 editais de tax deed publicados agora): Bradford 3 itens; Glades 0; Union 0
  - 10/10 00:20 Taylor: 6 itens
  - 10/10 00:26 Madison: 4 itens
  - 10/10 00:32 Dixie: 1 itens

## 2026-10-10 13:44 ET — Claude: conferência no ar + propostas
- 13:44 · Claude · — · conferido no ar o build de 10/10 00:32 ET (6a9d2d5): editais de tax deed por jornal — Hardee 10, DeSoto 11, Taylor 6 (sem cadastro → sem valor/tipo), Madison 4 (únicos com opening bid), Bradford 3, Dixie 1; aviso de resgate na ficha ok; lote de Bradford com área úmida + SFHA corretamente fora de FLIP/CONSIDER · conferido pelo Claude
- PROPOSTA · Claude · **barra de "Meus candidatos" (Exportar/Importar JSON) fica numa coluna estreita no meio da altura da página** na vista 🎯 (é o 1º item do grid de cartões) → o Fernando não achou o botão. Sugestão: tirar a `.candbar` de dentro do grid (ou `grid-column:1/-1; align-self:start`) para ficar no topo, largura total.
- PROPOSTA · Claude · **favoritos padrão** (`data/favoritos.json`, fora do git) ainda são do plano antigo → trocar pelo plano novo que o Fernando tem (arquivo JSON de candidatos, 21 itens); considerar também ler um `cand` exportado pelo site como fonte do favoritos.json.
- PROPOSTA · Claude · selo **"Gaio-da-flórida (scrub-jay): licença exigida"** em lotes de Charlotte: camada oficial `agis3.charlottecountyfl.gov/arcgis/rest/services/Essentials/CCGISLayers/MapServer/56` (ScrubjayPermitBoundary, campo INFO = "Permit Required"/"No Permit Required"), interseção com o polígono da parcela; idem para Sarasota/North Port se houver camada equivalente.
