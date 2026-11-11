"""表紙画像（1080x1920）を台本から作る：python3 tools/cover.py script.json out.png
・枠や帯は使わず、白地に見出しの文字だけで組む（新聞の一面のような構成）
・見出しは「何が起きたか」が一読でわかる2行。要点の句だけを青にする
・プロフィール一覧では中央の 3:4（上下240pxずつ切れる）だけが見えるので、すべてその範囲に収める
台本の "cover": [{"sect", "title"（改行で2行、*…* が青）}, ...]（3本）を使う。"""
import sys, os, json, html, re, datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qn_short as q

sc = json.load(open(sys.argv[1], encoding="utf-8"))
out = sys.argv[2]
m = re.match(r"(\d{4})\.(\d{1,2})\.(\d{1,2})", sc.get("date_label", ""))
d = datetime.date(*map(int, m.groups())) if m else datetime.date.today()
wd = "月火水木金土日"[d.weekday()]
esc = html.escape


def fmt(t):
    t = re.sub(r"\*(.+?)\*", r'<em>\1</em>', esc(t))
    return re.sub(r"([ぁ-んァ-ヶー、。・]+)", r'<span class="kn">\1</span>', t)


single = isinstance(sc["cover"], dict)
rows = ""
for k, it in enumerate([] if single else sc["cover"][:3]):
    lines = "".join(f'<span class="ln">{fmt(l)}</span>' for l in it["title"].split("\n"))
    rows += f'<div class="it"><div class="lb"><b>0{k + 1}</b>{esc(it["sect"])}</div><div class="hl">{lines}</div></div>'
fl = "".join(f'<link rel="stylesheet" href="file://{q.FONT_DIR}/{w}.css">' for w in (500, 700, 900))
page = f"""<!doctype html><html><head><meta charset="utf-8">{fl}<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1920px;background:#F7F8FA;font-family:"Yu Gothic","Zen Kaku Gothic New",sans-serif;color:#0B1B33;position:relative;overflow:hidden}}
.top{{position:absolute;left:96px;right:96px;top:282px;display:flex;align-items:baseline;justify-content:space-between}}
.logo{{font-size:50px;font-weight:900;letter-spacing:-.01em;margin-left:-2px}}
.logo i{{font-style:normal;color:#1F5BFF}}
.dt{{font-size:28px;font-weight:700;letter-spacing:.08em;color:#5B6B82}}
.list{{position:absolute;left:96px;right:96px;top:380px;bottom:336px;border-top:2px solid #0B1B33;display:flex;flex-direction:column}}
.it{{flex:1;display:flex;flex-direction:column;justify-content:center;border-bottom:1px solid #D9E0EA}}
.lb{{font-size:27px;font-weight:700;color:#5B6B82;letter-spacing:.1em;margin-bottom:18px;display:flex;gap:16px}}
.lb b{{color:#1F5BFF;font-weight:900;letter-spacing:.04em}}
.hl{{font-size:84px;font-weight:700;line-height:1.24;letter-spacing:-.025em}}
.ln{{display:block;white-space:nowrap;width:max-content}}
.hl em{{font-style:normal;color:#1F5BFF;font-weight:900}}
.kn{{letter-spacing:-.07em}}
.ft{{position:absolute;left:96px;right:96px;top:1618px;font-size:26px;font-weight:700;color:#8A97AA;letter-spacing:.12em}}
</style></head><body>
<div class="top"><div class="logo">Quick <i>News</i></div><div class="dt">{d.month}/{d.day}（{wd}）の時事3本</div></div>
<div class="list">{rows}</div>
<div class="ft">{esc(sc.get("tagline", "1日1分で社会がわかる"))}</div>
</body></html>"""
if single:   # 1本のニュースの表紙：大きな見出し＋補足の問い＋その話の地図
    cv = sc["cover"]
    lines = "".join(f'<span class="ln">{fmt(l)}</span>' for l in cv["title"].split("\n"))
    subl = "<br>".join(fmt(l) for l in cv.get("sub", "").split("\n"))
    libs = "".join(f'<script src="file://{q.LIB_DIR}/{n}"></script>' for n in ("d3-array.min.js", "d3-geo.min.js", "topojson-client.min.js", "world50m.js"))
    mp = json.dumps(cv.get("map"), ensure_ascii=False)
    page = f"""<!doctype html><html><head><meta charset="utf-8">{fl}{libs}<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:1080px;height:1920px;background:#F7F8FA;font-family:"Yu Gothic","Zen Kaku Gothic New",sans-serif;color:#0B1B33;position:relative;overflow:hidden}}
.top{{position:absolute;left:96px;right:96px;top:282px;display:flex;align-items:baseline;justify-content:space-between;padding-bottom:26px;border-bottom:2px solid #0B1B33}}
.logo{{font-size:50px;font-weight:900;letter-spacing:-.01em;margin-left:-2px}}
.logo i{{font-style:normal;color:#1F5BFF}}
.dt{{font-size:28px;font-weight:700;letter-spacing:.08em;color:#5B6B82}}
.lb{{position:absolute;left:96px;top:430px;font-size:30px;font-weight:700;color:#1F5BFF;letter-spacing:.1em}}
.hl{{position:absolute;left:96px;top:486px;font-size:104px;font-weight:700;line-height:1.22;letter-spacing:-.03em}}
.ln{{display:block;white-space:nowrap;width:max-content}}
.hl em{{font-style:normal;color:#1F5BFF;font-weight:900}}
.sub{{position:absolute;left:96px;right:96px;font-size:40px;font-weight:700;line-height:1.5;color:#5B6B82;letter-spacing:-.01em}}
.kn{{letter-spacing:-.07em}}
#map{{position:absolute;left:0;width:1080px}}
.ft{{position:absolute;left:96px;right:96px;top:1618px;font-size:26px;font-weight:700;color:#8A97AA;letter-spacing:.12em}}
</style></head><body>
<div class="top"><div class="logo">Quick <i>News</i></div><div class="dt">{d.month}/{d.day}（{wd}）</div></div>
<div class="lb">{esc(cv.get("label", ""))}</div><div class="hl">{lines}</div><div class="sub">{subl}</div>
<svg id="map"></svg><div class="ft">{esc(sc.get("tagline", "1日1分で社会がわかる"))}</div>
<script>
window.layoutMap=function(top,bottom){{const M={mp};if(!M)return;const svg=document.getElementById('map'),W=1080,H=bottom-top;svg.style.top=top+'px';svg.setAttribute('width',W);svg.setAttribute('height',H);
 const ns='http://www.w3.org/2000/svg',mk=(t,a)=>{{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);svg.appendChild(e);return e;}};
 const fs=topojson.feature(WORLD,WORLD.objects.countries).features;
 const lo=Math.min(M.from[0],M.to[0])-14,hi=Math.max(M.from[0],M.to[0])+14,la=Math.min(M.from[1],M.to[1])-(M.pad_s||9),ha=Math.max(M.from[1],M.to[1])+8;
 const proj=d3.geoConicConformal().rotate([-(lo+hi)/2,0]).parallels([40,60]).fitExtent([[96,10],[W-96,H-10]],{{type:'MultiPoint',coordinates:[[lo,la],[hi,la],[lo,ha],[hi,ha]]}});
 const path=d3.geoPath(proj);const hl=new Set((M.hl||[]).map(x=>String(x).padStart(3,'0')));
 const defs=mk('defs',{{}});defs.innerHTML='<linearGradient id="fd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".12" stop-color="#fff" stop-opacity="1"/><stop offset=".88" stop-color="#fff" stop-opacity="1"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient><mask id="mk"><rect width="'+W+'" height="'+H+'" fill="url(#fd)"/></mask>';
 const g=mk('g',{{mask:'url(#mk)'}});const ad=(t,a)=>{{const e=document.createElementNS(ns,t);for(const k in a)e.setAttribute(k,a[k]);g.appendChild(e);return e;}};
 fs.forEach(f=>ad('path',{{d:path(f),fill:hl.has(String(f.id).padStart(3,'0'))?'#1F5BFF':'#E1E7F0',stroke:'#F7F8FA','stroke-width':1.2}}));
 const a=proj(M.from),b=proj(M.to),mx=(a[0]+b[0])/2,my=Math.min(a[1],b[1])-120;
 ad('path',{{d:`M${{a[0]}},${{a[1]}} Q${{mx}},${{my}} ${{b[0]}},${{b[1]}}`,fill:'none',stroke:'#0B1B33','stroke-width':4,'stroke-dasharray':'12 12','stroke-linecap':'round'}});
 [[a,M.from_label,'#0B1B33'],[b,M.to_label,'#1F5BFF']].forEach(([p,l,c])=>{{ad('circle',{{cx:p[0],cy:p[1],r:16,fill:'#fff',stroke:c,'stroke-width':6}});
  const t=ad('text',{{x:p[0],y:p[1]-34,'text-anchor':'middle','font-size':34,'font-weight':700,fill:'#0B1B33','font-family':'Zen Kaku Gothic New',stroke:'#F7F8FA','stroke-width':9,'paint-order':'stroke','stroke-linejoin':'round'}});t.textContent=l;}});
}};
</script></body></html>"""
fn = os.path.join(os.path.dirname(os.path.abspath(out)), "_cover.html")
open(fn, "w", encoding="utf-8").write(page)
with sync_playwright() as pw:
    br = pw.chromium.launch(); pg = br.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto("file://" + fn); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(400)
    if single:
        pg.evaluate("""(()=>{const h=document.querySelector('.hl'),W=888;let s=104;
          while([...h.querySelectorAll('.ln')].some(l=>l.getBoundingClientRect().width>W)&&s>50){s-=1;h.style.fontSize=s+'px';}
          const sb=document.querySelector('.sub');sb.style.top=(h.getBoundingClientRect().bottom+30)+'px';
          layoutMap(sb.getBoundingClientRect().bottom+20,1600);})()""")
    # 3本の見出しは同じ大きさにそろえる：いちばん長い行が幅に収まる大きさ
    pg.evaluate("""(()=>{const hs=[...document.querySelectorAll('.hl')],W=888;let s=84;
      const over=()=>hs.some(h=>[...h.querySelectorAll('.ln')].some(l=>l.getBoundingClientRect().width>W));
      while(over()&&s>40){s-=1;hs.forEach(h=>h.style.fontSize=s+'px');}return s;})()""")
    print("size", pg.evaluate("getComputedStyle(document.querySelector('.hl')).fontSize"))
    pg.screenshot(path=out); br.close()
os.remove(fn)
