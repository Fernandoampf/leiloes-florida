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
| Cadastro (uso DOR, valor, área, ano, homestead, dono) e **vendas comparáveis** | Florida DOR – arquivos NAL (2026) |
| Água e esgoto | FDOH – Florida Water Management Inventory (ArcGIS público) |
| Mercado por ZIP (dias no mercado, preço, US$/sqft) e aluguel típico | Redfin Data Center, Zillow ZHVI e ZORI |

Não automatizados (por regra ou termos de uso): Auction.com, Xome, Hubzu, Bid4Assets; leilões presenciais/listas em PDF de alguns condados.

## O que tem no painel
- **Avaliação estilo BidToFlip:** condado, *Valor de mercado (POV/ARV)* com fonte, julgamento/lance com % vs. valor, lance máximo (17%) com depósito de 5%, NET, ROI, veredito (**FLIP** ≥ 25% · **CONSIDERAR** 17–25% · **PASSAR** < 17%), categoria (J>MAX / abaixo de 17% / lucro baixo / viável), nota 0–100 e autor.
- Faixa de KPIs (desconto mediano, alto patrimônio, enchente, vagos, ≤ 7 dias), aviso **JR-LIEN?**, blocos de categoria clicáveis, **seletor de tipo de imóvel**, ordenação rápida, filtros (inclusive água/esgoto e distância de Orlando), favoritos ★ e cores ● (salvos no aparelho), CSV, link com filtros.
- Visões: **Lista**, **Cards**, **Favoritos**, **Mapa**, **Inteligência** (por condado, autores, mapa de calor valor × desconto), **Resultados** (leilões passados: vendidos, p/ terceiros, cancelados, preço ÷ avaliação), **Calendário** (super dias) e **Dia do leilão** (lista imprimível/CSV dos favoritos com lance máximo, depósito, processo e links).
- Painel de detalhes: **galeria** (fotos, Street View e satélite sem chave de API; links Zillow/Realtor/Maps), alertas de risco com status (*confirmado / indício / estimativa / não verificado*), bloco de **terreno** (água, esgoto, frente, acesso, zoneamento, área, FEMA, wetlands), estratégias FLIP × HOLD/BRRRR, simulador “E se…”, escada de lances (17% mínimo, 25%, 30%, 70% do ARV, break-even, preço esperado, julgamento), P&L com custo de posse por mês e prazo de saída pelo ZIP, BRRRR, reconstrução, **comps** (estimativa), **histórico de leilões / preço esperado**, mercado do ZIP e flip tracker.

## Conta (estrutura do BidToFlip, padrões realistas – tudo editável no painel)
- **Compra:** doc stamps 0,7% do lance + taxa do clerk (3% dos primeiros US$ 500 + 1,5% do restante).
- **Reforma por idade e tamanho:** US$/sqft – 2020+ US$ 5 · 2015–19 US$ 10 · 2005–14 US$ 20 · 1995–2004 US$ 30 · antes de 1995 US$ 40; mínimo US$ 8 mil; ano desconhecido US$ 35 mil; +US$ 5 mil com piscina; **contingência 10%**. Terreno: zero.
- **Posse:** 6 meses (terreno 4) × (imposto anual ÷ 12 + seguro 1% do valor/ano + US$ 350/mês de contas/manutenção).
- **Venda (sobre o ARV):** corretor vendedor 2,5% + comprador 2,5% + título/escrow 1,5% + doc stamps 0,7% + fechamento/diversos US$ 1.500 + WRA US$ 399.
- **Extras:** quiet title US$ 2.500 (tax deed e lotes), limpeza/agrimensura de lote US$ 1.500, despejo US$ 2.500 se ocupado, liens que sobrevivem (1ª hipoteca quando há indício).
- **NET** = ARV − custos de venda − custo all-in; **ROI** = NET ÷ custo all-in. **Retorno mínimo 17%** (lance máximo = maior lance com ROI de 17%); **FLIP** ≥ 25%, **CONSIDERAR** 17–25%, **PASSAR** < 17%.
- Cada linha do P&L é editável no painel do imóvel; “Salvar custos como meu padrão” grava no aparelho (com botão para voltar aos padrões).
- Tax deed: NET/ROI no **preço esperado** (histórico do condado) quando disponível – o lance inicial é só o imposto devido.
- O prazo de saída pelo ZIP (dias no mercado Redfin) aparece no P&L como sensibilidade; pode substituir os meses fixos em ⚙ Premissas.

## Regerar
```bash
python3 build.py --site                         # offline (o que a rotina das 7:46 roda); gera index.html criptografado
python3 build.py --fetch --site                 # também baixa o que falta do PropertyOnion e do FDOH (água/esgoto)
python3 build.py --site --no-encrypt --out .plain/index.html   # versão sem senha, só para teste local
python3 build.py --fetch-market                 # atualiza Redfin/Zillow (ZHVI e ZORI)
python3 test_dashboard.py                       # testes headless (fórmula, filtros, galeria, alertas, visões, celular)
```
Os comandos são os mesmos da v3. `--site` gera `index.html`, `manifest.webmanifest`, `icons/` e `robots.txt`. A senha é lida de um arquivo fora do repositório. `cache/`, `.plain/` e capturas `*.png` (exceto ícones) não são versionados. Os dados brutos dos leilões ficam em `/workspace/auc/` (fora do repositório). Módulos: `rawdata.py` (leilões), `po_fetch.py` (PropertyOnion), `nal.py` (cadastro DOR), `flwmi.py` (água/esgoto).

## ⚠️ Aviso
Material informativo, gerado automaticamente – **não é recomendação de investimento**. Dados podem estar errados ou desatualizados e leilões são cancelados/adiados com frequência. **Antes de qualquer lance confirme tudo no site do Clerk (leilão e processo) e no Property Appraiser do condado**, faça pesquisa de título (liens, hipotecas sobreviventes, HOA, code enforcement) e vistorie o imóvel.

O site não é indexado por buscadores (`noindex` + `robots.txt`), mas qualquer pessoa com o link e a senha pode acessá-lo.
