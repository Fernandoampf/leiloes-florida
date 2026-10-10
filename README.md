# LEILÃO – Leilões Flórida v4 (CHALLENGE CAPITAL)

Painel com imóveis em leilão na **Flórida inteira** (referência de distância: Orlando): **tax deed**, **foreclosure**, leilões privados e imóveis do governo federal, de **todos os tipos** (lote, terreno, casa, townhouse, condo, mobile, multifamily, comercial, outros).

- **Site:** https://fernandoampf.github.io/leiloes-florida/ (protegido por senha com StaticCrypt – AES; a senha **não** fica no repositório).
- **Moeda:** tudo em US$. **Retorno mínimo:** 17% (lance máximo = maior lance que ainda rende 17%; editável em ⚙ Premissas). **Sem teto de orçamento.**

## Fontes (todas públicas e gratuitas, acesso educado com cache)
| Dado | Fonte |
|---|---|
| Leilões agendados (tax deed e foreclosure) e resultados passados | sites RealAuction dos condados (realtaxdeed.com / realforeclose.com), Orange County Clerk |
| Leilões privados / federais | Tranzon (busca pública “Florida”), U.S. Treasury Real Property |
| Detalhes do imóvel, AVM, aluguel, ocupação, hipotecas, FEMA, histórico, fotos | PropertyOnion (páginas públicas) |
| POV, confiança, liens totais, ocupação/vago, valor da terra, tipo da venda anterior | PropertyOnion **Premium CSV** (`/workspace/auc/statewide/po_exports/po_<condado>_<data>.csv`) |
| Cadastro (uso DOR, valor, área, ano, homestead, dono) e **vendas comparáveis** | Florida DOR – arquivos NAL (2026) |
| Água e esgoto | FDOH – Florida Water Management Inventory (ArcGIS público) |
| Mercado por ZIP (dias no mercado, preço, US$/sqft) e aluguel típico | Redfin Data Center, Zillow ZHVI e ZORI |

Não automatizados (por regra ou termos de uso): Auction.com, Xome, Hubzu, Bid4Assets; leilões presenciais/listas em PDF de alguns condados.

## O que tem no painel
- **Avaliação estilo BidToFlip:** condado, *Valor de mercado (POV/ARV)* com fonte, julgamento/lance com % vs. valor, lance máximo (17%) com depósito de 5%, NET, ROI, veredito (**FLIP** ≥ 25% · **CONSIDERAR** 17–25% · **PASSAR** < 17%), categoria (J>MAX / abaixo de 17% / lucro baixo / viável), nota 0–100 e autor.
- Faixa de KPIs (desconto mediano, alto patrimônio, enchente, vagos, ≤ 7 dias), aviso **JR-LIEN?**, blocos de categoria clicáveis, **seletor de tipo de imóvel**, ordenação rápida, filtros (inclusive água/esgoto e distância de Orlando), favoritos ★ e cores ● (salvos no aparelho), CSV, link com filtros.
- Visões: **Lista**, **Cards**, **Favoritos**, **Mapa**, **Inteligência** (por condado, autores, mapa de calor valor × desconto), **Resultados** (leilões passados: vendidos, p/ terceiros, cancelados, preço ÷ avaliação), **Calendário** (super dias) e **Dia do leilão** (lista imprimível/CSV dos favoritos com lance máximo, depósito, processo e links).
- Painel de detalhes: **galeria** (fotos, Street View e satélite sem chave de API; links Zillow/Realtor/Maps), alertas de risco com status (*confirmado / indício / estimativa / não verificado*), bloco de **terreno** (água, esgoto, frente, acesso, zoneamento, área, FEMA, wetlands), estratégias FLIP × HOLD/BRRRR, simulador “E se…”, escada de lances (17% mínimo, 25%, 30%, 70% do ARV, break-even, preço esperado, julgamento), P&L com custo de posse por mês e prazo de saída pelo ZIP, BRRRR, reconstrução, **comps** (estimativa), **histórico de leilões / preço esperado**, mercado do ZIP e flip tracker.

## Como o Claude e o Grok trabalham neste repositório
Início de sessão: `git pull` + ler o **[DIARIO.md](DIARIO.md)** e os commits do outro. Fim de sessão: linha no DIARIO.md + commit com **[Claude]** ou **[Grok]** + `git push`. Ninguém desfaz o trabalho do outro (discordância vira PROPOSTA no diário; o Fernando decide). Repositório público: nada de caixa, plano ou decisão de compra.

## Regras do Fernando (out/2026 – compra às cegas, tudo editável em ⚙ Premissas)
- **Lance máximo pelas regras** (não só 17%): construído = ROI ≥ 17% **e** NET ≥ US$ 25 mil; **lote = escada por custo all-in** – até US$ 15 mil: ROI ≥ 40% e NET ≥ US$ 3 mil · até US$ 60 mil: ROI ≥ 25% · acima: 17% (oferta alta na subdivisão **não** soma pontos desde out/2026: o valor de venda e a posse já descontam). Os dois: **teste de estresse** (NET ≥ 0 com ARV −10%).
- **Premissas mais conservadoras:** reforma US$ 30/35/48 por sqft (2005–14 / 1995–2004 / antes de 1995), mínimo US$ 15 mil, contingência 20%, posse 7 meses (+2 com despejo), seguro 2%/ano, imposto nunca abaixo de 1,8% do valor no construído (o homestead cai na venda), concessões 2% do ARV na venda, lote com comissão total de 8%, **custo do capital 8% a.a.** sobre compra + reforma nos meses de posse.
- **Cash to Close** = lance inteiro + clerk + doc stamps (só o depósito de 5% é pago no leilão; o saldo vence logo depois).
- **Filtro "Dar lance (proxy no teto)"** em Verdict: FLIP + CONSIDER + CONTESTED que ainda têm espaço (lance máx. acima do lance inicial/julgamento). O preço esperado é um chute; lançar o proxy no lance máximo em vários lotes é o que pega as pechinchas.
- **Retorno ao ano** (coluna ROI/ano e ordenação 🚀): ROI no lance realista ÷ meses de posse × 12 (simples) – a métrica de crescimento de capital.
- **Vista 📦 Pacotes:** lotes com espaço para lance da mesma subdivisão/ZIP no mesmo leilão (mín. 3), com soma dos lances máximos, depósito, construtoras que compram ali e cenário de venda em pacote (85% do valor por lote, 4 meses; editável em ⚙ Premissas).
- **Teto da nota** quando o dado é fraco: sem julgamento conferido 60 · tax deed com resgate provável/homestead 60 · comercial/outro 50 · construído com menos de 3 comps 70 (asterisco na nota, motivo no tooltip).

## Conta (estrutura do BidToFlip, padrões realistas – tudo editável no painel)
- **Compra:** doc stamps 0,7% do lance + taxa do clerk (3% dos primeiros US$ 500 + 1,5% do restante).
- **Reforma por idade e tamanho:** US$/sqft – 2020+ US$ 5 · 2015–19 US$ 10 · 2005–14 US$ 20 · 1995–2004 US$ 30 · antes de 1995 US$ 40; mínimo US$ 8 mil; ano desconhecido US$ 35 mil; +US$ 5 mil com piscina; **contingência 10%**. Terreno: zero.
- **Posse:** 6 meses (terreno 4) × (imposto anual ÷ 12 + seguro 1% do valor/ano + US$ 350/mês de contas/manutenção).
- **Venda (sobre o ARV):** corretor vendedor 2,5% + comprador 2,5% + seguro de título do proprietário pela tabela promulgada FL (zero em Miami-Dade, Broward, Sarasota, Collier) + doc stamps 0,7% + fechamento/diversos US$ 1.000 (lote: 3% do ARV, US$ 500–1.000) + taxa fixa de venda US$ 399 (BidToFlip, só construído). Posse 5 meses (lote 3).
- **Valor de venda — análise local (`local_comps.py`):** vendas qualificadas do cadastro DOR dos últimos 18 meses, mesmo uso e tamanho, na mesma subdivisão → ≈0,5 / 1 / 3 mi (distância aproximada pela seção PLSS), ajustadas pelo ZHVI do ZIP; mostra nível, n e confiança, e com confiança ≥ 60 vira o ARV. Contexto: % construído da subdivisão e da rua, mediana do just value das casas, golfe/HOA, água/esgoto, flood zone. **Avaliações manuais** em `data/valuations_manual.json` vencem o cálculo e o teto limita o Max Bid.
- **Termos em inglês com tooltip:** rótulos usam os termos do mercado americano (ARV, Max Bid, Opening Bid, Final Judgment…); passe o mouse, use Tab ou toque para ver tradução e explicação (dicionário central `TERMS` no template; lista completa no Glossário).
- **Veredito por espaço de lance (FLIP / CONSIDER / CONTESTED / NO ROOM):** SEM ESPAÇO (nenhum lance dá 17% ou tax deed com lance inicial acima do lance máx.) · DISPUTADO – lance até US$ X (foreclosure com julgamento acima do lance máx. – o banco pode aceitar menos – ou preço esperado acima do lance máx.) · FLIP/CONSIDERAR (preço esperado ≤ lance máx.). Hipoteca que sobrevive: desconta o saldo estimado (30 anos amortizados), sem PASSAR automático. ARV só com just value: ÷ 0,85.
- **Extras:** quiet title US$ 2.500 (tax deed e lotes), limpeza/agrimensura de lote US$ 1.500, despejo US$ 2.500 se ocupado, liens que sobrevivem (1ª hipoteca quando há indício).
- **NET** = ARV − custos de venda − custo all-in; **ROI** = NET ÷ custo all-in. **Retorno mínimo 17%** (lance máximo = maior lance com ROI de 17%); **FLIP** ≥ 25%, **CONSIDERAR** 17–25%, **PASSAR** < 17%.
- Cada linha do P&L é editável no painel do imóvel; “Salvar custos como meu padrão” grava no aparelho (com botão para voltar aos padrões).
- **Capa (v7):** NET/ROI/nota no **lance realista** = maior entre lance inicial/julgamento, preço histórico do condado, 55% (TD) / 70% (FC) do lance máx. de 17% e 28%/40% do ARV. “ROI no lance inicial” é só nota. Valor suspeito (ARV vs comps ou condado > 2×) usa o menor número e corta a nota.
- O prazo de saída pelo ZIP (dias no mercado Redfin) aparece no P&L como sensibilidade; pode substituir os meses fixos em ⚙ Premissas.

## Regerar
```bash
python3 build.py --site --offline               # sem RealAuction/PropertyOnion; sites dos CLERKS (listas presenciais, TaxSmart) atualizam 1x/dia
python3 build.py --site --offline --no-clerk    # sem rede nenhuma (só cache)
python3 build.py --site                         # igual, e também não consulta RealAuction (só cache). `--fetch-bids` liga a rede do clerk.
python3 build.py --fetch --site                 # também baixa o que falta do PropertyOnion e do FDOH (água/esgoto)
python3 build.py --site --no-encrypt --out .plain/index.html   # versão sem senha, só para teste local
python3 build.py --fetch-market                 # atualiza Redfin/Zillow (ZHVI e ZORI)
python3 test_dashboard.py                       # testes headless (fórmula, filtros, galeria, alertas, visões, celular)
```
Os comandos são os mesmos da v3. `--site` gera `index.html`, `manifest.webmanifest`, `icons/` e `robots.txt`. A senha é lida de um arquivo fora do repositório. `cache/`, `.plain/` e capturas `*.png` (exceto ícones) não são versionados. Os dados brutos dos leilões ficam em `/workspace/auc/` (fora do repositório). Módulos: `rawdata.py` (leilões), `po_fetch.py` (PropertyOnion páginas), `po_export.py` (exports Premium CSV), `po_bids.py` (preenche Julgamento/Opening Bid de listagens só-PO a partir do RealAuction público, com cache; Lake/Osceola FC exigem login → pulados), `nal.py` (cadastro DOR), `flwmi.py` (água/esgoto).

No painel: alerta **Hipoteca pode sobreviver** (HOA/JR-lien, com valor estimado do PO e toggle no P&L), filtro Negócios limpos/nota penalizados; aba **Meus candidatos** (checklist pré-lance em localStorage, export/import JSON).

### Exports PropertyOnion Premium (rotina 6h / build offline)
1. Baixe o CSV no PropertyOnion (Upcoming, por condado) e salve como
   `/workspace/auc/statewide/po_exports/po_<condado>_<YYYY-MM-DD>.csv`
   (ex.: `po_orange_2026-10-08.csv`, `po_seminole_2026-10-08.csv`). O condado no nome é um fallback;
   a coluna **County** do CSV manda quando presente.
2. O build (`python3 build.py --site`) usa automaticamente o **arquivo mais recente por condado**.
   Limite típico Premium ≈ 2.500 linhas/mês – 1 export/condado-alvo por semana basta.
3. Join: número do processo → parcela → endereço normalizado. Linhas sem match no RealAuction entram
   como imóveis “PropertyOnion” (sem AID inventado; sem julgamento/lance → selo **Sem lance inicial**, preenchido depois por `po_bids.py` quando o RealAuction público já lista o caso).
4. POV vira ARV só com confiança ≥ 70 e dentro de ~35% do valor de condado; senão fica referência.
5. **Nunca** commitar os CSV no repositório público – só o `index.html` criptografado leva os dados ao ar.


## ⚠️ Aviso
Material informativo, gerado automaticamente – **não é recomendação de investimento**. Dados podem estar errados ou desatualizados e leilões são cancelados/adiados com frequência. **Antes de qualquer lance confirme tudo no site do Clerk (leilão e processo) e no Property Appraiser do condado**, faça pesquisa de título (liens, hipotecas sobreviventes, HOA, code enforcement) e vistorie o imóvel.

O site não é indexado por buscadores (`noindex` + `robots.txt`), mas qualquer pessoa com o link e a senha pode acessá-lo.

## Leilões presenciais — Lake e Osceola (`inperson.py`)
Foreclosures de Lake e Osceola são vendidas NO FÓRUM (não no RealAuction). O build lê as listas oficiais do clerk
(Lake: foreclosurecalendar.lakecountyclerkfl.gov; Osceola: CivilMortgageForeclosuresWeb.pdf), baixadas 1× por dia
para `/workspace/auc/statewide/inperson/` (com `--offline` usa só o cache). Casa pelo nº do processo (normalizado),
atualiza datas, remove cancelados e o que saiu da lista, adiciona processos novos (sem endereço = "Processo … — endereço
não publicado"), classifica o autor (HOA/condomínio → alerta de 1ª hipoteca que sobrevive; banco; outro) e mostra o
badge "Leilão presencial — Fórum de Tavares/Kissimmee, 11h" com depósito/pagamento e link do processo (ShowCase / Benchmark).
