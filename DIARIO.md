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
- PROPOSTA · Claude · cruzar a geometria de cada lote com o mapa de áreas alagadas (USFWS NWI) e consultar a zona FEMA em vários pontos; excluir dos vereditos FLIP/CONSIDER lote com área alagada relevante ou zona A/AE/AH/VE (caso Collier TD 26136: ~71% alagado + AH) · regra do Fernando "área alagada não" · **Grok trabalhando**
