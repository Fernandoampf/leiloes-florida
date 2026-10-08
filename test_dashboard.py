#!/usr/bin/env python3
"""Teste automatizado do painel (Playwright + Chrome headless).

Uso:  python3 test_dashboard.py [arquivo_ou_url]
Padrão: .plain/index.html (gerado com  python3 build.py --site --no-encrypt --out .plain/index.html).
Testa a versão SEM criptografia; a versão publicada é a mesma página após o StaticCrypt.
"""
import os, sys, json, pathlib
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
target = sys.argv[1] if len(sys.argv) > 1 else str(HERE / '.plain' / 'index.html')
URL = target if '://' in target else pathlib.Path(target).resolve().as_uri()
CHROME = os.environ.get('CHROME', '/usr/bin/google-chrome')
fails = []
def check(cond, msg):
    print(('OK   ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=CHROME if os.path.exists(CHROME) else None, args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 1440, 'height': 950}, accept_downloads=True)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='load', timeout=180000); pg.wait_for_timeout(1500)
    D = 'window.__dash'
    n = pg.evaluate(D + '.ITEMS.length'); check(n > 100, f'itens carregados: {n}')
    check(pg.evaluate(D + '.PR.ret') == 10, 'retorno mínimo padrão = 10%')
    check(pg.locator('#tbl tbody tr').count() > 0, 'tabela renderizada')
    check(pg.locator('#kpis > *').count() >= 7, 'KPIs (7 cards)')
    check(pg.locator('#types [data-cat]').count() >= 5, 'chips de tipo com contagem')
    # fórmula: no lance máximo o ROI é exatamente o mínimo
    bad = pg.evaluate('''(()=>{const d=window.__dash;let bad=[];for(const r of d.ITEMS){ if(r.mb==null||r.mb<=0) continue;
        const p=d.pnl(r,r.mb); if(Math.abs(p.roi-d.PR.ret/100)>0.002) bad.push([r.id,p.roi]); } return bad.slice(0,5);})()''')
    check(not bad, f'ROI no lance máximo = 10% para todos os itens ({bad})')
    # ordenação rápida
    pg.click('#qs [data-sort="net"]'); pg.wait_for_timeout(300)
    nets = pg.evaluate(D + '.CUR.slice(0,30).map(r=>r.net??-1e12)')
    check(nets == sorted(nets, reverse=True), 'ordenar por Maior NET')
    # filtro por categoria
    pg.click('#types [data-cat="Condo"]'); pg.wait_for_timeout(300)
    cats = set(pg.evaluate(D + '.CUR.map(r=>r.cat)')); check(cats == {'Condo'}, f'chip Condo filtra ({cats})')
    pg.click('#types [data-cat=""]'); pg.wait_for_timeout(200)
    # filtro ROI mínimo
    pg.fill('#mroi', '50'); pg.dispatch_event('#mroi', 'input'); pg.wait_for_timeout(400)
    rois = pg.evaluate(D + '.CUR.map(r=>r.roi)'); check(rois and min(rois) >= 0.5, f'filtro ROI mín. 50% ({len(rois)} itens)')
    # link com filtros na URL
    pg.click('#blink'); pg.wait_for_timeout(200)
    h = pg.evaluate('location.hash'); check('mroi' in h or 'f=' in h, 'filtros vão para o link (#f=...)')
    pg.click('#breset'); pg.wait_for_timeout(300)
    check(pg.evaluate(D + '.CUR.length') == n, 'limpar filtros volta ao total')
    # painel de detalhes coerente com a tabela
    pg.click('#qs [data-sort="sc"]'); pg.wait_for_timeout(200)
    rid = pg.evaluate(D + '.CUR.find(r=>r.t==="FC"&&r.net!=null).id')
    tnet = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").net')
    pg.evaluate(f'{D}.openDrawer("{rid}")'); pg.wait_for_timeout(400)
    dnet = pg.locator('#dplnet').inner_text()
    check(f"{round(tnet):,}".replace(',', '.') in dnet, f'NET do painel = NET da tabela ({dnet} vs {tnet:.0f})')
    check(pg.locator('#drawer a', has_text='Zillow').count() >= 1 and pg.locator('#drawer a', has_text='Realtor').count() >= 1, 'links Zillow e Realtor no painel')
    mb = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    pg.fill('#w-bid', str(round(mb))); pg.dispatch_event('#w-bid', 'input'); pg.wait_for_timeout(200)
    check('10,0% ROI' in pg.locator('#dplnet').inner_text() or '9,9% ROI' in pg.locator('#dplnet').inner_text() or '10,1% ROI' in pg.locator('#dplnet').inner_text(), 'simulador: no lance máximo ROI ≈ 10% (' + pg.locator('#dplnet').inner_text() + ')')
    pg.click('#w-reset'); pg.wait_for_timeout(200)
    check(f"{round(tnet):,}".replace(',', '.') in pg.locator('#dplnet').inner_text(), 'Reset volta ao valor da tabela')
    pg.click('[data-trk="interessa"]'); pg.wait_for_timeout(100)
    check('interessa' in (pg.evaluate("localStorage.getItem('leilao_tracker_v1')") or ''), 'flip tracker salvo no aparelho')
    pg.click('#dclose'); pg.wait_for_timeout(200)
    # favoritos
    pg.locator('#tbl [data-star]').first.click(); pg.wait_for_timeout(100)
    check(len(json.loads(pg.evaluate("localStorage.getItem('leilao_fav_v1')") or '[]')) == 1, 'favorito salvo (★)')
    # premissas: retorno 20% reduz o lance máximo
    mb10 = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    pg.evaluate(f'{D}.applyPrem({{...{D}.PR, ret:20}})'); pg.wait_for_timeout(300)
    mb20 = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    check(mb20 < mb10, f'premissa retorno 20% reduz lance máx. ({mb10:.0f} → {mb20:.0f})')
    pg.evaluate(f'{D}.applyPrem({{...{D}.PDEF}})'); pg.wait_for_timeout(300)
    check(pg.evaluate("localStorage.getItem('leilao_premissas_v2')") is None, 'padrões restaurados')
    # CSV
    with pg.expect_download() as dl: pg.click('#bcsv')
    path = dl.value.path(); lines = open(path, encoding='utf-8-sig').read().splitlines()
    check(len(lines) == n + 1 and 'zillow' in lines[0], f'CSV exportado ({len(lines)-1} linhas)')
    # cards e mapa
    pg.click('#tabs [data-v="cards"]'); pg.wait_for_timeout(300); check(pg.locator('#grid .card').count() > 0, 'cards')
    check(pg.locator('#grid a', has_text='Zillow').count() > 0, 'links Zillow nos cards')
    pg.click('#tabs [data-v="map"]'); pg.wait_for_timeout(2500)
    check(pg.locator('#map .leaflet-interactive, #map .leaflet-marker-icon').count() > 0, 'mapa com pontos')
    z = pg.evaluate(f'{D}.zillowUrl({D}.ITEMS[0])'); check(z.startswith('https://www.zillow.com/homes/') and z.endswith('_rb/'), 'formato do link Zillow')
    check(not errs, f'sem erros de JavaScript {errs[:3]}')
    # celular 390px
    m = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = m.new_page(); merr = []; mp.on('pageerror', lambda e: merr.append(str(e)))
    mp.goto(URL, wait_until='load', timeout=180000); mp.wait_for_timeout(1500)
    check(mp.evaluate('document.documentElement.scrollWidth') <= 392, 'celular: sem rolagem horizontal')
    check(mp.locator('#grid .card').count() > 0, 'celular abre em cards')
    mp.locator('#grid .card').first.click(); mp.wait_for_timeout(400)
    check(mp.evaluate("document.querySelector('#drawer').getBoundingClientRect().width") >= 380, 'celular: painel em tela cheia')
    check(not merr, 'celular: sem erros JS')
    b.close()
print('\n' + ('TODOS OS TESTES OK' if not fails else f'{len(fails)} FALHA(S)'))
sys.exit(1 if fails else 0)
