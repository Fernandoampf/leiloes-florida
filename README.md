# LEILÃO – Leilões Flórida (CHALLENGE CAPITAL)

Painel (dashboard) com imóveis em leilões de **tax deed** e **foreclosure** na Flórida, com foco em comprar e revender (flip) e lotes edificáveis, tendo Orlando como base.

- **Site:** https://fernandoampf.github.io/leiloes-florida/
- **Data dos dados:** 08/10/2026 (leilões a partir dessa data; os já realizados foram removidos).
- **Fontes:** sites oficiais de leilão dos condados (RealAuction / Clerk), PropertyOnion (detalhes, AVM, aluguel, ocupação, hipotecas, FEMA, histórico, fotos) e Property Appraiser. Mercado por ZIP: **Redfin Data Center** (janelas de 90 dias, até 31/05/2026) e **Zillow ZHVI** (até 31/08/2026). Valores ausentes aparecem como "—"; reforma, aluguel e custos são **estimativas** indicadas como tal.
- **Acesso protegido por senha** (StaticCrypt: a página é criptografada com AES e só abre com a senha; a senha **não** fica no repositório).

## Como usar no celular
Abra o link, digite a senha (marque "lembrar" para não pedir de novo) e use **"Adicionar à Tela de Início"** (iPhone: Safari › Compartilhar; Android: Chrome › menu ⋮ › Instalar app). O ícone "LEILÃO" abre o painel em tela cheia.

## O que tem no painel
- Chips por tipo (SFR, Townhouse, Condo, Mobile, Multifamiliar, Lote) com contagem, KPIs (viáveis, J>MAX, abaixo de 18%, aluguel forte, considerar, NET viável) e linha de resumo.
- Ordenação rápida (nota, NET, ROI, spread, data, mais novo, ARV, yield, revenda mais rápida, hoje, < 7 dias, ★ favoritos) e filtros completos; o botão **Copiar link** leva os filtros na URL. Exportar CSV e escolher colunas.
- Tabela densa, cards e mapa. Cada imóvel tem links para **Zillow**, **Realtor.com**, Google Maps, Property Appraiser e leilão.
- Painel de detalhes (clique na linha/card): simulador "E se…" (lance, ARV, reforma, meses, aluguel, reserva p/ dívidas, refi), lances de referência (piso 10%, 25%, 30%, regra dos 70%, break-even, lance inicial/julgamento), P&L do flip, BRRRR (aluguel), custo de reconstrução, mercado do ZIP e flip tracker (salvo no aparelho).

## Como funciona o lance máximo, o veredito e a nota (0–100)
**Lance máximo = o maior lance que ainda dá retorno mínimo de 10%** sobre todo o dinheiro investido até a revenda.

- **Investido** = lance + taxas do clerk/título/registro (1,5% do lance) + doc stamps na compra (0,70%) + taxas do leilão (US$ 200) + quiet title nos tax deeds (US$ 2.500) + despejo se ocupado (US$ 2.500, estimativa) + reforma estimada + posse (2,5% do valor ao ano × meses) + reserva para hipoteca que sobrevive, quando houver.
- **Meses** = 6 + 3 (tax deed, quiet title) + 2 (se houver despejo).
- **Venda** = comissão do vendedor 2,5% + comprador 2,5% + título/escrow 1,5% + doc stamps 0,70% = 7,2% do valor de revenda (ARV).
- **NET** = ARV − venda − investido; **ROI** = NET ÷ investido. Na tabela, calculados no julgamento (foreclosure) ou no lance inicial (tax deed – otimista, marcado com ¹, porque a disputa sobe o preço).
- **Veredito:** FLIP se ROI ≥ 18% · CONSIDER entre 10% e 18% · PASS abaixo de 10% ou com risco grave. **J>MAX** = julgamento acima do lance pela regra dos 70% (0,70 × ARV − reforma).
- **Nota 0–100** (critério do radar): retorno até 50 pts (cheio com ROI ≥ 40%) + folga entre lance máximo e lance de referência até 40 pts + risco 10/5/0 − 3 por dado faltando (máx. −15); EVITAR limita a 10 e hipoteca que sobrevive a 15.
- **Temperatura de revenda** (HOT/WARM/COOL/COLD, 0–100) inferida dos dados Redfin do ZIP: dias no mercado, venda/pedido, % vendido em 2 semanas e variação anual.

Todos os valores são padrão e podem ser mudados no botão **⚙ Premissas** (ficam salvos no aparelho). As regras completas estão em "Como a nota é calculada", dentro do painel.

**Não disponível** (sem fonte gratuita confiável): vendas comparáveis individuais (comps), taxa de HOA, imposto predial real, cotação de seguro e dias no mercado do próprio imóvel.

## Regerar
```bash
python3 build.py --site                         # offline; gera index.html criptografado (senha lida de um arquivo fora do repositório)
python3 build.py --site --no-encrypt --out .plain/index.html   # versão sem senha, só para teste local
python3 build.py --fetch-market                 # atualiza os dados de mercado Redfin/Zillow
python3 test_dashboard.py                       # testes headless (fórmula, filtros, painel, celular)
```
`--site` gera `index.html`, `manifest.webmanifest`, `icons/` e `robots.txt`. As pastas `cache/` e `.plain/` não são versionadas.

## ⚠️ Aviso
Material apenas informativo, gerado automaticamente – **não é recomendação de investimento**. Os dados podem estar desatualizados ou incorretos e leilões são cancelados/adiados com frequência. **Antes de qualquer lance, confirme tudo diretamente no site do Clerk (leilão e processo), no Property Appraiser do condado** e com pesquisa de título (liens, hipotecas sobreviventes, débitos de HOA/condomínio, code enforcement), além de vistoriar o imóvel.

O site não é indexado por buscadores (`noindex` + `robots.txt`), mas qualquer pessoa com o link pode acessá-lo.
