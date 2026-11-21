# Nota para o Claude – valores do processo já lidos pelo navegador e conferência do banco no dia do leilão

Escrita em 21/11/2026 ~01h ET pelo Grok (P21, lotes 2–5 do navegador). Pedido do Fernando (20/11): deixar registrado quais julgamentos já foram lidos no processo, e nos imóveis interessantes conferir **no dia do leilão** se o banco foi mesmo até onde se espera.

Regras que continuam valendo:
- **P20:** o lance do banco é só informativo até o dia do leilão – não entra em teto, nota, veredito, preço esperado, filtro nem ordenação antes do dia. No dia, a rotina das 8h ET (dayof_refresh) relê e o painel mostra "lance do banco hoje · banco vai até".
- O julgamento lido no processo **não substitui** um número oficial diferente da lista do RealAuction; quando diferem, fica a nota `fjDiff`. Julgamento **parcial** (só parte do documento lida) nunca vira o total: aparece como "julgamento parcial ≥ US$ X (conferir total)".
- Sem nome de pessoa no git. Os dados crus (com nomes) ficam fora do git, em /workspace/auc/statewide/dossie_browser/batch*.json.

## 1) Julgamentos (Final Judgment) já lidos no processo do clerk – 76 imóveis

Fonte de todos: **processo no clerk**, aberto pelo navegador (Lake = ShowCase, Volusia = clerk.org, Brevard = BECA, Broward = Odyssey/Turnstile, Orange = myeClerk). "Lido em" = data da leitura (ET). Veredito = painel de 21/11 após o build.

| Condado | Endereço | Processo | Leilão | Julgamento (FJ) | Parcial? | Lido em | Veredito hoje |
|---|---|---|---|---|---|---|---|
| Lake | 141 Cataldo Way Groveland, FL 34736 | 2025ca002438 | 24/11/2026 | US$ 76.030,04 | não | 20/11/2026 | DISPUTADO |
| Lake | 39227 Treeline Dr Lady Lake, FL 32159 | 2025ca002501 | 24/11/2026 | US$ 506.716,86 | não | 20/11/2026 | PASSAR |
| Lake | 5013 Harbor Hts Lady Lake, FL 32159 | 2025ca002223 | 24/11/2026 | US$ 234.438,14 | não | 20/11/2026 | DISPUTADO |
| Lake | 8080 Cherrystone St Leesburg, FL 34748 | 2025ca001588 | 24/11/2026 | US$ 510.361,99 | não | 20/11/2026 | FLIP |
| Orange | 262 PLEASANT GARDENS DR APOPKA, 32703 | 2025-CA-008467-O | 24/11/2026 | US$ 103.220,75 | não | 21/11/2026 | DISPUTADO |
| Volusia | 2134 N NORMANDY BLVD DELTONA, FL 32725 | 2026 10482 CIDL | 24/11/2026 | US$ 235.654,82 | não | 20/11/2026 | DISPUTADO |
| Volusia | 3177 NEWHOPE DR DELTONA, FL 32738 | 2025 11056 CIDL | 24/11/2026 | US$ 459.763,66 | não | 20/11/2026 | DISPUTADO |
| Volusia | 623 MCMORMICK ST DAYTONA BEACH, FL 32114 | 2025 13643 CICI | 25/11/2026 | US$ 112.408,33 | não | 20/11/2026 | DISPUTADO |
| Orange | 2025 RIBBON FALLS PKWY ORLANDO, 32824 | 2024-CA-007298-O | 30/11/2026 | US$ 239.078,08 | não | 21/11/2026 | DISPUTADO |
| Orange | 7744 RIFFLE LN ORLANDO, 32818 | 2025-CA-012054-O | 30/11/2026 | US$ 539.709,18 | não | 21/11/2026 | DISPUTADO |
| Broward | 4128 SW 183 AVE MIRAMAR, 33029 | CACE-24-013582 | 01/12/2026 | ≥ US$ 602.022,66 (lista RealAuction: US$ 662.781,54) | **parcial** | 20/11/2026 | DISPUTADO |
| Broward | 8345 NW 7 PL PLANTATION, 33324 | CACE-25-019324 | 01/12/2026 | US$ 724.698,60 | não | 20/11/2026 | DISPUTADO |
| Orange | 11205 TINDALL RD ORLANDO, 32832 | 2026-CA-001238-O | 01/12/2026 | US$ 2.081.521,61 | não | 21/11/2026 | CONSIDERAR |
| Orange | 14139 WARD RD ORLANDO, 32824 | 2025-CA-011892-O | 01/12/2026 | US$ 512.466,29 | não | 21/11/2026 | FLIP |
| Orange | 14291 SWANLEY ST ORLANDO, 32832 | 2025-CA-008997-O | 01/12/2026 | US$ 278.616,41 | não | 21/11/2026 | FLIP |
| Orange | 1547 PRIORY CIR WINTER GARDEN, 34787-5566 | 2024-CA-010876-O | 01/12/2026 | US$ 378.380,92 | não | 21/11/2026 | CONFERIR TÍTULO |
| Orange | 5244 OLD WINGER GARDEN ROAD ORLANDO, 32811 | 2024-CA-007937-O | 01/12/2026 | US$ 1.457.814,27 | não | 21/11/2026 | CONSIDERAR |
| Orange | 5440 AMAZON ST ORLANDO, 32810 | 2026-CA-002181-O | 01/12/2026 | US$ 302.498,84 | não | 21/11/2026 | FLIP |
| Orange | 8670 VEDDER LN ORLANDO, 32832 | 2025-CA-003378-O | 01/12/2026 | US$ 418.222,21 | não | 21/11/2026 | FLIP |
| Volusia | 4085 MONZA DR NEW SMYRNA BEACH, FL 32168 | 2025 13290 CIDL | 01/12/2026 | US$ 187.957,02 | não | 20/11/2026 | DISPUTADO |
| Brevard | 1280 RAYFIELD ST SE PALM BAY, FL 32909 | 05-2025-CA-039975-XXCA-BC | 02/12/2026 | US$ 181.787,62 | não | 20/11/2026 | DISPUTADO |
| Brevard | 2170 SPRING CREEK CIR NE PALM BAY, FL 32905 | 05-2025-CA-053667-XXCA-BC | 02/12/2026 | US$ 391.757,17 | não | 20/11/2026 | DISPUTADO |
| Brevard | 2901 TIVOLI AVE SE PALM BAY, FL 32909 | 05-2025-CA-042721-XXCA-BC | 02/12/2026 | US$ 363.897,89 | não | 20/11/2026 | DISPUTADO |
| Brevard | 2990 N TROPICAL TRL MERRITT ISLAND, FL 32953 | 05-2016-CA-042099-XXXX-XX | 02/12/2026 | US$ 361.214,32 no processo – vale o da lista do RealAuction: US$ 274.873,00 | não | 20/11/2026 | DISPUTADO |
| Brevard | 3333 SIDERWHEEL DR ROCKLEDGE, FL 32955 | 05-2025-CA-039983-XXCA-BC | 02/12/2026 | US$ 399.791,68 | não | 20/11/2026 | DISPUTADO |
| Brevard | 5362 TALBOT BLVD COCOA, FL 32926 | 05-2026-CA-024728-XXCA-BC | 02/12/2026 | US$ 503.427,12 | não | 20/11/2026 | DISPUTADO |
| Brevard | 961 CULPEPPER AVE SE PALM BAY, FL 32909 | 05-2025-CA-062171-XXCA-BC | 02/12/2026 | US$ 266.121,36 | não | 20/11/2026 | CONSIDERAR |
| Brevard | 975 DUGAN CIR SE PALM BAY, FL 32909 | 05-2025-CA-043656-XXCA-BC | 02/12/2026 | US$ 383.952,87 | não | 20/11/2026 | FLIP |
| Broward | 14857 SW 38 ST DAVIE, 33331 | CACE-26-006537 | 02/12/2026 | US$ 2.353.247,43 | não | 21/11/2026 | DISPUTADO |
| Broward | 1831 SW 48 AVE WEST PARK, 33023 | CACE-26-009749 | 02/12/2026 | US$ 518.327,60 | não | 21/11/2026 | DISPUTADO |
| Broward | 2311 SW 86 WAY MIRAMAR, 33025 | CACE-26-005427 | 02/12/2026 | ≥ US$ 70.343,82 | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 3513 NW 14 CT LAUDERHILL, 33311 | CACE-26-005077 | 02/12/2026 | ≥ US$ 41.237,54 | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 5832 NW 54 CIR CORAL SPRINGS, 33067 | CACE-25-014769 | 02/12/2026 | US$ 9.222,31 | não | 21/11/2026 | DISPUTADO |
| Broward | 8556 SW 23 CT MIRAMAR, 33025 | CACE-24-001546 | 02/12/2026 | US$ 352.141,97 | não | 21/11/2026 | DISPUTADO |
| Orange | 15006 BELLINKOFF LN ORLANDO, 32828 | 2026-CA-006029-O | 02/12/2026 | US$ 62.989,68 | não | 21/11/2026 | DISPUTADO |
| Broward | 1231 SW 46 AVE POMPANO BEACH, 33069 | CACE-19-006130 | 03/12/2026 | ≥ US$ 227.323,16 | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 2890 SW 130 TER MIRAMAR, 33027 | CACE-22-006017 | 03/12/2026 | US$ 700.027,42 | não | 21/11/2026 | DISPUTADO |
| Broward | 3526 NW 14 CT LAUDERHILL, 33311 | CACE-26-002003 | 03/12/2026 | ≥ US$ 22.788,64 (lista RealAuction: US$ 30.774,64) | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 4900 NW 48 TER TAMARAC, 33319 | CACE-26-007579 | 03/12/2026 | ≥ US$ 5.208,10 | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 5406 NW 48 LN TAMARAC, 33319 | CACE-25-015920 | 03/12/2026 | ≥ US$ 425.243,11 (lista RealAuction: US$ 438.923,11) | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 610 W LAS OLAS BLVD FORT LAUDERDALE, 33312 | CACE-26-002347 | 03/12/2026 | US$ 378.264,90 | não | 21/11/2026 | DISPUTADO |
| Orange | 1312 RALPH POE DR APOPKA, 32703 | 2025-CA-008454-O | 03/12/2026 | US$ 571.951,31 | não | 21/11/2026 | FLIP |
| Volusia | 1197 AUGUST SKY DR DELTONA, FL 32738 | 2025 13525 CIDL | 03/12/2026 | US$ 425.580,01 | não | 20/11/2026 | DISPUTADO |
| Volusia | 2405 MARSH RD DELAND, FL 32724 | 2025 12924 CIDL | 03/12/2026 | US$ 413.996,11 | não | 20/11/2026 | DISPUTADO |
| Volusia | 2816 S SLATER DR DELTONA, FL 32738 | 2018 11972 CIDL | 03/12/2026 | ≥ US$ 125.054,49 | **parcial** | 20/11/2026 | DISPUTADO |
| Volusia | 3526 FERNANDA DR DELTONA, FL 32738 | 2025 10876 CIDL | 03/12/2026 | US$ 273.537,99 | não | 20/11/2026 | DISPUTADO |
| Volusia | 953 PRESCOTT BLVD DELTONA, FL 32738 | 2026 11472 CIDL | 03/12/2026 | US$ 212.196,72 | não | 20/11/2026 | DISPUTADO |
| Broward | 4067 CRYSTAL LAKE DR DEERFIELD BEACH, 33064 | CONO-26-020641 | 04/12/2026 | US$ 17.186,37 | não | 21/11/2026 | DISPUTADO |
| Broward | 4460 NW 8 PL PLANTATION, 33317 | CONO-26-021199 | 04/12/2026 | US$ 17.275,19 | não | 21/11/2026 | DISPUTADO |
| Orange | 6106 APOLLOS CORNER WAY ORLANDO, 32829 | 2025-CA-010175-O | 04/12/2026 | US$ 403.048,15 | não | 21/11/2026 | DISPUTADO |
| Volusia | 3733 CARDINAL BLVD 5 DAYTONA BEACH SHORES, FL 32118 | 2025 22823 COCI | 07/12/2026 | US$ 48.082,14 | não | 21/11/2026 | CONFERIR TÍTULO |
| Broward | 1018 NE 17 TER FORT LAUDERDALE, 33304 | CACE-26-009212 | 08/12/2026 | ≥ US$ 519.873,19 | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 1558 MYRTLE OAK TER HOLLYWOOD, 33021 | CACE-24-015132 | 08/12/2026 | US$ 670.824,16 | não | 21/11/2026 | DISPUTADO |
| Orange | 6135 ARBOR WATCH LOOP ORLANDO, 32829 | 2025-CA-003987-O | 08/12/2026 | US$ 437.135,43 | não | 21/11/2026 | CONFERIR TÍTULO |
| Volusia | 1588 NAPLES CIR DELTONA, FL 32738 | 2024 12194 CIDL | 08/12/2026 | US$ 108.201,13 | não | 21/11/2026 | DISPUTADO |
| Volusia | 1608 LADY FERN TR DELAND, FL 32720 | 2025 11272 CIDL | 08/12/2026 | US$ 268.818,14 | não | 21/11/2026 | DISPUTADO |
| Volusia | 2017 COURTLAND BLVD DELTONA, FL 32738 | 2026 10254 CIDL | 08/12/2026 | US$ 341.006,36 | não | 21/11/2026 | DISPUTADO |
| Volusia | 505 DORSEY CT DELTONA, FL 32725 | 2025 14373 CIDL | 08/12/2026 | US$ 360.161,10 | não | 21/11/2026 | DISPUTADO |
| Volusia | 924 ADLER DR DELTONA, FL 32738 | 2026 12066 CIDL | 08/12/2026 | US$ 383.236,83 | não | 21/11/2026 | DISPUTADO |
| Brevard | 6395 MULLER AVE, Cocoa, FL 32927 | 05-2016-CA-010468-XXXX-XX | 09/12/2026 | US$ 363.276,17 | não | 20/11/2026 | DISPUTADO |
| Broward | 6819 SIENNA CLUB DR LAUDERHILL, 33319 | CACE-18-015526 | 09/12/2026 | ≥ US$ 95.608,05 (lista RealAuction: US$ 100.215,57) | **parcial** | 21/11/2026 | DISPUTADO |
| Broward | 81 ISLE OF VENICE DR FORT LAUDERDALE, 33301 | CACE-08-031733 | 09/12/2026 | ≥ US$ 3.464.145,94 (lista RealAuction: US$ 4.673.776,55) | **parcial** | 21/11/2026 | DISPUTADO |
| Orange | 1348 WHITNEY ISLES DR WINDERMERE, 34786 | 2025-CA-003624-O | 09/12/2026 | US$ 466.898,49 | não | 21/11/2026 | DISPUTADO |
| Orange | 13804 DOVE WING CT ORLANDO, 32828 | 2025-CA-011575-O | 09/12/2026 | US$ 10.534,88 | não | 21/11/2026 | DISPUTADO |
| Orange | 817 POLK ST ORLANDO, 32805 | 2025-CA-003835-O | 09/12/2026 | US$ 261.689,68 | não | 21/11/2026 | CONFERIR TÍTULO |
| Broward | 5076 SW 139 TER MIRAMAR, 33027 | CACE-26-005019 | 10/12/2026 | ≥ US$ 178.117,24 | **parcial** | 21/11/2026 | DISPUTADO |
| Volusia | 219 SHADY LANE ORANGE CITY, FL 32763 | 2021 11724 CIDL | 10/12/2026 | ≥ US$ 523.484,63 | **parcial** | 21/11/2026 | DISPUTADO |
| Volusia | 2507 HOPTREE LN EDGEWATER, FL 32141 | 2025 13353 CIDL | 10/12/2026 | US$ 379.019,18 no processo – vale o da lista do RealAuction: US$ 379.029,18 | não | 21/11/2026 | DISPUTADO |
| Volusia | 707 RIDGE BVLD SOUTH DAYTONA, FL 32119 | 2024 29167 COCI | 14/12/2026 | US$ 30.591,66 | não | 20/11/2026 | DISPUTADO |
| Brevard | 1204 E UNIVERSITY BLVD MELBOURNE, FL 32901 | 05-2025-CA-059985-XXCA-BC | 16/12/2026 | US$ 123.623,58 | não | 21/11/2026 | DISPUTADO |
| Brevard | 1542 RACHEL AVE SE PALM BAY, FL 32909 | 05-2025-CA-045676-XXCA-BC | 16/12/2026 | US$ 407.395,74 | não | 21/11/2026 | DISPUTADO |
| Brevard | 2127 SANS SOUCI AVE SE PALM BAY, FL 32909 | 05-2026-CA-013891-XXCA-BC | 16/12/2026 | US$ 251.927,43 | não | 20/11/2026 | DISPUTADO |
| Volusia | 88 SPINNAKER CIR SOUTH DAYTONA, FL 32119 | 2026 11971 CICI | 16/12/2026 | US$ 434.345,24 | não | 21/11/2026 | DISPUTADO |
| Volusia | 508 EASTWOOD LANE DAYTONA BEACH, FL 32118 | 2024 11074 CICI | 23/12/2026 | US$ 384.644,08 | não | 21/11/2026 | DISPUTADO |
| Volusia | 1140 5TH ST ORANGE CITY, FL 32763 | 2025 14365 CIDL | 29/12/2026 | US$ 262.464,72 | não | 21/11/2026 | DISPUTADO |
| Volusia | 9 Bella Oaks Dr Port Orange, FL 32129 | 2025 13693 Cici | 06/01/2027 | US$ 336.437,05 | não | 21/11/2026 | DISPUTADO |

Total: 76 imóveis com julgamento lido (13 parciais). Polk (lote 1, 4 casas) não foi lido: os termos do clerk de Polk proíbem acesso automatizado.

## 2) Pedido: conferir no dia do leilão até onde o banco foi

Imóveis interessantes = FLIP, CONSIDERAR, CONFERIR TÍTULO (que pela conta seriam FLIP/CONSIDERAR) e DISPUTADO com folga pequena (preço esperado no máximo 10% acima do nosso lance máx.). Para o Fernando, onde o banco não publicou o lance, a dúvida é se o banco vai até o julgamento ("vai longe") ou baixa/tira no dia.

**No dia de cada leilão abaixo, por favor:**
1. Conferir que a rotina das 8h ET releu o lance do banco (lista pública do RealAuction, campo "Plaintiff Max Bid" via chamada UPDATE, campo P; "A" = oculto). Se der, reler ~1 h antes do leilão.
2. Registrar a leitura (valor ou "oculto", com hora ET) – fica em bankbid_history / dayof (fora do git).
3. Depois do leilão, registrar o resultado: vendido a terceiro (por quanto), ficou com o banco (por quanto), cancelado ou resgatado. Comparar com o julgamento lido no processo e com o nosso lance máx., para medir por autor quantas vezes o banco baixou ou saiu (P20).
4. Nada disso muda teto/veredito antes do dia (P20). Lance, pagamento ou contato só com ordem expressa do Fernando.

### 2a) Banco ainda sem lance publicado (oculto ou sem valor publicado) – 52 imóveis

| Leilão | Condado | Endereço | Processo | Veredito | Nosso lance máx. | Preço esperado | Julgamento lido | Banco hoje | Alertas do processo |
|---|---|---|---|---|---|---|---|---|---|
| 24/11/2026 | Lake | 8080 Cherrystone St Leesburg, FL 34748 | 2025ca001588 | FLIP | US$ 290.503 | US$ 265.854 | US$ 510.361,99 | sem valor publicado até agora | financiamento solar/obra no processo, governo renunciou (exceto sobra) |
| 30/11/2026 | Orange | 2025 RIBBON FALLS PKWY ORLANDO, 32824 | 2024-CA-007298-O | DISPUTADO | US$ 203.057 | US$ 222.240 | US$ 239.078,08 | oculto | financiamento solar/obra no processo, risco alto de cancelamento, processo reaberto |
| 01/12/2026 | Broward | 4128 SW 183 AVE MIRAMAR, 33029 | CACE-24-013582 | DISPUTADO | US$ 732.040 | US$ 751.750 | ≥ US$ 602.022,66 (parcial) | sem valor publicado até agora | processo contestado, risco alto de cancelamento, julgamento parcial ≥ US$ 602.023, julgamento de 2025, vários julgamentos no processo |
| 01/12/2026 | Broward | 8345 NW 7 PL PLANTATION, 33324 | CACE-25-019324 | DISPUTADO | US$ 461.429 | US$ 469.050 | US$ 724.698,60 | sem valor publicado até agora | – |
| 01/12/2026 | Orange | 11205 TINDALL RD ORLANDO, 32832 | 2026-CA-001238-O | CONSIDERAR | US$ 673.392 | US$ 607.500 | US$ 2.081.521,61 | sem valor publicado até agora | – |
| 01/12/2026 | Orange | 14139 WARD RD ORLANDO, 32824 | 2025-CA-011892-O | FLIP | US$ 488.840 | US$ 410.400 | US$ 512.466,29 | sem valor publicado até agora | risco alto de cancelamento, pedido de cancelamento pendente |
| 01/12/2026 | Orange | 14291 SWANLEY ST ORLANDO, 32832 | 2025-CA-008997-O | FLIP | US$ 239.896 | US$ 206.550 | US$ 278.616,41 | sem valor publicado até agora | – |
| 01/12/2026 | Orange | 1547 PRIORY CIR WINTER GARDEN, 34787-5566 | 2024-CA-010876-O | CONFERIR TÍTULO | US$ 271.095 | US$ 197.400 | US$ 378.380,92 | sem valor publicado até agora | falência em série, julgamento de 2025 |
| 01/12/2026 | Orange | 5244 OLD WINGER GARDEN ROAD ORLANDO, 32811 | 2024-CA-007937-O | CONSIDERAR | US$ 588.991 | US$ 587.208 | US$ 1.457.814,27 | sem valor publicado até agora | risco alto de cancelamento, vários julgamentos no processo |
| 01/12/2026 | Orange | 5440 AMAZON ST ORLANDO, 32810 | 2026-CA-002181-O | FLIP | US$ 161.591 | US$ 130.000 | US$ 302.498,84 | sem valor publicado até agora | 120 dias de resgate federal |
| 01/12/2026 | Orange | 8670 VEDDER LN ORLANDO, 32832 | 2025-CA-003378-O | FLIP | US$ 254.670 | US$ 216.000 | US$ 418.222,21 | sem valor publicado até agora | – |
| 02/12/2026 | Brevard | 2990 N TROPICAL TRL MERRITT ISLAND, FL 32953 | 05-2016-CA-042099-XXXX-XX | DISPUTADO | US$ 304.474 | US$ 327.985 | US$ 361.214,32 (lista: US$ 274.873,00) | sem valor publicado até agora | falência em série, financiamento solar/obra no processo, vários julgamentos no processo, FJ do processo US$ 361.214 ≠ lista |
| 02/12/2026 | Brevard | 3333 SIDERWHEEL DR ROCKLEDGE, FL 32955 | 05-2025-CA-039983-XXCA-BC | DISPUTADO | US$ 268.268 | US$ 286.170 | US$ 399.791,68 | sem valor publicado até agora | processo contestado |
| 02/12/2026 | Brevard | 961 CULPEPPER AVE SE PALM BAY, FL 32909 | 05-2025-CA-062171-XXCA-BC | CONSIDERAR | US$ 166.738 | US$ 160.052 | US$ 266.121,36 | sem valor publicado até agora | financiamento solar/obra no processo |
| 02/12/2026 | Brevard | 975 DUGAN CIR SE PALM BAY, FL 32909 | 05-2025-CA-043656-XXCA-BC | FLIP | US$ 215.053 | US$ 150.537 | US$ 383.952,87 | sem valor publicado até agora | – |
| 02/12/2026 | Broward | 14857 SW 38 ST DAVIE, 33331 | CACE-26-006537 | DISPUTADO | US$ 1.442.655 | US$ 1.463.000 | US$ 2.353.247,43 | sem valor publicado até agora | – |
| 02/12/2026 | Broward | 1831 SW 48 AVE WEST PARK, 33023 | CACE-26-009749 | DISPUTADO | US$ 337.878 | US$ 347.370 | US$ 518.327,60 | sem valor publicado até agora | 120 dias de resgate federal |
| 02/12/2026 | Broward | 2311 SW 86 WAY MIRAMAR, 33025 | CACE-26-005427 | DISPUTADO | US$ 240.149 | US$ 253.610 | ≥ US$ 70.343,82 (parcial) | sem valor publicado até agora | associação contestou, julgamento parcial ≥ US$ 70.344 |
| 02/12/2026 | Broward | 3513 NW 14 CT LAUDERHILL, 33311 | CACE-26-005077 | DISPUTADO | US$ 182.086 | US$ 198.180 | ≥ US$ 41.237,54 (parcial) | sem valor publicado até agora | 120 dias de resgate federal, hipoteca sobrevive, julgamento parcial ≥ US$ 41.238 |
| 02/12/2026 | Broward | 5832 NW 54 CIR CORAL SPRINGS, 33067 | CACE-25-014769 | DISPUTADO | US$ 486.691 | US$ 509.320 | US$ 9.222,31 | sem valor publicado até agora | hipoteca sobrevive, risco alto de cancelamento |
| 02/12/2026 | Broward | 8556 SW 23 CT MIRAMAR, 33025 | CACE-24-001546 | DISPUTADO | US$ 240.149 | US$ 253.610 | US$ 352.141,97 | sem valor publicado até agora | risco alto de cancelamento, julgamento de 2025, vários julgamentos no processo |
| 02/12/2026 | Orange | 15006 BELLINKOFF LN ORLANDO, 32828 | 2026-CA-006029-O | DISPUTADO | US$ 175.485 | US$ 188.730 | US$ 62.989,68 | sem valor publicado até agora | hipoteca executada não é a 1ª, risco alto de cancelamento |
| 03/12/2026 | Broward | 2890 SW 130 TER MIRAMAR, 33027 | CACE-22-006017 | DISPUTADO | US$ 503.856 | US$ 526.750 | US$ 700.027,42 | sem valor publicado até agora | falência em série, 1 ano de resgate federal, julgamento de 2023 |
| 03/12/2026 | Broward | 3526 NW 14 CT LAUDERHILL, 33311 | CACE-26-002003 | DISPUTADO | US$ 181.910 | US$ 198.030 | ≥ US$ 22.788,64 (parcial) | sem valor publicado até agora | 120 dias de resgate federal, hipoteca sobrevive, julgamento parcial ≥ US$ 22.789 |
| 03/12/2026 | Broward | 4900 NW 48 TER TAMARAC, 33319 | CACE-26-007579 | DISPUTADO | US$ 362.109 | US$ 370.000 | ≥ US$ 5.208,10 (parcial) | sem valor publicado até agora | hipoteca sobrevive, julgamento parcial ≥ US$ 5.208 |
| 03/12/2026 | Broward | 5406 NW 48 LN TAMARAC, 33319 | CACE-25-015920 | DISPUTADO | US$ 351.099 | US$ 360.010 | ≥ US$ 425.243,11 (parcial) | sem valor publicado até agora | 120 dias de resgate federal, julgamento parcial ≥ US$ 425.243, vários julgamentos no processo |
| 03/12/2026 | Orange | 1312 RALPH POE DR APOPKA, 32703 | 2025-CA-008454-O | FLIP | US$ 334.908 | US$ 286.200 | US$ 571.951,31 | sem valor publicado até agora | – |
| 03/12/2026 | Volusia | 1197 AUGUST SKY DR DELTONA, FL 32738 | 2025 13525 CIDL | DISPUTADO | US$ 203.537 | US$ 215.160 | US$ 425.580,01 | sem valor publicado até agora | 120 dias de resgate federal, associação contestou, financiamento solar/obra no processo, ocupação: possivelmente vago (cartas devolvidas) |
| 03/12/2026 | Volusia | 2405 MARSH RD DELAND, FL 32724 | 2025 12924 CIDL | DISPUTADO | US$ 514.338 | US$ 527.523 | US$ 413.996,11 | sem valor publicado até agora | 120 dias de resgate federal, processo contestado, possível hipoteca reversa (HECM), ocupação: provável dono/herdeiro no imóvel |
| 03/12/2026 | Volusia | 3526 FERNANDA DR DELTONA, FL 32738 | 2025 10876 CIDL | DISPUTADO | US$ 195.860 | US$ 207.900 | US$ 273.537,99 | sem valor publicado até agora | falência ativa, associação contestou, julgamento de 2025 |
| 04/12/2026 | Broward | 4460 NW 8 PL PLANTATION, 33317 | CONO-26-021199 | DISPUTADO | US$ 293.127 | US$ 301.540 | US$ 17.275,19 | sem valor publicado até agora | hipoteca sobrevive |
| 04/12/2026 | Orange | 6106 APOLLOS CORNER WAY ORLANDO, 32829 | 2025-CA-010175-O | DISPUTADO | US$ 172.483 | US$ 183.600 | US$ 403.048,15 | sem valor publicado até agora | inquilino com direitos, ocupação: ocupado (inquilino no processo) |
| 07/12/2026 | Volusia | 3733 CARDINAL BLVD 5 DAYTONA BEACH SHORES, FL 32118 | 2025 22823 COCI | CONFERIR TÍTULO | US$ 260.758 | US$ 189.832 | US$ 48.082,14 | sem valor publicado até agora | hipoteca sobrevive |
| 08/12/2026 | Broward | 1018 NE 17 TER FORT LAUDERDALE, 33304 | CACE-26-009212 | DISPUTADO | US$ 494.945 | US$ 502.475 | ≥ US$ 519.873,19 (parcial) | sem valor publicado até agora | julgamento parcial ≥ US$ 519.873 |
| 08/12/2026 | Broward | 1558 MYRTLE OAK TER HOLLYWOOD, 33021 | CACE-24-015132 | DISPUTADO | US$ 435.078 | US$ 443.500 | US$ 670.824,16 | sem valor publicado até agora | risco alto de cancelamento, julgamento de 2025 |
| 08/12/2026 | Orange | 6135 ARBOR WATCH LOOP ORLANDO, 32829 | 2025-CA-003987-O | CONFERIR TÍTULO | US$ 251.627 | US$ 213.246 | US$ 437.135,43 | sem valor publicado até agora | processo contestado, inquilino com direitos |
| 08/12/2026 | Volusia | 1608 LADY FERN TR DELAND, FL 32720 | 2025 11272 CIDL | DISPUTADO | US$ 181.900 | US$ 194.700 | US$ 268.818,14 | sem valor publicado até agora | associação contestou, risco alto de cancelamento |
| 08/12/2026 | Volusia | 505 DORSEY CT DELTONA, FL 32725 | 2025 14373 CIDL | DISPUTADO | US$ 184.343 | US$ 197.010 | US$ 360.161,10 | sem valor publicado até agora | – |
| 08/12/2026 | Volusia | 924 ADLER DR DELTONA, FL 32738 | 2026 12066 CIDL | DISPUTADO | US$ 208.349 | US$ 212.817 | US$ 383.236,83 | sem valor publicado até agora | – |
| 09/12/2026 | Broward | 81 ISLE OF VENICE DR FORT LAUDERDALE, 33301 | CACE-08-031733 | DISPUTADO | US$ 1.921.385 | US$ 1.937.865 | ≥ US$ 3.464.145,94 (parcial) | sem valor publicado até agora | processo contestado, risco alto de cancelamento, julgamento parcial ≥ US$ 3.464.146 |
| 09/12/2026 | Orange | 1348 WHITNEY ISLES DR WINDERMERE, 34786 | 2025-CA-003624-O | DISPUTADO | US$ 360.123 | US$ 369.090 | US$ 466.898,49 | sem valor publicado até agora | falência ativa |
| 09/12/2026 | Orange | 13804 DOVE WING CT ORLANDO, 32828 | 2025-CA-011575-O | DISPUTADO | US$ 220.552 | US$ 231.228 | US$ 10.534,88 | sem valor publicado até agora | hipoteca sobrevive |
| 09/12/2026 | Orange | 817 POLK ST ORLANDO, 32805 | 2025-CA-003835-O | CONFERIR TÍTULO | US$ 150.257 | US$ 117.097 | US$ 261.689,68 | sem valor publicado até agora | devedor falecido – herdeiros, possível hipoteca reversa (HECM), lien municipal, risco alto de cancelamento, governo renunciou (exceto sobra) |
| 10/12/2026 | Broward | 5076 SW 139 TER MIRAMAR, 33027 | CACE-26-005019 | DISPUTADO | US$ 376.160 | US$ 397.145 | ≥ US$ 178.117,24 (parcial) | sem valor publicado até agora | 1 ano de resgate federal, devedor falecido – herdeiros, julgamento parcial ≥ US$ 178.117 |
| 10/12/2026 | Volusia | 219 SHADY LANE ORANGE CITY, FL 32763 | 2021 11724 CIDL | DISPUTADO | US$ 241.551 | US$ 265.072 | ≥ US$ 523.484,63 (parcial) | sem valor publicado até agora | falência em série, processo contestado, julgamento parcial ≥ US$ 523.485, julgamento de 2023 |
| 10/12/2026 | Volusia | 2507 HOPTREE LN EDGEWATER, FL 32141 | 2025 13353 CIDL | DISPUTADO | US$ 226.011 | US$ 236.412 | US$ 379.019,18 (lista: US$ 379.029,18) | sem valor publicado até agora | financiamento solar/obra no processo, risco alto de cancelamento, FJ do processo US$ 379.019 ≠ lista |
| 16/12/2026 | Brevard | 1204 E UNIVERSITY BLVD MELBOURNE, FL 32901 | 05-2025-CA-059985-XXCA-BC | DISPUTADO | US$ 115.594 | US$ 125.000 | US$ 123.623,58 | sem valor publicado até agora | devedor falecido – herdeiros |
| 16/12/2026 | Brevard | 1542 RACHEL AVE SE PALM BAY, FL 32909 | 05-2025-CA-045676-XXCA-BC | DISPUTADO | US$ 206.315 | US$ 211.200 | US$ 407.395,74 | sem valor publicado até agora | risco alto de cancelamento, processo reaberto |
| 16/12/2026 | Brevard | 2127 SANS SOUCI AVE SE PALM BAY, FL 32909 | 05-2026-CA-013891-XXCA-BC | DISPUTADO | US$ 195.511 | US$ 201.280 | US$ 251.927,43 | sem valor publicado até agora | 120 dias de resgate federal, ocupação: possivelmente vago (cartas devolvidas) |
| 16/12/2026 | Volusia | 88 SPINNAKER CIR SOUTH DAYTONA, FL 32119 | 2026 11971 CICI | DISPUTADO | US$ 185.257 | US$ 201.438 | US$ 434.345,24 | sem valor publicado até agora | – |
| 23/12/2026 | Volusia | 508 EASTWOOD LANE DAYTONA BEACH, FL 32118 | 2024 11074 CICI | DISPUTADO | US$ 413.998 | US$ 424.618 | US$ 384.644,08 | sem valor publicado até agora | processo contestado, lien municipal |
| 06/01/2027 | Volusia | 9 Bella Oaks Dr Port Orange, FL 32129 | 2025 13693 Cici | DISPUTADO | US$ 156.599 | US$ 170.775 | US$ 336.437,05 | sem valor publicado até agora | inquilino com direitos |

### 2b) Banco já publicou um valor (reler no dia mesmo assim – pode baixar ou tirar) – 2 imóveis

| Leilão | Condado | Endereço | Processo | Veredito | Nosso lance máx. | Preço esperado | Julgamento lido | Banco hoje | Alertas do processo |
|---|---|---|---|---|---|---|---|---|---|
| 24/11/2026 | Orange | 262 PLEASANT GARDENS DR APOPKA, 32703 | 2025-CA-008467-O | DISPUTADO | US$ 158.037 | US$ 167.400 | US$ 103.220,75 | publicado US$ 109.709,93 (leitura até 16/11/2026) – informativo, reler no dia | 120 dias de resgate federal, risco alto de cancelamento, pedido de cancelamento pendente, processo reaberto |
| 24/11/2026 | Volusia | 3177 NEWHOPE DR DELTONA, FL 32738 | 2025 11056 CIDL | DISPUTADO | US$ 179.927 | US$ 193.380 | US$ 459.763,66 | publicado US$ 275.684,00 (leitura até 20/11/2026) – informativo, reler no dia | – |

Observações:
- **14139 Ward Rd (01/12):** FLIP pela conta, mas o processo foi reaberto e há 2 pedidos de cancelamento pendentes – conferir no dia se o leilão acontece.
- **15006 Bellinkoff (02/12)** e **13804 Dove Wing (09/12):** a hipoteca executada não é a 1ª / ação só da associação → a 1ª hipoteca sobrevive e fica com o arrematante; o lance máx. do painel ainda não desconta essa hipoteca.
- **1348 Whitney Isles (09/12):** falência ativa (Capítulo 13) – o leilão pode ser suspenso.
- **1547 Priory Cir, 6135 Arbor Watch, 817 Polk St:** CONFERIR TÍTULO (falência em série / processo contestado / herdeiros) – seriam FLIP pela conta; só liberam com titleOk.
- HUD réu = 120 dias de resgate federal depois do leilão (IRS/SBA/VA = 1 ano).

Ao terminar cada dia, por favor anotar no DIARIO o que o banco fez em cada imóvel desta lista.
