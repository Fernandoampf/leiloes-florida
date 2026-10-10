#!/usr/bin/env python3
"""Teste automatizado do painel v4 (Playwright + Chrome headless).

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
    ctx.add_init_script("localStorage.setItem('leilao_noseed','1')")   # legacy tests start without the plan's default favourites
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until='load', timeout=180000)
    pg.wait_for_function('window.__dash', timeout=60000); pg.wait_for_timeout(500)
    D = 'window.__dash'
    n = pg.evaluate(D + '.ITEMS.length'); check(n > 1000, f'itens carregados: {n}')
    n0 = pg.evaluate(D + '.CUR.length'); check(0 < n0 <= n, f'lista padrão: {n0} (faixas/áreas comuns e execuções de HOA ocultas)')
    check(pg.evaluate(D + ".S.cat") == 'resid', 'filtro padrão = Residencial (casa/townhouse/condo)')
    top = pg.evaluate(D + ".CUR.slice(0,30).map(r=>r.ty)")
    check(sum(1 for x in top if x in ('Casa','Townhouse','Condo')) >= 20, f'topo da lista é residencial ({top[:8]})')
    check(pg.evaluate(D + '.PR.ret') == 17 and pg.evaluate(D + '.PR.flip') == 25, 'retorno mínimo padrão = 17%, FLIP ≥ 25%')
    check('Orçamento' not in pg.inner_text('body') and 'teto orç' not in pg.inner_text('body'), 'sem orçamento de US$ 150 mil na página')
    check(pg.locator('#tbl tbody tr').count() > 0, 'tabela renderizada')
    heads = pg.evaluate("document.querySelector('#tbl thead').textContent")
    for h in ('Condado', 'ARV', 'POV', 'Final Judgment', 'Opening Bid', 'Max Bid', 'NET', 'ROI', 'Verdict', 'Nota', 'Cat.', 'Plaintiff'):
        check(h in heads, f'coluna “{h}”')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.pov).length') > 50, 'itens com POV PropertyOnion')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.povAsArv).length') > 20, 'itens com POV como ARV')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.plat==="PropertyOnion").length') >= 1, 'imóveis só-PropertyOnion')
    check(pg.locator('#fpovc').count()==1 and pg.locator('#hpov').count()==1, 'filtros POV (confiança + só com POV)')
    check(pg.locator('#kstrip > div').count() == 5, 'faixa de KPIs (5 indicadores)')
    check(pg.locator('#kpis > *').count() >= 7, 'blocos de categoria (7)')
    check('JR-LIEN' in pg.inner_text('#jrban'), 'aviso JR-LIEN')
    # seletor de tipo: 9 tipos + Todos
    types = pg.evaluate("[...document.querySelectorAll('#types [data-cat]')].map(b=>b.dataset.cat)")
    check(set(['Lote', 'Terreno', 'Casa', 'Townhouse', 'Condo', 'Mobile', 'Multifamily', 'Comercial', 'Outro']) <= set(types), f'chips de tipo ({len(types)})')
    for t in ('Lote', 'Condo', 'Comercial'):
        pg.click('#types [data-cat=""]'); pg.wait_for_timeout(200); pg.click(f'#types [data-cat="{t}"]'); pg.wait_for_timeout(250)
        got = set(pg.evaluate(D + '.CUR.map(r=>r.ty)')); check(got == {t}, f'chip {t} filtra ({len(pg.evaluate(D + ".CUR"))} itens)')
    pg.click('#types [data-cat=""]'); pg.wait_for_timeout(200)
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.ty==="Lote"||r.ty==="Terreno").length') > 200, 'lotes/terrenos incluídos (>200)')
    # vereditos e categorias
    vds = set(pg.evaluate(D + '.ITEMS.map(r=>r.vd)')); check(vds <= {'FLIP', 'CONSIDERAR', 'DISPUTADO', 'PASSAR'} and {'FLIP','DISPUTADO','PASSAR'} <= vds, f'vereditos {vds}')
    bad = pg.evaluate(D + '''.ITEMS.filter(r=>r.roi!=null&&r.mb!=null&&!(r.geo&&r.geo.poly!==false&&((r.geo.wetPct||0)>=10||(r.geo.sfhaPct||0)>=10))).filter(r=>{
        const room = r.mb>0, over = r.ref!=null && r.ref>r.mb+1;
        if(r.vd==='FLIP'||r.vd==='CONSIDERAR') return !(room && !over && !(r.xbid>r.mb+1) && (r.vd==='FLIP'?r.roi>=0.25:r.roi<0.25));
        if(r.vd==='PASSAR') return !( !room || (r.t!=='FC' && over) );
        if(r.vd==='DISPUTADO') return !( room && ((r.t==='FC' && over) || r.xbid>r.mb+1) );
        return true; }).map(r=>r.addr+' '+r.vd).slice(0,5)''')
    check(not bad, f'veredito por espaço de lance: SEM ESPAÇO / DISPUTADO / FLIP ≥ 25% / CONSIDERAR {bad}')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.t==="FC"&&r.vd==="PASSAR"&&r.mb>0&&r.ref>r.mb+1&&!(r.geo&&r.geo.poly!==false&&((r.geo.wetPct||0)>=10||(r.geo.sfhaPct||0)>=10))).length') == 0, 'foreclosure com julgamento acima do lance máx. é DISPUTADO, não SEM ESPAÇO')
    kats = pg.evaluate(D + '.ITEMS.map(r=>r.kat).join()'); check('NO ROOM' in kats and 'CONTESTED' in kats, 'categorias “NO ROOM” e “CONTESTED”')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.fl.includes("mtg")&&r.roi!=null&&r.mb>0&&!(r.ref>r.mb)&&!(r.xbid>r.mb+1)).every(r=>r.vd!=="PASSAR")'), 'hipoteca que sobrevive não é PASSAR automático')
    check(pg.evaluate(D + '.ITEMS.filter(r=>r.survOrig).every(r=>r.survAmt<=r.survOrig)'), 'dívida que sobrevive = saldo estimado (≤ valor original)')
    jvb = pg.evaluate(D + '.ITEMS.filter(r=>r.jv85&&!r.suspect&&!r.povAsArv&&!(r.sup&&r.sup.disc)&&!r.bld).filter(r=>Math.abs((r.val0!=null?r.val0:r.val)-r.jv85/0.85)>1).map(r=>[r.addr,r.val0,r.val,r.jv85]).slice(0,3)')
    check(not jvb and pg.evaluate(D + '.ITEMS.filter(r=>r.jv85).length') > 100, f'ARV só com just value = just value ÷ 0,85 {jvb}')
    check(pg.locator('#fvd option[value="DISPUTADO"]').count()==1 and 'contested' in pg.inner_text('#kpis').lower(), 'filtro e KPI CONTESTED')
    kats = set(pg.evaluate(D + '.ITEMS.map(r=>r.katk)')); check({'viavel', 'abaixo', 'lucro', 'disp', 'semdados'} <= kats and 'jmax' not in kats, f'categorias (regras 30e37bc, sem jmax) {kats}')
    # regras do Fernando (30e37bc): no lance máximo o ROI respeita a escada (lote ≤15k all-in 40% + NET 3k; ≤60k 25%; acima 17%; +supAdd com oferta alta) e casa 17% + NET mínimo
    bad = pg.evaluate('''(()=>{const d=window.__dash,Q=d.PR;let bad=[];for(const r of d.ITEMS){ if(r.mb==null||r.mb<=0||r.man) continue;
        const p=d.pnl(r,r.mb), land=r.ty==='Lote'||r.ty==='Terreno', add=land&&r.fl.includes('supH')?Q.supAdd:0; let th=Q.ret, nmin=0;
        if(land){ if(p.inv<=Q.lotS){th=Q.lotSroi;nmin=Q.lotSnet;} else if(p.inv<=Q.lotM) th=Q.lotMroi; }
        else if(r.ty!=='Comercial'&&r.ty!=='Outro') nmin=Q.netHouse;
        if(p.roi < (th+add)/100-0.002 || (nmin>0 && p.net < nmin-2)) bad.push([r.id,r.ty,Math.round(p.inv),+p.roi.toFixed(3),Math.round(p.net)]); } return bad.slice(0,5);})()''')
    check(not bad, f'ROI/NET no lance máximo ≥ mínimo da escada de regras ({bad})')
    dep = pg.evaluate(D + '.ITEMS.filter(r=>r.mb>0).every(r=>Math.abs(r.dep-r.mb*0.05)<1)'); check(dep, 'depósito = 5% do lance máximo')
    # ordenação rápida
    pg.click('#qs [data-sort="net"]'); pg.wait_for_timeout(300)
    nets = pg.evaluate(D + '.CUR.slice(0,30).map(r=>r.net??-1e12)')
    check(nets == sorted(nets, reverse=True), 'ordenar por Maior NET')
    # filtro ROI mínimo (em Mais filtros)
    pg.click('#fmorebtn'); pg.wait_for_timeout(200)
    pg.fill('#mroi', '50'); pg.dispatch_event('#mroi', 'input'); pg.wait_for_timeout(400)
    rois = pg.evaluate(D + '.CUR.map(r=>r.roi)'); check(rois and min(rois) >= 0.5, f'filtro ROI mín. 50% ({len(rois)} itens)')
    pg.click('#blink'); pg.wait_for_timeout(200)
    h = pg.evaluate('location.hash'); check('mroi' in h, 'filtros vão para o link (#f=...)')
    pg.click('#breset'); pg.wait_for_timeout(300)
    check(pg.evaluate(D + '.CUR.length') == n0, 'limpar filtros volta à lista padrão')
    # filtro de água/esgoto
    pg.select_option('#fut', 'known'); pg.wait_for_timeout(300)
    k = pg.evaluate(D + '.CUR.length'); check(k > 0 and pg.evaluate(D + '.CUR.every(r=>r.util)'), f'filtro água/esgoto FDOH ({k})')
    pg.click('#breset'); pg.wait_for_timeout(300)
    # painel de detalhes coerente com a tabela
    pg.click('#qs [data-sort="sc"]'); pg.wait_for_timeout(200)
    rid = pg.evaluate(D + '.CUR.find(r=>r.t==="FC"&&r.ref!=null&&r.net!=null&&r.imgs&&r.imgs.length&&r.sqft>0&&r.yr).id')
    tnet = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").net')
    pg.evaluate(f'{D}.openDrawer("{rid}")'); pg.wait_for_timeout(500)
    dnet = pg.locator('#dplnet').inner_text()
    check(f"{round(tnet):,}".replace(',', '.') in dnet, f'NET do painel = NET da tabela ({dnet} vs {tnet:.0f})')
    check(pg.locator('#drawer a', has_text='Zillow').count() >= 1 and pg.locator('#drawer a', has_text='Realtor').count() >= 1, 'links Zillow e Realtor no painel')
    check(pg.locator('#galmain img').count() == 1, 'galeria: foto exibida')
    pg.click('#gal [data-gt="sv"]'); pg.wait_for_timeout(200)
    check('svembed' in (pg.locator('#galmain iframe').get_attribute('src') or ''), 'galeria: Street View embutido (sem chave)')
    pg.click('#gal [data-gt="sat"]'); pg.wait_for_timeout(200)
    check('t=k' in (pg.locator('#galmain iframe').get_attribute('src') or ''), 'galeria: satélite')
    al = pg.locator('#drawer .alerts li').count(); check(al >= 8, f'alertas de risco ({al})')
    check(pg.locator('#drawer .alerts .st.nv').count() >= 1, 'alertas marcam “não verificado”')
    check(pg.locator('#dland .lv > div').count() >= 9, 'bloco água/esgoto/terreno')
    tiles = pg.evaluate("document.querySelector('#dtiles').textContent")
    for t in ('17% mínimo', '25% alvo', '30% esticado', '70% máx.', 'Final Judgment'):
        check(t in tiles, f'escada de lances: {t}')
    check('Deposit no leilão' in pg.inner_text('#ddep'), 'depósito de 5% no painel')
    check(pg.locator('#dstrat > div').count() == 2, 'estratégias FLIP e HOLD/BRRRR')
    pl = pg.evaluate("document.querySelector('#dpl').textContent")
    for t in ('ARV (preço de venda)', 'Winning Bid', 'Clerk Fee', 'Doc Stamps (compra)', 'Total da aquisição', 'Rehab', 'Rehab Contingency', 'Holding Costs', 'Flat Sale Fee (BidToFlip)', 'Listing Commission', 'Buyer Agent Commission', 'Title Insurance', 'Doc Stamps (venda)', 'Closing Costs', 'NET (lucro líquido)', '/mês'):
        check(t in pl, f'P&L: linha “{t}”')
    check('US$ 399' in pl, 'P&L: taxa fixa de venda US$ 399')
    check(pg.locator('#drepc').count() == 1 and ('RECONSTRUÇÃO' in pg.evaluate("document.querySelector('#drep').textContent")), 'custo de reposição com selo acima/abaixo')
    # clerk fee: 3% of first 500 + 1.5% of rest; formula reproduces BidToFlip example
    ex = pg.evaluate('''(()=>{const d=window.__dash; const r={...d.ITEMS.find(x=>x.id===%r), val:2214600, rep:8000, tax:null, fl:[], t:'FC', ty:'Casa'}; const o={...d.base(r), arv:2214600, rehab:8000, months:4, lien:0}; const p=d.pnl(r,1550220,o); return [Math.round(p.clerk), Math.round(p.docb), Math.round(p.sell.buyc), Math.round(p.sell.title), Math.round(p.sell.docs), p.sell.wra, Math.round(p.sell.list), p.sell.misc, Math.round(p.cont)];})()''' % rid)
    check(ex[:6] == [23261, 10852, 55365, 8112, 15502, 399], f'deduções (clerk, doc stamps, comprador, título promulgado FL, doc stamps venda, taxa fixa) {ex[:6]}')
    check(ex[6] == 55365 and ex[7] == 1000 and ex[8] == 1600, f'padrões: vendedor 2,5%, fechamento US$ 1.000, contingência 20% {ex[6:]}')
    tt = pg.evaluate('''(()=>{const d=window.__dash; const h=d.ITEMS.find(x=>x.co==='Orange'&&x.ty==='Casa'); const m=d.ITEMS.find(x=>x.co==='Miami-Dade'&&x.ty==='Casa'); const l=d.ITEMS.find(x=>(x.ty==='Lote')&&x.val);
      const T=(r,a)=>{const o={...d.base(r),arv:a}; return Math.round(d.pnl(r,100000,o).sell.title);}; return [T(h,300000), m?T(m,300000):0, Math.round(d.pnl(l,l.xbid||1000,d.base(l)).sell.wra)];})()''')
    check(tt == [1575, 0, 0], f'título promulgado US$ 1.575 em US$ 300 mil, zero em Miami-Dade, sem taxa fixa em lote {tt}')
    defs = pg.evaluate(D + '.PDEF'); check(defs['months'] == 7 and defs['monthsLot'] == 3 and defs['hins'] == 2 and defs['cont'] == 20 and defs['rhbMin'] == 15000 and defs['capc'] == 8 and defs['lotSroi'] == 40 and defs['netHouse'] == 25000 and defs['hutil'] == 350 and defs['rhbUnk'] == 35000 and defs['misc'] == 1000 and defs['titleP'] == 100, 'padrões: posse 7 meses (lote 3), seguro 2%, contingência 20%, reforma mínima US$ 15 mil, capital 8%, escada de lote 40%, NET casa US$ 25 mil, US$ 350/mês, reforma desconhecida US$ 35 mil, fechamento US$ 1.000')
    # every P&L line editable, live recalculation
    n_in = pg.locator('#dpl .pin').count(); check(n_in >= 14, f'P&L editável ({n_in} campos)')
    before = pg.locator('#dplnet').inner_text()
    pg.fill('#dpl [data-pk="list"]', '6'); pg.wait_for_timeout(200)
    after = pg.locator('#dplnet').inner_text(); check(after != before, f'editar comissão recalcula ao vivo ({before} → {after})')
    pg.fill('#dpl [data-ok="months"]', '9'); pg.wait_for_timeout(200)
    check(pg.locator('#w-months').input_value() == '9', 'meses editados no P&L sincronizam com o simulador')
    pg.click('#w-reset'); pg.wait_for_timeout(200)
    check(pg.locator('#dplnet').inner_text() == before, 'desfazer edições do imóvel')
    pg.fill('#dpl [data-pk="hutil"]', '400'); pg.wait_for_timeout(150); pg.click('#plsave'); pg.wait_for_timeout(300)
    check((json.loads(pg.evaluate("localStorage.getItem('leilao_premissas_v8')") or '{}')).get('hutil') == 400, 'salvar custos como padrão (localStorage)')
    pg.evaluate(f'{D}.openDrawer("{rid}")'); pg.wait_for_timeout(300); pg.click('#pldef'); pg.wait_for_timeout(300)
    check(pg.evaluate("localStorage.getItem('leilao_premissas_v8')") is None and pg.evaluate(D + '.PR.hutil') == 350, 'voltar aos padrões originais')
    pg.evaluate(f'{D}.openDrawer("{rid}")'); pg.wait_for_timeout(300)
    # what-if exactly like BidToFlip: every line follows bid / ARV / rehab / months live
    row = '''(t=>{const tr=[...document.querySelectorAll('#dpl tr')].find(x=>x.cells[0]&&x.cells[0].textContent.startsWith(t));return tr?tr.cells[1].textContent:null;})'''
    snap = lambda: pg.evaluate('''()=>{const g=%s;return {clerk:g('Clerk Fee'),docb:g('Doc Stamps (compra)'),list:g('Listing Commission'),hold:g('Holding Costs'),net:document.querySelector('#dplnet').textContent,lad:document.querySelector('#dtiles').textContent,rep:(document.querySelector('#drep')||{}).textContent,dep:document.querySelector('#ddep').textContent,wsr:document.querySelector('#wsr').textContent,hdr:document.querySelector('#dnet').textContent};}''' % row)
    s0 = snap()
    pg.fill('#w-bid', '123500'); pg.wait_for_timeout(150); s1 = snap()
    check(s1['clerk'] != s0['clerk'] and s1['docb'] != s0['docb'] and s1['net'] != s0['net'] and s1['dep'] != s0['dep'] and s1['hdr'] != s0['hdr'] and 'US$ 123.500' in s1['wsr'], 'lance digitado: clerk, doc stamps, lucro, ROI, depósito e cabeçalho ao vivo')
    check(s1['rep'] != s0['rep'] or not s0['rep'], 'lance digitado: custo de reposição ao vivo')
    check(pg.locator('#w-sl').input_value() == '123500', 'campo do lance sincroniza com o slider')
    pg.locator('#w-sl').evaluate("e=>{e.value=80000;e.dispatchEvent(new Event('input',{bubbles:true}))}"); pg.wait_for_timeout(150); s2 = snap()
    check(pg.locator('#w-bid').input_value() == '80000' and s2['clerk'] != s1['clerk'] and s2['net'] != s1['net'], 'slider do lance: campo e linhas ao vivo')
    pg.fill('#w-arv', '450000'); pg.wait_for_timeout(150); s3 = snap()
    check(s3['list'] != s2['list'] and s3['lad'] != s2['lad'] and s3['net'] != s2['net'] and s3['hold'] != s2['hold'], 'ARV: comissões, posse (seguro/imposto), lucro e escada ao vivo')
    pg.fill('#w-rehab', '60000'); pg.wait_for_timeout(150); s4 = snap()
    check(s4['lad'] != s3['lad'] and s4['net'] != s3['net'] and pg.locator('#dpl [data-ok="rehab"]').input_value() == '60000', 'reforma: escada, lucro e linha do P&L ao vivo')
    pg.fill('#w-months', '10'); pg.wait_for_timeout(150); s5 = snap()
    check(s5['hold'] != s4['hold'] and s5['lad'] != s4['lad'], 'meses de posse: posse e escada ao vivo')
    pg.click('#w-reset'); pg.wait_for_timeout(150)
    check(pg.locator('#dcomps, #drawer .sec h3:has-text("comparáveis")').count() >= 1, 'bloco de comps')
    check(pg.locator('#dhist').count() == 1, 'bloco de histórico de leilões')
    mb = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    pg.fill('#w-bid', str(round(mb))); pg.dispatch_event('#w-bid', 'input'); pg.wait_for_timeout(200)
    t = pg.locator('#dplnet').inner_text()
    check(any(x in t for x in ('17,0% ROI', '16,9% ROI', '17,1% ROI')), 'simulador: no lance máximo ROI ≈ 17% (' + t + ')')
    pg.click('#w-reset'); pg.wait_for_timeout(200)
    check(f"{round(tnet):,}".replace(',', '.') in pg.locator('#dplnet').inner_text(), 'Reset volta ao valor da tabela')
    pg.click('[data-trk="interessa"]'); pg.wait_for_timeout(100)
    check('interessa' in (pg.evaluate("localStorage.getItem('leilao_tracker_v1')") or ''), 'flip tracker salvo no aparelho')
    pg.click('#dclose'); pg.wait_for_timeout(200)
    # lote com utilidades
    lid = pg.evaluate(D + '.ITEMS.find(r=>(r.ty==="Lote"||r.ty==="Terreno")&&r.util)?.id')
    check(bool(lid), 'existe lote com dado de água/esgoto')
    if lid:
        pg.evaluate(f'{D}.openDrawer("{lid}")'); pg.wait_for_timeout(400)
        check('Terreno' in pg.evaluate("document.querySelector('#dland h3').textContent"), 'painel do lote mostra bloco de terreno')
        pg.click('#dclose'); pg.wait_for_timeout(200)
    # favoritos e cores
    pg.locator('#tbl [data-star]').first.click(); pg.wait_for_timeout(100)
    check(len(json.loads(pg.evaluate("localStorage.getItem('leilao_fav_v1')") or '[]')) == 1, 'favorito salvo (★)')
    pg.locator('#tbl [data-flag]').first.click(); pg.wait_for_timeout(100)
    check(len(json.loads(pg.evaluate("localStorage.getItem('leilao_flags_v1')") or '{}')) == 1, 'cor marcada salva')
    # premissas
    mb10 = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    pg.evaluate(f'{D}.applyPrem({{...{D}.PR, ret:25}})'); pg.wait_for_timeout(300)
    mb20 = pg.evaluate(f'{D}.ITEMS.find(r=>r.id==="{rid}").mb')
    check(mb20 < mb10, f'premissa retorno 25% reduz lance máx. ({mb10:.0f} → {mb20:.0f})')
    check(pg.evaluate("localStorage.getItem('leilao_premissas_v8')") is not None, 'premissas salvas (v8)')
    pg.evaluate(f'{D}.applyPrem({{...{D}.PDEF}})'); pg.wait_for_timeout(300)
    check(pg.evaluate("localStorage.getItem('leilao_premissas_v8')") is None, 'padrões restaurados')
    # CSV
    with pg.expect_download() as dl: pg.click('#bcsv')
    lines = open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    check(len(lines) >= n0 + 1 and 'zillow' in lines[0] and 'deposito' in lines[0], f'CSV exportado ({len(lines)-1} linhas)')
    # outras visões
    pg.click('#tabs [data-v="cards"]'); pg.wait_for_timeout(300); check(pg.locator('#grid .card').count() > 0, 'cards')
    pg.click('#tabs [data-v="fav"]'); pg.wait_for_timeout(300); check(pg.locator('#grid .card').count() == 1, 'aba Favoritos')
    pg.click('#tabs [data-v="intel"]'); pg.wait_for_timeout(300); check(pg.locator('#v-intel tbody tr').count() > 20, 'inteligência por condado')
    check(pg.locator('#v-intel .heat [data-heat]').count() == 9, 'mapa de calor valor × desconto')
    pg.click('#tabs [data-v="res"]'); pg.wait_for_timeout(300); check(pg.locator('#v-res tbody tr').count() > 20, 'resultados de leilões passados')
    pg.click('#tabs [data-v="cal"]'); pg.wait_for_timeout(300)
    check(pg.locator('#v-cal .calrow').count() > 5, f'calendário ({pg.locator("#v-cal .calrow").count()} dias)')
    check(pg.locator('#v-cal .super').count() >= 1, 'calendário marca super dias')
    pg.click('#tabs [data-v="day"]'); pg.wait_for_timeout(300)
    check(pg.locator('#daytbl tbody tr').count() == 1, 'lista do dia do leilão (favorito)')
    with pg.expect_download() as dl: pg.click('#daycsv')
    dl_lines = open(dl.value.path(), encoding='utf-8-sig').read().splitlines()
    check(len(dl_lines) == 2 and 'deposito_usd' in dl_lines[0] and 'processo' in dl_lines[0], 'CSV do dia (lance máx., depósito, processo)')
    pg.click('#tabs [data-v="map"]'); pg.wait_for_timeout(3000)
    check(pg.locator('#map .leaflet-interactive').count() > 0, 'mapa com pontos')
    check(pg.locator('.mapleg').count()>=1, 'legenda do mapa')
    z = pg.evaluate(f'{D}.zillowUrl({D}.ITEMS[0])'); check(z.startswith('https://www.zillow.com/homes/') and z.endswith('_rb/'), 'formato do link Zillow')
    check('US$' in pg.inner_text('#kpis') + pg.inner_text('#sumline') and 'R$' not in pg.inner_text('body'), 'moeda: só US$')
    check(not errs, f'sem erros de JavaScript {errs[:3]}')
    # surviving-lien + Meus candidatos
    surv_n = pg.evaluate(D + ".ITEMS.filter(r=>r.fl.includes('surv')||r.survAmt).length")
    check(surv_n >= 1, f'imóveis com alerta hipoteca pode sobreviver: {surv_n}')
    check(pg.evaluate(D + ".ITEMS.filter(r=>r.fl.includes('surv')).every(r=>!r.clean)"), 'surv fora de Negócios limpos')
    check('Surviving Lien' in pg.evaluate("window.__dash.FL.surv.l"), 'selo FL.surv')
    check(pg.locator('#tabs [data-v="cand"]').count()==1, 'aba Meus candidatos')
    # add candidato from first list row
    rid = pg.evaluate(D + ".CUR[0].id")
    pg.evaluate(f"window.__dash.candAdd('{rid}')")
    pg.click('#tabs [data-v="cand"]'); pg.wait_for_timeout(400)
    check(pg.evaluate(D + '.view')=='cand', 'view candidatos')
    check(pg.locator('.ccard').count() >= 1, 'card de candidato renderizado')
    check(pg.locator('.cchk input[type=checkbox]').count() >= 4, 'checklist no candidato')
    check('Max Bid' in pg.inner_text('.ccard'), 'mostra Max Bid 17%')
    pg.locator('.cchk input[type=checkbox]').first.check(); pg.wait_for_timeout(200)
    prog = pg.inner_text('.cprog')
    check('1/5' in prog or '2/5' in prog, f'progresso checklist atualiza ({prog[:40]})')
    pg.evaluate("window.__dash.candRem(Object.keys(window.__dash.CAND)[0])")
    pg.wait_for_timeout(200)
    # bid-fill: some former nobid now have ref
    filled = pg.evaluate(D + ".ITEMS.filter(r=>r.plat==='PropertyOnion' && r.ref!=null && !r.nobid).length")
    still = pg.evaluate(D + ".ITEMS.filter(r=>r.nobid).length")
    check(filled >= 1, f'PO-only com FJ/OB preenchido: {filled} (ainda nobid={still})')
    pg.click('#tabs [data-v="table"]'); pg.wait_for_timeout(200)
    xbad = pg.evaluate("""(()=>{const d=window.__dash; const bad=[];
      for(const r of d.ITEMS){ if(r.xbid==null||r.roi==null) continue;
        const p=d.pnl(r,r.xbid); if(Math.abs((p.roi||0)-r.roi)>0.01) bad.push(r.id); }
      return bad.slice(0,3);})()""")
    check(not xbad, f'ROI da capa = P&L no lance realista ({xbad})')
    td = pg.evaluate("""(()=>{const d=window.__dash; const rows=d.ITEMS.filter(r=>r.t==="TD"&&r.mb>1000&&r.ref!=null&&r.ref<r.mb*0.2&&r.xbid!=null);
      const low=rows.filter(r=>r.xbid+1<r.ref || r.xbid+1<0.55*r.mb-1);
      const gap=rows.filter(r=>r.roi0!=null && r.roi!=null && r.roi0>r.roi+0.5);
      return {n:rows.length, low:low.length, gap:gap.length};})()""")
    check(td['n']>20 and td['low']==0 and td['gap']>5, f'tax deed no lance realista {td}')
    sus = pg.evaluate("""(()=>{const d=window.__dash; const s=d.ITEMS.filter(r=>r.suspect);
      const bad=s.filter(r=>r.risk==="baixo" || (r.sc!=null && r.sc>60) || (r.val0!=null && r.val>r.val0+1));
      return {n:s.length, bad:bad.length};})()""")
    check(sus['n']>=1 and sus['bad']==0, f'valor suspeito {sus}')
    check(pg.evaluate('window.__dash.ITEMS.every(r=>!r.titleNv || r.risk!=="baixo")'), 'título não verificado não é risco baixo')
    check(pg.evaluate('window.__dash.ITEMS.filter(r=>r.hist&&r.hist.length).every(r=>r.fl.includes("rebid")&&r.risk!=="baixo")'), 'leilão anterior com flag')
    check(pg.locator('#bgloss').count()==1, 'botão Glossário')
    # ---- English trade terms with Portuguese tooltips (central TERMS dictionary)
    pg.click('#tabs [data-v="table"]'); pg.wait_for_timeout(400)
    nth = pg.locator('#tbl thead .tm').count(); check(nth >= 6, f'termos em inglês com tooltip no cabeçalho ({nth})')
    pg.locator('#tbl thead .tm[data-tm="Max Bid"]').first.hover(); pg.wait_for_timeout(150)
    tip = pg.inner_text('#tmtip') if pg.locator('#tmtip').is_visible() else ''
    check('Lance máximo' in tip and '17%' in tip, f'hover mostra tradução + explicação ({tip[:60]})')
    pg.mouse.move(1, 1); pg.wait_for_timeout(100)
    pg.locator('#tbl thead .tm[data-tm="ARV"]').first.focus(); pg.wait_for_timeout(100)
    check(pg.locator('#tmtip').is_visible() and 'Valor de revenda' in pg.inner_text('#tmtip'), 'foco do teclado mostra o tooltip')
    check(pg.locator('#tbl thead .tm').first.get_attribute('tabindex') == '0', 'termo focável (tabindex 0)')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(100)
    check(pg.locator('#filters label .tm[data-tm="Verdict"]').count() >= 1, 'filtro Verdict com tooltip')
    check(pg.locator('#kpis .tm').count() >= 2, 'KPIs com tooltip')
    pg.click('#bgloss'); pg.wait_for_timeout(200)
    gl = pg.inner_text('#glossb')
    check(all(t in gl for t in ('Opening Bid', 'Final Judgment', 'Surviving Lien', 'Certificate Holder', 'Lis Pendens', 'CDD', 'Subdivision', 'Cash to Close', 'NO ROOM', 'CONTESTED')), 'Glossário lista os termos em inglês')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(150)
    # ---- local resale value + manual valuations
    lc = pg.evaluate("(()=>{const I=window.__dash.ITEMS; return {n:I.filter(r=>r.lc&&r.lc.lvl).length, used:I.filter(r=>r.lc&&r.lc.used).length, sub:I.filter(r=>r.lc&&r.lc.lvl==='sub').length, bad:I.filter(r=>r.lc&&r.lc.used&&!r.man&&!(r.sup&&r.sup.disc)&&!r.bld&&!(r.subst&&r.subst.arv0)&&Math.abs(r.val0-r.lc.est)>1).length, lowc:I.filter(r=>r.lc&&r.lc.used&&r.lc.conf<60).length};})()")
    check(lc['n'] > 1000 and lc['used'] > 500 and lc['sub'] > 100 and lc['bad'] == 0 and lc['lowc'] == 0, f'comps locais {lc}')
    ho = pg.evaluate('window.__dash.ITEMS.find(r=>r.parcel==="01596160")')
    check(ho and ho['val'] == 100000 and ho['addr'].startswith('Hickory Oak Dr') and ho['man']['holdYr'] == 5700 and ho['man']['qt'] == 2000, f"Hickory Oak manual {ho and (ho['val'], ho['addr'], round(ho['mb']))}")
    sc = pg.evaluate('window.__dash.ITEMS.find(r=>r.parcel==="01575842")')
    check(sc and sc['vd'] == 'PASSAR' and sc['val'] == 23500, f"Southern Charm PASSAR {sc and (sc['vd'], sc['val'])}")
    nman = pg.evaluate('window.__dash.ITEMS.filter(r=>r.man).length'); check(nman == 6, f'6 avaliações manuais ({nman})')
    pg.evaluate('window.__dash.openDrawer(window.__dash.ITEMS.find(r=>r.parcel==="01596160").id)'); pg.wait_for_timeout(400)
    dl = pg.evaluate("document.querySelector('#dlocal').textContent")
    check('Valor de venda — análise local' in dl and 'Avaliação manual' in dl and 'SOUTHERN HILLS PLANTATION' in dl and 'construída' in dl, 'painel: seção Valor de venda — análise local')
    pg.evaluate('window.__dash.closeDrawer && window.__dash.closeDrawer()'); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    check(pg.locator('#tbl .lcb').count() >= 5, 'selo de confiança na lista')
    na = pg.evaluate("window.__dash.ITEMS.filter(r=>!/^\\s*\\d/.test(r.addr0||r.addr)).length")
    check(na > 10 and pg.evaluate("document.body.innerHTML.includes('Endereço aproximado — dar lance pelo nº do processo')"), f'selo de endereço aproximado ({na})')
    check(not pg.evaluate("window.__dash.ITEMS.some(r=>r.man&&/^\\s*\\d/.test(r.addr))"), 'avaliações manuais sem número de casa adivinhado')
    lots = pg.evaluate("""(()=>{const d=window.__dash;
      const lands=d.ITEMS.filter(r=>r.ty==="Lote"||r.ty==="Terreno");
      const capped=lands.filter(r=>(r.lotBadges||[]).length);
      const over=capped.filter(r=>r.sc!=null && r.sc>55);
      const pasture=lands.find(r=>/LAKE PICKETT/i.test(r.addr||""));
      const west=lands.filter(r=>/WEST AVE/i.test(r.addr||"") && /CLERMONT/i.test(r.addr||""));
      const hwy=lands.find(r=>/HIGHWAY 27/i.test(r.addr||"") && /LEESBURG/i.test(r.addr||""));
      const ranked=lands.slice().sort((a,b)=>(b.sc||0)-(a.sc||0));
      const want=["ROYAL PALM","DALE DR","PALIFOX","ALTAMONTE","SANFORD","BALTIC"];
      const ranks=want.map(w=>ranked.findIndex(r=>(r.addr||"").toUpperCase().includes(w)));
      return {capped:capped.length, over:over.length, ranks,
        pasture:pasture?{sc:pasture.sc,b:pasture.lotBadges}:null,
        west:west.map(r=>({sc:r.sc,b:r.lotBadges})),
        hwy:hwy?{sc:hwy.sc,sus:!!hwy.suspect,val:hwy.val,b:hwy.lotBadges}:null,
        top:ranked.slice(0,6).map(r=>r.addr)};})()""")
    check(lots["over"]==0 and lots["capped"]>30, f'lotes sem comps/gleba/uso comercial têm nota ≤55 ({lots["capped"]} limitados, acima={lots["over"]})')
    check(lots["pasture"] and lots["pasture"]["sc"]<=55 and "big" in lots["pasture"]["b"], f'pastagem Lake Pickett limitada {lots["pasture"]}')
    check(lots["west"] and all(w["sc"]<=55 and "use" in w["b"] for w in lots["west"]), f'West Ave comercial limitada {lots["west"]}')
    check(lots["hwy"] and lots["hwy"]["sc"]<=55 and lots["hwy"]["sus"] and lots["hwy"]["val"]<200000, f'US-27 Leesburg suspeito e limitado {lots["hwy"]}')
    check(all(i>=0 and i<12 for i in lots["ranks"]), f'os 6 lotes residenciais ficam no topo {lots["ranks"]} {lots["top"]}')
    lm = pg.evaluate("""(()=>{const d=window.__dash;
      const lands=d.ITEMS.filter(r=>(r.ty==="Lote"||r.ty==="Terreno") && r.xbid!=null && r.val);
      // the historical-price term may never push a lot's realistic bid above 65% of ARV (unless the opening bid itself is higher)
      const over=lands.filter(r=>r.xbid>Math.max(r.ref||0, 0.65*r.val, 0.55*(r.mb||0), 0.28*r.val)+1);
      const lot=lands.find(r=>r.t==="TD"); const o=d.base(lot); const p=d.pnl(lot,lot.xbid,o);
      const H=d.ITEMS.filter(r=>/hernando/i.test(r.co));
      return {over:over.length, qt:p.fees.qt, clear:p.fees.clear, misc:p.sell.misc, val:lot.val,
        hern:H.length, hernLots:H.filter(r=>r.ty==="Lote"||r.ty==="Terreno").length, hernParcel:H.filter(r=>r.parcel).length,
        pin:d.ITEMS.filter(r=>r.co==="Pinellas"&&/LINCOLN AVE/.test(r.addr||"")).map(r=>r.ty)};})()""")
    check(lm["over"]==0, f'lance realista de lote ≤ 65% do ARV pelo preço histórico ({lm["over"]} acima)')
    check(lm["qt"]==1200 and lm["clear"]==500 and 500<=lm["misc"]<=1500, f'custos fixos de lote: título {lm["qt"]}, limpeza {lm["clear"]}, fechamento {round(lm["misc"])}')
    check(lm["hern"]>=40 and lm["hernLots"]>=35 and lm["hernParcel"]==lm["hern"], f'Hernando: {lm["hern"]} itens, {lm["hernLots"]} lotes/terrenos, {lm["hernParcel"]} com parcela')
    check(lm["pin"] and all(t=="Lote" for t in lm["pin"]), f'Pinellas casa pela parcela (SS-TT-RR) {lm["pin"]}')
    pg.click('#dchips [data-win="7"]'); pg.wait_for_timeout(400)
    check('próximos 7 dias' in pg.inner_text('#fnotice'), 'filtro de data aparece no aviso')
    span = pg.evaluate("""(()=>{const d1=document.querySelector('#d1').value, d2=document.querySelector('#d2').value;
      const bad=window.__dash.CUR.filter(r=>r.date<d1||r.date>d2);
      return {d1,d2,n:window.__dash.CUR.length,bad:bad.length, saved:!!localStorage.getItem('leilao_ui_v9')};})()""")
    check(span["bad"]==0 and span["n"]>0 and span["saved"], f'próximos 7 dias recortam a lista e gravam a vista {span}')
    pg.click('#dchips [data-win="0"]'); pg.wait_for_timeout(300)
    check('próximos' not in (pg.locator('#fnotice').inner_text() or ''), 'Todas tira o período')
    pg.fill('#q', 'zzzz-sem-match'); pg.dispatch_event('#q', 'input'); pg.wait_for_timeout(400)
    check('Filtros ativos' in pg.inner_text('#fnotice'), 'aviso de filtros ativos')
    pg.click('#fnotice-clear'); pg.wait_for_timeout(400)
    check('Filtros ativos' not in (pg.locator('#fnotice').inner_text() or ''), 'limpar some com o aviso')
    tc = pg.evaluate("(()=>{const I=window.__dash.ITEMS.filter(r=>r.tconf); const c=window.__dash.ITEMS.find(r=>/2412 CHANTILLY AVE/i.test(r.addr)); return {n:I.length, used:I.filter(r=>r.lc&&r.lc.used).length, ch:c?{ty:c.ty, t:c.tconf, fl:c.fl.includes('tconf')}:null};})()")
    check(tc['n'] > 0 and tc['used'] == 0 and tc['ch'] and tc['ch']['fl'], f"conflito de tipo: {tc['n']} itens, nenhum com comps de lote como ARV; Chantilly {tc['ch']}")
    mt = pg.evaluate("(()=>{const r=window.__dash.ITEMS.find(r=>/8364 MANTUA AVE/i.test(r.addr)); return r&&{val:r.val, fl:r.fl, m:r._o.months, sup:r.sup};})()")
    check(mt and 'supH' in mt['fl'] and mt['val'] <= 8000 and mt['m'] >= 9 and mt['sup']['ask'] == 8000, f'oferta alta em Sun n Lake (Mantua) {mt and (mt["val"], mt["m"], mt["fl"])}')
    hk = pg.evaluate("window.__dash.ITEMS.find(r=>r.parcel==='01596160')")
    check(not any(f in hk['fl'] for f in ('supH', 'supM')) and hk['val'] == 100000, 'Hickory Oak (manual) sem desconto de oferta')
    nb = pg.evaluate("window.__dash.ITEMS.filter(r=>r.fl.includes('bldA')).length"); check(nb > 20, f'lotes com construtoras ativas ({nb})')
    pg.click('#tabs [data-v="bld"]'); pg.wait_for_timeout(400)
    check(pg.locator('#v-bld tbody tr').count() > 10 and 'Lennar' in pg.inner_text('#v-bld'), 'view Builders com áreas e construtoras')
    pg.click('#tabs [data-v="table"]'); pg.wait_for_timeout(300)
    # ---- deep links
    tgt = pg.evaluate("(()=>{const r=window.__dash.ITEMS.find(r=>r.case&&r.t==='TD'&&!/^(Casa|Condo)$/.test(r.ty)); return {id:r.id, c:r.case};})()")
    for u, lbl in ((URL.split('#')[0] + '#id=' + tgt['id'], '#id='), (URL.split('#')[0] + '?case=' + tgt['c'], '?case=')):
        p3 = ctx.new_page(); p3.goto(u, wait_until='load', timeout=180000); p3.wait_for_function('window.__dash', timeout=60000); p3.wait_for_timeout(500)
        check(p3.locator('#drawer.on').count() == 1 and p3.evaluate('window.__dash.S.cat') == '', f'link direto {lbl} abre o painel do imóvel sem filtros')
        if lbl == '#id=': check('Copiar link do imóvel' in p3.inner_text('#dshare'), 'botão Copiar link do imóvel')
        p3.close()
    # ---- multi-select type filter
    pg.evaluate("window.__dash.setView('table')"); pg.wait_for_timeout(300)
    pg.click('#types [data-cat=""]'); pg.wait_for_timeout(300)
    check(pg.evaluate(D + '.S.cat') == '' and pg.evaluate(D + '.CUR.length') > pg.evaluate(D + '.CUR.filter(r=>r.ty==="Casa").length'), 'Todos limpa a seleção de tipo')
    for t in ('Lote', 'Terreno', 'Casa'): pg.click(f'#types [data-cat="{t}"]'); pg.wait_for_timeout(250)
    tys = set(pg.evaluate(D + '.CUR.map(r=>r.ty)'))
    check(pg.evaluate(D + '.S.cat') == 'Casa,Lote,Terreno' and tys == {'Lote', 'Terreno', 'Casa'}, f'multi-seleção Lote + Terreno + Casa ({tys})')
    check(pg.locator('#types .chip.on').count() == 3 and pg.locator('#types [data-cat="Lote"][aria-pressed="true"]').count() == 1, 'chips ligados independentes (aria-pressed)')
    chip = pg.inner_text('#types [data-cat="Lote"]'); check('(' in chip and any(ch.isdigit() for ch in chip), f'contagem no chip ({chip})')
    check('Casa + Lote + Terreno' in pg.inner_text('#fnotice'), 'tipos ativos no aviso de filtros')
    check('Casa%2CLote%2CTerreno' in pg.url or 'Casa,Lote,Terreno' in pg.url, 'tipos no link (hash)')
    check(pg.evaluate("JSON.parse(localStorage.getItem('leilao_ui_v9')).cat") == 'Casa,Lote,Terreno', 'tipos salvos na visão (leilao_ui_v9)')
    pg.click('#types [data-cat="Terreno"]'); pg.wait_for_timeout(250)
    check(pg.evaluate(D + '.S.cat') == 'Casa,Lote', 'desligar um tipo mantém os outros')
    url = pg.url
    p2 = ctx.new_page(); p2.goto(url, wait_until='load', timeout=180000); p2.wait_for_function('window.__dash', timeout=60000); p2.wait_for_timeout(400)
    check(p2.evaluate(D + '.S.cat') == 'Casa,Lote' and set(p2.evaluate(D + '.CUR.map(r=>r.ty)')) == {'Casa', 'Lote'}, 'link copiado restaura a multi-seleção'); p2.close()
    for t in ('Casa', 'Lote'): pg.click(f'#types [data-cat="{t}"]'); pg.wait_for_timeout(200)
    check(pg.evaluate(D + '.S.cat') == '', 'desligar todos = Todos')
    for t in ('Casa', 'Townhouse', 'Condo'): pg.click(f'#types [data-cat="{t}"]'); pg.wait_for_timeout(200)
    check(pg.evaluate(D + '.S.cat') == 'resid' and pg.locator('#types [data-cat="resid"].on').count() == 1, 'Casa + Townhouse + Condo = preset Residencial')
    pg.click('#types [data-cat="Lote"]'); pg.wait_for_timeout(200); pg.click('#types [data-cat="resid"]'); pg.wait_for_timeout(250)
    check(pg.evaluate(D + '.S.cat') == 'resid' and pg.locator('#types .tchip.on').count() == 3, 'Residencial seleciona Casa + Townhouse + Condo')
    # regressão aa9e9d4: nota longa de origem do valor esticava a coluna ARV e jogava NET / Max Bid para fora da tela
    pg.set_viewport_size({'width': 1920, 'height': 1000}); pg.evaluate(D + ".S.cat='Lote'; " + D + ".setView('table')"); pg.wait_for_timeout(500)
    wm = pg.evaluate("""(()=>{const th=[...document.querySelectorAll('#tbl thead th')]; const g=n=>th.find(h=>h.textContent.trim().startsWith(n)); const w=document.querySelector('#v-table .tblwrap');
     return {arv:g('ARV').getBoundingClientRect().width, net:g('NET').getBoundingClientRect().right, mb:g('Max Bid').getBoundingClientRect().right, wrap:w.getBoundingClientRect().right};})()""")
    check(wm['arv'] <= 260 and wm['net'] <= wm['wrap'] and wm['mb'] <= wm['wrap'], f'lotes: ARV estreito e NET/Max Bid visíveis a 1920px {wm}')
    blank = pg.evaluate("""(()=>{const th=[...document.querySelectorAll('#tbl thead th')].map(h=>h.textContent.trim()); const ix=k=>th.findIndex(h=>h.startsWith(k)); const I=window.__dash.ITEMS;
     return [...document.querySelectorAll('#tbl tbody tr')].filter(tr=>{const r=I.find(x=>tr.innerHTML.includes(x.id)); if(!r||r.ref==null||r.val==null) return false; return ['NET','Max Bid'].some(k=>{const c=tr.children[ix(k)]; return !c||!c.textContent.trim()||c.textContent.trim()==='—';});}).length;})()""")
    check(blank == 0, f'nenhum lote com ref e valor mostra NET/Max Bid vazio ({blank})')
    pg.set_viewport_size({'width': 1440, 'height': 950})
    # leilões presenciais (Lake / Osceola): lista oficial do clerk
    ipx = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.ip); return {n:I.length, lake:I.filter(r=>r.co==='Lake').length, osc:I.filter(r=>r.co==='Osceola').length,
      hoaNoMtg:I.filter(r=>r.ip.ptype==='hoa'&&!r.fl.includes('mtg')).length, ra:I.filter(r=>/realforeclose|realtaxdeed|realauction/i.test(JSON.stringify(r.links||{}))).length,
      noFlag:I.filter(r=>!r.fl.includes('ipres')).length, id:(I.find(r=>r.val)||I[0]).id};})()""")
    check(ipx['lake'] > 20 and ipx['osc'] > 20 and ipx['hoaNoMtg'] == 0 and ipx['ra'] == 0 and ipx['noFlag'] == 0, f'presencial: itens Lake/Osceola da lista oficial, HOA com alerta de hipoteca, sem link RealAuction {ipx}')
    pg.evaluate(D + ".openDrawer('" + ipx['id'] + "')"); pg.wait_for_timeout(700)
    dtx = pg.evaluate("document.body.textContent")
    check('Leilão presencial — Fórum de' in dtx and '11h' in dtx and 'epósito de 5%' in dtx and ('ShowCase' in dtx or 'Benchmark' in dtx), 'presencial: badge, regras de pagamento e link do processo no drawer')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    # favoritos padrão (data/favoritos.json): navegador novo -> ★ + Meus candidatos com Max Bid do plano; remover persiste
    fc = b.new_context(viewport={'width': 1440, 'height': 950}); fp = fc.new_page(); fp.goto(URL, wait_until='load', timeout=180000)
    fp.wait_for_function('window.__dash', timeout=60000); fp.wait_for_timeout(400)
    FZ = """(()=>{const F=JSON.parse(localStorage.getItem('leilao_favseed_v1')||'[]'), FV=JSON.parse(localStorage.getItem('leilao_fav_v1')||'[]'), C=JSON.parse(localStorage.getItem('leilao_cand_v1')||'{}'); const I=window.__dash.ITEMS.filter(r=>r.plan);
      return {seed:F.length, plan:I.length, fav:I.filter(r=>FV.includes(r.id)).length, cand:I.filter(r=>C[r.id]&&C[r.id].maxBid===r.plan.mb).length, id:I[0]&&I[0].id};})()"""
    fz = fp.evaluate(FZ)
    check(fz['plan'] >= 17 and fz['seed'] == fz['plan'] == fz['fav'] == fz['cand'], f'favoritos do plano: ★ e Meus candidatos com Max Bid do plano {fz}')
    fp.evaluate("(id=>{const f=JSON.parse(localStorage.getItem('leilao_fav_v1')).filter(x=>x!==id); localStorage.setItem('leilao_fav_v1',JSON.stringify(f));})('" + fz['id'] + "')")
    fp.reload(wait_until='load'); fp.wait_for_function('window.__dash', timeout=60000); fp.wait_for_timeout(300)
    fz2 = fp.evaluate(FZ); check(fz2['fav'] == fz['plan'] - 1, f'favorito do plano removido continua removido após recarregar {fz2}')
    fp.evaluate(D + ".openDrawer('" + fz['id'] + "')"); fp.wait_for_timeout(400)
    check('Max Bid do plano' in fp.evaluate('document.body.textContent'), 'drawer mostra o plano (prioridade e Max Bid)')
    fc.close()
    # tax deed presencial do clerk (Sumter): itens com opening bid, badge Bushnell e sem host RealAuction
    sm = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.cs==='sumter'&&r.t==='TD'); return {n:I.length, ob:I.filter(r=>r.ref>0).length, ip:I.filter(r=>r.ip&&r.ip.city==='Bushnell'&&r.fl.includes('ipres')).length, ra:I.filter(r=>/realtaxdeed|realforeclose/.test(JSON.stringify(r.links))).length};})()""")
    check(sm['n'] > 0 and sm['ob'] == sm['n'] and sm['ip'] == sm['n'] and sm['ra'] == 0, f'Sumter: tax deed presencial do clerk com opening bid e badge Bushnell {sm}')
    cl = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.cs==='collier'&&r.t==='TD'); return {n:I.length, ip:I.filter(r=>r.ip&&r.ip.city==='Naples').length, nob:I.filter(r=>r.ref==null&&!r.fl.includes('nobid')).length, lot:I.filter(r=>r.ty==='Lote'||r.ty==='Terreno').length};})()""")
    check(cl['n'] > 0 and cl['ip'] == cl['n'] and cl['nob'] == 0, f'Collier: tax deed presencial (edital do clerk), badge Naples, Sem Opening Bid marcado {cl}')
    # dados conferidos no clerk: Live Oak Ln (Citrus) opening bid 22.790,32; Gerry Rd (Sarasota) resgatado = fora; endereço pelo DOR
    dq = pg.evaluate("""(()=>{const I=window.__dash.ITEMS; const lo=I.find(r=>r.cs==='citrus'&&/LIVE OAK/i.test(r.addr)); const g=I.find(r=>r.cs==='sarasota'&&/GERRY/i.test(r.addr));
      const glued=I.filter(r=>/^\\d{5,}[A-Z]/.test(r.addr||'')).length; return {lo: lo?lo.ref:null, gerry: !!g, glued};})()""")
    check(dq['lo'] and abs(dq['lo'] - 22790.32) < 1 and not dq['gerry'] and dq['glued'] == 0, f'clerk: opening bid corrigido (Live Oak), resgatado removido (Gerry Rd), sem nº colado na rua {dq}')
    hb = pg.evaluate("(()=>{const r=window.__dash.ITEMS.find(r=>r.cs==='hillsborough'&&r.t==='TD'); return r?r.id:null;})()")
    if hb:
        pg.evaluate(D + ".openDrawer('" + hb + "')"); pg.wait_for_timeout(400)
        check('Não aceita wire' in pg.evaluate('document.body.textContent'), 'Hillsborough: regra de pagamento do tax deed no drawer')
        pg.keyboard.press('Escape')
    # Gulf: tax deed presencial (lista do clerk), badge Port St. Joe, resgatado fora
    gu = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.cs==='gulf'&&r.t==='TD'); return {n:I.length, ip:I.filter(r=>r.ip&&r.ip.city==='Port St. Joe').length, ob:I.filter(r=>r.ref>0).length, starfish:I.some(r=>/STARFISH/i.test(r.addr||''))};})()""")
    check(gu['n'] >= 1 and gu['ip'] == gu['n'] and gu['ob'] == gu['n'] and not gu['starfish'], f'Gulf: tax deed presencial do clerk, badge Port St. Joe, resgatado fora {gu}')
    # lote abaixo do mínimo (Tampa RS-50): flag + ARV limitado ao valor oficial; Collier 26136 resgatado fora
    ss = pg.evaluate("""(()=>{const I=window.__dash.ITEMS;const r=I.find(r=>/3506 E CHELSEA/i.test(r.addr||''));return {fl:r&&r.fl, val:r&&r.val, mkt:r&&r.mkt, c:I.some(r=>r.parcel==='40684200008')};})()""")
    check(ss['fl'] and 'subst' in ss['fl'] and ss['val'] <= max(ss['mkt'] or 0, 1) + 1 and not ss['c'], f'lote abaixo do mínimo: flag e ARV no valor oficial; Collier 26136 resgatado fora {ss}')
    # áreas úmidas / inundação pelo polígono: lote com wetland >= limite ou FEMA A* material não pode ser FLIP/CONSIDER; drawer mostra
    gr = pg.evaluate("""(()=>{const I=window.__dash.ITEMS; const G=I.filter(r=>r.geo&&r.geo.poly!==false); const wm=10, fm=10;
      const badv=G.filter(r=>((r.geo.wetPct||0)>=wm||(r.geo.sfhaPct||0)>=fm)&&(r.vd==='FLIP'||r.vd==='CONSIDERAR')).length;
      const ex=G.find(r=>(r.geo.wetPct||0)>=wm); return {n:G.length, badv, ex: ex?ex.id:null, flagged: ex?(ex.fl||[]).includes('wet'):null};})()""")
    check(gr['n'] > 0 and gr['badv'] == 0 and (gr['ex'] is None or gr['flagged']), f'áreas úmidas/inundação: nenhum lote acima do limite em FLIP/CONSIDER, badge presente {gr}')
    if gr['ex']:
        pg.evaluate(D + ".openDrawer('" + gr['ex'] + "')"); pg.wait_for_timeout(400)
        check('USFWS NWI' in pg.evaluate('document.body.textContent'), 'áreas úmidas: seção no drawer')
        pg.keyboard.press('Escape')
    # Levy: tax deed presencial pelo TaxSmart do clerk (opening bid, resgatados fora), badge Bronson
    lv = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.cs==='levy'&&r.t==='TD'); return {n:I.length, ip:I.filter(r=>r.ip&&r.ip.city==='Bronson').length, ob:I.filter(r=>r.ref>0).length, addr:I.filter(r=>/^\\d/.test(r.addr||'')).length};})()""")
    check(lv['n'] >= 1 and lv['ip'] == lv['n'] and lv['ob'] == lv['n'], f'Levy: tax deed presencial (TaxSmart do clerk), opening bid, badge Bronson {lv}')
    # Wakulla: tax deed presencial pelos avisos em PDF do clerk (parcela + opening bid)
    wk = pg.evaluate("""(()=>{const I=window.__dash.ITEMS.filter(r=>r.cs==='wakulla'&&r.t==='TD'); return {n:I.length, ip:I.filter(r=>r.ip&&r.ip.city==='Crawfordville').length, ob:I.filter(r=>r.ref>0).length};})()""")
    check(wk['n'] >= 1 and wk['ip'] == wk['n'] and wk['ob'] == wk['n'], f'Wakulla: tax deed presencial (PDF do clerk), opening bid, badge Crawfordville {wk}')
    # condados por edital (floridapublicnotices.com): itens presenciais, badge, 'Sem Opening Bid' quando o edital não traz lance
    np_ = pg.evaluate("""(()=>{const C=['hardee','desoto','bradford','glades','taylor','madison','union','dixie']; const I=window.__dash.ITEMS.filter(r=>C.includes(r.cs)&&r.t==='TD');
      return {n:I.length, ip:I.filter(r=>r.ip&&/floridapublicnotices/.test(r.ip.list||'')).length, semob:I.filter(r=>r.ref==null).length, semobFlag:I.filter(r=>r.ref==null&&(r.fl||[]).includes('nobid')).length, cos:[...new Set(I.map(r=>r.cs))].sort()};})()""")
    check(np_['n'] >= 1 and np_['ip'] == np_['n'] and np_['semob'] == np_['semobFlag'], f'editais: tax deeds presenciais dos condados sem lista online, Sem Opening Bid marcado {np_}')
    # celular 390px
    m = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
    mp = m.new_page(); merr = []; mp.on('pageerror', lambda e: merr.append(str(e)))
    mp.goto(URL, wait_until='load', timeout=180000); mp.wait_for_function('window.__dash', timeout=60000); mp.wait_for_timeout(500)
    check(mp.evaluate('document.documentElement.scrollWidth') <= 392, 'celular: sem rolagem horizontal')
    check(mp.locator('#grid .card').count() > 0, 'celular abre em cards')
    check(mp.locator('#tbl tbody tr').count() == 0 or not mp.locator('#v-table').is_visible(), 'celular: tabela larga oculta (cards no lugar)')
    mp.locator('#types [data-cat="Lote"]').tap(); mp.wait_for_timeout(300); mp.locator('#types [data-cat="Terreno"]').tap(); mp.wait_for_timeout(300)
    check(mp.evaluate('window.__dash.S.cat') == 'Casa,Condo,Lote,Terreno,Townhouse' and mp.locator('#types .tchip.on').count() == 5, f"celular: toque soma tipos ({mp.evaluate('window.__dash.S.cat')})")
    mp.screenshot(path='/workspace/theme_preview/melhoria12_tipos_mobile.png')
    mp.locator('#types [data-cat="resid"]').tap(); mp.wait_for_timeout(300)
    check(mp.evaluate("getComputedStyle(document.querySelector('#typesbar')).position") == 'sticky', 'celular: chips de tipo fixos no topo (sticky)')
    check(mp.evaluate("getComputedStyle(document.querySelector('#ftoggle')).position") == 'fixed', 'celular: botão flutuante de filtros')
    overlap = mp.evaluate("(()=>{const a=document.querySelector('#kstrip').getBoundingClientRect(); const b=document.querySelector('#ftoggle').getBoundingClientRect(); return !(b.right<a.left||b.left>a.right||b.bottom<a.top||b.top>a.bottom);})()")
    check(overlap==False, 'celular: botão de filtros não cobre os KPIs')
    clipped = mp.evaluate("[...document.querySelectorAll('#types .chip')].filter(e=>e.scrollWidth>e.clientWidth+2).length")
    check(clipped==0, f'celular: chips de tipo sem corte ({clipped})')
    check(not mp.locator('#filters .fgrid').is_visible(), 'celular: filtros recolhidos')
    mp.click('#ftoggle'); mp.wait_for_timeout(300)
    sheet = mp.evaluate("(()=>{const r=document.querySelector('#filters').getBoundingClientRect();return [getComputedStyle(document.querySelector('#filters')).position, Math.round(r.bottom), Math.round(r.width)]})()")
    check(sheet[0] == 'fixed' and sheet[1] >= 840 and sheet[2] >= 388 and mp.locator('#filters .fgrid').is_visible(), f'celular: filtros em painel inferior (bottom sheet) {sheet}')
    check('Ver' in mp.inner_text('#ftoggle'), 'celular: botão “Ver N imóveis” no painel de filtros')
    mp.click('#ftoggle'); mp.wait_for_timeout(300)
    check(not mp.locator('#filters .fgrid').is_visible(), 'celular: painel de filtros fecha')
    small = mp.evaluate("[...document.querySelectorAll('#types .chip, #ftoggle, #grid .card [data-star]')].filter(e=>e.offsetParent&&e.getBoundingClientRect().height<36).length")
    check(small == 0, f'celular: alvos de toque ≥ 36 px ({small} pequenos)')
    rid = mp.evaluate("window.__dash.CUR.find(r=>r.imgs&&r.imgs.length>1)?.id")
    if rid:
        mp.evaluate(f"window.__dash.openDrawer('{rid}')")
    else:
        mp.locator('#grid .card').first.click()
    mp.wait_for_timeout(500)
    check(mp.evaluate("document.querySelector('#drawer').getBoundingClientRect().width") >= 380, 'celular: painel em tela cheia')
    if rid:
        src0 = mp.get_attribute('#galimg', 'src')
        box = mp.locator('#galmain').bounding_box()
        mp.evaluate('''(()=>{const el=document.querySelector('#galmain');const mk=(t,x)=>new TouchEvent(t,{bubbles:true,touches:t==='touchend'?[]:[new Touch({identifier:1,target:el,clientX:x,clientY:200})],changedTouches:[new Touch({identifier:1,target:el,clientX:x,clientY:200})]});el.dispatchEvent(mk('touchstart',300));el.dispatchEvent(mk('touchend',120));})()''')
        mp.wait_for_timeout(300)
        check(mp.get_attribute('#galimg', 'src') != src0 and '2 /' in mp.inner_text('#galmain'), 'celular: galeria troca foto com swipe')
    check(not mp.locator('#ftoggle').is_visible(), 'celular: botão de filtros some com o painel aberto')
    check(mp.evaluate("document.querySelector('#drawer').scrollWidth <= document.querySelector('#drawer').clientWidth + 2"), 'celular: painel sem rolagem horizontal')
    check(not merr, 'celular: sem erros JS')
    b.close()
print('\n' + ('TODOS OS TESTES OK' if not fails else f'{len(fails)} FALHA(S)'))
sys.exit(1 if fails else 0)
