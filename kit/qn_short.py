#!/usr/bin/env python3
"""Quick News（1日1分で社会がわかる）ショート動画エンジン v4：白×青のエディトリアルデザイン.

使い方:
  python3 qn_short.py script.json out.mp4             # 本番
  python3 qn_short.py script.json out.mp4 --stills d  # 各シーンの見せ場を JPEG で確認

・シーンは HTML/CSS で描き、Playwright で1フレームずつ撮影して ffmpeg で動画にする。
・書体は 游ゴシック（端末にあれば）→ Zen Kaku Gothic New（無料・近い字形）の順に使う。QN_FONT_DIR に
  @fontsource/zen-kaku-gothic-new の package フォルダを置く。
・ナレーションは VOICEVOX（VOICEVOX_DIR）。既定は No.7 アナウンス。使えなければ pyopenjtalk。
・BGM と効果音は numpy で合成する。
"""
import re
import json, os, sys, subprocess, tempfile, shutil, wave, random, io, glob, html as H
import numpy as np
from playwright.sync_api import sync_playwright

W, HGT, FPS, SR = 1080, 1920, 30, 48000
ENC = ["-c:v", "libx264", "-crf", "18", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS)]
FONT_DIR = os.environ.get("QN_FONT_DIR", "/home/claude/news_short/fonts/package")
LIB_DIR = os.environ.get("QN_LIB_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
rnd = random.Random(11)

# ───────── 配色（白ベース・青アクセント） ─────────
C = dict(bg="#F6F8FB", ink="#0B1B33", sub="#5B6B82", line="#DCE3EE", blue="#1F5BFF", blue2="#6E93FF",
         pale="#E8EFFF", card="#FFFFFF", warn="#D93A3A", acc="#EA6A12", accp="#FFF1E6")


def esc(s):
    return H.escape(str(s))


def chunks(text):
    """'日経平均が *一時6万円台* に' → [(text, accent)]。半角スペースは区切り（表示しない）、*…* は青."""
    out = []
    for part in text.split(" "):
        if not part:
            continue
        acc = part.startswith("*") and part.endswith("*") and len(part) > 1
        out.append((part.strip("*"), acc))
    return out


exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "picto.py"), encoding="utf-8").read(), globals())

# 上部の見出しの位置。Instagram・TikTok の上部の表示（「リール」やタブ）に隠れないよう、ヘッダーごと下げてある
TITLE_Y = 336   # .cam ごと 120px 下げているので、画面上では 500px


def kin(text, start, cls="", step=0.11, style="", tag="div"):
    """キネティック見出し：文節ごとにぼかし→くっきり。\\n で改行."""
    style = style.replace("top:336px", f"top:{TITLE_Y}px")   # 上部の見出しは TITLE_Y にそろえる
    lines = text.split("\n")
    html, k = [], 0
    for li, line in enumerate(lines):
        segs = []
        for t, acc in chunks(line):
            segs.append(f'<span class="ph{" acc" if acc else ""}" style="animation-delay:{start + k * step:.3f}s">{esc(t)}</span>')
            k += 1
        html.append("".join(segs))
    return f'<{tag} class="kin {cls}" style="{style}">{"<br>".join(html)}</{tag}>'


def fmt_num(v, dec=0):
    return f"{v:,.{dec}f}"


# ───────── 共通CSS ─────────
BASE_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:%(bg)s;--ink:%(ink)s;--sub:%(sub)s;--line:%(line)s;--blue:%(blue)s;--blue2:%(blue2)s;--pale:%(pale)s;--card:%(card)s;--warn:%(warn)s;--acc:%(acc)s;--accp:%(accp)s}
body{width:1080px;height:1920px;overflow:hidden;background:var(--bg);color:var(--ink);
font-family:'Yu Gothic','YuGothic','游ゴシック','游ゴシック体','Zen Kaku Gothic New',sans-serif;font-weight:500;
font-feature-settings:"palt" 1;-webkit-font-smoothing:antialiased;word-break:auto-phrase;line-break:strict}
.abs{position:absolute}
#bg{position:absolute;inset:0;overflow:hidden}
.glow{position:absolute;border-radius:50%;filter:blur(90px);opacity:.55}
.g1{width:900px;height:900px;left:-300px;top:200px;background:#D9E4FF;animation:drift1 9s ease-in-out infinite alternate}
.g2{width:800px;height:800px;right:-320px;top:900px;background:#E3EAFF;animation:drift2 11s ease-in-out infinite alternate}
@keyframes drift1{to{transform:translate(120px,80px)}}
@keyframes drift2{to{transform:translate(-100px,-120px)}}
#scene{position:absolute;inset:0;animation:sin .34s cubic-bezier(.2,.8,.2,1) both, sout .22s ease-in forwards;animation-delay:0s,var(--zout)}
.cam{position:absolute;left:0;right:0;top:164px;bottom:-164px;transform-origin:50% 42%;animation:cam var(--D) linear both}
@keyframes cam{from{transform:scale(1)}to{transform:scale(1.045)}}
.dots{position:absolute;inset:-60px;background-image:radial-gradient(#DDE5F1 2px,transparent 2px);background-size:30px 30px;opacity:.55;animation:dots 6s linear infinite}
@keyframes dots{to{transform:translate(30px,-30px)}}
@keyframes sin{0%{opacity:0;filter:blur(10px);transform:translateY(90px)}100%{opacity:1;filter:none;transform:none}}
@keyframes sout{0%{opacity:1}100%{opacity:0;filter:blur(10px);transform:translateY(-110px)}}
/* 枠まわり（細いラベルとヘアライン） */
#frame{position:absolute;inset:0;z-index:50;pointer-events:none}
.brand{position:absolute;left:94px;top:248px;font-size:76px;font-weight:900;letter-spacing:-.035em;color:var(--ink);line-height:1}
.brand i{font-style:normal;color:var(--blue)}
.tagl{position:absolute;right:150px;top:256px;font-size:24px;font-weight:500;color:var(--sub);letter-spacing:.06em;white-space:nowrap}
.date{position:absolute;right:150px;top:294px;font-size:24px;color:var(--sub);letter-spacing:.12em}
.rule{position:absolute;left:96px;right:150px;top:348px;height:2px;background:var(--line)}
.rule b{position:absolute;left:0;top:-1px;height:4px;border-radius:2px;background:var(--blue);animation:prog var(--D) linear both}
@keyframes prog{from{width:var(--p0)}to{width:var(--p1)}}
.sect{position:absolute;left:96px;top:372px;font-size:24px;color:var(--blue);letter-spacing:.06em;font-weight:700}
.sect span{color:var(--sub);font-weight:500;margin-left:12px;letter-spacing:.08em}
/* 字幕 */
#cap{position:absolute;left:96px;right:150px;top:1318px;z-index:40}
.cap{position:absolute;left:0;right:0;background:rgba(255,255,255,.92);border:1px solid var(--line);border-radius:22px;
padding:26px 34px;font-size:39px;line-height:1.6;font-weight:500;color:var(--ink);opacity:0;word-break:auto-phrase;text-wrap:pretty;
box-shadow:0 18px 50px rgba(20,40,90,.08)}
.capin{animation:capin .22s ease-out both}
@keyframes capin{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:none}}
.capout{animation:capin .22s ease-out both, capout .01s linear forwards}
@keyframes capout{to{opacity:0}}
#src{position:absolute;right:150px;top:372px;font-size:24px;color:var(--sub);letter-spacing:.02em;z-index:51}
/* キネティック見出し */
.kin{position:absolute;left:96px;right:150px;font-weight:700;line-height:1.28;letter-spacing:-.02em;color:var(--ink)}
.ph{display:inline-block;white-space:nowrap;animation:ph .55s cubic-bezier(.2,.8,.2,1) both}
.ph.acc{color:var(--blue)}
@keyframes ph{0%{opacity:0;filter:blur(12px);transform:translateY(26px)}100%{opacity:1;filter:none;transform:none}}
.eyebrow{position:absolute;left:96px;font-size:28px;font-weight:700;color:var(--blue);letter-spacing:.08em;animation:fadeup .5s both}
.eyebrow span{color:var(--sub);font-weight:500;letter-spacing:.08em;margin-left:10px}
@keyframes fadeup{0%{opacity:0;transform:translateY(16px)}100%{opacity:1;transform:none}}
.card{background:var(--card);border:1px solid var(--line);border-radius:26px;box-shadow:0 24px 60px rgba(20,40,90,.10)}
.tag{display:inline-block;font-size:22px;font-weight:700;letter-spacing:.12em;color:var(--blue);background:var(--pale);border-radius:999px;padding:6px 16px}
.mono{font-variant-numeric:tabular-nums;letter-spacing:.04em}
.tt,.sect,.eyebrow,.rl,.tagline,.cta,.warn,.wcard .tx,.rt,.chip .ck,.nv,.hl-big,.brand{white-space:nowrap}
"""
for _k, _v in C.items():
    BASE_CSS = BASE_CSS.replace("%(" + _k + ")s", _v)


def shell(body, css, js, D, p0, p1, sc, beats, B, source, sect, first, bg='white', prev_bg='white'):
    # 画像アニメーションの密度（density）：1 が従来。2 以上で、強調語にマーカーを引く。
    # 動くピクト（picto.py）は nodes / list / term の icon で出す。30秒版（2026-11-12〜）は 2.5
    dens = float(sc.get("density", 1))
    dense_js = ""
    css = css + PICTO_CSS
    if dens > 1 and not sc.get("_nodense"):
        # 2026-11-13：場面全体が揺れる動き（左右の振り・文ごとの寄りのパンチ）は「振動して見える」のでやめた。
        # カメラは従来のゆっくりした寄り（.cam の cam アニメーション）だけ。動きは場面の中の絵と言葉で出す
        css = css + """
.kin .ph.acc{background:linear-gradient(rgba(255,181,71,.42),rgba(255,181,71,.42)) 0 92%/0% 26% no-repeat;animation:ph .55s cubic-bezier(.2,.8,.2,1) both,mk .95s cubic-bezier(.6,0,.2,1) both}
@keyframes mk{0%,40%{background-size:0% 26%}100%{background-size:100% 26%}}
"""
    caps = []
    beats = [] if (sc.get('_nocap')) else beats
    for i, b in enumerate(beats):
        cap = b.get("cap") or b["say"]
        if i + 1 < len(beats):
            caps.append(f'<div class="cap capout" style="animation-delay:{B[i]:.3f}s,{B[i + 1]:.3f}s">{esc(cap)}</div>')
        else:
            caps.append(f'<div class="cap capin" style="animation-delay:{B[i]:.3f}s">{esc(cap)}</div>')
    font_links = "".join(f'<link rel="stylesheet" href="file://{FONT_DIR}/{w}.css">' for w in (400, 500, 700, 900)) \
        if os.path.isdir(FONT_DIR) else ""
    sect_html = (f'<div class="sect">{esc(sect[0])}<span>{esc(sect[1])}</span></div>' if sect[0] else f'<div class="sect">{esc(sect[1])}</div>') if sect else ""
    src = f'<div id="src">出典：{esc(source)}</div>' if source else ""
    first_css = "#scene{animation:none;-webkit-mask-image:none}" if first else ""
    BGC = {"white": "#F6F8FB", "blue": "#1F5BFF", "navy": "#0B1B33", "sky": "#E3EBFF"}
    dark = bg in ("blue", "navy")
    hv = (":root{--hfg:#fff;--hnews:" + ("#0B1B33" if bg == "blue" else "#7FA2FF") + ";--hsub:rgba(255,255,255,.72);--hline:rgba(255,255,255,.28)}") if dark else ""
    name = sc.get("channel", "Quick News")
    a, _, b2 = name.partition(" ")
    libs = "".join(f'<script src="file://{LIB_DIR}/{n}"></script>' for n in ("d3-array.min.js", "d3-geo.min.js", "topojson-client.min.js", "world50m.js", "qnmorph.js"))
    return f"""<!doctype html><html lang="ja"><head><meta charset="utf-8">{font_links}{libs}<style>
{BASE_CSS}
{ILLUS_CSS}
{DIAG_CSS}

:root{{--hfg:#0B1B33;--hnews:#1F5BFF;--hsub:#5B6B82;--hline:#DCE3EE}}
@property --rv{{syntax:'<length>';inherits:false;initial-value:0px}}
#scene{{position:absolute;inset:0;animation:reveal .55s cubic-bezier(.65,0,.25,1) both;
-webkit-mask-image:radial-gradient(circle at 50% 44%,#000 var(--rv),transparent calc(var(--rv) + 90px))}}
@keyframes reveal{{from{{--rv:0px}}to{{--rv:1700px}}}}
.sbg{{position:absolute;inset:0}}
.cx{{position:absolute;inset:0;transform-origin:50% 40%;animation:cxout .26s cubic-bezier(.5,0,.75,0) forwards;animation-delay:var(--zout)}}
@keyframes cxout{{0%{{opacity:1}}100%{{opacity:0;transform:scale(.82);filter:blur(10px)}}}}
#grain{{position:absolute;inset:0;z-index:60;pointer-events:none;opacity:.07;mix-blend-mode:multiply;
background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='260' height='260'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}}
.brand{{color:var(--hfg)!important;letter-spacing:-.01em!important}}
.brand i{{font-style:normal;color:var(--hnews)}}
.tagl,.date{{color:var(--hsub)!important}}
.sect{{color:var(--hnews)!important}}.sect span{{color:var(--hsub)!important}}
.rule{{background:var(--hline)!important}}
.rule b{{background:var(--hnews)!important}}


.gl{{position:absolute;overflow:hidden;-webkit-mask-image:linear-gradient(180deg,transparent 0,#000 8%,#000 92%,transparent 100%)}}
.gl svg{{position:absolute;left:0;top:0}}
.gov{{position:absolute;inset:0}}
.gpin{{position:absolute;left:0;top:0;opacity:0}}
.gpin i{{position:absolute;left:-13px;top:-13px;width:26px;height:26px;border-radius:50%;background:var(--blue);border:5px solid #fff;box-shadow:0 4px 14px rgba(31,91,255,.45)}}
.gpin b{{position:absolute;left:-26px;top:-26px;width:52px;height:52px;border-radius:50%;border:2px solid var(--blue)}}
.gpin .lb{{position:absolute;left:30px;top:-40px;background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px 18px;white-space:nowrap;box-shadow:0 12px 30px rgba(20,40,90,.12)}}
.gpin.left .lb{{left:auto;right:30px}}
.gpin em{{display:block;font-style:normal;font-size:36px;font-weight:700;color:var(--ink);line-height:1.2}}
.gpin small{{display:block;font-size:22px;color:var(--blue);font-weight:700;margin-top:2px}}
.gchip{{position:absolute;left:0;top:0;width:64px;height:64px;margin:-32px 0 0 -32px}}
.gstage{{position:absolute;left:96px;top:26px;background:var(--blue);color:#fff;font-size:26px;font-weight:700;letter-spacing:.06em;border-radius:999px;padding:8px 22px}}

:root{{--D:{D:.3f}s;--p0:{p0 * 100:.2f}%;--p1:{p1 * 100:.2f}%;--zout:{max(0, D - 0.22):.3f}s}}
{css}
{hv}
body{{background:{BGC.get(prev_bg, prev_bg)}}}
{first_css}
</style></head><body>
<div id="scene"><div class="sbg" style="background:{BGC.get(bg, bg)}"></div>{'' if dark else '<div id="bg"><div class="glow g1"></div><div class="glow g2"></div><div class="dots"></div></div>'}<div class="cam"><div class="cx">{body}</div></div></div>
<div id="grain"></div>
<div id="frame"><div class="brand">{esc(a)} <i>{esc(b2)}</i></div><div class="tagl">{esc(sc.get("tagline", "1日1分で社会がわかる"))}</div>
<div class="date">{esc(sc.get("date_label", ""))}</div><div class="rule"><b></b></div>{sect_html}</div>
<div id="cap">{''.join(caps)}</div>{src}
<script>
window.__tick=[];
{PALT_JS}
{GLOBE_JS}
{LAYOUT_JS}
{js}
{dense_js}
window.seek=function(t){{if(!window.__pd){{window.__pd=1;__palt(document);__layout();}}document.getAnimations().forEach(a=>{{a.pause();a.currentTime=t*1000;}});for(const f of __tick)f(t);}};
</script></body></html>"""



LAYOUT_JS = r"""
/* 余白の自動調整（毎回の書き出しで必ず実行）
   ・上部の見出しと本文（図・表・カード）の間を最低 GAP_T あける
   ・本文の下端と字幕の間を最低 GAP_B あける
   ・本文が帯に収まるときは、空きの1/3を上に置いて、見出しと字幕の間でバランスよく配置する
   ・守れないときは console に [layout] で警告を出す（書き出し側が表示する） */
window.__layout=function(){
 const cx=document.querySelector('.cx');if(!cx||document.getElementById('qnm'))return;
 const GAP_T=72,GAP_B=56,CAP=1318-164;   // .cam が 164px 下げているので .cx 座標に直す（ヘッダーを SNS の上部表示から逃がした分 +120）
 const kids=[...cx.children].filter(e=>getComputedStyle(e).position==='absolute');
 // 位置は計算済みの top、高さは要素の高さ（SVG は height 属性）。data-pad は上下の透明な余白（地球儀のフェードなど）
 kids.forEach(e=>{if(e.dataset.t0==null)e.dataset.t0=parseFloat(getComputedStyle(e).top)||0;else e.style.top=e.dataset.t0+'px';
   e.dataset.h=e.offsetHeight!=null?e.offsetHeight:(parseFloat(e.getAttribute('height'))||parseFloat(getComputedStyle(e).height)||0);});
 const pad=e=>+(e.dataset.pad||0),top=e=>+e.dataset.t0+pad(e),bot=e=>+e.dataset.t0+(+e.dataset.h)-pad(e);
 const titles=kids.filter(e=>e.classList.contains('kin')&&top(e)<620);
 if(!titles.length)return;
 const tb=Math.max(...titles.map(bot)),tt=Math.min(...titles.map(top));
 const head=kids.filter(e=>top(e)<tb&&top(e)>=tt-120&&!e.classList.contains('gl'));
 const body=kids.filter(e=>!head.includes(e)&&!titles.includes(e)&&bot(e)>tb+40&&top(e)<CAP);
 if(!body.length)return;
 const hb=Math.max(...head.map(bot)),bt=Math.min(...body.map(top)),bb=Math.max(...body.map(bot));
 const h=bb-bt,band0=hb+GAP_T,band1=CAP-GAP_B,free=band1-band0-h;
 let want=free>=0?band0+free/3:band0;
 const d=Math.round(want-bt);
 body.forEach(e=>{e.style.top=(+e.dataset.t0+d)+'px';});
 if(free<0)console.warn('[layout] 本文が見出しと字幕の間に収まりません（'+Math.round(-free)+'px 超過）');
 window.__layoutInfo={titleBottom:hb,bodyTop:bt+d,bodyBottom:bb+d,captionTop:CAP,shift:d};
};
"""


GLOBE_JS = r'''
window.QNGlobe=function(host,o){
 const ns='http://www.w3.org/2000/svg',W=o.w,H=o.h;
 const svg=document.createElementNS(ns,'svg');svg.setAttribute('width',W);svg.setAttribute('height',H);host.appendChild(svg);
 const mk=(tag,a,par)=>{const e=document.createElementNS(ns,tag);for(const k in a)e.setAttribute(k,a[k]);(par||svg).appendChild(e);return e;};
 const feats=topojson.feature(WORLD,WORLD.objects.countries).features;
 const proj=d3.geoOrthographic().translate([W/2,H/2]).clipAngle(90).precision(0.5);
 const path=d3.geoPath(proj);
 const sph=mk('path',{fill:'#EEF3FB',stroke:'#C9D4E6','stroke-width':1.5});
 const gr=mk('path',{fill:'none',stroke:'#DCE4F0','stroke-width':1});
 const g=mk('g',{});
 const land=feats.map(f=>mk('path',{fill:'#C6D2E4',stroke:'#FFFFFF','stroke-width':0.9},g));
 const hl=(o.hl||[]).map(h=>({h,f:feats.find(f=>String(f.id)===String(h.id)),el:mk('path',{fill:'#1F5BFF','fill-opacity':0,stroke:'#1F5BFF','stroke-opacity':0,'stroke-width':1.4},g)}));
 const arcEl=mk('path',{fill:'none',stroke:'#1F5BFF','stroke-width':5,'stroke-linecap':'round'});
 const grat=d3.geoGraticule10();
 const ov=document.createElement('div');ov.className='gov';host.appendChild(ov);
 const pins=(o.pins||[]).map(p=>{const d=document.createElement('div');d.className='gpin';
   d.innerHTML='<b></b><i></i><div class="lb"><em>'+p.label+'</em>'+(p.sub?'<small>'+p.sub+'</small>':'')+'</div>';if(p.left)d.classList.add('left');ov.appendChild(d);return {p,d};});
 let chip=null;if(o.chip){chip=document.createElement('div');chip.className='gchip';chip.innerHTML=o.chip;ov.appendChild(chip);}
 let stage=null;if(o.stages){stage=document.createElement('div');stage.className='gstage';ov.appendChild(stage);}
 const ease=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
 const K=o.keys;
 function view(t){if(t<=K[0].t)return K[0];for(let i=1;i<K.length;i++){const a=K[i-1],b=K[i];if(t<=b.t){const u=ease((t-a.t)/(b.t-a.t));
   const ip=d3.geoInterpolate([a.lon,a.lat],[b.lon,b.lat])(u);const sc=Math.exp(Math.log(a.scale)+(Math.log(b.scale)-Math.log(a.scale))*u);
   return {lon:ip[0],lat:ip[1],scale:sc};}}return K[K.length-1];}
 const arcI=o.arc?d3.geoInterpolate(o.arc.from,o.arc.to):null;
 const t0=o.start||0;
 return function(T){
  const t=T-t0; if(o.until!==undefined&&(T<t0-0.4||T>o.until+0.4))return;
  const v=view(t);proj.rotate([-v.lon,-v.lat]).scale(v.scale);
  sph.setAttribute('d',path({type:'Sphere'})||'');gr.setAttribute('d',path(grat)||'');
  const c=[v.lon,v.lat];const lim=Math.min(Math.PI/2,Math.asin(Math.min(1,Math.hypot(W,H)/2/v.scale)))+0.35;
  land.forEach((e,i)=>{const ce=d3.geoCentroid(feats[i]);const far=d3.geoDistance(ce,c)>lim+0.5;e.setAttribute('d',far?'':(path(feats[i])||''));});
  hl.forEach(x=>{if(!x.f)return;const p=Math.min(1,Math.max(0,(t-x.h.t)/0.5));x.el.setAttribute('d',path(x.f)||'');x.el.setAttribute('fill-opacity',(x.h.op||0.88)*p);x.el.setAttribute('stroke-opacity',p);});
  if(arcI){const p=Math.min(1,Math.max(0,(t-o.arc.t0)/(o.arc.t1-o.arc.t0)));const pe=ease(p);const pts=[];for(let k=0;k<=80;k++)pts.push(arcI(pe*k/80));
   arcEl.setAttribute('d',p>0?(path({type:'LineString',coordinates:pts})||''):'');
   if(chip){const tip=arcI(pe);const xy=proj(tip);const vis=d3.geoDistance(tip,c)<Math.PI/2&&p>0&&p<1;chip.style.opacity=vis?1:0;if(xy)chip.style.transform='translate('+xy[0]+'px,'+xy[1]+'px)';}}
  pins.forEach(({p,d})=>{const xy=proj(p.at);const vis=d3.geoDistance(p.at,c)<Math.PI/2*0.97&&t>=p.t;const k=Math.min(1,Math.max(0,(t-p.t)/0.3));
   d.style.opacity=vis?k:0;if(xy)d.style.transform='translate('+xy[0]+'px,'+xy[1]+'px)';const r=((t-p.t)%1.1+1.1)%1.1;const b=d.querySelector('b');b.style.transform='scale('+(1+r*1.8)+')';b.style.opacity=Math.max(0,1-r/1.1);});
  if(stage){let cur='';o.stages.forEach(s=>{if(t>=s.t)cur=s.label;});stage.textContent=cur;stage.style.opacity=cur?1:0;}
 };
};
'''

PALT_JS = r'''(function(){
 const RE=/[、-〃〈-】〔-〟ぁ-ゖ゛-ゟァ-ヺー-ヿ！（），．：？｜]/;
 const cv=document.createElement('canvas').getContext('2d');
 window.__palt=function(root){
  root.querySelectorAll('.ph,.tt,.dt,.rres,.fdt,.gpin em,.gpin small,.gstage,.wcard .tx,.nv,.rl,.rt,.hl-big,.hl-sub,.df,.qch,.cl,.chip .ck,.eyebrow,.sect,.tagline,.cta,.warn,.ms').forEach(el=>{
   if(el.dataset.palt)return; el.dataset.palt=1;
   const cs=getComputedStyle(el); cv.font=cs.fontWeight+' '+cs.fontSize+' '+cs.fontFamily;
   const fs=parseFloat(cs.fontSize), pad=fs*0.03;
   const walk=n=>{ if(n.nodeType===3){ const t=n.textContent; if(!RE.test(t))return; const f=document.createDocumentFragment();
      for(const ch of t){ if(RE.test(ch)){ const m=cv.measureText(ch); const l=Math.max(0,-m.actualBoundingBoxLeft-pad), r=Math.max(0,m.width-m.actualBoundingBoxRight-pad);
          const sp=document.createElement('span'); sp.textContent=ch; sp.style.marginLeft=(-l*0.9).toFixed(1)+'px'; sp.style.marginRight=(-r*0.9).toFixed(1)+'px'; f.appendChild(sp);}
        else f.appendChild(document.createTextNode(ch)); }
      n.replaceWith(f);} else if(n.nodeType===1 && n.tagName!=='SCRIPT') [...n.childNodes].forEach(walk); };
   walk(el); });
 };
})();
'''


# ───────── イメージアニメーション（線画・控えめ） ─────────
# 白×青の画面を邪魔しないよう、細い線で描き、線が引かれていく動きと、ゆっくりした反復だけを使う。

ILLUS_CSS = """
.il{position:absolute;left:96px;right:150px;pointer-events:none}
.il svg{display:block;overflow:visible}
.il .ln,.il .lnb{fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:ildraw .9s cubic-bezier(.4,0,.2,1) forwards}
.il .ln{stroke:var(--ink);stroke-width:3}
.il .lnb{stroke:var(--blue);stroke-width:3}
.il .thin{stroke-width:2;opacity:.45}
@keyframes ildraw{to{stroke-dashoffset:0}}
.il .pop{transform-box:fill-box;transform-origin:50% 50%;animation:ilpop .45s cubic-bezier(.2,1.5,.4,1) both}
@keyframes ilpop{0%{transform:scale(0);opacity:0}100%{transform:none;opacity:1}}
.il .fade{animation:ilfade .5s both}
@keyframes ilfade{0%{opacity:0}100%{opacity:1}}
.il text{font-family:inherit;font-weight:700;fill:var(--ink)}
.il .lab{font-size:26px;fill:var(--sub);font-weight:500}
.il .labb{font-size:26px;fill:var(--blue);font-weight:700}
"""


def _d(t):
    return f"animation-delay:{t:.2f}s"


def il_roundtable(t0=0.6, members=("日", "米", "英", "仏", "独", "伊", "加"), extra="EU"):
    """会議のテーブルを上から見た線画。席が順に埋まり、中央に向かって線が集まる."""
    import math
    cx, cy, rx, ry = 417, 150, 200, 66
    seats = list(members) + ([extra] if extra else [])
    n = len(seats)
    parts = [f'<ellipse class="ln" style="{_d(t0)}" cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" pathLength="1"/>',
             f'<ellipse class="ln thin" style="{_d(t0 + .1)}" cx="{cx}" cy="{cy + 10}" rx="{rx}" ry="{ry}" pathLength="1"/>']
    for i, m in enumerate(seats):
        a = -math.pi / 2 + 2 * math.pi * i / n
        x, y = cx + 300 * math.cos(a), cy + 112 * math.sin(a)
        t = t0 + 0.5 + i * 0.09
        small = m == extra
        r = 24 if small else 30
        parts.append(f'<line class="lnb thin" style="{_d(t + 0.6)}" x1="{x:.0f}" y1="{y:.0f}" x2="{cx}" y2="{cy}" pathLength="1"/>')
        parts.append(f'<g class="pop" style="{_d(t)}"><circle cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="#fff" stroke="{"#5B6B82" if small else "#1F5BFF"}" stroke-width="3"/>'
                     f'<text x="{x:.0f}" y="{y + (8 if small else 10):.0f}" text-anchor="middle" style="font-size:{20 if small else 26}px;fill:{"#5B6B82" if small else "#0B1B33"}">{m}</text></g>')
    parts.append(f'<text class="fade" style="{_d(t0 + 1.4)};font-size:30px;fill:#1F5BFF" x="{cx}" y="{cy + 10}" text-anchor="middle">G7</text>')
    return f'<svg width="834" height="300" viewBox="0 0 834 300">{"".join(parts)}</svg>'


def il_route(t0=0.5, left=("米国", "半導体株 上昇"), right=("日本", "関連銘柄に 買い")):
    """2点を結ぶ弧の上を、半導体チップの線画が渡っていく."""
    arc = "M120,250 C260,40 560,30 714,236"
    dots = "".join(f'<circle class="fade" style="{_d(t0 + (i % 9) * .03)}" cx="{40 + i * 22}" cy="{252 + 10 * ((i * 7) % 3)}" r="2" fill="#C9D5EA"/>' for i in range(35))
    chip = ('<g class="chip"><rect x="-22" y="-22" width="44" height="44" rx="6" fill="#fff" stroke="#1F5BFF" stroke-width="3"/>'
            '<rect x="-10" y="-10" width="20" height="20" rx="3" fill="#E8EFFF" stroke="#1F5BFF" stroke-width="2"/>'
            + "".join(f'<line x1="{-14 + k * 9}" y1="-30" x2="{-14 + k * 9}" y2="-22" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/>'
                      f'<line x1="{-14 + k * 9}" y1="22" x2="{-14 + k * 9}" y2="30" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/>' for k in range(4))
            + '</g>')
    svg = (f'<svg width="834" height="340" viewBox="0 0 834 340">{dots}'
           f'<path class="lnb thin" style="{_d(t0)};stroke-dasharray:6 10;stroke-dashoffset:0;animation:none;opacity:.5" d="{arc}"/>'
           f'<path class="lnb" style="{_d(t0 + .2)};animation-duration:1.6s" d="{arc}" pathLength="1"/>'
           f'<g class="pop" style="{_d(t0)}"><circle cx="120" cy="250" r="12" fill="#1F5BFF"/></g>'
           f'<g class="pop" style="{_d(t0 + 1.7)}"><circle cx="714" cy="236" r="12" fill="#1F5BFF"/><circle cx="714" cy="236" r="26" fill="none" stroke="#1F5BFF" stroke-width="2" opacity=".35"/></g>'
           f'<text class="fade" style="{_d(t0)};font-size:34px" x="120" y="306" text-anchor="middle">{left[0]}</text>'
           f'<text class="fade lab" style="{_d(t0 + .1)}" x="120" y="340" text-anchor="middle">{left[1]}</text>'
           f'<text class="fade" style="{_d(t0 + 1.7)};font-size:34px" x="714" y="292" text-anchor="middle">{right[0]}</text>'
           f'<text class="fade labb" style="{_d(t0 + 1.8)}" x="714" y="326" text-anchor="middle">{right[1]}</text>'
           '</svg><div class="chipw" style="' + _d(t0 + .2) + '"><svg width="72" height="72" viewBox="-36 -36 72 72">' + chip + '</svg></div>')
    css = ("""
.chipw{position:absolute;left:0;top:0;width:72px;height:72px;margin:-36px 0 0 -36px;offset-path:path('%s');offset-rotate:0deg;
offset-distance:0%%;animation:chipmove 1.6s cubic-bezier(.5,0,.3,1) both}
@keyframes chipmove{0%%{offset-distance:0%%;opacity:0}8%%{opacity:1}92%%{opacity:1}100%%{offset-distance:100%%;opacity:0}}
""" % arc)
    return svg, css


def il_breach(t0=0.5):
    """データベースの線画。鍵が外れ、個人情報のカードが少しずつ外へ出ていく."""
    db = (f'<ellipse class="ln" style="{_d(t0)}" cx="150" cy="60" rx="90" ry="26" pathLength="1"/>'
          f'<path class="ln" style="{_d(t0 + .1)}" d="M60,60 L60,190 A90,26 0 0 0 240,190 L240,60" pathLength="1"/>'
          f'<path class="ln thin" style="{_d(t0 + .2)}" d="M60,103 A90,26 0 0 0 240,103" pathLength="1"/>'
          f'<path class="ln thin" style="{_d(t0 + .25)}" d="M60,146 A90,26 0 0 0 240,146" pathLength="1"/>')
    lock = (f'<g class="pop" style="{_d(t0 + .5)}"><rect x="210" y="130" width="70" height="56" rx="10" fill="#fff" stroke="#1F5BFF" stroke-width="3"/>'
            f'<circle cx="245" cy="154" r="6" fill="#1F5BFF"/><line x1="245" y1="158" x2="245" y2="172" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/></g>'
            f'<path class="shackle" style="{_d(t0 + .5)}" d="M224,130 L224,112 A21,21 0 0 1 266,112 L266,130" fill="none" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/>')
    cards = ""
    for i in range(5):
        t = t0 + 1.2 + i * 0.28
        y = 95
        cards += (f'<g class="idc" style="{_d(t)};--tx:{140 + i * 70}px;--ty:{[-20, 30, -35, 20, -10][i]}px"><g transform="translate(250 {y})">'
                  f'<rect width="96" height="62" rx="9" fill="#fff" stroke="#5B6B82" stroke-width="2.5"/>'
                  f'<circle cx="24" cy="26" r="9" fill="none" stroke="#5B6B82" stroke-width="2.5"/><path d="M12,48 Q24,36 36,48" fill="none" stroke="#5B6B82" stroke-width="2.5" stroke-linecap="round"/>'
                  f'<line x1="48" y1="22" x2="82" y2="22" stroke="#C3CCDA" stroke-width="4" stroke-linecap="round"/>'
                  f'<line x1="48" y1="36" x2="76" y2="36" stroke="#C3CCDA" stroke-width="4" stroke-linecap="round"/></g></g>')
    svg = f'<svg width="834" height="250" viewBox="0 0 834 250">{db}{cards}{lock}</svg>'
    css = """
.shackle{animation:unlock .5s cubic-bezier(.3,1.4,.5,1) forwards;transform-box:fill-box;transform-origin:100% 100%}
@keyframes unlock{0%{transform:none}100%{transform:translateY(-12px) rotate(28deg)}}
.idc{opacity:0;animation:idout 2.4s cubic-bezier(.3,.6,.3,1) forwards}
@keyframes idout{0%{opacity:0;transform:translate(0,0)}15%{opacity:1}100%{opacity:.8;transform:translate(var(--tx),var(--ty))}}
"""
    return svg, css


def icon_svg(kind, t):
    """要約カードの右上に置く小さな線アイコン（強調されたときに線が引かれる）."""
    if kind == "globe":
        body = ('<circle class="lnb" cx="32" cy="32" r="26" pathLength="1"/><ellipse class="lnb" cx="32" cy="32" rx="11" ry="26" pathLength="1"/>'
                '<path class="lnb" d="M7,24 H57 M7,40 H57" pathLength="1"/>')
    elif kind == "chart":
        body = ('<path class="lnb" d="M8,56 H58" pathLength="1"/><path class="lnb" d="M10,46 L24,34 L34,40 L54,14" pathLength="1"/>'
                '<path class="lnb" d="M44,14 H54 V24" pathLength="1"/>')
    else:  # lock
        body = ('<rect class="lnb" x="12" y="28" width="40" height="30" rx="6" pathLength="1"/>'
                '<path class="lnb" d="M20,28 V20 A12,12 0 0 1 44,20 V28" pathLength="1"/><path class="lnb" d="M32,38 V48" pathLength="1"/>')
    return f'<svg class="ic" width="64" height="64" viewBox="0 0 64 64" style="--t:{t:.2f}s">{body}</svg>'


# ───────── テンプレート ─────────
# 各テンプレートは (s, B, D) を受け取り (body, css, js) を返す。B=各ナレーションの開始秒、D=シーン長。


def t_hook_q(s, B, D):
    """冒頭フック：質問カードに文字がタイプされ、答えの見出しが出る（1フレーム目から文字が見える）."""
    q = s["question"]
    js = f"""
(function(){{const q={json.dumps(q)};
__tick.push(t=>{{const n=Math.max(3,Math.min(q.length,Math.floor((t+0.15)/0.07)));
document.querySelectorAll('#qtext .qc').forEach((c,i)=>c.style.display=i<n?'inline':'none');
document.getElementById('caret').style.opacity=(Math.floor(t*2.4)%2===0||n<q.length)?1:0;}});}})();"""
    t_done = 0.07 * len(q)
    qspans = "".join('<span class="qc qch">' + esc(ch) + '</span>' for ch in q)
    body = (f'<div class="qwm">？</div><div class="eyebrow" style="top:420px;animation:none">{esc(s.get("label", "面接でよく聞かれる質問"))}</div>'
            f'<div class="qcard card"><div class="who"><span class="dot"></span>{esc(s.get("who", "面接官"))}</div>'
            f'<div class="qline"><span id="qtext">{qspans}</span><span id="caret">｜</span></div></div>'
            + kin(s["headline"], t_done + 0.25, "", 0.12, "top:860px;font-size:92px")
            + (f'<div class="hsub" style="animation-delay:{t_done + 0.7:.2f}s">{esc(s["sub"])}</div>' if s.get("sub") else ""))
    css = """
.qcard{position:absolute;left:96px;right:150px;top:480px;padding:40px 44px 46px}
.who{font-size:26px;color:var(--sub);letter-spacing:.08em;display:flex;align-items:center;gap:12px;margin-bottom:18px}
.who .dot{width:14px;height:14px;border-radius:50%;background:var(--blue);box-shadow:0 0 0 6px var(--pale)}
.qline{font-size:66px;font-weight:700;line-height:1.35;letter-spacing:-.03em;color:var(--ink)}
.qwm{position:absolute;right:110px;top:700px;font-size:640px;font-weight:900;line-height:1;color:#E6EDFB}
#caret{color:var(--blue);font-weight:400;margin-left:2px}
.hsub{position:absolute;left:96px;right:150px;top:1110px;font-size:34px;color:var(--sub);letter-spacing:.04em;animation:fadeup .5s both}
"""
    return body, css, js



def t_summary(s, B, D):
    """冒頭の要約：3本の見出しが1フレーム目から並び、読み上げに合わせて1本ずつ強調され、要点が出る."""
    items = s["items"]
    n = len(items)
    starts = B[len(B) - n:] if len(B) >= n else [0.6 + i * (D - 0.8) / n for i in range(n)]
    cards = []
    for i, it in enumerate(items):
        t = starts[i]
        t_off = starts[i + 1] if i + 1 < n else 999
        cards.append(
            f'<div class="sc card" style="top:{462 + i * 320}px">'
            f'<b class="bar" style="animation-delay:{t:.2f}s,{t_off:.2f}s"></b>'
            + icon_svg(it.get("icon", "globe"), t) +
            f'<div class="hd"><span class="no mono">{i + 1:02d}</span><span class="tag">{esc(it["tag"])}</span></div>'
            f'<div class="tt" style="animation-delay:{t:.2f}s">{esc(it["title"])}</div>'
            f'<div class="dt" style="animation-delay:{t + 0.15:.2f}s">{esc(it["detail"])}</div></div>')
    body = kin(s.get("title", "今日の *3本*"), -1.0, "", 0.0, "top:318px;font-size:96px") + "".join(cards)
    css = """
.sc{position:absolute;left:96px;right:150px;height:290px;padding:38px 40px 34px 46px;overflow:hidden}
.sc .ic{position:absolute;right:34px;top:30px;overflow:visible}
.sc .ic .lnb{fill:none;stroke:var(--blue);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:ildraw .9s var(--t) cubic-bezier(.4,0,.2,1) forwards}
.sc .bar{position:absolute;left:0;top:0;bottom:0;width:8px;background:var(--blue);opacity:0;animation:bon .25s forwards, boff .25s forwards}
@keyframes bon{to{opacity:1}}
@keyframes boff{to{opacity:0}}
.sc .hd{display:flex;align-items:center;gap:16px;margin-bottom:12px}
.sc .no{font-size:30px;font-weight:700;color:var(--blue)}
.sc .tt{font-size:56px;font-weight:700;letter-spacing:-.02em;line-height:1.3;color:#A3AEBF;white-space:nowrap;animation:ink .3s forwards}
@keyframes ink{to{color:var(--ink)}}
.sc .dt{font-size:32px;line-height:1.55;color:var(--sub);margin-top:12px;opacity:0;animation:fadeup .45s both}
"""
    return body, css, ""

def t_wall(s, B, D):
    """浮遊する見出しカード → 整列（参考：浮かぶUIカード）."""
    items = s["items"]
    tops = [520, 700, 880]
    scat = [(-120, -40, -9), (160, 60, 7), (-60, 120, -5)]
    cards = []
    for i, it in enumerate(items):
        dx, dy, r = scat[i % 3]
        cards.append(f'<div class="wcard card" style="top:{tops[i]}px;--dx:{dx}px;--dy:{dy}px;--r:{r}deg;animation-delay:{0.05 + i * 0.12:.2f}s,{0.9 + i * 0.08:.2f}s">'
                     f'<span class="no mono">{i + 1:02d}</span><span class="tag">{esc(it["tag"])}</span><span class="tx">{esc(it["text"])}</span></div>')
    body = kin(s.get("title", "今日の *3本*"), 0.1, "", 0.12, "top:330px;font-size:104px") + "".join(cards)
    css = """
.wcard{position:absolute;left:96px;right:150px;height:150px;display:flex;align-items:center;gap:22px;padding:0 36px;
animation:wfloat .6s cubic-bezier(.2,.8,.2,1) both, walign .7s cubic-bezier(.6,0,.2,1) both}
@keyframes wfloat{0%{opacity:0;transform:translate(calc(var(--dx)*1.6),calc(var(--dy) + 160px)) rotate(calc(var(--r)*1.5)) scale(.9)}100%{opacity:1;transform:translate(var(--dx),var(--dy)) rotate(var(--r))}}
@keyframes walign{0%{transform:translate(var(--dx),var(--dy)) rotate(var(--r))}100%{transform:none}}
.wcard .no{font-size:30px;color:var(--blue);font-weight:700;width:46px}
.wcard .tx{font-size:44px;font-weight:700;white-space:nowrap}
"""
    return body, css, ""


def t_stat(s, B, D):
    """巨大数字（数字がスクランブルして確定）＋小さな説明＋スタッツチップ（参考：4.8x／$166,043）."""
    num = float(s["number"])
    dec = int(s.get("decimals", 0))
    t0, dur = 0.45, 1.1
    js = f"""
(function(){{const el=document.getElementById('num');const target={num};const dec={dec};
const fmt=v=>v.toLocaleString('en-US',{{minimumFractionDigits:dec,maximumFractionDigits:dec}});
const final=fmt(target);
__tick.push(t=>{{const p=Math.min(1,Math.max(0,(t-{t0})/{dur}));
 if(p>=1){{el.textContent=final;return;}}
 const e=1-Math.pow(1-p,3);const cur=fmt(target*e);const keep=Math.floor(cur.length*p);let out='';
 for(let i=0;i<cur.length;i++){{const c=cur[i];out+=(/[0-9]/.test(c)&&i>=keep)?String(Math.floor((Math.sin(t*97+i*13)+1)*4.99)):c;}}
 el.textContent=out;}});}})();"""
    chips = ""
    for i, ch in enumerate(s.get("chips", [])):
        chips += (f'<div class="chip card" style="animation-delay:{1.5 + i * 0.15:.2f}s"><div class="cv mono">{esc(ch["value"])}</div>'
                  f'<div class="ck">{esc(ch["label"])}</div></div>')
    trend = ""
    if s.get("trend") in ("up", "down"):
        d = "M0,300 C200,290 300,250 420,200 S640,90 780,40" if s["trend"] == "up" else "M0,40 C200,50 300,90 420,140 S640,250 780,300"
        trend = (f'<svg class="trend" width="834" height="340" viewBox="0 0 834 340"><path class="tl" d="{d}" pathLength="1"/>'
                 f'<circle class="td" r="10" cx="780" cy="{40 if s["trend"] == "up" else 300}"/></svg>')
    body = (f'<div class="eyebrow" style="top:380px">{esc(s.get("eyebrow", ""))}<span>{esc(s.get("eyebrow_sub", ""))}</span></div>' + trend +
            f'<div class="statbox"><span class="pre">{esc(s.get("prefix", ""))}</span><span id="num" class="mono">0</span>'
            f'<span class="unit">{esc(s.get("unit", ""))}</span></div>'
            f'<div class="statcap">{esc(s.get("caption", ""))}</div><div class="chips">{chips}</div>')
    css = """
.trend{position:absolute;left:96px;top:470px;opacity:.45}
.tl{fill:none;stroke:var(--blue2);stroke-width:5;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.3s .3s cubic-bezier(.4,0,.2,1) forwards}
@keyframes draw{to{stroke-dashoffset:0}}
.td{fill:var(--blue);filter:drop-shadow(0 0 12px rgba(31,91,255,.8));opacity:0;animation:fadein .2s 1.55s forwards}
@keyframes fadein{to{opacity:1}}
.statbox{position:absolute;left:96px;right:150px;top:640px;display:flex;align-items:baseline;gap:10px;color:var(--blue);animation:fadeup .4s .3s both}
.statbox .pre{font-size:56px;font-weight:700;color:var(--ink);margin-right:8px}
#num{font-size:200px;font-weight:900;letter-spacing:-.03em;line-height:1}
.statbox .unit{font-size:72px;font-weight:700}
.statcap{position:absolute;left:100px;top:900px;font-size:28px;color:var(--sub);letter-spacing:.12em;animation:fadeup .5s .9s both}
.chips{position:absolute;left:96px;right:150px;top:990px;display:flex;gap:20px}
.chip{flex:1;padding:26px 30px;animation:fadeup .5s both}
.chip .cv{font-size:52px;font-weight:900;color:var(--ink);letter-spacing:-.01em}
.chip .ck{font-size:24px;color:var(--sub);margin-top:6px;letter-spacing:.06em}
"""
    return body, css, js


def t_nodes(s, B, D):
    """ノード図：原因 → 結果を線でつなぐ（参考：ノードが線でつながる図）."""
    nodes = s["nodes"]
    n = len(nodes)
    span = max(0.5, (D - 1.0) / n)
    top0, gap = 470, 205
    parts = [kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px")]
    # ナレーションの区切りに合わせて1つずつ出す（最初の文は前置きとみなす）
    if len(B) >= n:
        ts = [max(0.3, B[len(B) - n + i] + 0.05) for i in range(n)]
    elif len(B) >= 2:
        ts = [B[i + 1] if i + 1 < len(B) else B[-1] + 0.45 * (D - B[-1]) * (i + 2 - len(B)) for i in range(n)]
    else:
        ts = [0.3 + i * span for i in range(n)]
    for i, nd in enumerate(nodes):
        t = ts[i]
        y = top0 + i * gap
        last = i == n - 1
        ic = picto(nd.get("icon", ""), 72, t + 0.2, "#fff" if last else "var(--blue)", 2.8)
        ic = f'<div class="pgc npg" style="--t:{t + 0.08:.2f}s">{ic}</div>' if ic else ""
        parts.append(f'<div class="node card{" last" if last else ""}{" hasic" if ic else ""}" style="top:{y}px;animation-delay:{t:.2f}s">'
                     f'<div class="nk">{esc(nd["key"])}</div><div class="nv">{esc(nd["value"])}</div>{ic}</div>')
        if not last:
            parts.append(f'<svg class="abs" style="left:150px;top:{y + 150}px" width="80" height="{gap - 150}">'
                         f'<path class="ln" style="animation-delay:{(t + ts[i + 1]) / 2:.2f}s" d="M20,0 C20,30 60,{gap - 190} 60,{gap - 150}" pathLength="1"/></svg>')
    css = """
.node{position:absolute;left:96px;right:150px;height:150px;padding:24px 36px;display:flex;flex-direction:column;justify-content:center;animation:fadeup .5s both}
.node .nk{font-size:24px;color:var(--blue);font-weight:700;letter-spacing:.14em}
.node .nv{font-size:44px;font-weight:700;margin-top:4px}
.node.last{background:var(--blue);border-color:var(--blue)}
.node.last .nk{color:#CFDBFF}.node.last .nv{color:#fff}
.node .npg{position:absolute;right:22px;top:17px;width:116px;height:116px}.node.last .pgc{background:rgba(255,255,255,.16)}.node.hasic{padding-right:160px}
.ln{fill:none;stroke:var(--blue);stroke-width:4;stroke-dasharray:1;stroke-dashoffset:1;animation:draw .5s ease-out forwards}
@keyframes draw{to{stroke-dashoffset:0}}
"""
    return "".join(parts), css, ""


def t_headline(s, B, D):
    """大見出し（左揃え、2行目が青）。glitch: true で青い語に一瞬のグリッチ."""
    g = "glitch" if s.get("glitch") else ""
    il, il_css = "", ""
    if s.get("illus") == "roundtable":
        il = f'<div class="il" style="top:{s.get("illus_top", 950)}px">{il_roundtable(1.0)}</div>'
    elif s.get("illus") == "breach":
        sv, il_css = il_breach(1.0)
        il = f'<div class="il" style="top:{s.get("illus_top", 1015)}px">{sv}</div>'
    sub_top, big_top = (800, 870) if il else (790, 920)
    body = (f'<div class="eyebrow" style="top:420px">{esc(s.get("eyebrow", ""))}<span>{esc(s.get("eyebrow_sub", ""))}</span></div>'
            + kin(s["text"], 0.2, g, 0.13, f"top:480px;font-size:{s.get('size', 112)}px")
            + (f'<div class="hl-sub" style="animation-delay:{0.9:.2f}s;top:{sub_top}px">{esc(s["sub"])}</div>' if s.get("sub") else "")
            + (f'<div class="hl-big mono" style="animation-delay:{1.2:.2f}s;top:{big_top}px">{esc(s["big"])}<small>{esc(s.get("big_label", ""))}</small></div>' if s.get("big") else "")
            + il)
    css = """
.hl-sub{position:absolute;left:96px;right:150px;top:790px;font-size:38px;line-height:1.6;color:var(--sub);white-space:pre-line;animation:fadeup .5s both}
.hl-big{position:absolute;left:96px;right:150px;top:920px;white-space:nowrap;font-size:112px;font-weight:900;color:var(--ink);letter-spacing:-.02em;animation:fadeup .5s both}
.hl-big small{font-size:28px;font-weight:500;color:var(--sub);letter-spacing:.1em;margin-left:18px}
.glitch .acc{animation:ph .55s cubic-bezier(.2,.8,.2,1) both, gl 2.4s .9s steps(1) infinite}
@keyframes gl{0%,86%,100%{text-shadow:none;transform:none}88%{text-shadow:-6px 0 rgba(31,91,255,.55),6px 0 rgba(255,60,90,.45);transform:translateX(4px) skewX(-8deg)}
91%{text-shadow:5px 0 rgba(31,91,255,.55),-5px 0 rgba(255,60,90,.45);transform:translateX(-3px)}94%{text-shadow:none;transform:none}}
"""
    return body, css + il_css, ""



def t_route(s, B, D):
    """2地点を結ぶ弧をチップが渡り、結果を青いカードで示す."""
    sv, css2 = il_route(0.5, tuple(s["from"]), tuple(s["to"]))
    body = (kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px")
            + f'<div class="rtbox card"><div class="il" style="left:0;right:0;top:18px">{sv}</div></div>'
            + f'<div class="rres" style="animation-delay:{max(2.1, D * 0.55):.2f}s"><div class="rk">{esc(s.get("result_key", "結果"))}</div>{esc(s["result"])}</div>')
    css = """
.rtbox{position:absolute;left:96px;right:150px;top:470px;height:400px;overflow:visible}
.rres{position:absolute;left:96px;right:150px;top:910px;background:var(--blue);color:#fff;border-radius:26px;padding:30px 40px;font-size:44px;font-weight:700;
box-shadow:0 20px 50px rgba(31,91,255,.25);animation:fadeup .5s both;white-space:nowrap}
.rres .rk{font-size:24px;letter-spacing:.06em;color:#CFDBFF;margin-bottom:4px}
"""
    return body, css + css2, ""


CHIPS = {"bolt": '<svg width="64" height="64" viewBox="-32 -32 64 64"><circle r="27" fill="#fff" stroke="#1F5BFF" stroke-width="3"/><path d="M4,-18 L-10,3 H0 L-4,18 L10,-3 H0 Z" fill="#EA6A12" stroke="#EA6A12" stroke-width="2" stroke-linejoin="round"/></svg>'}


def globe_opts(kind, s, start=0.0, span=None, w=1080, h=760):
    """地球儀の動き（キーフレーム）を種類ごとに作る。span はこの動きに使える秒数."""
    if kind == "zoom":
        tx = s.get("target", [2.35, 48.86])
        sp = span or 3.2
        f = sp / 3.2
        keys = [{"t": 0, "lon": tx[0] - 40, "lat": 18, "scale": h * 0.42},
                {"t": 0.9 * f, "lon": tx[0] + 4, "lat": tx[1] - 8, "scale": h * 0.5},
                {"t": 1.9 * f, "lon": tx[0] + 3, "lat": tx[1] - 2, "scale": h * 1.9},
                {"t": 2.9 * f, "lon": tx[0], "lat": tx[1], "scale": h * 7.5}]
        stages = [{"t": k["t"], "label": l} for k, l in zip(keys, s.get("stages", ["世界", "ヨーロッパ", "フランス", "パリ"]))]
        return dict(w=w, h=h, keys=keys, start=start, hl=[{"id": i, "t": 1.9 * f} for i in s.get("hl", ["250"])],
                    pins=[{"at": tx, "t": 2.9 * f, "label": s.get("pin", "パリ"), "sub": s.get("pin_sub", "")}],
                    stages=stages if s.get("show_stages", True) else None)
    if kind == "route":
        a, b = s["from_at"], s["to_at"]
        sp = span or 3.4
        f = sp / 3.4
        keys = [{"t": 0, "lon": a[0] - 10, "lat": a[1] + 4, "scale": h * 0.62},
                {"t": 0.7 * f, "lon": a[0] - 15, "lat": a[1] + 10, "scale": h * 0.58},
                {"t": 2.5 * f, "lon": b[0] + 12, "lat": b[1] + 10, "scale": h * 0.58},
                {"t": 3.3 * f, "lon": b[0], "lat": b[1] + 2, "scale": h * 0.8}]
        return dict(w=w, h=h, keys=keys, start=start,
                    hl=[{"id": s.get("from_id", "840"), "t": 0.2 * f, "op": 0.35}, {"id": s.get("to_id", "392"), "t": 2.4 * f}],
                    arc={"from": a, "to": b, "t0": 0.6 * f, "t1": 2.6 * f}, chip=CHIPS.get(s.get("chip")) or '<svg width="64" height="64" viewBox="-32 -32 64 64"><rect x="-20" y="-20" width="40" height="40" rx="7" fill="#fff" stroke="#1F5BFF" stroke-width="3"/><rect x="-9" y="-9" width="18" height="18" rx="3" fill="#E8EFFF" stroke="#1F5BFF" stroke-width="2"/><path d="M-12,-27V-20M-4,-27V-20M4,-27V-20M12,-27V-20M-12,20V27M-4,20V27M4,20V27M12,20V27M-27,-12H-20M-27,-4H-20M-27,4H-20M-27,12H-20M20,-12H27M20,-4H27M20,4H27M20,12H27" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/></svg>',
                    pins=[{"at": a, "t": 0.3 * f, "label": s["from"][0], "sub": s["from"][1]},
                          {"at": b, "t": 2.6 * f, "label": s["to"][0], "sub": s["to"][1], "left": True}])
    raise ValueError(kind)


def t_globe(s, B, D):
    """実際の世界地図の地球儀。mode=zoom（目的地へ寄る）/ route（2地点を弧で結ぶ）."""
    mode = s.get("mode", "zoom")
    span = min(max(2.6, D - 1.4), 3.6)
    if mode == "zoom":
        mh = s.get("map_h", 650)
        o = globe_opts("zoom", s, 0.15, span, 1080, mh)
        body = (f'<div class="gl" id="g1" style="left:0;top:300px;width:1080px;height:{mh}px"></div>'
                + kin(s["title"], s.get("title_at", 0.15 + span * 0.92), "hero" if s.get("hero") else "", 0.12,
                      "top:%dpx;font-size:%dpx;line-height:1.16;letter-spacing:-.035em" % (s.get("hero_top", 960), s.get("hero_size", 118)) if s.get("hero") else "top:992px;font-size:84px")
                + (f'<div class="hsub" style="top:{s.get("hero_top", 960) + int(s.get("hero_size", 118) * 1.16 * 2) + 26}px">{esc(s["hero_sub"])}</div>' if s.get("hero_sub") else ""))
    else:
        o = globe_opts("route", s, 0.3, span, 1080, 600)
        body = (kin(s["title"], 0.05, "", 0.12, "top:336px;font-size:84px")
                + f'<div class="gl" id="g1" data-pad="70" style="left:0;top:420px;width:1080px;height:600px"></div>'
                + (f'<div class="rres" style="animation-delay:{0.3 + span:.2f}s;top:950px"><div class="rk">{esc(s.get("result_key", "結果"))}</div>{esc(s["result"])}</div>' if s.get("result") else ""))
    js = "(function(){const tk=QNGlobe(document.getElementById('g1')," + json.dumps(o, ensure_ascii=False) + ");__tick.push(tk);})();"
    if s.get("hero"):   # 大見出しの回：字幕は出さず（見出しが同じ内容）、見出しを幅いっぱいに
        js += "(function(){const h=document.querySelector('.kin.hero');if(!h)return;let f=parseFloat(getComputedStyle(h).fontSize);const W=h.clientWidth;const over=()=>[...h.querySelectorAll('.ln,.line')].some(l=>l.scrollWidth>W)||h.scrollWidth>W;while(over()&&f>70){f-=2;h.style.fontSize=f+'px';}})();"
    css = ("#cap{display:none}" if s.get("hero") else "") + """
.hsub{position:absolute;left:96px;right:150px;font-size:40px;font-weight:700;color:var(--sub);letter-spacing:.02em;animation:fadeup .5s .25s both}
.rres{position:absolute;left:96px;right:150px;background:var(--blue);color:#fff;border-radius:26px;padding:26px 40px;font-size:44px;font-weight:700;
box-shadow:0 20px 50px rgba(31,91,255,.25);animation:fadeup .5s both;white-space:nowrap}
.rres .rk{font-size:24px;letter-spacing:.06em;color:#CFDBFF;margin-bottom:4px}
"""
    return body, css, js


def t_flash(s, B, D):
    """冒頭の要約：3本の要点が素早く切り替わる。上にストーリー風の進行バー、各本に動くビジュアル."""
    items = s["items"]
    n = len(items)
    starts = B[len(B) - n:] if len(B) >= n else [i * D / n for i in range(n)]
    ends = [starts[i + 1] for i in range(n - 1)] + [D]
    panels, js_parts = [], []
    pips = "".join(f'<div class="pip"><b style="animation-delay:{(0 if i == 0 else starts[i]):.2f}s;animation-duration:{ends[i] - (0 if i == 0 else starts[i]):.2f}s"></b></div>' for i in range(n))
    for i, it in enumerate(items):
        t0 = 0.0 if i == 0 else starts[i] - 0.08
        t1 = ends[i] - 0.1
        inn = "none" if i == 0 else f"fin .3s {t0:.2f}s cubic-bezier(.2,.8,.2,1) both"
        out = f"fout .22s {t1:.2f}s ease-in forwards" if i < n - 1 else "none"
        anim = ",".join(a for a in (inn, out) if a != "none") or "none"
        k = it.get("visual", "globe")
        vis = ""
        if k == "globe":
            o = globe_opts("zoom", it, t0, max(1.6, (t1 - t0) - 0.5), 1080, 700)
            o["until"] = t1 + 0.3
            o["stages"] = None
            vis = f'<div class="gl" id="fg{i}" style="left:0;top:300px;width:1080px;height:700px"></div>'
            js_parts.append(f"__tick.push(QNGlobe(document.getElementById('fg{i}'),{json.dumps(o, ensure_ascii=False)}));")
        elif k == "counter":
            js_parts.append(counter_js(f"fn{i}", it["number"], t0 + 0.15, 0.9, it.get("decimals", 0)))
            vis = (f'<svg class="fspark" width="834" height="380" viewBox="0 0 834 380"><path d="M0,350 C120,330 210,300 300,250 S520,120 600,110 S760,40 834,20" pathLength="1" style="animation-delay:{t0 + .05:.2f}s"/></svg>'
                   f'<div class="fnum"><span class="pre">{esc(it.get("prefix", ""))}</span><span id="fn{i}" class="mono">0</span><span class="u">{esc(it.get("unit", ""))}</span></div>'
                   f'<div class="farrow" style="animation-delay:{t0 + .9:.2f}s">▲</div>')
        elif k == "breach":
            sv, bcss = il_breach(t0 + 0.05)
            js_parts.append(counter_js(f"fn{i}", it["number"], t0 + 0.4, 0.9, it.get("decimals", 0)))
            vis = (f'<div class="il fbreach">{sv}</div><style>{bcss}</style>'
                   f'<div class="fnum small"><span class="pre">{esc(it.get("prefix", ""))}</span><span id="fn{i}" class="mono">0</span><span class="u">{esc(it.get("unit", ""))}</span></div>')
        panels.append(
            f'<div class="fp" style="animation:{anim}">{vis}'
            f'<div class="fhd"><span class="mono">{i + 1:02d}</span><span class="tag">{esc(it["tag"])}</span></div>'
            + '<div class="fbody">' + kin(it["title"], -1.0 if i == 0 else t0 + 0.1, "ftt", 0.09, "position:relative;left:0;right:0;font-size:78px")
            + f'<div class="fdt" style="animation-delay:{(-1.0 if i == 0 else t0 + 0.3):.2f}s">{esc(it.get("detail", ""))}</div></div></div>')
    body = f'<div class="pips">{pips}</div>' + "".join(panels)
    css = """
.pips{position:absolute;left:96px;right:150px;top:248px;display:flex;gap:10px;z-index:5}
.pip{flex:1;height:6px;border-radius:3px;background:#DCE3EE;overflow:hidden}
.pip b{display:block;height:100%;background:var(--blue);width:0;animation-name:pipf;animation-timing-function:linear;animation-fill-mode:both}
@keyframes pipf{from{width:0}to{width:100%}}
.fp{position:absolute;inset:0}
@keyframes fin{0%{opacity:0;transform:translateX(160px);filter:blur(8px)}100%{opacity:1;transform:none;filter:none}}
@keyframes fout{0%{opacity:1}100%{opacity:0;transform:translateX(-180px);filter:blur(8px)}}
.fhd{position:absolute;left:96px;top:290px;display:flex;align-items:center;gap:16px;z-index:3}
.fhd .mono{font-size:40px;font-weight:900;color:var(--blue)}
.rule{opacity:0}
.fbody{position:absolute;left:96px;right:150px;top:1060px}
.fdt{position:relative;margin-top:22px;font-size:38px;line-height:1.5;color:var(--sub);animation:fadeup .4s both}
.fspark{position:absolute;left:96px;top:420px;opacity:.5}
.fspark path{fill:none;stroke:var(--blue2);stroke-width:6;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;animation:ildraw 1s cubic-bezier(.4,0,.2,1) forwards}
.fnum{position:absolute;left:96px;right:150px;top:560px;display:flex;align-items:baseline;gap:8px;color:var(--blue)}
.fnum .pre{font-size:56px;font-weight:700;color:var(--ink);margin-right:6px}
.fnum .mono{font-size:190px;font-weight:900;letter-spacing:-.035em;line-height:1}
.fnum .u{font-size:70px;font-weight:700}
.fnum.small{top:780px}.fnum.small .mono{font-size:150px}
.farrow{position:absolute;right:170px;top:430px;font-size:90px;color:var(--blue);animation:ilpop .45s cubic-bezier(.2,1.5,.4,1) both}
.fbreach{top:420px}
"""
    return body, css, "".join(js_parts)


def counter_js(el_id, num, t0, dur, dec=0):
    return ("(function(){const el=document.getElementById('%s');const target=%s;const dec=%d;"
            "const fmt=v=>v.toLocaleString('en-US',{minimumFractionDigits:dec,maximumFractionDigits:dec});"
            "__tick.push(t=>{const p=Math.min(1,Math.max(0,(t-%s)/%s));if(p>=1){el.textContent=fmt(target);return;}"
            "const e=1-Math.pow(1-p,3);const cur=fmt(target*e);const keep=Math.floor(cur.length*p);let out='';"
            "for(let i=0;i<cur.length;i++){const c=cur[i];out+=(/[0-9]/.test(c)&&i>=keep)?String(Math.floor((Math.sin(t*97+i*13)+1)*4.99)):c;}"
            "el.textContent=out;});})();") % (el_id, float(num), int(dec), t0, dur)


# ───────── 解説イラスト（平面的な図形・やわらかい影・ゆっくりした反復） ─────────
# 配色はブランドの紺と青を軸に、差し色を少しだけ使う。
PAL = dict(navy="#0B1B33", navy2="#1B2E57", navy3="#24407A", blue="#1F5BFF", blue2="#3F6FFF", sky="#DCE8FF",
           sky2="#F4F8FF", teal="#2EC4B6", amber="#FFC24B", coral="#FF7A59", sand="#F3E3B5", mint="#9ADBD0", white="#FFFFFF")

FLAT_CSS = """
.ipanel{position:absolute;left:96px;right:150px;top:430px;height:700px;border-radius:36px;overflow:hidden;
box-shadow:0 30px 70px rgba(20,40,90,.16);animation:ipin .55s cubic-bezier(.2,.8,.2,1) both}
@keyframes ipin{0%{opacity:0;transform:translateY(60px) scale(.97)}100%{opacity:1;transform:none}}
.ipanel svg{position:absolute;left:0;top:0}
.f-pop{transform-box:fill-box;transform-origin:50% 100%;animation:fpop .5s cubic-bezier(.2,1.5,.4,1) both}
@keyframes fpop{0%{transform:scale(0);opacity:0}100%{transform:none;opacity:1}}
.f-rise{transform-box:fill-box;transform-origin:50% 100%;animation:frise .7s cubic-bezier(.2,.9,.3,1.1) both}
@keyframes frise{0%{transform:scaleY(0)}100%{transform:none}}
.f-fade{animation:ffade .5s both}
@keyframes ffade{0%{opacity:0}100%{opacity:1}}
.f-bob{animation:fbob 2.4s ease-in-out infinite alternate}
@keyframes fbob{from{transform:translateY(0)}to{transform:translateY(-10px)}}
.f-drift{animation:fdrift 14s linear infinite}
@keyframes fdrift{from{transform:translateX(-60px)}to{transform:translateX(60px)}}
.f-wave{animation:fwave 3s linear infinite}
@keyframes fwave{from{transform:translateX(0)}to{transform:translateX(-120px)}}
.f-blink{animation:fblink 1.1s steps(1) infinite}
@keyframes fblink{0%,100%{opacity:1}50%{opacity:.25}}
.f-glow{transform-box:fill-box;transform-origin:50% 50%;animation:fglow 1.6s ease-in-out infinite alternate}
@keyframes fglow{from{transform:scale(.9);opacity:.35}to{transform:scale(1.15);opacity:.7}}
.f-pill{animation:fpill .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes fpill{0%{opacity:0;transform:translateY(18px) scale(.9)}100%{opacity:1;transform:none}}
.f-pill rect{filter:drop-shadow(0 8px 14px rgba(11,27,51,.18))}
.f-txt{font-family:inherit;font-weight:700}
"""


def _dl(t):
    return f"animation-delay:{t:.2f}s"


def pill(x, y, text, t, fill=None, color=None, size=28, w=None, anchor="middle"):
    fill = fill or PAL["white"]
    color = color or PAL["navy"]
    w = w or int(len(text) * size * 0.98 + 44)
    x0 = x - w / 2 if anchor == "middle" else x
    return (f'<g class="f-pill" style="{_dl(t)}"><rect x="{x0:.0f}" y="{y - size * 0.95:.0f}" width="{w}" height="{size * 1.9:.0f}" rx="{size * 0.95:.0f}" fill="{fill}"/>'
            f'<text class="f-txt" x="{x0 + w / 2:.0f}" y="{y + size * 0.33:.0f}" text-anchor="middle" font-size="{size}" fill="{color}">{text}</text></g>')


def building(x, base, w, h, col, win, t, lit=()):
    """窓のある平面的なビル。右側に影の面."""
    out = [f'<g class="f-rise" style="{_dl(t)}">',
           f'<rect x="{x}" y="{base - h}" width="{w}" height="{h}" fill="{col}"/>',
           f'<rect x="{x + w * 0.62}" y="{base - h}" width="{w * 0.38}" height="{h}" fill="#000" opacity=".14"/>']
    cols = max(2, int(w // 22))
    rows = max(2, int(h // 34))
    for r in range(rows):
        for c in range(cols):
            wx = x + 8 + c * (w - 16) / cols
            wy = base - h + 14 + r * 32
            if wy > base - 20:
                continue
            on = (r * 7 + c * 3 + int(x)) % 5 in lit
            out.append(f'<rect x="{wx:.0f}" y="{wy:.0f}" width="{(w - 16) / cols - 6:.0f}" height="14" rx="2" fill="{PAL["amber"] if on else win}" opacity="{0.95 if on else 0.55}"/>')
    out.append("</g>")
    return "".join(out)


def cloud(x, y, s, t, op=0.9):
    return (f'<g class="f-drift" style="{_dl(-t)}"><g transform="translate({x} {y}) scale({s})" opacity="{op}">'
            '<circle cx="0" cy="0" r="26" fill="#fff"/><circle cx="30" cy="-12" r="34" fill="#fff"/><circle cx="66" cy="0" r="26" fill="#fff"/>'
            '<rect x="0" y="0" width="66" height="26" fill="#fff"/></g></g>')


def person(x, base, col, t, h=120, head="#F2D7C3", arm=None):
    """顔を描かない、まるい頭と丸みのある胴の人物（特定の人に似せない）."""
    bw = h * 0.42
    return (f'<g class="f-pop" style="{_dl(t)}">'
            f'<rect x="{x - bw / 2:.0f}" y="{base - h * 0.62:.0f}" width="{bw:.0f}" height="{h * 0.62:.0f}" rx="{bw / 2:.0f}" fill="{col}"/>'
            f'<rect x="{x:.0f}" y="{base - h * 0.62:.0f}" width="{bw / 2:.0f}" height="{h * 0.62:.0f}" rx="{bw / 4:.0f}" fill="#000" opacity=".12"/>'
            f'<circle cx="{x:.0f}" cy="{base - h * 0.78:.0f}" r="{h * 0.17:.0f}" fill="{head}"/>'
            f'<circle cx="{x + h * 0.06:.0f}" cy="{base - h * 0.78:.0f}" r="{h * 0.17:.0f}" fill="#000" opacity=".06"/>'
            '</g>')


def il_market(B, D):
    """経済：米国の半導体株高が、海を越えて東京の関連銘柄へ波及する."""
    P = PAL
    t1 = B[0] + 0.2 if B else 0.3
    sky = (f'<defs><linearGradient id="msky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#CFE0FF"/><stop offset="1" stop-color="{P["sky2"]}"/></linearGradient>'
           f'<linearGradient id="msea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["blue2"]}"/><stop offset="1" stop-color="#1640B8"/></linearGradient>'
           f'<radialGradient id="mglow"><stop offset="0" stop-color="{P["amber"]}" stop-opacity=".9"/><stop offset="1" stop-color="{P["amber"]}" stop-opacity="0"/></radialGradient></defs>'
           f'<rect width="834" height="700" fill="url(#msky)"/>'
           f'<circle cx="680" cy="120" r="60" fill="#fff" opacity=".7"/>'
           + cloud(120, 110, 1.0, 3) + cloud(560, 190, 0.8, 8))
    sea = (f'<rect y="470" width="834" height="230" fill="url(#msea)"/>'
           + "".join(f'<g class="f-wave" style="{_dl(-i * 0.7)}"><path d="M{-20 + i * 37},{505 + i * 34} q30,-10 60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0" fill="none" stroke="#fff" stroke-width="3" opacity=".22"/></g>' for i in range(5)))
    left = (building(40, 470, 70, 230, P["navy2"], "#5A7BC4", 0.2, (1,)) + building(118, 470, 90, 330, P["navy3"], "#6E8FD8", 0.3, (2,))
            + building(216, 470, 64, 190, P["navy2"], "#5A7BC4", 0.4, (0,)))
    chip = (f'<g class="f-pop" style="{_dl(t1)}"><circle cx="163" cy="100" r="80" fill="url(#mglow)" class="f-glow"/>'
            f'<g class="f-bob"><rect x="133" y="70" width="60" height="60" rx="10" fill="{P["amber"]}"/><rect x="148" y="85" width="30" height="30" rx="5" fill="#E09A1F"/>'
            + "".join(f'<rect x="{139 + k * 13}" y="60" width="6" height="12" rx="3" fill="{P["amber"]}"/><rect x="{139 + k * 13}" y="128" width="6" height="12" rx="3" fill="{P["amber"]}"/>' for k in range(4))
            + "</g></g>"
            f'<g class="f-pop" style="{_dl(t1 + 0.35)}"><path d="M232,120 l26,-34 l26,34 h-16 v40 h-20 v-40 z" fill="{P["teal"]}"/></g>')
    tower = (f'<g class="f-rise" style="{_dl(0.5)}"><path d="M690,470 L716,250 L742,470 Z" fill="{P["coral"]}"/>'
             f'<path d="M716,250 L742,470 L728,470 Z" fill="#000" opacity=".12"/>'
             + "".join(f'<rect x="{696 + k * 3}" y="{300 + k * 50}" width="{40 - k * 6 + 14:.0f}" height="8" fill="#fff" opacity=".85" transform="translate({-k * 2},0)"/>' for k in range(4))
             + f'<rect x="712" y="215" width="8" height="40" fill="{P["coral"]}"/></g>')
    right = building(540, 470, 80, 210, P["navy3"], "#6E8FD8", 0.45, (3,)) + building(626, 470, 56, 150, P["navy2"], "#5A7BC4", 0.55, (1,)) + tower + building(752, 470, 60, 180, P["navy3"], "#6E8FD8", 0.6, (2,))
    t2 = t1 + 0.9
    board = (f'<g class="f-pop" style="{_dl(t2 + 1.1)}"><g class="f-bob" style="{_dl(-1)}"><rect x="560" y="70" width="210" height="130" rx="18" fill="#fff"/>'
             + "".join(f'<rect class="f-rise" style="{_dl(t2 + 1.3 + k * 0.15)}" x="{588 + k * 44}" y="{180 - hh}" width="28" height="{hh}" rx="6" fill="{c}"/>'
                       for k, (hh, c) in enumerate([(40, P["sky"]), (62, "#9DB8FF"), (84, P["blue"]), (100, P["blue"])]))
             + "</g></g>")
    arc = "M190,150 C330,10 520,10 650,140"
    dots = "".join(f'<circle r="{7 - k % 3}" fill="{P["amber"]}" class="mdot" style="offset-path:path(\'{arc}\');animation-delay:{t2 + k * 0.12:.2f}s"/>' for k in range(10))
    labels = (pill(150, 420, "米国　半導体株 ↑", t1 + 0.2, P["navy"], "#fff", 28)
              + pill(630, 420, "東京　関連銘柄に買い", t2 + 1.2, P["blue"], "#fff", 28))
    svg = f'<svg width="834" height="700" viewBox="0 0 834 700">{sky}{sea}{left}{right}{chip}{board}{dots}{labels}</svg>'
    css = """.mdot{offset-rotate:0deg;opacity:0;animation:mdot 1.4s cubic-bezier(.4,0,.3,1) both}
@keyframes mdot{0%{offset-distance:0%;opacity:0}10%{opacity:1}90%{opacity:1}100%{offset-distance:100%;opacity:0}}"""
    return svg, css


def il_breach_flat(B, D):
    """社会：サーバーの鍵が破られ、個人情報のカードが外へ流れ出す（夜の部屋）."""
    P = PAL
    t0 = 0.3
    t_open = (B[0] + 1.0) if B else 1.2
    bg = (f'<defs><linearGradient id="bsky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#13265A"/><stop offset="1" stop-color="#0B1B33"/></linearGradient>'
          f'<radialGradient id="bfl"><stop offset="0" stop-color="{P["blue2"]}" stop-opacity=".55"/><stop offset="1" stop-color="{P["blue2"]}" stop-opacity="0"/></radialGradient></defs>'
          f'<rect width="834" height="700" fill="url(#bsky)"/>'
          + "".join(f'<circle cx="{(k * 97) % 834}" cy="{40 + (k * 53) % 260}" r="{1.5 + k % 3}" fill="#fff" opacity="{0.25 + (k % 4) * 0.1}" class="f-blink" style="{_dl(-k * 0.13)}"/>' for k in range(24))
          + f'<ellipse cx="300" cy="610" rx="300" ry="60" fill="url(#bfl)"/><rect y="600" width="834" height="100" fill="#0A1630"/>')
    rack = [f'<g class="f-rise" style="{_dl(t0)}"><rect x="180" y="230" width="230" height="380" rx="22" fill="{P["navy3"]}"/>'
            f'<rect x="330" y="230" width="80" height="380" rx="0" fill="#000" opacity=".15"/>']
    for r in range(6):
        y = 255 + r * 58
        rack.append(f'<rect x="200" y="{y}" width="190" height="44" rx="8" fill="{P["navy2"]}"/>')
        for k in range(3):
            c = [P["teal"], P["amber"], P["teal"]][(r + k) % 3]
            rack.append(f'<circle cx="{222 + k * 18}" cy="{y + 22}" r="5" fill="{c}" class="f-blink" style="{_dl(-(r * 3 + k) * 0.17)}"/>')
        rack.append(f'<rect x="300" y="{y + 18}" width="74" height="8" rx="4" fill="#5A7BC4" opacity=".6"/>')
    rack.append("</g>")
    lock = (f'<g class="f-pop" style="{_dl(t0 + 0.4)}"><rect x="355" y="380" width="96" height="78" rx="14" fill="{P["amber"]}"/>'
            f'<rect x="403" y="380" width="48" height="78" rx="0" fill="#000" opacity=".12"/><circle cx="403" cy="413" r="9" fill="#7A5A10"/>'
            f'<rect x="399" y="416" width="8" height="20" rx="4" fill="#7A5A10"/></g>'
            f'<path class="bshk" style="{_dl(t_open)}" d="M372,382 V352 A31,31 0 0 1 434,352 V382" fill="none" stroke="{P["amber"]}" stroke-width="14" stroke-linecap="round"/>'
            f'<circle cx="403" cy="410" r="70" fill="#fff" class="bflash" style="{_dl(t_open)}"/>')
    cards = ""
    for i in range(9):
        t = t_open + 0.25 + i * 0.22
        cards += (f'<g class="bcard" style="{_dl(t)};--tx:{150 + (i % 3) * 70}px;--ty:{-210 + (i % 4) * 60}px;--r:{(-14 + i * 7) % 28 - 14}deg">'
                  f'<g transform="translate(380 330)"><rect width="110" height="70" rx="12" fill="#fff"/><circle cx="28" cy="30" r="12" fill="{P["sky"]}"/>'
                  f'<path d="M14,58 Q28,42 42,58" fill="{P["sky"]}"/><rect x="54" y="22" width="44" height="8" rx="4" fill="#C9D4E6"/><rect x="54" y="38" width="32" height="8" rx="4" fill="#C9D4E6"/></g></g>')
    count = pill(620, 640, "最大 3,762万件", t_open + 0.8, P["coral"], "#fff", 34)
    svg = f'<svg width="834" height="700" viewBox="0 0 834 700">{bg}{"".join(rack)}{cards}{lock}{count}</svg>'
    css = """.bshk{transform-box:fill-box;transform-origin:100% 100%;animation:bshk .45s cubic-bezier(.3,1.6,.5,1) forwards}
@keyframes bshk{to{transform:translateY(-22px) rotate(32deg)}}
.bflash{opacity:0;animation:bfl .5s ease-out forwards}
@keyframes bfl{0%{opacity:.75;transform:scale(.4)}100%{opacity:0;transform:scale(1.6)}}
.bflash{transform-box:fill-box;transform-origin:50% 50%}
.bcard{opacity:0;animation:bcard 2.2s cubic-bezier(.25,.6,.3,1) forwards}
@keyframes bcard{0%{opacity:0;transform:none}12%{opacity:1}100%{opacity:.92;transform:translate(var(--tx),var(--ty)) rotate(var(--r))}}"""
    return svg, css


def il_status_quo(B, D):
    """国際：海の上の「現状」の線を、力で動かそうとする矢印。G7の7人が横一列に並び、反対の旗で止める."""
    P = PAL
    b0 = B[0] if B else 0.1
    b1 = B[1] if len(B) > 1 else D * 0.55
    bg = (f'<defs><linearGradient id="gsea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#BFD4FF"/><stop offset="1" stop-color="{P["blue2"]}"/></linearGradient></defs>'
          f'<rect width="834" height="700" fill="url(#gsea)"/>'
          + "".join(f'<g class="f-wave" style="{_dl(-i * 0.6)}"><path d="M{-30 + i * 23},{120 + i * 105} q30,-10 60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0 t60,0" fill="none" stroke="#fff" stroke-width="3" opacity=".25"/></g>' for i in range(6))
          + f'<g class="f-fade" style="{_dl(0.2)}"><ellipse cx="90" cy="660" rx="120" ry="40" fill="{P["sand"]}"/><ellipse cx="90" cy="650" rx="96" ry="26" fill="{P["mint"]}"/>'
          f'<ellipse cx="770" cy="680" rx="110" ry="36" fill="{P["sand"]}"/><ellipse cx="770" cy="671" rx="86" ry="24" fill="{P["mint"]}"/></g>')
    line = (f'<path class="gline" d="M30,430 H804" stroke="#fff" stroke-width="6" stroke-dasharray="18 14" stroke-linecap="round"/>'
            + pill(96, 470, "現状", 0.4, "#fff", P["navy"], 26))
    arrow = (f'<g class="garrow" style="{_dl(b0 + 0.3)}"><path d="M444,-40 H500 V150 H540 L472,232 L404,150 H444 Z" fill="{P["coral"]}"/>'
             f'<path d="M472,-40 H500 V150 H540 L472,232 Z" fill="#000" opacity=".1"/>'
             f'<text class="f-txt" x="424" y="70" font-size="30" fill="#fff" text-anchor="end">力・威圧</text></g>')
    people = ""
    cols = [P["blue"], P["navy3"], P["teal"], P["blue2"], P["navy2"], "#5A7BC4", P["blue"]]
    for i in range(7):
        x = 280 + i * 64
        people += person(x, 430, cols[i], b0 + 0.9 + i * 0.08, 110)
    banner = (f'<g class="f-pop" style="{_dl(b0 + 1.6)}"><rect x="252" y="244" width="440" height="58" rx="12" fill="#fff"/>'
              f'<rect x="268" y="302" width="8" height="40" fill="#fff"/><rect x="668" y="302" width="8" height="40" fill="#fff"/>'
              f'<text class="f-txt" x="472" y="284" text-anchor="middle" font-size="32" fill="{P["blue"]}">現状変更に反対</text></g>'
              + pill(472, 480, "G7", b0 + 1.4, P["blue"], "#fff", 30, 100))
    seas = (pill(210, 590, "東シナ海", b1 + 0.1, "#fff", P["navy"], 26) + pill(420, 640, "南シナ海", b1 + 0.3, "#fff", P["navy"], 26)
            + pill(630, 590, "台湾海峡", b1 + 0.5, "#fff", P["navy"], 26))
    svg = f'<svg width="834" height="700" viewBox="0 0 834 700">{bg}{line}{arrow}{people}{banner}{seas}</svg>'
    css = """.garrow{animation:garrow 1.4s cubic-bezier(.3,.7,.3,1) both}
@keyframes garrow{0%{transform:translateY(-300px);opacity:0}15%{opacity:1}72%{transform:translateY(8px)}84%{transform:translateY(-14px)}100%{transform:translateY(-6px)}}
.gline{stroke-dashoffset:0;animation:gline 2s linear infinite}
@keyframes gline{to{stroke-dashoffset:-64}}"""
    return svg, css


FLAT = {"market": il_market, "breach": il_breach_flat, "status_quo": il_status_quo}


def t_illus(s, B, D):
    """解説イラストの場面：見出し＋大きなイラストのパネル."""
    svg, css2 = FLAT[s["illus"]](B, D)
    body = kin(s["title"], 0.05, "", 0.12, f"top:336px;font-size:{s.get('size', 84)}px") + f'<div class="ipanel">{svg}</div>'
    return body, css2, ""


# ───────── 解説図（白×青・細い線・柔らかい影。弾まない、なめらかな動き） ─────────
DIAG_CSS = """
.ipanel{position:absolute;left:96px;right:150px;top:470px;height:720px}
.dcard{position:absolute;background:#fff;border:1px solid var(--line);border-radius:28px;box-shadow:0 30px 70px rgba(20,40,90,.10),0 2px 6px rgba(20,40,90,.04);
animation:dcin .7s cubic-bezier(.2,.8,.2,1) both}
@keyframes dcin{0%{opacity:0;transform:translateY(40px)}100%{opacity:1;transform:none}}
.dlab{position:absolute;font-size:24px;font-weight:700;color:var(--sub);letter-spacing:.06em}
.dchip{position:absolute;display:inline-flex;align-items:center;gap:10px;white-space:nowrap;font-size:28px;font-weight:700;color:var(--ink);background:#fff;
border:1px solid var(--line);border-radius:999px;padding:10px 22px;box-shadow:0 12px 30px rgba(20,40,90,.10);animation:dchip .5s cubic-bezier(.2,.8,.2,1) both}
.dchip.blue{background:var(--blue);color:#fff;border-color:var(--blue);box-shadow:0 14px 34px rgba(31,91,255,.28)}
.dchip.acc{background:var(--acc);color:#fff;border-color:var(--acc);box-shadow:0 14px 34px rgba(234,106,18,.30)}
.dchip.ghost{background:var(--pale);border-color:transparent;color:var(--blue)}
.dchip i{width:12px;height:12px;border-radius:50%;background:var(--blue);display:inline-block}
@keyframes dchip{0%{opacity:0;transform:translateY(14px)}100%{opacity:1;transform:none}}
.dfade{animation:dfade .6s both}
@keyframes dfade{0%{opacity:0}100%{opacity:1}}
.ddraw{fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;animation:ddraw 1s cubic-bezier(.4,0,.2,1) forwards}
@keyframes ddraw{to{stroke-dashoffset:0}}
.dx{position:absolute;width:92px;height:92px;border-radius:50%;background:#fff;border:4px solid var(--warn);box-shadow:0 16px 36px rgba(217,58,58,.25);
display:flex;align-items:center;justify-content:center;animation:dxin .45s cubic-bezier(.2,.8,.2,1) both}
.dx:before,.dx:after{content:"";position:absolute;width:46px;height:6px;border-radius:3px;background:var(--warn);transform:rotate(45deg)}
.dx:after{transform:rotate(-45deg)}
@keyframes dxin{0%{opacity:0;transform:scale(.6)}100%{opacity:1;transform:none}}
.dpart{position:absolute;left:0;top:0;width:12px;height:12px;margin:-6px 0 0 -6px;border-radius:50%;background:var(--blue);box-shadow:0 0 14px 4px rgba(31,91,255,.45);
offset-rotate:0deg;opacity:0;animation:dpart 1.5s cubic-bezier(.45,0,.35,1) infinite}
@keyframes dpart{0%{offset-distance:0%;opacity:0}12%{opacity:1}88%{opacity:1}100%{offset-distance:100%;opacity:0}}
.tilt-l{transform:perspective(1400px) rotateY(10deg) rotateX(4deg)}
.tilt-r{transform:perspective(1400px) rotateY(-10deg) rotateX(4deg)}
.dbar{height:14px;border-radius:7px;background:linear-gradient(90deg,var(--blue),var(--blue2));transform-origin:0 50%;animation:dbar .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes dbar{0%{transform:scaleX(0)}100%{transform:none}}
"""


def _a(t):
    return f"animation-delay:{t:.2f}s"


def chip(x, y, text, t, kind="", dot=False):
    return f'<div class="dchip {kind}" style="left:{x}px;top:{y}px;{_a(t)}">{"<i></i>" if dot else ""}{esc(text)}</div>'


# ── 国際：力による現状変更に反対 ──
def d_status_quo(B, D):
    """地図の境界線＝現状。力で線を押し曲げる試み（点線）に ✕、G7 は反対。2文目で念頭の海域を出す."""
    b0 = B[0] if B else 0.1
    b1 = B[1] if len(B) > 1 else D * 0.55
    tp0, tp1 = b0 + 1.2, b0 + 2.4          # 押し込む
    tx = b0 + 2.6                           # ✕
    tg = b0 + 3.1                           # G7
    W, H = 834, 440
    js = f"""
(function(){{
 const W={W},H={H},x0=W*0.5;
 const base=y=>x0+18*Math.sin(y/52)+10*Math.sin(y/23+1);
 const P=document.getElementById('sqA'),Q=document.getElementById('sqB'),F=document.getElementById('sqF'),R=document.getElementById('sqRegion'),AR=document.getElementById('sqArrow');
 const ease=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
 function line(k){{let d='';for(let y=20;y<=H-20;y+=8){{const x=base(y)+k*170*Math.exp(-Math.pow((y-H/2)/95,2));d+=(y===20?'M':'L')+x.toFixed(1)+','+y;}}return d;}}
 P.setAttribute('d',line(0));
 const lr=y=>base(y);
 let reg='M0,0 L'+x0+',0 ';
 __tick.push(t=>{{
  const k=ease(Math.min(1,Math.max(0,(t-{tp0})/({tp1}-{tp0}))));
  Q.setAttribute('d',line(k));Q.style.opacity=k>0.01?1:0;
  // 押し込まれた部分（元の線と新しい線のあいだ）
  let d='';for(let y=20;y<=H-20;y+=8){{d+=(y===20?'M':'L')+base(y).toFixed(1)+','+y;}}
  for(let y=H-20;y>=20;y-=8){{const x=base(y)+k*170*Math.exp(-Math.pow((y-H/2)/95,2));d+='L'+x.toFixed(1)+','+y;}}
  F.setAttribute('d',d+'Z');F.style.opacity=k*0.9;
  const tipx=base(H/2)+k*170;AR.style.transform='translate('+(tipx-250)+'px,'+(H/2-34)+'px)';AR.style.opacity=t>{tp0 - 0.4}?Math.min(1,(t-{tp0 - 0.4})/0.3):0;
 }});
}})();"""
    svg = (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="position:absolute;left:0;top:0">'
           f'<defs><linearGradient id="sqL" x1="0" x2="1"><stop offset="0" stop-color="#EEF3FF"/><stop offset="1" stop-color="#E3EBFF"/></linearGradient>'
           f'<pattern id="sqH" width="12" height="12" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="12" height="12" fill="#FDECEC"/><rect width="5" height="12" fill="#F7C9C9"/></pattern></defs>'
           f'<rect x="0" y="0" width="{W / 2 + 20}" height="{H}" fill="url(#sqL)"/>'
           f'<rect x="{W / 2 + 20}" y="0" width="{W / 2}" height="{H}" fill="#F6F8FB"/>'
           f'<path id="sqF" fill="url(#sqH)" opacity="0"/>'
           f'<path id="sqA" class="ddraw" style="{_a(0.5)};stroke:#0B1B33;stroke-width:5" pathLength="1"/>'
           f'<path id="sqB" fill="none" stroke="#D93A3A" stroke-width="4" stroke-dasharray="14 12" stroke-linecap="round" opacity="0"/>'
           f'</svg>')
    arrow = (f'<div id="sqArrow" style="position:absolute;left:0;top:0;opacity:0;width:240px;height:68px">'
             f'<svg width="240" height="68" viewBox="0 0 240 68"><defs><linearGradient id="arG" x1="0" x2="1"><stop offset="0" stop-color="#0B1B33" stop-opacity="0"/><stop offset="1" stop-color="#0B1B33"/></linearGradient></defs>'
             f'<path d="M0,22 H190 V6 L236,34 L190,62 V46 H0 Z" fill="url(#arG)"/></svg>'
             f'<div style="position:absolute;left:40px;top:-46px;font-size:26px;font-weight:700;color:var(--ink);white-space:nowrap">力・威圧</div></div>')
    card = (f'<div class="dcard" style="left:0;top:0;width:{W}px;height:{H}px;overflow:hidden;{_a(0.1)}">{svg}{arrow}'
            + chip(28, 26, "現状の線", 0.9, "", True)
            + f'<div class="dlab" style="left:{W / 2 + 120}px;top:{H - 58}px;animation:dfade .6s both;{_a(tp1)};white-space:nowrap;color:var(--warn)">力による一方的な変更</div>'
            + f'<div class="dx" style="left:{W / 2 + 128}px;top:{H / 2 - 46}px;{_a(tx)}"></div></div>')
    g7 = (f'<div class="dcard" style="left:0;top:{H + 30}px;width:{W}px;height:118px;{_a(tg)};display:flex;align-items:center;gap:22px;padding:0 34px">'
          f'<span style="font-size:44px;font-weight:900;color:var(--blue)">G7</span>'
          f'<span style="font-size:34px;font-weight:700">この変更に強く反対</span></div>')
    seas = (f'<div class="dlab" style="left:4px;top:{H + 180}px;animation:dfade .5s both;{_a(b1)}">念頭にあるのは中国の動き</div>'
            + chip(0, H + 220, "東シナ海", b1 + 0.15, "ghost") + chip(190, H + 220, "南シナ海", b1 + 0.3, "ghost") + chip(380, H + 220, "台湾海峡", b1 + 0.45, "ghost"))
    return card + g7 + seas, "", js


# ── 経済：米国の半導体株高 → 東京へ波及 ──
def d_market(B, D):
    b0 = B[0] if B else 0.1
    t_l, t_r = b0 + 0.2, b0 + 1.6
    lc = (f'<div class="dcard tilt-l" style="left:0;top:20px;width:390px;height:300px;{_a(t_l)};padding:30px 32px">'
          f'<div style="font-size:24px;color:var(--sub);font-weight:700;letter-spacing:.06em">前日　米国市場</div>'
          f'<div style="font-size:40px;font-weight:900;margin-top:6px">半導体株 <span style="color:var(--acc)">▲</span></div>'
          f'<svg width="326" height="150" viewBox="0 0 326 150" style="margin-top:18px"><path d="M0,140 H326" stroke="#E3E9F2" stroke-width="2"/>'
          f'<path class="ddraw" style="{_a(t_l + 0.4)};stroke:var(--acc);stroke-width:6" d="M0,128 C50,124 80,110 120,96 S200,64 240,46 S300,18 326,10" pathLength="1"/>'
          f'<circle cx="326" cy="10" r="9" fill="var(--acc)" class="dfade" style="{_a(t_l + 1.3)}"/></svg>'
          f'<svg width="56" height="56" viewBox="0 0 64 64" style="position:absolute;right:28px;top:26px"><rect x="12" y="12" width="40" height="40" rx="8" fill="none" stroke="#1F5BFF" stroke-width="3"/>'
          f'<rect x="24" y="24" width="16" height="16" rx="3" fill="#E8EFFF" stroke="#1F5BFF" stroke-width="2"/>'
          f'<path d="M22,4V12M32,4V12M42,4V12M22,52V60M32,52V60M42,52V60M4,22H12M4,32H12M4,42H12M52,22H60M52,32H60M52,42H60" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/></svg></div>')
    rows = "".join(f'<div style="display:flex;align-items:center;gap:16px;margin-top:22px"><span style="width:150px;font-size:26px;font-weight:700">{n}</span>'
                   f'<div class="dbar" style="width:{w}px;{_a(t_r + 0.5 + i * 0.2)}"></div></div>'
                   for i, (n, w) in enumerate([("半導体関連", 150), ("ハイテク", 110), ("日経平均", 130)]))
    rc = (f'<div class="dcard tilt-r" style="left:444px;top:290px;width:390px;height:340px;{_a(t_r)};padding:30px 32px">'
          f'<div style="font-size:24px;color:var(--sub);font-weight:700;letter-spacing:.06em">当日　東京市場</div>'
          f'<div style="font-size:40px;font-weight:900;margin-top:6px">買いが広がる <span style="color:var(--acc)">▲</span></div>{rows}</div>')
    path = "M380,190 C560,190 300,450 460,450"
    flow = (f'<svg width="834" height="640" viewBox="0 0 834 640" style="position:absolute;left:0;top:0;overflow:visible">'
            f'<path class="ddraw" style="{_a(t_l + 0.9)};stroke:#9DB8FF;stroke-width:3;stroke-dasharray:1" d="{path}" pathLength="1"/></svg>'
            + "".join(f'<div class="dpart" style="offset-path:path(\'{path}\');animation-delay:{t_l + 1.0 + k * 0.3:.2f}s"></div>' for k in range(5)))
    res = chip(0, 670, "上げ幅は一時 1,700円超", t_r + 1.4, "acc")
    return lc + flow + rc + res, "", ""


# ── 社会：不正アクセスと個人情報の流出 ──
def d_breach(B, D):
    b0 = B[0] if B else 0.1
    t0 = b0 + 0.2
    t_open = b0 + 1.6
    layers = "".join(
        f'<div class="dly" style="top:{150 + i * 46}px;{_a(t0 + i * 0.12)};background:{c}"></div>'
        for i, c in enumerate(["linear-gradient(135deg,#FFFFFF,#E8EFFF)", "linear-gradient(135deg,#F4F7FF,#D9E5FF)", "linear-gradient(135deg,#E9F0FF,#C8D8FF)"]))
    stack = f'<div class="dstack">{layers}</div>'
    lock = (f'<div class="dlock" style="{_a(t0 + 0.4)}"><svg width="120" height="140" viewBox="0 0 120 140">'
            f'<path class="shk" style="{_a(t_open)}" d="M34,62 V42 A26,26 0 0 1 86,42 V62" fill="none" stroke="#1F5BFF" stroke-width="8" stroke-linecap="round"/>'
            f'<rect x="18" y="60" width="84" height="66" rx="16" fill="#fff" stroke="#1F5BFF" stroke-width="6"/>'
            f'<circle cx="60" cy="88" r="7" fill="#1F5BFF"/><path d="M60,92 V106" stroke="#1F5BFF" stroke-width="6" stroke-linecap="round"/></svg>'
            f'<div class="dring" style="{_a(t_open)}"></div></div>')
    recs = ""
    for i in range(6):
        t = t_open + 0.3 + i * 0.25
        recs += (f'<div class="drec" style="{_a(t)};--tx:{330 + (i % 2) * 40}px;--ty:{-150 + i * 62}px">'
                 f'<svg width="34" height="34" viewBox="0 0 34 34"><circle cx="17" cy="12" r="6" fill="none" stroke="#5B6B82" stroke-width="2.5"/>'
                 f'<path d="M6,30 Q17,18 28,30" fill="none" stroke="#5B6B82" stroke-width="2.5" stroke-linecap="round"/></svg>'
                 f'<b></b><b style="width:46px"></b></div>')
    count = (f'<div class="dcard" style="left:0;top:560px;width:834px;height:130px;{_a(t_open + 1.2)};display:flex;align-items:center;justify-content:space-between;padding:0 36px">'
             f'<span style="font-size:30px;font-weight:700;color:var(--sub)">流出したおそれ</span>'
             f'<span style="font-size:64px;font-weight:900;color:var(--ink)">最大 <span style="color:var(--blue)">3,762</span><span style="font-size:34px">万件</span></span></div>')
    css = """
.dstack{position:absolute;left:60px;top:0;width:380px;height:520px}
.dly{position:absolute;left:30px;width:300px;height:180px;border-radius:30px;border:1px solid #D3DEF3;box-shadow:0 26px 50px rgba(20,40,90,.12);
transform:perspective(1200px) rotateX(58deg) rotateZ(-38deg);animation:dly .8s cubic-bezier(.2,.8,.2,1) both}
@keyframes dly{0%{opacity:0;transform:perspective(1200px) rotateX(58deg) rotateZ(-38deg) translateZ(-120px)}100%{opacity:1;transform:perspective(1200px) rotateX(58deg) rotateZ(-38deg)}}
.dlock{position:absolute;left:190px;top:40px;width:120px;height:140px;animation:dfade .6s both}
.shk{transform-box:fill-box;transform-origin:100% 100%;animation:shk .6s cubic-bezier(.3,1.2,.4,1) forwards}
@keyframes shk{to{transform:translateY(-20px)}}
.dring{position:absolute;left:10px;top:30px;width:100px;height:100px;border-radius:50%;border:3px solid var(--blue);opacity:0;animation:dring .9s ease-out forwards}
@keyframes dring{0%{opacity:.8;transform:scale(.6)}100%{opacity:0;transform:scale(2.2)}}
.drec{position:absolute;left:250px;top:250px;display:flex;align-items:center;gap:10px;background:#fff;border:1px solid var(--line);border-radius:16px;padding:10px 16px;
box-shadow:0 14px 30px rgba(20,40,90,.12);opacity:0;animation:drec 1.6s cubic-bezier(.2,.8,.2,1) forwards}
.drec b{display:block;width:70px;height:10px;border-radius:5px;background:#D5DDE9}
@keyframes drec{0%{opacity:0;transform:translate(0,0) scale(.85)}20%{opacity:1}100%{opacity:1;transform:translate(var(--tx),var(--ty))}}
"""
    return stack + recs + lock + count, css, ""


FLAT = {"market": d_market, "breach": d_breach, "status_quo": d_status_quo}


def t_illus(s, B, D):
    """解説図の場面：見出し＋図."""
    body_d, css2, js = FLAT[s["illus"]](B, D)
    body = kin(s["title"], 0.05, "", 0.12, f"top:336px;font-size:{s.get('size', 84)}px") + f'<div class="ipanel">{body_d}</div>'
    return body, css2, js


# ── 一覧の行アイコン ──
def row_icon(kind):
    p = {
        "person": '<circle cx="24" cy="16" r="8"/><path d="M8,42 Q24,24 40,42"/>',
        "home": '<path d="M8,24 L24,10 L40,24"/><path d="M13,21 V40 H35 V21"/><path d="M21,40 V30 H27 V40"/>',
        "phone": '<rect x="14" y="6" width="20" height="36" rx="4"/><path d="M21,36 H27"/>',
        "mail": '<rect x="6" y="12" width="36" height="26" rx="4"/><path d="M8,15 L24,27 L40,15"/>',
        "key": '<circle cx="16" cy="24" r="8"/><path d="M24,24 H42 M36,24 V30 M41,24 V29"/>',
        "card": '<rect x="5" y="12" width="38" height="26" rx="4"/><path d="M5,20 H43"/><path d="M11,31 H21"/>',
        "calendar": '<rect x="7" y="10" width="34" height="30" rx="4"/><path d="M7,18 H41 M16,6 V13 M32,6 V13"/>',
    }.get(kind, '<circle cx="24" cy="24" r="14"/>')
    return f'<svg class="ri" width="48" height="48" viewBox="0 0 48 48">{p}</svg>'


ICONS = {
    "dot": "M100,44 A56,56 0 1 1 99.99,44 Z",
    "globe": "M100,18 A82,82 0 1 1 99.99,18 Z",
    "pin": "M100,18 C142,18 170,48 170,88 C170,130 100,184 100,184 C100,184 30,130 30,88 C30,48 58,18 100,18 Z",
    "arrow": "M100,16 L178,98 H132 V184 H68 V98 H22 Z",
    "chart": "M20,184 H180 V34 H138 V166 H122 V84 H80 V166 H64 V122 H22 V166 H20 Z",
    "lock": "M58,96 V70 C58,40 78,20 100,20 C122,20 142,40 142,70 V96 H158 Q168,96 168,106 V174 Q168,184 158,184 H42 Q32,184 32,174 V106 Q32,96 42,96 Z",
    "card": "M32,46 H168 Q184,46 184,62 V138 Q184,154 168,154 H32 Q16,154 16,138 V62 Q16,46 32,46 Z",
    "shield": "M100,16 L172,44 V98 C172,142 140,172 100,186 C60,172 28,142 28,98 V44 Z",
    "bubble": "M36,34 H164 Q182,34 182,52 V124 Q182,142 164,142 H96 L58,180 L66,142 H36 Q18,142 18,124 V52 Q18,34 36,34 Z",
    "cross": "M46,28 L100,82 L154,28 L172,46 L118,100 L172,154 L154,172 L100,118 L46,172 L28,154 L82,100 L28,46 Z",
}
MBG = {"white": "#F6F8FB", "blue": "#1F5BFF", "navy": "#0B1B33", "sky": "#E3EBFF"}


def deco(ic, fg, bg, t, kind):
    """アイコンの上に描く細部（背景色で抜く）と、周りに飛ぶ線."""
    st = f'style="animation-delay:{t:.2f}s"'
    out = ""
    if ic == "globe":
        out = (f'<g class="mdc" {st} fill="none" stroke="{bg}" stroke-width="6"><ellipse cx="100" cy="100" rx="34" ry="82"/>'
               f'<path d="M22,74 H178 M22,126 H178 M100,18 V182"/></g>')
    elif ic == "pin":
        out = f'<g class="mdc" {st}><circle cx="100" cy="86" r="26" fill="{bg}"/></g>'
    elif ic == "lock":
        out = (f'<g class="mdc" {st}><path d="M78,96 V72 C78,52 88,40 100,40 C112,40 122,52 122,72 V96 Z" fill="{bg}"/>'
               f'<circle cx="100" cy="132" r="13" fill="{bg}"/><rect x="94" y="132" width="12" height="28" rx="6" fill="{bg}"/></g>')
    elif ic == "card":
        out = (f'<g class="mdc" {st} fill="{bg}"><circle cx="62" cy="88" r="17"/><path d="M36,132 Q62,104 88,132 Z"/>'
               f'<rect x="104" y="80" width="56" height="12" rx="6"/><rect x="104" y="106" width="40" height="12" rx="6"/></g>')
    elif ic == "shield":
        out = f'<g class="mdc" {st}><path d="M66,100 L92,126 L138,78" fill="none" stroke="{bg}" stroke-width="14" stroke-linecap="round" stroke-linejoin="round"/></g>'
    elif ic == "chart":
        out = f'<g class="mdc" {st}><path d="M18,120 L70,70 L104,96 L176,24" fill="none" stroke="{bg}" stroke-width="0"/></g>'
    if kind == "burst":
        rays = ""
        for k in range(10):
            import math
            a = 2 * math.pi * k / 10 - math.pi / 2
            x1, y1 = 100 + 112 * math.cos(a), 100 + 112 * math.sin(a)
            x2, y2 = 100 + 138 * math.cos(a), 100 + 138 * math.sin(a)
            rays += f'<path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}"/>'
        out += f'<g class="mray" style="animation-delay:{t + 0.05:.2f}s" stroke="{fg}" stroke-width="7" stroke-linecap="round">{rays}</g>'
    return out


def t_morph(s, B, D):
    """1つの図形が次のアイコンへ変形し、新しい背景色が円形に広がって画面が入れ替わる。shots の数だけ beats を用意する."""
    shots = s["shots"]
    n = len(shots)
    starts = list(B[-n:]) if len(B) >= n else [i * D / n for i in range(n)]
    starts[0] = 0.0
    ends = starts[1:] + [D]
    first_scene = s.get("_first", False)
    S, texts, decos, js_parts = [], [], [], []
    for i, sh in enumerate(shots):
        bg = sh.get("bg", "white")
        dark = bg in ("blue", "navy")
        fg = sh.get("fg") or ("#FFFFFF" if dark else "#1F5BFF")
        t0, t1 = starts[i], ends[i]
        S.append({"t0": t0, "bg": MBG[bg], "fg": fg, "ic": sh.get("icon", "dot"), "dark": dark, "logo": bool(sh.get("logo"))})
        decos.append(f'<g class="mdg" style="animation-delay:{t0:.2f}s,{t1 - 0.12:.2f}s">{deco(sh.get("icon", "dot"), fg, MBG[bg], t0 + 0.38, sh.get("deco", ""))}</g>')
        ink = "#FFFFFF" if dark else "#0B1B33"
        acc = "#A9C1FF" if bg == "navy" else ("#0B1B33" if bg == "blue" else "#1F5BFF")
        sub = "rgba(255,255,255,.78)" if dark else "#5B6B82"
        tin = -1.0 if (i == 0 and first_scene) else t0 + 0.12
        body = ""
        if sh.get("logo"):
            letters = "".join(f'<span class="ml" style="animation-delay:{t0 + 0.25 + k * 0.05:.2f}s{";color:#7FA2FF" if k >= 6 else ""}">{"&nbsp;" if ch == " " else esc(ch)}</span>'
                              for k, ch in enumerate("QUICK NEWS"))
            body = (f'<div class="mlogo">{letters}<span class="ldot"></span></div>'
                    f'<div class="mtag" style="animation-delay:{t0 + 0.9:.2f}s;color:{sub}">{esc(sh.get("tagline", "1日1分で社会がわかる"))}</div>'
                    f'<div class="mcta" style="animation-delay:{t0 + 1.2:.2f}s">{esc(sh.get("cta", "フォローして毎朝の習慣に"))}</div>')
        else:
            if sh.get("kicker"):
                body += f'<div class="mk" style="animation-delay:{tin:.2f}s;color:{acc}">{esc(sh["kicker"])}</div>'
            if sh.get("number") is not None:
                body += (f'<div class="mnum" style="animation-delay:{tin:.2f}s;color:{ink}"><span class="pre">{esc(sh.get("prefix", ""))}</span>'
                         f'<span id="mn{i}" class="mono" style="color:{acc}">0</span><span class="u" style="color:{acc}">{esc(sh.get("unit", ""))}</span></div>')
                js_parts.append(counter_js(f"mn{i}", sh["number"], t0 + 0.2, 0.9, sh.get("decimals", 0)))
            if sh.get("big"):
                body += kin(sh["big"], tin + 0.05, "mbig", 0.08, f"position:relative;left:0;right:0;font-size:{sh.get('size', 92)}px;color:{ink}").replace(
                    'class="ph acc"', f'class="ph acc" data-c="{acc}"')
            if sh.get("sub"):
                body += f'<div class="msub" style="animation-delay:{tin + 0.3:.2f}s;color:{sub}">{esc(sh["sub"])}</div>'
        out_anim = f",mtout .22s {t1 - 0.2:.2f}s cubic-bezier(.5,0,.75,0) forwards" if i < n - 1 else ""
        texts.append(f'<div class="mt" style="animation:mtin .01s {(-0.1 if tin < 0 else tin):.2f}s both{out_anim}">{body}</div>')
    js = """
(function(){const S=%s;const P=%s;
 const icon=document.getElementById('mi'),svg=document.getElementById('msvg'),base=document.getElementById('mbase'),wipe=document.getElementById('mwipe');
 const I=[];for(let i=1;i<S.length;i++)I.push(S[i].ic===S[i-1].ic?null:flubber.interpolate(P[S[i-1].ic],P[S[i].ic],{maxSegmentLength:3}));
 const eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
 document.querySelectorAll('.mbig .acc').forEach(e=>{e.style.color=e.closest('.ph')?e.dataset.c:'';if(e.dataset.c)e.style.color=e.dataset.c;});
 __tick.push(t=>{
  let k=0;for(let i=0;i<S.length;i++)if(t>=S[i].t0-0.12)k=i;
  const sh=S[k];
  // 変形
  let d=P[sh.ic],sx=1,sy=1,rot=0;
  if(k>0){const p=Math.min(1,Math.max(0,(t-(S[k].t0-0.12))/0.55));const e=eio(p);
    if(I[k-1]&&p<1)d=I[k-1](e);
    const w=Math.sin(Math.PI*p);sx=1+0.16*w;sy=1-0.12*w;rot=10*Math.sin(Math.PI*2*p)*(1-p);}
  else{const p=Math.min(1,Math.max(0,(t+0.2)/0.5));const w=Math.sin(Math.PI*p);sx=1-0.08*w;sy=1+0.1*w;}
  icon.setAttribute('d',d);icon.setAttribute('fill',(k>0&&t<S[k].t0+0.12)?S[k-1].fg:sh.fg);
  let tx=0,ty=0,sc=1;
  if(sh.logo){const dot=document.querySelector('.ldot');if(dot){const r=dot.getBoundingClientRect(),q=svg.parentNode.getBoundingClientRect();
    const p=Math.min(1,Math.max(0,(t-sh.t0-0.2)/0.6));const e=eio(p);sc=1-0.88*e;
    tx=(r.left+r.width/2-q.left-200)*e;ty=(r.top+r.height/2-q.top-200)*e;}}
  if(!sh.logo){ty+=10*Math.sin(t*2.6);rot+=2.5*Math.sin(t*1.7);const br=1+0.025*Math.sin(t*3.3);sx*=br;sy*=br;}
  svg.style.transform='translate('+tx+'px,'+ty+'px) rotate('+rot.toFixed(2)+'deg) scale('+(sx*sc).toFixed(3)+','+(sy*sc).toFixed(3)+')';
  // 背景の円形の広がり
  if(k>0&&S[k].bg!==S[k-1].bg){const p=Math.min(1,Math.max(0,(t-(S[k].t0-0.06))/0.6));const e=eio(p);
    base.style.background=S[k-1].bg;wipe.style.background=S[k].bg;wipe.style.transform='scale('+(e*9).toFixed(3)+')';wipe.style.opacity=p>0?1:0;}
  else{base.style.background=sh.bg;wipe.style.opacity=0;}
  const dk=(k>0&&t<S[k].t0+0.15)?S[k-1].dark:sh.dark;const R=document.documentElement.style;
  R.setProperty('--hfg',dk?'#fff':'#0B1B33');R.setProperty('--hnews',dk?(sh.bg==='#1F5BFF'?'#0B1B33':'#7FA2FF'):'#1F5BFF');
  R.setProperty('--hsub',dk?'rgba(255,255,255,.72)':'#5B6B82');R.setProperty('--hline',dk?'rgba(255,255,255,.28)':'#DCE3EE');
 });})();""" % (json.dumps(S), json.dumps(ICONS))
    body = (f'<div id="mbase" style="position:absolute;left:-200px;right:-200px;top:-200px;bottom:-200px"></div>'
            f'<div id="mwipe" style="position:absolute;left:340px;top:460px;width:400px;height:400px;border-radius:50%;filter:blur(18px);opacity:0"></div>'
            f'<div class="mstage"><svg id="msvg" width="400" height="400" viewBox="-20 -20 240 240"><path id="mi"/>{"".join(decos)}</svg></div>'
            f'<div class="mtext">{"".join(texts)}</div>')
    css = """
.mstage{position:absolute;left:340px;top:460px;width:400px;height:400px}
#msvg{overflow:visible;transform-origin:50% 50%}
.mdg{opacity:0;animation:mdin .2s both, mdout .15s forwards}
@keyframes mdin{to{opacity:1}}@keyframes mdout{to{opacity:0}}
.mdc{opacity:0;animation:mdc .35s cubic-bezier(.2,.8,.2,1) forwards;transform-box:fill-box;transform-origin:50% 50%}
@keyframes mdc{0%{opacity:0;transform:scale(.6)}100%{opacity:1;transform:none}}
.mray{opacity:0;transform-origin:100px 100px;animation:mray .6s cubic-bezier(.2,.8,.2,1) forwards}
@keyframes mray{0%{opacity:0;transform:scale(.7) rotate(-12deg)}40%{opacity:1}100%{opacity:1;transform:none}}
.mtext{position:absolute;left:96px;right:150px;top:930px}
.mt{position:absolute;left:0;right:0;top:0}
@keyframes mtin{from{visibility:hidden}to{visibility:visible}}
@keyframes mtout{0%{opacity:1}100%{opacity:0;transform:translateY(-60px);filter:blur(8px)}}
.mk{font-size:30px;font-weight:700;letter-spacing:.08em;margin-bottom:14px;animation:fadeup .4s both}
.mbig{line-height:1.25;letter-spacing:-.03em}
.msub{font-size:36px;line-height:1.5;margin-top:18px;animation:fadeup .45s both}
.mnum{display:flex;align-items:baseline;gap:10px;animation:fadeup .35s both}
.mnum .pre{font-size:54px;font-weight:700}.mnum .mono{font-size:170px;font-weight:900;letter-spacing:-.04em;line-height:1}.mnum .u{font-size:64px;font-weight:700}
.mlogo{position:absolute;left:-96px;right:-150px;top:-300px;text-align:center;font-size:138px;font-weight:900;letter-spacing:-.02em;color:#fff;white-space:nowrap}
.ml{display:inline-block;animation:mlin .5s cubic-bezier(.2,.9,.3,1.2) both}
@keyframes mlin{0%{opacity:0;transform:translateY(80px) scale(.6)}100%{opacity:1;transform:none}}
.ldot{display:inline-block;width:34px;height:34px;margin-left:8px}
.mtag{position:absolute;left:-96px;right:-150px;top:-110px;text-align:center;font-size:36px;letter-spacing:.14em;animation:fadeup .5s both}
.mcta{position:absolute;left:150px;right:96px;top:20px;text-align:center;font-size:38px;font-weight:700;color:#0B1B33;background:#fff;border-radius:999px;padding:22px 0;animation:fadeup .5s both}
"""
    return body, css, "".join(js_parts) + js


# ───────── 変形＋移動の場面（v10） ─────────
# 画面の中央にいるアイコンが、点線の軌跡を描きながら次の地点へ飛び、カメラが追いかける。
# 着いた地点で別のアイコンに変形し、新しい背景色が円形に広がり、その地点の大きな表現（地球儀・数字と線・データの流出など）が展開する。
import math as _m

ICONS["lock_open"] = ("M58,96 V40 C58,10 78,-6 100,-6 C122,-6 142,10 142,40 V58 H126 V40 C126,22 116,10 100,10 "
                      "C84,10 74,22 74,40 V96 H158 Q168,96 168,106 V174 Q168,184 158,184 H42 Q32,184 32,174 V106 Q32,96 42,96 Z")
ANCHORS = [(0, 0), (1150, -860), (2350, 80), (3450, -900), (4600, 60), (5700, -880)]


def _rnd(seed):
    x = _m.sin(seed * 12.9898) * 43758.5453
    return x - _m.floor(x)


def t_morph(s, B, D):
    shots = s["shots"]
    n = len(shots)
    starts = list(B[-n:]) if len(B) >= n else [i * D / n for i in range(n)]
    starts[0] = 0.0
    ends = starts[1:] + [D]
    first_scene = s.get("_first", False)
    base_i = s.get("anchor_offset", 0)
    S, texts, layers, trails, js_parts = [], [], [], [], []
    for i, sh in enumerate(shots):
        bg = sh.get("bg", "white")
        dark = bg in ("blue", "navy")
        fg = sh.get("fg") or ("#FFFFFF" if dark else "#1F5BFF")
        t0, t1 = starts[i], ends[i]
        ta = t0 + (0.0 if i == 0 else 0.35)                    # 到着
        ax, ay = ANCHORS[(base_i + i) % len(ANCHORS)]
        vis = sh.get("visual", "")
        S.append({"t0": t0, "ta": ta, "bg": MBG[bg], "fg": fg, "ic": sh.get("icon", "dot"), "dark": dark,
                  "x": ax, "y": ay, "logo": bool(sh.get("logo")), "hide": vis in ("globe", "bars"),
                  "ic2": sh.get("icon2"), "t2": ta + sh.get("icon2_at", 0.6), "badge": vis in ("spark", "cards")})
        ink = "#FFFFFF" if dark else "#0B1B33"
        acc = "#A9C1FF" if bg == "navy" else ("#0B1B33" if bg == "blue" else "#1F5BFF")
        sub = "rgba(255,255,255,.78)" if dark else "#5B6B82"
        soft = "rgba(255,255,255,.22)" if dark else "rgba(31,91,255,.16)"
        L = []
        # 共通の装飾：軌道の輪・点、到着時の波紋と粒
        L.append(f'<div class="morb" style="left:{ax - 270}px;top:{ay - 270}px;border-color:{soft};animation-delay:{ta:.2f}s,{ta:.2f}s">'
                 f'<i style="background:{fg}"></i></div>')
        for k in range(3):
            L.append(f'<div class="mpulse" style="left:{ax - 150}px;top:{ay - 150}px;border-color:{fg};animation-delay:{ta + k * 0.18:.2f}s"></div>')
        for k in range(14):
            a = 2 * _m.pi * _rnd(i * 31 + k)
            r = 260 + 260 * _rnd(i * 17 + k * 3)
            sz = 10 + 18 * _rnd(i * 7 + k)
            shape = ["50%", "4px", "50% 50% 0 50%"][k % 3]
            col = fg if k % 2 == 0 else acc
            L.append(f'<b class="mpart" style="left:{ax - sz / 2:.0f}px;top:{ay - sz / 2:.0f}px;width:{sz:.0f}px;height:{sz:.0f}px;border-radius:{shape};'
                     f'background:{col};--dx:{r * _m.cos(a):.0f}px;--dy:{r * _m.sin(a):.0f}px;--rr:{int(360 * _rnd(k + i))}deg;animation-delay:{ta + 0.05 + k * 0.02:.2f}s"></b>')
        # 地点ごとの大きな表現
        if vis == "globe":
            o = globe_opts("zoom", sh, ta + 0.15, max(1.4, (t1 - ta) - 0.45), 640, 640)
            o["keys"][0]["scale"] = 137
            o["keys"][1]["scale"] = 260
            o["stages"] = None
            o["until"] = t1 + 1.2
            L.append(f'<div class="gl mglobe" id="mg{i}" style="left:{ax - 320}px;top:{ay - 320}px;width:640px;height:640px;animation-delay:{ta + 0.1:.2f}s"></div>')
            js_parts.append(f"__tick.push(QNGlobe(document.getElementById('mg{i}'),{json.dumps(o, ensure_ascii=False)}));")
        elif vis == "spark":
            L.append(f'<svg class="mspark" style="left:{ax - 470}px;top:{ay - 230}px" width="940" height="460" viewBox="0 0 940 460">'
                     f'<path d="M0,430 C150,410 240,370 340,300 S560,170 660,140 S860,40 940,18" pathLength="1" style="stroke:{fg};animation-delay:{ta:.2f}s"/>'
                     f'<circle cx="940" cy="18" r="16" fill="{fg}" class="mdotg" style="animation-delay:{ta + 1.0:.2f}s"/></svg>')
            L.append(f'<div class="mbignum" style="left:{ax - 470}px;top:{ay - 90}px;width:940px;color:{acc};animation-delay:{ta + 0.1:.2f}s">'
                     f'<span class="pre" style="color:{ink}">{esc(sh.get("prefix", ""))}</span><span id="mn{i}" class="mono">0</span><span class="u">{esc(sh.get("unit", ""))}</span></div>')
            js_parts.append(counter_js(f"mn{i}", sh["number"], ta + 0.15, 0.9, sh.get("decimals", 0)))
        elif vis == "records":
            for k in range(10):
                a = -_m.pi * 0.85 + _m.pi * 1.7 * k / 9
                L.append(f'<div class="mrec" style="left:{ax - 70}px;top:{ay - 30}px;--dx:{420 * _m.cos(a) + 120:.0f}px;--dy:{380 * _m.sin(a) - 40:.0f}px;'
                         f'--rr:{int(-20 + 40 * _rnd(k + 5))}deg;animation-delay:{ta + 0.75 + k * 0.08:.2f}s"><svg width="30" height="30" viewBox="0 0 34 34">'
                         f'<circle cx="17" cy="12" r="6" fill="none" stroke="#1F5BFF" stroke-width="3"/><path d="M6,30 Q17,18 28,30" fill="none" stroke="#1F5BFF" stroke-width="3" stroke-linecap="round"/></svg><b></b></div>')
            if sh.get("number") is not None:
                L.append(f'<div class="mchipn" style="left:{ax + 60}px;top:{ay + 210}px;animation-delay:{ta + 1.3:.2f}s">'
                         f'{esc(sh.get("prefix", ""))} <span id="mn{i}">0</span>{esc(sh.get("unit", ""))}</div>')
                js_parts.append(counter_js(f"mn{i}", sh["number"], ta + 1.3, 0.8, 0))
        elif vis == "bars":
            labels = sh.get("bar_labels", ["", "", ""])
            for k, (h, lab) in enumerate(zip((150, 230, 320), labels)):
                x = ax - 270 + k * 200
                L.append(f'<div class="mbar" style="left:{x}px;top:{ay + 170 - h}px;height:{h}px;background:{fg};animation-delay:{ta + 0.2 + k * 0.18:.2f}s"></div>'
                         f'<div class="mbarl" style="left:{x - 40}px;top:{ay + 190}px;color:{sub};animation-delay:{ta + 0.35 + k * 0.18:.2f}s">{esc(lab)}</div>')
            L.append(f'<svg class="mspark" style="left:{ax - 290}px;top:{ay - 230}px" width="600" height="420" viewBox="0 0 600 420">'
                     f'<path d="M20,330 L190,250 L390,170 L580,40" pathLength="1" style="stroke:{acc};stroke-width:8;animation-delay:{ta + 0.8:.2f}s"/></svg>')
        elif vis == "cards":
            for k in range(5):
                L.append(f'<div class="mcard" style="left:{ax - 120}px;top:{ay - 80}px;--rr:{-36 + k * 18}deg;--dx:{-200 + k * 100}px;animation-delay:{ta + 0.15 + k * 0.06:.2f}s"><i></i><b></b><b style="width:50px"></b></div>')
            if sh.get("number") is not None:
                L.append(f'<div class="mbignum" style="left:{ax - 470}px;top:{ay + 10}px;width:940px;color:{acc};font-size:0;animation-delay:{ta + 0.2:.2f}s">'
                         f'<span class="pre" style="color:{ink}">{esc(sh.get("prefix", ""))}</span><span id="mn{i}" class="mono">0</span><span class="u">{esc(sh.get("unit", ""))}</span></div>')
                js_parts.append(counter_js(f"mn{i}", sh["number"], ta + 0.25, 0.9, sh.get("decimals", 0)))
        L.append(f'<div class="mdeco" style="left:{ax - 200}px;top:{ay - 200}px;animation-delay:{ta + 0.3:.2f}s,{t1 - 0.1:.2f}s">'
                 f'<svg width="400" height="400" viewBox="-20 -20 240 240">{deco(sh.get("icon", "dot"), fg, MBG[bg], ta + 0.3, sh.get("deco", ""))}</svg></div>'
                 if not sh.get("icon2") and vis not in ("globe", "bars", "spark", "cards") else "")
        if sh.get("icon2") == "lock_open":
            L.append(f'<div class="mdeco" style="left:{ax - 200}px;top:{ay - 200}px;animation-delay:{ta + sh.get("icon2_at", 0.6) + 0.25:.2f}s,{t1 - 0.1:.2f}s">'
                     f'<svg width="400" height="400" viewBox="-20 -20 240 240"><g fill="{MBG[bg]}"><circle cx="100" cy="132" r="13"/><rect x="94" y="132" width="12" height="28" rx="6"/></g></svg></div>')
        layers.append("".join(L))
        # 前の地点からの点線の軌跡
        if i > 0:
            px, py = S[i - 1]["x"], S[i - 1]["y"]
            cx, cy = (px + ax) / 2 + (ay - py) * 0.35, (py + ay) / 2 - (ax - px) * 0.35
            dots = ""
            for k in range(1, 34):
                u = k / 34
                x = (1 - u) ** 2 * px + 2 * (1 - u) * u * cx + u * u * ax
                y = (1 - u) ** 2 * py + 2 * (1 - u) * u * cy + u * u * ay
                dots += f'<i class="mtd" style="left:{x - 5:.0f}px;top:{y - 5:.0f}px;animation-delay:{t0 - 0.2 + u * 0.55:.2f}s"></i>'
            trails.append(dots)
            S[i]["cx"], S[i]["cy"] = cx, cy
        # 画面に固定した文字（移動の向きから入って、反対へ抜ける）
        tin = -1.0 if (i == 0 and first_scene) else ta + 0.05
        body = ""
        if sh.get("logo"):
            letters = "".join(f'<span class="ml" style="animation-delay:{ta + 0.25 + k * 0.05:.2f}s{";color:#7FA2FF" if k >= 6 else ""}">{"&nbsp;" if ch == " " else esc(ch)}</span>'
                              for k, ch in enumerate("QUICK NEWS"))
            body = (f'<div class="mlogo">{letters}<span class="ldot"></span></div>'
                    f'<div class="mtag" style="animation-delay:{ta + 0.9:.2f}s;color:{sub}">{esc(sh.get("tagline", "1日1分で社会がわかる"))}</div>'
                    f'<div class="mcta" style="animation-delay:{ta + 1.2:.2f}s">{esc(sh.get("cta", "フォローして毎朝の習慣に"))}</div>')
        else:
            if sh.get("kicker"):
                body += f'<div class="mk" style="animation-delay:{tin:.2f}s;color:{acc}">{esc(sh["kicker"])}</div>'
            if sh.get("number") is not None and vis not in ("spark", "records", "cards"):
                body += (f'<div class="mnum" style="animation-delay:{tin:.2f}s;color:{ink}"><span class="pre">{esc(sh.get("prefix", ""))}</span>'
                         f'<span id="mn{i}" class="mono" style="color:{acc}">0</span><span class="u" style="color:{acc}">{esc(sh.get("unit", ""))}</span></div>')
                js_parts.append(counter_js(f"mn{i}", sh["number"], ta + 0.2, 0.9, sh.get("decimals", 0)))
            if sh.get("big"):
                body += kin(sh["big"], tin + 0.05, "mbig", 0.08, f"position:relative;left:0;right:0;font-size:{sh.get('size', 92)}px;color:{ink}").replace(
                    'class="ph acc"', f'class="ph acc" data-c="{acc}"')
            if sh.get("sub"):
                body += f'<div class="msub" style="animation-delay:{tin + 0.3:.2f}s;color:{sub}">{esc(sh["sub"])}</div>'
        out_anim = f",mtout .26s {t1 - 0.22:.2f}s cubic-bezier(.5,0,.75,0) forwards" if i < n - 1 else ""
        texts.append(f'<div class="mt" style="animation:mtin .01s {(-0.1 if tin < 0 else tin):.2f}s both{out_anim}">{body}</div>')

    # 遠景の図形（ゆっくり流れて奥行きを出す）
    far = ""
    for k in range(70):
        x = -1400 + 8200 * _rnd(k * 3 + 1)
        y = -2200 + 3400 * _rnd(k * 5 + 2)
        sz = 8 + 46 * _rnd(k * 7 + 3) ** 2
        kind = k % 4
        style = ["border-radius:50%", "border-radius:6px;transform:rotate(25deg)", "border-radius:50%;background:transparent;border:3px solid currentColor", "border-radius:50% 50% 0 50%"][kind]
        far += f'<i class="mfar" style="left:{x:.0f}px;top:{y:.0f}px;width:{sz:.0f}px;height:{sz:.0f}px;{style}"></i>'

    js = """
(function(){const S=%(S)s;const P=%(P)s;
 const icon=document.getElementById('mi'),ic=document.getElementById('mic'),world=document.getElementById('mworld'),farL=document.getElementById('mfarL'),
   base=document.getElementById('mbase'),wipe=document.getElementById('mwipe');
 const I=[];for(let i=1;i<S.length;i++)I.push(S[i].ic===S[i-1].ic?null:flubber.interpolate(P[S[i-1].ic],P[S[i].ic],{maxSegmentLength:3}));
 const I2=S.map(s=>s.ic2?flubber.interpolate(P[s.ic],P[s.ic2],{maxSegmentLength:3}):null);
 const eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
 const eob=x=>{const c1=1.4,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2);};
 document.querySelectorAll('.mbig .acc').forEach(e=>{if(e.dataset.c)e.style.color=e.dataset.c;});
 const q=(a,b,c,u)=>(1-u)*(1-u)*a+2*(1-u)*u*b+u*u*c;
 __tick.push(t=>{
  let k=0;for(let i=0;i<S.length;i++)if(t>=S[i].t0-0.2)k=i;
  const sh=S[k];
  // 移動：アイコンは軌跡に沿って先に飛び、カメラは少し遅れて追う
  let ix=sh.x,iy=sh.y,camx=sh.x,camy=sh.y,zoom=1,crot=0,fly=0;
  if(k>0){const a=S[k-1];const p=Math.min(1,Math.max(0,(t-(sh.t0-0.2))/0.6));fly=p;
    const ei=eio(Math.min(1,p*1.12));ix=q(a.x,sh.cx,sh.x,ei);iy=q(a.y,sh.cy,sh.y,ei);
    const ec=eio(p);camx=a.x+(sh.x-a.x)*ec;camy=a.y+(sh.y-a.y)*ec;
    zoom=1-0.22*Math.sin(Math.PI*p);crot=(sh.x>a.x?-1:1)*4*Math.sin(Math.PI*p);}
  else{const p=Math.min(1,Math.max(0,(t+0.1)/0.6));zoom=0.86+0.14*eob(p);}
  const tEnd=(k+1<S.length?S[k+1].t0:%(D)s);const prog=Math.min(1,Math.max(0,(t-sh.ta)/Math.max(0.5,tEnd-sh.ta)));
  zoom*=1+0.09*prog;const drift=Math.sin(t*0.9)*14+40*(prog-0.5)*(k%%2?1:-1);
  world.style.transform='rotate('+crot.toFixed(2)+'deg) scale('+zoom.toFixed(3)+') translate('+(-camx+drift).toFixed(1)+'px,'+(-camy).toFixed(1)+'px)';
  farL.style.transform='scale('+zoom.toFixed(3)+') translate('+(-camx*0.35).toFixed(1)+'px,'+(-camy*0.35).toFixed(1)+'px)';
  farL.style.color=sh.dark?'rgba(255,255,255,.14)':'rgba(31,91,255,.10)';
  // 変形
  let d=P[sh.ic],sx=1,sy=1,rot=0,op=1,sc=1,bx=0,by=0;
  if(k>0){const p=Math.min(1,Math.max(0,(t-(sh.t0-0.05))/0.55));if(I[k-1]&&p<1)d=I[k-1](eio(p));
    const w=Math.sin(Math.PI*Math.min(1,fly*1.1));sx=1+0.22*w;sy=1-0.16*w;rot=(sh.x>S[k-1].x?18:-18)*w;}
  if(sh.ic2&&t>sh.t2){const p=Math.min(1,(t-sh.t2)/0.45);d=I2[k](eob(p)>1?1:eob(p));if(p>=1)d=P[sh.ic2];}
  if(sh.hide){op=1-Math.min(1,Math.max(0,(t-sh.ta-0.25)/0.3));}
  if(sh.badge){const p=eio(Math.min(1,Math.max(0,(t-sh.ta-0.1)/0.5)));sc=1-0.62*p;bx=-330*p;by=-260*p;}
  if(sh.logo){const dot=document.querySelector('.ldot');if(dot){const r=dot.getBoundingClientRect(),qq=ic.getBoundingClientRect();
    const p=eio(Math.min(1,Math.max(0,(t-sh.ta-0.2)/0.6)));sc=1-0.9*p;bx=(r.left+r.width/2-(qq.left+qq.width/2))*p/zoom;by=(r.top+r.height/2-(qq.top+qq.height/2))*p/zoom;}}
  icon.setAttribute('d',d);icon.setAttribute('fill',(k>0&&t<sh.t0+0.1)?S[k-1].fg:sh.fg);
  ic.style.opacity=op;
  ic.style.transform='translate('+(ix-200+bx).toFixed(1)+'px,'+(iy-200+by).toFixed(1)+'px) rotate('+rot.toFixed(2)+'deg) scale('+(sx*sc).toFixed(3)+','+(sy*sc).toFixed(3)+')';
  // 背景色：着いた瞬間に円形に広がる
  if(k>0&&sh.bg!==S[k-1].bg){const p=Math.min(1,Math.max(0,(t-(sh.ta-0.05))/0.6));const e=eio(p);
    base.style.background=S[k-1].bg;wipe.style.background=sh.bg;wipe.style.transform='scale('+(e*10).toFixed(3)+')';wipe.style.opacity=p>0?1:0;}
  else{base.style.background=sh.bg;wipe.style.opacity=0;}
  const dk=(k>0&&t<sh.ta+0.15)?S[k-1].dark:sh.dark;const R=document.documentElement.style;
  R.setProperty('--hfg',dk?'#fff':'#0B1B33');R.setProperty('--hnews',dk?(sh.bg==='#1F5BFF'&&t>=sh.ta+0.15?'#0B1B33':'#7FA2FF'):'#1F5BFF');
  R.setProperty('--hsub',dk?'rgba(255,255,255,.72)':'#5B6B82');R.setProperty('--hline',dk?'rgba(255,255,255,.28)':'#DCE3EE');
  document.querySelectorAll('.mtd').forEach(e=>e.style.background=sh.dark&&t>sh.ta?'rgba(255,255,255,.6)':'rgba(11,27,51,.35)');
 });})();""" % dict(S=json.dumps(S), P=json.dumps(ICONS), D=D)
    body = (f'<div id="mbase" style="position:absolute;left:-300px;right:-300px;top:-300px;bottom:-300px"></div>'
            f'<div id="mwipe" style="position:absolute;left:390px;top:490px;width:300px;height:300px;border-radius:50%;filter:blur(20px);opacity:0"></div>'
            f'<div class="mvp"><div id="mfarL" class="mlayer">{far}</div>'
            f'<div id="mworld" class="mlayer">{"".join(trails)}{"".join(layers)}'
            f'<div id="mic" class="mic"><svg width="400" height="400" viewBox="-20 -20 240 240"><path id="mi"/></svg></div></div></div>'
            f'<div class="mtext">{"".join(texts)}</div>')
    css = """
.mvp{position:absolute;left:540px;top:640px;width:0;height:0}
.mlayer{position:absolute;left:0;top:0;width:0;height:0;transform-origin:0 0}
.mic{position:absolute;left:0;top:0;width:400px;height:400px;transform-origin:200px 200px}
.mic svg{overflow:visible}
.mfar{position:absolute;background:currentColor;display:block}
.mtd{position:absolute;width:10px;height:10px;border-radius:50%;opacity:0;animation:mtd .2s forwards}
@keyframes mtd{0%{opacity:0;transform:scale(0)}100%{opacity:1;transform:none}}
.morb{position:absolute;width:540px;height:540px;border-radius:50%;border:3px dashed;opacity:0;animation:morbin .6s cubic-bezier(.2,.8,.2,1) forwards, morbrot 9s linear infinite}
.morb i{position:absolute;left:50%;top:-12px;width:22px;height:22px;margin-left:-11px;border-radius:50%}
@keyframes morbin{0%{opacity:0;transform:scale(.5) rotate(-60deg)}100%{opacity:1;transform:none}}
@keyframes morbrot{to{rotate:360deg}}
.mpulse{position:absolute;width:300px;height:300px;border-radius:50%;border:4px solid;opacity:0;animation:mpulse 1s ease-out forwards}
@keyframes mpulse{0%{opacity:.7;transform:scale(.4)}100%{opacity:0;transform:scale(2.2)}}
.mpart{position:absolute;display:block;opacity:0;animation:mpart 1.1s cubic-bezier(.15,.8,.25,1) forwards, mfloat 3s 1.1s ease-in-out infinite alternate}
@keyframes mpart{0%{opacity:0;transform:translate(0,0) scale(.2) rotate(0)}30%{opacity:1}100%{opacity:.9;transform:translate(var(--dx),var(--dy)) scale(1) rotate(var(--rr))}}
@keyframes mfloat{from{translate:0 0}to{translate:0 -18px}}
.mglobe{border-radius:50%;opacity:0;animation:mglobe .5s cubic-bezier(.2,.8,.2,1) forwards;-webkit-mask-image:none;box-shadow:0 40px 90px rgba(0,0,0,.18)}
@keyframes mglobe{0%{opacity:0;transform:scale(.42)}100%{opacity:1;transform:none}}
.mspark{position:absolute;overflow:visible}
.mspark path{fill:none;stroke-width:10;stroke-linecap:round;stroke-dasharray:1;stroke-dashoffset:1;animation:ddraw 1.1s cubic-bezier(.4,0,.2,1) forwards}
.mdotg{opacity:0;animation:dfade .3s forwards;filter:drop-shadow(0 0 16px rgba(31,91,255,.9))}
.mbignum{position:absolute;display:flex;align-items:baseline;justify-content:center;gap:12px;animation:mbn .6s cubic-bezier(.2,.9,.3,1.2) both}
.mbignum .pre{font-size:60px;font-weight:700}.mbignum .mono{font-size:200px;font-weight:900;letter-spacing:-.04em;line-height:1}.mbignum .u{font-size:74px;font-weight:700}
@keyframes mbn{0%{opacity:0;transform:scale(1.6);filter:blur(14px)}100%{opacity:1;transform:none;filter:none}}
.mrec{position:absolute;display:flex;align-items:center;gap:10px;background:#fff;border-radius:16px;padding:10px 18px;box-shadow:0 18px 40px rgba(0,0,0,.25);
opacity:0;animation:mrec 1.2s cubic-bezier(.15,.8,.25,1) forwards}
.mrec b{display:block;width:80px;height:12px;border-radius:6px;background:#D5DDE9}
@keyframes mrec{0%{opacity:0;transform:scale(.4)}20%{opacity:1}100%{opacity:1;transform:translate(var(--dx),var(--dy)) rotate(var(--rr))}}
.mchipn{position:absolute;white-space:nowrap;background:#E8433A;color:#fff;font-size:44px;font-weight:900;border-radius:999px;padding:14px 34px;
box-shadow:0 18px 40px rgba(232,67,58,.4);animation:mbn .5s cubic-bezier(.2,.9,.3,1.2) both}
.mbar{position:absolute;width:120px;border-radius:18px 18px 6px 6px;transform-origin:50% 100%;animation:mbar .7s cubic-bezier(.2,.9,.3,1.15) both}
@keyframes mbar{0%{transform:scaleY(0)}100%{transform:none}}
.mbarl{position:absolute;width:200px;text-align:center;font-size:26px;font-weight:700;white-space:nowrap;animation:fadeup .4s both}
.mcard{position:absolute;width:240px;height:160px;border-radius:22px;background:#fff;border:2px solid #DCE3EE;box-shadow:0 20px 44px rgba(20,40,90,.16);
padding:28px;opacity:0;animation:mcard .7s cubic-bezier(.2,.9,.3,1.1) forwards}
.mcard i{display:block;width:44px;height:44px;border-radius:50%;background:#E8EFFF;margin-bottom:14px}
.mcard b{display:block;width:120px;height:12px;border-radius:6px;background:#D5DDE9;margin-top:10px}
@keyframes mcard{0%{opacity:0;transform:scale(.3)}100%{opacity:1;transform:translate(var(--dx),-250px) rotate(var(--rr))}}
.mdeco{position:absolute;width:400px;height:400px;opacity:0;animation:mdin .2s forwards, mdout .15s forwards}
@keyframes mdin{to{opacity:1}}@keyframes mdout{to{opacity:0}}
.mdeco svg{overflow:visible}
.mtext{position:absolute;left:96px;right:150px;top:990px}
.mt{position:absolute;left:0;right:0;top:0}
@keyframes mtin{from{visibility:hidden}to{visibility:visible}}
@keyframes mtout{0%{opacity:1}100%{opacity:0;transform:translateX(-140px);filter:blur(10px)}}
.mk{font-size:30px;font-weight:700;letter-spacing:.08em;margin-bottom:14px;animation:mtx .5s cubic-bezier(.2,.8,.2,1) both}
@keyframes mtx{0%{opacity:0;transform:translateX(140px)}100%{opacity:1;transform:none}}
.mbig{line-height:1.25;letter-spacing:-.03em}
.mbig .ph{animation:mph .55s cubic-bezier(.2,.9,.3,1.1) both}
@keyframes mph{0%{opacity:0;transform:translateX(160px) skewX(-12deg);filter:blur(10px)}100%{opacity:1;transform:none;filter:none}}
.msub{font-size:36px;line-height:1.5;margin-top:18px;animation:mtx .5s cubic-bezier(.2,.8,.2,1) both}
.mnum{display:flex;align-items:baseline;gap:10px;animation:mtx .45s both}
.mnum .pre{font-size:54px;font-weight:700}.mnum .mono{font-size:170px;font-weight:900;letter-spacing:-.04em;line-height:1}.mnum .u{font-size:64px;font-weight:700}
.mlogo{position:absolute;left:-96px;right:-150px;top:-380px;text-align:center;font-size:138px;font-weight:900;letter-spacing:-.02em;color:#fff;white-space:nowrap}
.ml{display:inline-block;animation:mlin .55s cubic-bezier(.2,.9,.3,1.25) both}
@keyframes mlin{0%{opacity:0;transform:translateY(120px) rotate(18deg) scale(.5)}100%{opacity:1;transform:none}}
.ldot{display:inline-block;width:34px;height:34px;margin-left:8px}
.mtag{position:absolute;left:-96px;right:-150px;top:-190px;text-align:center;font-size:36px;letter-spacing:.14em;animation:fadeup .5s both}
.mcta{position:absolute;left:150px;right:96px;top:-60px;text-align:center;font-size:38px;font-weight:700;color:#0B1B33;background:#fff;border-radius:999px;padding:22px 0;animation:fadeup .5s both}
"""
    return body, css, "".join(js_parts) + js



def t_list(s, B, D):
    """一覧表：行が順に入り、状態ピルが付く."""
    rows = s["rows"]
    n = len(rows)
    span = max(0.25, (D - 1.0) / n)
    rh = []
    for i, r in enumerate(rows):
        t = 0.35 + i * span
        st = r.get("state", "")
        neg = r.get("neg", False)
        rh.append(f'<div class="row" style="animation-delay:{t:.2f}s"><span class="rli" style="--t:{t + 0.1:.2f}s">{picto(r.get("icon", ""), 52, t + 0.1, "var(--blue)", 3) or row_icon(r.get("icon", ""))}</span><span class="rl">{esc(r["label"])}</span>'
                  f'<span class="pill{" neg" if neg else ""}" style="animation-delay:{t + 0.18:.2f}s">{esc(st)}</span></div>')
    body = (kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px") + f'<div class="tbl card">{"".join(rh)}</div>')
    css = """
.tbl{position:absolute;left:96px;right:150px;top:480px;padding:12px 40px}
.row{display:flex;align-items:center;justify-content:space-between;height:124px;border-bottom:1px solid var(--line);animation:fadeup .4s both}
.row:last-child{border-bottom:none}
.rl{font-size:46px;font-weight:700;margin-right:auto}
.rli{width:72px;height:72px;border-radius:20px;background:var(--pale);display:flex;align-items:center;justify-content:center;margin-right:26px;flex:none}
.ri path,.ri circle,.ri rect{fill:none;stroke:var(--blue);stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:200;stroke-dashoffset:200;animation:ridraw .9s var(--t) cubic-bezier(.4,0,.2,1) forwards}
@keyframes ridraw{to{stroke-dashoffset:0}}
.pill{font-size:28px;font-weight:700;letter-spacing:.08em;padding:10px 24px;border-radius:999px;background:var(--blue);color:#fff;animation:pillin .3s cubic-bezier(.2,1.4,.4,1) both}
.pill.neg{background:#EEF1F6;color:var(--sub)}
@keyframes pillin{0%{transform:scale(.4);opacity:0}100%{transform:none;opacity:1}}
"""
    return body, css, ""


def t_quotes(s, B, D):
    """発言の要旨：話し手（肩書き・名前）と、報道による発言の要旨を細い線で組む。
    実在の人物の言葉を合成音声で「本人の発言」のように見せない（TikTok の AI 生成コンテンツ規定で違反になった）：
    引用符は使わず、見出しの下に「※ ○○の報道による発言の要旨。読み上げは合成音声」と必ず出す。via＝報道元（省略時は場面の source）."""
    qs = s["quotes"]
    n = len(qs)
    starts = list(B[-n:]) if len(B) >= n else [0.3 + i * (D - 1) / n for i in range(n)]
    via = s.get("via") or s.get("source", "")
    parts = [kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px"),
             f'<div class="qnote" style="top:516px">※ {esc(via)}の報道による発言の要旨です。読み上げは合成音声です。</div>']
    y = 516 + (36 if len(via) < 14 else 70) + 26
    for i, q in enumerate(qs):
        t = max(0.35, starts[i] + 0.05)
        parts.append(f'<div class="qt" style="top:{y}px;--t:{t:.2f}s">'
                     f'<div class="qwho"><b>{esc(q["who"])}</b>{esc(q.get("role", ""))}</div>'
                     f'<div class="qtx">{esc(q["text"])}</div></div>')
        lines = -(-len(q["text"]) // 16)          # 1行およそ16字（48px・幅796px）
        y += 46 + lines * 66 + 38
    css = """
.qnote{position:absolute;left:96px;right:96px;font-size:24px;color:var(--sub);font-weight:700;letter-spacing:.02em;line-height:1.45;opacity:0;animation:qin .5s .3s both}
.qt{position:absolute;left:96px;right:150px;padding-left:34px;border-left:4px solid var(--blue);animation:qin .55s var(--t) cubic-bezier(.2,.8,.2,1) both}
@keyframes qin{0%{opacity:0;transform:translateY(40px);filter:blur(8px)}100%{opacity:1;transform:none;filter:none}}
.qwho{font-size:28px;color:var(--sub);font-weight:700;letter-spacing:.06em;display:flex;gap:14px;align-items:baseline}
.qwho b{color:var(--blue);font-size:30px}
.qtx{font-size:48px;font-weight:700;line-height:1.38;letter-spacing:-.01em;margin-top:14px}
"""
    return "".join(parts), css, ""


def t_phone(s, B, D):
    """スマホに通知が届き、注意ラベルが付く（明るい配色）."""
    nt = s["notification"]
    body = (kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px") +
            f'''<div class="phone"><div class="notch"></div><div class="scr"><div class="clock mono">7:30</div>
<div class="note"><div class="ic">✉</div><div><div class="fr">{esc(nt["from"])}</div><div class="ms">{esc(nt["text"])}</div></div></div></div></div>
<div class="warn" style="animation-delay:{max(1.2, D * 0.45):.2f}s">{esc(s["label"])}</div>''')
    css = """
.phone{position:absolute;left:300px;top:470px;width:480px;height:700px;border-radius:64px;background:#fff;border:12px solid #E3E8F0;
box-shadow:0 30px 80px rgba(20,40,90,.16);overflow:hidden;animation:phin .6s cubic-bezier(.2,.9,.2,1) both}
@keyframes phin{0%{transform:translateY(120px);opacity:0}100%{transform:none;opacity:1}}
.notch{position:absolute;left:50%;top:14px;width:130px;height:30px;margin-left:-65px;background:#E3E8F0;border-radius:16px}
.scr{position:absolute;inset:0;background:linear-gradient(180deg,#EEF3FF,#F8FAFD);padding:96px 22px}
.clock{font-size:96px;text-align:center;font-weight:400;color:var(--ink);margin-bottom:30px}
.note{display:flex;gap:16px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:24px;padding:22px;
box-shadow:0 10px 30px rgba(20,40,90,.08);animation:nin .45s .5s cubic-bezier(.2,1.2,.3,1) both}
@keyframes nin{0%{transform:translateY(-300px);opacity:0}100%{transform:none;opacity:1}}
.note .ic{width:60px;height:60px;border-radius:16px;background:var(--pale);color:var(--blue);font-size:34px;display:flex;align-items:center;justify-content:center;flex:none}
.note .fr{font-size:22px;color:var(--sub)}.note .ms{font-size:30px;font-weight:700;line-height:1.35}
.warn{position:absolute;left:240px;right:210px;top:1020px;text-align:center;font-size:40px;font-weight:700;color:var(--warn);
background:#fff;border:3px solid var(--warn);border-radius:999px;padding:16px 0;box-shadow:0 14px 40px rgba(217,58,58,.18);animation:pillin .35s cubic-bezier(.2,1.4,.4,1) both}
@keyframes pillin{0%{transform:scale(.4);opacity:0}100%{transform:none;opacity:1}}
"""
    return body, css, ""


def t_zoom(s, B, D):
    """デジタルズーム：枠が段階的に寄り、座標ラベルとピン."""
    stages = s["stages"]
    n = len(stages)
    k = 2.6
    step = min(0.7, max(0.38, (D * 0.55) / n))
    frames = []
    for i, st in enumerate(stages):
        size = 560 / (k ** i)
        bw = 2.5 / (k ** i)
        fs = 24 / (k ** i)
        frames.append(f'<div class="zf" style="width:{size:.2f}px;height:{size:.2f}px;margin:{-size / 2:.2f}px 0 0 {-size / 2:.2f}px;border-width:{bw:.3f}px">'
                      f'<span style="font-size:{fs:.3f}px;padding:{4 / k ** i:.3f}px {10 / k ** i:.3f}px">{esc(st)}</span></div>')
    tot = step * (n - 1) + 0.3
    kf = []
    for i in range(n):
        kf.append(f"{min(100, i * step / tot * 100):.1f}%{{transform:scale({k ** i:.3f})}}")
        if i < n - 1:
            kf.append(f"{min(100, (i * step + step * 0.45) / tot * 100):.1f}%{{transform:scale({k ** i:.3f})}}")
    kf.append(f"100%{{transform:scale({k ** (n - 1):.3f})}}")
    pin_t = tot + 0.15
    body = (f'<div class="zwrap card"><div class="zdots"></div><div class="zin">{"".join(frames)}</div>'
            f'<div class="coord mono">{esc(s.get("coord", ""))}</div><div class="pin" style="animation-delay:{pin_t:.2f}s"><i></i></div></div>'
            + kin(s["title"], pin_t + 0.15, "", 0.12, "top:1030px;font-size:84px"))
    css = """
.zwrap{position:absolute;left:96px;right:150px;top:300px;height:700px;overflow:hidden}
.zin{position:absolute;left:417px;top:350px;width:0;height:0;animation:zz %(tot).2fs .2s cubic-bezier(.65,0,.25,1) both}
@keyframes zz{%(kf)s}
.zf{position:absolute;left:0;top:0;border:solid var(--blue);border-radius:2%%}
.zf span{position:absolute;left:0;top:0;background:var(--blue);color:#fff;white-space:nowrap;font-weight:700;letter-spacing:.06em}
.zdots{position:absolute;inset:0;background-image:radial-gradient(#D3DCEC 2px,transparent 2px);background-size:26px 26px}
.coord{position:absolute;right:26px;bottom:22px;font-size:22px;color:var(--sub)}
.pin{position:absolute;left:417px;top:350px;animation:pinin .5s cubic-bezier(.2,1.5,.4,1) both}
.pin i{position:absolute;left:-14px;top:-14px;width:28px;height:28px;border-radius:50%%;background:var(--blue);box-shadow:0 0 0 10px rgba(31,91,255,.18),0 0 0 26px rgba(31,91,255,.08)}
@keyframes pinin{0%%{transform:scale(0)}100%%{transform:none}}
""" % dict(tot=tot, kf="".join(kf))
    return body, css, ""


def t_term(s, B, D):
    """今日の用語。members があれば、世界地図で加盟国が順に光り、下のチップと連動する（例：G7）."""
    mem = s.get("members")
    if not mem:
        body = (f'<div class="eyebrow" style="top:420px">{esc(s.get("eyebrow", "今日の用語"))}</div>'
                + kin(s["term"], 0.25, "", 0.12, "top:470px;font-size:" + ("136px" if s.get("icon") and len(s["term"]) <= 4 else "150px"))
                + f'<div class="rd">{esc(s.get("reading", ""))}</div><div class="df">{esc(s.get("definition", ""))}</div>'
                + (f'<div class="pgc" style="--t:.35s;position:absolute;right:110px;top:392px;width:290px;height:290px">{picto(s["icon"], 190, 0.55, "var(--blue)", 2.0)}</div>' if s.get("icon") and len(s["term"]) <= 4 else "")
                + (f'<div class="pgc" style="--t:.8s;position:absolute;left:96px;top:950px;width:140px;height:140px">{picto(s["icon"], 92, 1.0, "var(--blue)", 2.6)}</div>' if s.get("icon") and len(s["term"]) > 4 else ""))
        css = """
.rd{position:absolute;left:100px;top:680px;font-size:30px;color:var(--sub);letter-spacing:.14em;animation:fadeup .5s .6s both}
.df{position:absolute;left:96px;right:150px;top:760px;font-size:42px;line-height:1.7;font-weight:500;padding-top:28px;border-top:2px solid var(--line);animation:fadeup .5s .85s both}
"""
        return body, css, ""
    ex = s.get("extra")
    n = len(mem) + (1 if ex else 0)
    span = max(1.6, min(2.4, D - 1.6))
    step = span / n
    t_m = [0.75 + k * step for k in range(len(mem))]
    t_ex = 0.75 + len(mem) * step if ex else None
    chips = ""
    for k, m in enumerate(mem):
        chips += f'<div class="tchip" style="--t:{t_m[k]:.2f}s"><b>{k + 1}</b>{esc(m["label"])}</div>'
    if ex:
        chips += f'<div class="tchip ex" style="--t:{t_ex:.2f}s"><b>＋</b>{esc(ex["label"])}</div>'
    body = (f'<div class="eyebrow" style="top:352px">{esc(s.get("eyebrow", "今日の用語"))}</div>'
            + kin(s["term"], 0.2, "", 0.12, "top:388px;font-size:138px;line-height:1")
            + f'<div class="rd2">{esc(s.get("reading", ""))}</div>'
            f'<div class="tmap card"><svg id="tm" width="834" height="340"></svg></div><div class="tchips">{chips}</div>')
    cfg = {"mem": [{"id": m["id"], "at": m["at"], "t": t_m[k]} for k, m in enumerate(mem)],
           "ex": ({"ids": ex["ids"], "t": t_ex} if ex else None)}
    js = """(function(){const C=%s;const ns='http://www.w3.org/2000/svg',svg=document.getElementById('tm'),W=834,H=340;
 const mk=(tag,a,par)=>{const e=document.createElementNS(ns,tag);for(const k in a)e.setAttribute(k,a[k]);(par||svg).appendChild(e);return e;};
 const feats=topojson.feature(WORLD,WORLD.objects.countries).features.filter(f=>String(f.id)!=='010');
 const proj=d3.geoEqualEarth().rotate([-12,0]).fitExtent([[10,10],[W-10,H-10]],{type:'MultiPoint',coordinates:[[-128,-34],[152,-34],[-128,80],[152,80],[12,82]]});const path=d3.geoPath(proj);
 const pid=x=>String(x).padStart(3,'0');
 const exIds=new Set(C.ex?C.ex.ids.map(pid):[]),memIds=C.mem.map(m=>pid(m.id));
 mk('path',{d:path({type:'Sphere'}),fill:'#F7F9FD',stroke:'#E3E9F3','stroke-width':1.5});
 const base=feats.map(f=>({f,id:pid(f.id),el:mk('path',{d:path(f),fill:'#DCE4F0',stroke:'#FFFFFF','stroke-width':0.6})}));
 const exEls=base.filter(b=>exIds.has(b.id)&&!memIds.includes(b.id));
 const mems=C.mem.map(m=>{const b=base.find(x=>x.id===pid(m.id));const xy=proj(m.at);
   const ring=mk('circle',{cx:xy[0],cy:xy[1],r:10,fill:'none',stroke:'#1F5BFF','stroke-width':3,opacity:0});
   const dot=mk('circle',{cx:xy[0],cy:xy[1],r:0,fill:'#1F5BFF',stroke:'#fff','stroke-width':3});return {m,b,ring,dot};});
 const eo=x=>1-Math.pow(1-Math.min(1,Math.max(0,x)),3);
 const ob=x=>{x=Math.min(1,Math.max(0,x));const c1=1.70158,c3=c1+1;return 1+c3*Math.pow(x-1,3)+c1*Math.pow(x-1,2);};
 const mix=(a,b,t)=>{const A=[1,3,5].map(i=>parseInt(a.slice(i,i+2),16)),B=[1,3,5].map(i=>parseInt(b.slice(i,i+2),16));return 'rgb('+A.map((v,i)=>Math.round(v+(B[i]-v)*t)).join(',')+')';};
 __tick.push(t=>{
  mems.forEach(({m,b,ring,dot})=>{const p=eo((t-m.t)/0.3);if(b)b.el.setAttribute('fill',mix('#DCE4F0','#1F5BFF',p));
   dot.setAttribute('r',(9*ob((t-m.t)/0.35)).toFixed(2));const r=(t-m.t);ring.setAttribute('r',(10+46*eo(r/0.7)).toFixed(1));ring.setAttribute('opacity',r>0&&r<0.7?(0.8*(1-r/0.7)).toFixed(2):0);});
  if(C.ex){const p=eo((t-C.ex.t)/0.4);exEls.forEach(b=>b.el.setAttribute('fill',mix('#DCE4F0','#9DB8FF',p)));}
 });})();""" % json.dumps(cfg)
    css = """
.rd2{position:absolute;left:330px;top:452px;font-size:30px;color:var(--sub);letter-spacing:.12em;animation:fadeup .5s .5s both;white-space:nowrap}
.tmap{position:absolute;left:96px;top:604px;width:834px;height:340px;overflow:hidden;animation:fadeup .5s .35s both}
.tchips{position:absolute;left:96px;right:150px;top:968px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px;animation:fadeup .5s .5s both}
.tchip{height:58px;border-radius:999px;border:1.5px solid var(--line);background:#fff;color:var(--sub);font-size:26px;font-weight:700;display:flex;align-items:center;justify-content:center;gap:10px;white-space:nowrap;
animation:tcin .3s var(--t) cubic-bezier(.2,.9,.3,1.3) both}
.tchip b{font-size:18px;width:28px;height:28px;border-radius:50%;background:var(--pale);color:var(--blue);display:flex;align-items:center;justify-content:center}
@keyframes tcin{0%{background:#fff;color:#5B6B82;border-color:#DCE3EE;transform:scale(.92)}60%{transform:scale(1.06)}100%{background:#1F5BFF;color:#fff;border-color:#1F5BFF;transform:none}}
.tchip.ex{animation-name:tcex}
@keyframes tcex{0%{background:#fff;color:#5B6B82;transform:scale(.92)}60%{transform:scale(1.06)}100%{background:#E8EFFF;color:#1F5BFF;border-color:#9DB8FF;transform:none}}
"""
    return body, css, js


def t_end(s, B, D):
    """締め：今日の3本の振り返り → ロゴ → フォローの呼びかけ."""
    rec = "".join(f'<div class="rc" style="animation-delay:{0.15 + i * 0.12:.2f}s"><span class="mono">{i + 1:02d}</span><span class="rt">{esc(h)}</span></div>'
                  for i, h in enumerate(s.get("recap", [])))
    name = s.get("logo", "Quick News")
    body = (f'<div class="recap">{rec}</div>'
            f'<div class="logo">{esc(name)}<i>.</i></div><div class="tagline">{esc(s.get("tagline", "1日1分で社会がわかる"))}</div>'
            f'<div class="cta">{esc(s.get("cta", "フォローして毎朝の習慣に"))}</div>')
    css = """
.recap{position:absolute;left:96px;right:150px;top:330px}
.rc{font-size:34px;font-weight:700;padding:22px 0;border-bottom:1px solid var(--line);animation:fadeup .45s both;display:flex;gap:22px}
.rc span{color:var(--blue)}
.logo{position:absolute;left:0;right:70px;top:760px;text-align:center;font-size:150px;font-weight:900;letter-spacing:-.03em;color:var(--ink);animation:logo .7s .55s cubic-bezier(.2,.8,.2,1) both}
.logo i{font-style:normal;color:var(--blue)}
@keyframes logo{0%{opacity:0;filter:blur(16px);transform:scale(1.06)}100%{opacity:1;filter:none;transform:none}}
.tagline{position:absolute;left:0;right:70px;top:960px;text-align:center;font-size:34px;color:var(--sub);letter-spacing:.14em;animation:fadeup .5s .9s both}
.cta{position:absolute;left:250px;right:320px;top:1060px;text-align:center;font-size:34px;font-weight:700;color:#fff;background:var(--blue);border-radius:999px;
padding:20px 0;box-shadow:0 16px 40px rgba(31,91,255,.30);animation:fadeup .5s 1.1s both}
"""
    return body, css, ""



def t_scroll(s, B, D):
    """（台本に "end_bg": "navy" を付けると、次の場面が紺から始まる）
    スマホでショート動画を次々スワイプする画面。スワイプはだんだん速くなり、横の時計が回る。
    2文目の頭でピタッと止まり、紺の面がスマホから画面いっぱいに広がって、問いかけ（big）が特大の文字で出る。
    宣伝動画の「自分の気づき」用。big は \n で改行、*…* がオレンジ."""
    tf = (B[1] if len(B) > 1 else D * 0.6) - 0.05
    cols = [("#0B1B33", "#1F3A7A"), ("#1F5BFF", "#6F95FF"), ("#DCE6FF", "#F4F7FF"), ("#13265A", "#1F5BFF"), ("#E9EEF7", "#C9D6F2"), ("#0B1B33", "#FFB547")]
    cards = ""
    for k in range(40):
        a, b = cols[(k * 5 + 2) % len(cols)]
        dark = a in ("#0B1B33", "#1F5BFF", "#13265A")
        fg = "rgba(255,255,255,.85)" if dark else "rgba(11,27,51,.55)"
        cards += (f'<div class="sv" style="top:{k * 100}%;background:linear-gradient(160deg,{a},{b})">'
                  f'<i class="pl" style="border-left-color:{fg}"></i>'
                  f'<b class="bar" style="background:{fg};width:{52 + (k * 37) % 30}%"></b><b class="bar b2" style="background:{fg};width:{30 + (k * 23) % 25}%"></b>'
                  f'<span class="rail"><em style="background:{fg}"></em><em style="background:{fg}"></em><em style="background:{fg}"></em></span></div>')
    lines = "".join(f'<div class="bl">{"".join(f"<span class=acc2>{esc(t)}</span>" if a_ else esc(t) for t, a_ in chunks(l))}</div>' for l in s["big"].split("\n"))
    body = (kin(s["title"], -1.0, "", 0.0, "top:336px;font-size:90px") +  # 1コマ目から見出しが読める
            f'<div class="scw"><div class="sph"><div class="scr2"><div class="feed" id="feed">{cards}</div></div><div class="notch2"></div></div>'
            f'<div class="sct"><div class="sl">{esc(s.get("counter_label", "スクロールした時間"))}</div><div class="sn mono" id="scn">00:00</div>'
            f'<div class="sl2">{esc(s.get("counter_sub", ""))}</div></div></div>'
            f'<div class="bigq" id="bigq"><div class="bqt">{lines}</div></div>')
    css = """
.scw{position:absolute;left:96px;right:96px;top:600px;height:440px}
.sph{position:absolute;left:0;top:0;width:250px;height:440px;border-radius:44px;background:#0B1B33;padding:12px;box-shadow:0 30px 80px rgba(20,40,90,.22)}
.scr2{position:relative;width:100%;height:100%;border-radius:44px;overflow:hidden;background:#0B1B33}
.notch2{position:absolute;left:50%;top:22px;width:110px;height:26px;margin-left:-55px;background:#0B1B33;border-radius:14px}
.feed{position:absolute;left:0;top:0;width:100%;height:100%;will-change:transform}
.sv{position:absolute;left:0;width:100%;height:100%}
.sv .pl{position:absolute;left:50%;top:44%;margin:-30px 0 0 -18px;border-left:52px solid;border-top:32px solid transparent;border-bottom:32px solid transparent}
.sv .bar{position:absolute;left:26px;bottom:74px;height:14px;border-radius:7px}.sv .b2{bottom:48px}
.sv .rail{position:absolute;right:20px;bottom:120px;display:flex;flex-direction:column;gap:22px}.sv .rail em{width:34px;height:34px;border-radius:50%;opacity:.8}
.sct{position:absolute;left:300px;top:60px;right:0}
.sl{font-size:30px;font-weight:700;color:var(--sub);letter-spacing:.04em}
.sn{font-size:118px;font-weight:700;color:var(--ink);letter-spacing:-.02em;line-height:1.1;margin-top:8px}
.sl2{font-size:28px;color:var(--sub);margin-top:6px}
.bigq{position:fixed;left:-200px;top:-400px;width:1480px;height:2800px;background:#0B1B33;z-index:50;clip-path:circle(0px at 450px 1300px)}
.bqt{position:absolute;left:296px;top:1010px;width:888px}
.bl{font-size:124px;font-weight:900;line-height:1.22;letter-spacing:-.04em;color:#fff;white-space:nowrap;opacity:0}
.bl .acc2{color:#FFB547}
"""
    js = """(function(){const tf=%.3f,feed=document.getElementById('feed'),n=document.getElementById('scn'),ph=document.querySelector('.sph'),bq=document.getElementById('bigq'),bl=[...bq.querySelectorAll('.bl')],sw=[];
 let t=0.55,iv=0.62;while(t<tf-0.05&&sw.length<38){sw.push(t);t+=iv;iv=Math.max(0.13,iv*0.8);}
 const ez=x=>x<0?0:x>1?1:1-Math.pow(1-x,3);
 // 紺の面の中心はスマホの中央（.bigq の座標）。スマホの実際の位置から求める
 const r=ph.getBoundingClientRect(),q=bq.getBoundingClientRect(),cxp=r.left+r.width/2-q.left,cyp=r.top+r.height/2-q.top;
 __tick.push(T=>{const tt=Math.min(T,tf);let k=0;for(const s0 of sw){k+=ez((tt-s0)/0.2);}
  feed.style.transform='translateY('+(-k*100)+'%%)';
  const sec=Math.round(%d*Math.pow(Math.min(1,tt/tf),2.2));n.textContent=String(Math.floor(sec/60)).padStart(2,'0')+':'+String(sec%%60).padStart(2,'0');
  const u=T<tf?0:(T-tf);bq.style.clipPath='circle('+(u<=0?0:2400*ez(u/0.32))+'px at '+cxp+'px '+cyp+'px)';
  const sh=u>0?Math.exp(-u*7)*Math.sin(u*55)*10:0;
  const R=document.documentElement.style,dk=u>0.1;R.setProperty('--hfg',dk?'#fff':'#0B1B33');R.setProperty('--hnews',dk?'#7FA2FF':'#1F5BFF');R.setProperty('--hsub',dk?'rgba(255,255,255,.72)':'#5B6B82');R.setProperty('--hline',dk?'rgba(255,255,255,.28)':'#DCE3EE');
  bl.forEach((e,i)=>{const v=u-0.12-i*0.09,a=v<=0?0:Math.min(1,v/0.12),sc=v<=0?1.6:1+0.6*Math.exp(-v*14);
   e.style.opacity=a;e.style.transform='translate('+sh+'px,0) scale('+sc+')';e.style.transformOrigin='0 50%%';});});})();""" % (tf, int(s.get("counter_to", 2832)))
    return body, css, js


_KW_FUNC = sorted(set("""の が を に で と は や へ も な だ か ね ほど など から まで より として による について での との への にも では には とは へも
ます ました です でした ません ませんでした ている ています ていた ていました になります になりました となる となり となります される された され する した して します しました
られる られた れる れた せる せた たい ない なかった ため ように ような そうです という といった""".split()), key=len, reverse=True)


def _kw_split(run):
    """ひらがなの並びを、送りがな（大きいまま）と助詞・助動詞（小さく）に分ける."""
    pre = next((f for f in _KW_FUNC if run.startswith(f) and len(f) < len(run)), "") if run else ""
    if run in _KW_FUNC:
        return [("", run)]
    rest = run[len(pre):]
    suf = next((f for f in _KW_FUNC if rest.endswith(f) and len(f) < len(rest)), "")
    mid = rest[:len(rest) - len(suf)] if suf else rest
    out = []
    if pre:
        out.append(("", pre))
    if mid:
        out.append((mid, ""))
    if suf:
        out.append(("", suf))
    return out


def _kw_html(text):
    """テロップ組み：中身の言葉（漢字・カタカナ・英数字と送りがな）は大きく、助詞・助動詞は小さく細く。*…* は重要語."""
    out = []
    for t, a in chunks(text):
        segs = re.findall(r"[ぁ-ゖ]+|[^ぁ-ゖ]+", t)
        for k, seg in enumerate(segs):
            if re.fullmatch(r"[ぁ-ゖ]+", seg):
                after_kanji = k > 0 and not re.fullmatch(r"[ぁ-ゖ]+", segs[k - 1]) and re.search(r"[一-龥々]$", segs[k - 1])
                pieces = _kw_split(seg) if after_kanji else ([("", seg)] if seg in _KW_FUNC else [(seg, "")])
                for big, small in pieces:
                    if big:
                        out.append(f'<span class="kc{" ka" if a else ""}">{esc(big)}</span>')
                    if small:
                        out.append(f'<span class="kf{" ka" if a else ""}">{esc(small)}</span>')
            else:
                out.append(f'<span class="kc{" ka" if a else ""}">{esc(seg.strip())}</span>')
    return "".join(out)


def t_kw(s, B, D):
    """キネティック・テロップ：ナレーション1文を1つの「意味のまとまり」として画面の中ほどに組み、
    言葉の区切り（kw）を話すのに合わせてその場に1つずつ足していく（入れ替えない）。文が変わるときだけ、まとまりごと静かに入れ替える。
    中身の言葉は大きく、助詞・助動詞（ひらがな）は小さく。*…* の重要語は青＋マーカー＋さらに大きく、icon があれば上にピクトを出す。
    label（例「背景」「なぜ大事？」）は上に小さく出す。各 kw は say の中の文字列（出る時刻を言葉の位置から決める）。"""
    blocks = []
    beats = s["beats"]
    for i, b in enumerate(beats):
        st = B[i] if i < len(B) else 0.2
        en = (B[i + 1] - 0.05) if i + 1 < len(B) else D - 0.25
        ln = max(0.4, (en - st) * 0.93)
        say = b.get("say", "")
        kws = b.get("kw") or [say]
        cur, parts = 0, []
        for j, k in enumerate(kws):
            k = k if isinstance(k, dict) else {"t": k}
            plain = k["t"].replace("*", "").strip()
            idx = say.find(plain, cur) if plain else -1
            frac = (j / max(1, len(kws))) if idx < 0 else idx / max(1, len(say))
            if idx >= 0:
                cur = idx + len(plain)
            parts.append(dict(k, at=round(max(st, st + frac * ln - 0.08), 3)))
        for j in range(1, len(parts)):
            parts[j]["at"] = max(parts[j]["at"], parts[j - 1]["at"] + 0.28)
        blocks.append({"st": st, "parts": parts})
    html = []
    for bi, bl in enumerate(blocks):
        icon = next((p for p in bl["parts"] if p.get("icon")), None)
        ic = (f'<div class="kic">{picto(icon["icon"], 132, icon["at"] + 0.02, "var(--blue)", 2.3)}</div>') if icon else ""
        ps = "".join(f'<span class="kp" data-at="{p["at"]}">{_kw_html(p["t"])}</span>' for p in bl["parts"])
        html.append(f'<div class="kb" data-st="{bl["st"]}" data-en="{blocks[bi + 1]["st"] if bi + 1 < len(blocks) else 999}">{ic}<div class="kt">{ps}</div></div>')
    lab = s.get("label", "")
    body = ((f'<div class="flab">{picto(s.get("label_icon", ""), 46, 0.1, "#fff", 3.2)}<b>{esc(lab)}</b></div>' if lab else "")
            + f'<div class="kst">{"".join(html)}</div>')
    css = """
.flab{position:absolute;left:96px;top:300px;display:flex;align-items:center;gap:12px;background:var(--blue);color:#fff;border-radius:999px;padding:12px 30px 12px 22px;animation:pillin .35s .05s cubic-bezier(.2,1.4,.4,1) both}
.flab b{font-size:36px;font-weight:900;letter-spacing:.04em}
.kst{position:absolute;left:96px;right:110px;top:400px;height:720px}
.kb{position:absolute;left:0;right:0;top:50%;opacity:0}
.kt{line-height:1.18;letter-spacing:-.03em;font-weight:900;color:var(--ink)}
.kp{display:block;opacity:0;white-space:nowrap;width:max-content;max-width:none}
.kc{font-size:var(--fc,108px)}
.kf{font-size:calc(var(--fc,108px) * .58);font-weight:700;color:#41506A;letter-spacing:0}
.kc.ka{font-size:calc(var(--fc,108px) * 1.2);color:var(--blue);background:linear-gradient(rgba(255,181,71,.5),rgba(255,181,71,.5)) 0 88%/var(--mk,0%) 26% no-repeat}
.kf.ka{color:var(--blue)}
.kic{height:146px;margin-bottom:10px}
"""
    js = r"""(function(){const K=[...document.querySelectorAll('.kb')],MAXH=600;
 K.forEach(k=>{let fc=108;k.style.setProperty('--fc',fc+'px');k.style.opacity=1;k.querySelectorAll('.kp').forEach(p=>p.style.opacity=1);
  const over=()=>k.offsetHeight>MAXH||[...k.querySelectorAll('.kp')].some(p=>p.scrollWidth>864);
  while(over()&&fc>56){fc-=4;k.style.setProperty('--fc',fc+'px');}
  k.querySelectorAll('.kp').forEach(p=>p.style.opacity=0);k.style.opacity=0;k.dataset.h=k.offsetHeight;});
 const ez=x=>x<=0?0:x>=1?1:1-Math.pow(1-x,3);
 __tick.push(t=>{K.forEach(k=>{const st=+k.dataset.st,en=+k.dataset.en,h=+k.dataset.h;
   const a=ez((t-st+0.02)/0.22),b=ez((t-en+0.02)/0.2);   // まとまりの出入り（上下とフェードだけ）
   k.style.opacity=(a*(1-b)).toFixed(3);k.style.transform='translateY('+(-h/2+30*(1-a)-40*b).toFixed(1)+'px)';
   k.querySelectorAll('.kp').forEach(p=>{const e=t-(+p.dataset.at),u=ez(e/0.22);
     p.style.opacity=(e<0?0:Math.max(.0,u)).toFixed(3);
     p.querySelectorAll('.ka').forEach(x=>x.style.setProperty('--mk',(100*ez((e-0.2)/0.4)).toFixed(1)+'%'));});});});})();"""
    return body, css, js


def t_custom(s, B, D):
    """自由演出：台本に html / css / js をそのまま書いて、そのニュースのためだけの場面を作る（2026-11-12〜）。
    js は __tick.push(t => {...}) で時刻 t（場面の頭からの秒）から絵を決める（毎フレーム同じ t なら同じ絵：Math.random と Date は使わない）。
    使える値：__B（ナレーション各文の開始秒の配列）、__D（場面の長さ）。picto("名前", 大きさ, 開始秒) は {{picto:名前:大きさ:開始秒}} と書くと埋め込める。
    座標は幅1080の .cx 内（上の見出しは top:336px、本文は 400〜1100px あたり）。"""
    html = s.get("html", "")
    html = re.sub(r"\{\{picto:(\w+):(\d+):([\d.]+)\}\}", lambda m: picto(m.group(1), int(m.group(2)), float(m.group(3))), html)
    if s.get("title"):
        html = kin(s["title"], 0.1, "", 0.12, "top:336px;font-size:84px") + html
    js = f"(function(){{const __B={json.dumps([round(x, 3) for x in B])},__D={D:.3f};\n{s.get('js', '')}\n}})();"
    return html, s.get("css", ""), js

TEMPLATES = {"morph": t_morph, "illus": t_illus, "globe": t_globe, "flash": t_flash, "route": t_route, "summary": t_summary, "hook_q": t_hook_q, "wall": t_wall, "stat": t_stat, "nodes": t_nodes, "headline": t_headline,
             "list": t_list, "quotes": t_quotes, "phone": t_phone, "zoom": t_zoom, "term": t_term, "end": t_end}
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "morph3.py"), encoding="utf-8").read(), globals())
TEMPLATES["morph"] = t_morph
TEMPLATES["scroll"] = t_scroll
TEMPLATES["kw"] = t_kw
TEMPLATES["custom"] = t_custom


# ───────── 音 ─────────
_VV = None


def _vv(voice_file):
    global _VV
    if _VV is None:
        d = os.environ.get("VOICEVOX_DIR", "/home/claude/vv/vc")
        try:
            from voicevox_core.blocking import Onnxruntime, OpenJtalk, Synthesizer, VoiceModelFile
            ort = Onnxruntime.load_once(filename=glob.glob(d + "/ort/*/lib/libvoicevox_onnxruntime.so")[0])
            syn = Synthesizer(ort, OpenJtalk(glob.glob(d + "/dict/open_jtalk_dic_utf_8-*")[0]))
            with VoiceModelFile.open(f"{d}/models/{voice_file}") as m:
                syn.load_voice_model(m)
            _VV = syn
        except Exception as e:
            print("voice: VOICEVOX が使えないので pyopenjtalk を使います:", e, flush=True)
            _VV = False
    return _VV


def tts(text, speed, voice):
    syn = _vv(voice.get("file", "6.vvm"))
    if syn:
        q = syn.create_audio_query(text, voice.get("id", 30))
        q.speed_scale = speed
        q.pre_phoneme_length = 0.03
        q.post_phoneme_length = 0.05
        q.intonation_scale = voice.get("intonation", 1.15)
        for ap in q.accent_phrases:
            pm = ap.pause_mora
            if pm is not None:
                if isinstance(pm, dict):
                    pm["vowel_length"] *= voice.get("pause", 0.35)
                else:
                    pm.vowel_length *= voice.get("pause", 0.35)
        with wave.open(io.BytesIO(syn.synthesis(q, voice.get("id", 30)))) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    else:
        import pyopenjtalk
        x, sr = pyopenjtalk.tts(text, speed=speed * 1.1)
        x = x.astype(np.float32)
    if sr != SR:
        idx = np.linspace(0, len(x) - 1, int(len(x) * SR / sr))
        x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    # 前後の無音を詰める（文と文のあいだの間を短くするため）
    nz = np.where(np.abs(x) > 0.012 * (np.max(np.abs(x)) or 1.0))[0]
    if len(nz):
        x = x[max(0, nz[0] - int(0.015 * SR)): nz[-1] + int(0.04 * SR)]
    return x / (np.max(np.abs(x)) or 1.0) * 0.9


def sfx_tick(f=1600, dur=0.05, vol=0.10):
    t = np.arange(int(SR * dur)) / SR
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 90) * vol).astype(np.float32)


def sfx_type():
    rng = np.random.default_rng(5)
    n = int(SR * 0.025)
    x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 260)
    return np.concatenate([[0], np.diff(x)]).astype(np.float32) * 0.07


def sfx_swish():
    n = int(SR * 0.35)
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(n).astype(np.float32)
    hp = np.concatenate([[0], np.diff(noise)])
    lp = np.convolve(hp, np.ones(6) / 6, mode="same")
    env = np.sin(np.linspace(0, np.pi, n)) ** 3
    return (lp * env * 0.07).astype(np.float32)


def sfx_soft_hit():
    t = np.arange(int(SR * 0.5)) / SR
    f = 70 * np.exp(-t * 4) + 45
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * np.exp(-t * 7) * 0.35).astype(np.float32)


def sfx_rise(dur=0.9):
    t = np.arange(int(SR * dur)) / SR
    f = 300 + 900 * (t / dur) ** 2
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * (t / dur) ** 2 * 0.05).astype(np.float32)


def bgm(seconds, bpm=104):
    """落ち着いたミニマルなビート＋柔らかいパッド（Am7 - Fmaj7 - C - G）."""
    n = int(SR * seconds)
    out = np.zeros(n, np.float32)
    beat = 60 / bpm
    rng = np.random.default_rng(3)
    tk = np.arange(int(SR * 0.22)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(50 + 70 * np.exp(-tk * 35)) / SR) * np.exp(-tk * 11) * 0.45
    th = np.arange(int(SR * 0.04)) / SR
    hat = np.concatenate([[0], np.diff(rng.standard_normal(len(th)))]) * np.exp(-th * 110) * 0.10

    def add(x, s):
        e = min(n, s + len(x))
        if e > s:
            out[s:e] += x[: e - s]
    chords = [[220.0, 261.63, 329.63, 392.0], [174.61, 220.0, 261.63, 329.63], [130.81, 196.0, 261.63, 329.63], [196.0, 246.94, 293.66, 392.0]]
    bar = beat * 4
    t, i = 0.0, 0
    while t < seconds:
        add(kick, int(t * SR)) if i % 2 == 0 else None
        add(hat, int((t + beat / 2) * SR))
        t += beat
        i += 1
    t, c = 0.0, 0
    while t < seconds:
        tb = np.arange(int(SR * bar)) / SR
        env = np.minimum(1, tb / 0.4) * np.minimum(1, (bar - tb) / 0.4)
        pad = sum(np.sin(2 * np.pi * f * tb) + 0.3 * np.sin(2 * np.pi * f * 2.001 * tb) for f in chords[c % 4]) * env * 0.018
        add(pad.astype(np.float32), int(t * SR))
        t += bar
        c += 1
    fade = int(SR * 1.0)
    out[-fade:] *= np.linspace(1, 0, fade)
    return out


# ───────── 組み立て ─────────

def plan(sc, speed):
    voice = sc.get("voice", {})
    scenes = []
    stories = [s.get("story", 0) for s in sc["scenes"]]
    n_st = max(stories) if stories else 0
    for idx, s in enumerate(sc["scenes"]):
        auds, B = [], []
        t = 0.03 if idx == 0 else 0.06
        for b in s["beats"]:
            a = tts(b.get("reading", b["say"]), speed, voice)
            B.append(t)
            auds.append((t, a))
            t += len(a) / SR + b.get("pad", 0.03)
        D = max(t + 0.1, s.get("min_dur", 0))
        nf = int(round(D * FPS))
        D = nf / FPS
        st = s.get("story", 0)
        sect = ((f"{st:02d} / {n_st:02d}" if n_st > 1 else ""), s.get("section", "")) if st else None
        scenes.append(dict(s=s, B=B, D=D, nf=nf, auds=auds, sect=sect))
    return scenes


def build_html(sc, p, t0, total, first):
    s = p["s"]
    if s["type"] == "morph":
        s = dict(s, _first=first, _t0=t0)
    body, css, js = TEMPLATES[s["type"]](s, p["B"], p["D"])
    is_logo = s["type"] == "morph" and any(sh.get("logo") for sh in s.get("shots", []))
    sc2 = dict(sc, _nocap=s.get("captions") is False or is_logo, _nodense=s["type"] in ("morph", "scroll", "kw"))
    return shell(body, css, js, p["D"], t0 / total, (t0 + p["D"]) / total, sc2, s["beats"], p["B"], s.get("source", ""), p["sect"], first,
                 p.get("bg", "white"), p.get("prev_bg", "white"))


def main():
    script, out = sys.argv[1], sys.argv[2]
    stills = sys.argv[sys.argv.index("--stills") + 1] if "--stills" in sys.argv else None
    sc = json.load(open(script, encoding="utf-8"))
    speed = sc.get("speed", 1.15)
    limit = sc.get("max_seconds", 32)
    floor = sc.get("min_seconds", 28)      # 2026-11-12 から1本30秒（28〜32秒）
    for _ in range(5):
        P = plan(sc, speed)
        total = sum(p["D"] for p in P)
        if total > limit and speed < 1.6:
            speed = min(1.6, speed * total / limit * 1.03)
        elif total < floor and speed > 1.0:
            speed = max(1.0, speed * total / floor * 0.98)
        else:
            break
    if total < floor:   # 話す速さを落としても足りない分は、締めの場面を延ばす
        P[-1]["s"] = dict(P[-1]["s"], min_dur=P[-1]["D"] + (floor - total))
        P = plan(dict(sc, scenes=[p["s"] for p in P]), speed)
        total = sum(p["D"] for p in P)
    prev = "white"
    for p_ in P:
        s_ = p_["s"]
        p_["bg"] = s_["shots"][0].get("bg", "white") if s_["type"] == "morph" else s_.get("bg", "white")
        p_["prev_bg"] = prev
        prev = s_["shots"][-1].get("bg", "white") if s_["type"] == "morph" else s_.get("end_bg", p_["bg"])  # end_bg：場面の終わりで背景が変わるとき（scroll の紺の面など）
    print(f"scenes={len(P)} duration={total:.1f}s speed={speed:.2f}", flush=True)
    # 場面ごとの開始・終了秒とナレーションを残す（投稿後の離脱分析で、平均視聴時間がどの場面に当たるかを見るため）
    tl, tc = [], 0.0
    for i, p_ in enumerate(P):
        s_ = p_["s"]
        tl.append({"i": i, "type": s_["type"], "start": round(tc, 2), "end": round(tc + p_["D"], 2),
                   "title": s_.get("title") or s_.get("term") or (s_["shots"][0].get("big", "") if s_["type"] == "morph" else ""),
                   "beats": [{"t": round(tc + bt, 2), "say": b.get("say", "")} for bt, b in zip(p_["B"], s_["beats"])]})
        tc += p_["D"]
    json.dump({"duration": round(total, 2), "scenes": tl}, open(os.path.splitext(out)[0] + ".timeline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if os.environ.get("QN_TIMELINE_ONLY"):
        return
    work = tempfile.mkdtemp(prefix="qn_")
    with sync_playwright() as pw:
        try:
            br = pw.chromium.launch()
        except Exception:
            br = pw.chromium.launch(executable_path="/usr/bin/google-chrome")
        pg = br.new_page(viewport={"width": W, "height": HGT})
        pg.on("console", lambda m: print("  " + m.text, flush=True) if "[layout]" in m.text else None)
        t0 = 0.0
        files = []
        for i, p in enumerate(P):
            hp = os.path.join(work, f"s{i:02d}.html")
            with open(hp, "w", encoding="utf-8") as f:
                f.write(build_html(sc, p, t0, total, i == 0))
            pg.goto("file://" + hp)
            pg.evaluate("document.fonts.ready")
            pg.evaluate("seek(5)")
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(250)
            pg.evaluate("window.__layout&&__layout()")   # フォント読み込み後に余白を測り直す
            info = pg.evaluate("window.__layoutInfo||null")
            if info:
                print(f"  layout s{i:02d}: 見出し下端 {info['titleBottom']:.0f} → 本文 {info['bodyTop']:.0f}〜{info['bodyBottom']:.0f}（字幕 {info['captionTop']}）", flush=True)
            if stills:
                os.makedirs(stills, exist_ok=True)
                for tt in sorted({0.0 if i == 0 else 0.6, min(p["D"] - 0.35, max(0.6, p["D"] * 0.85))}):
                    pg.evaluate(f"seek({tt:.3f})")
                    pg.screenshot(path=os.path.join(stills, f"s{i:02d}_{p['s']['type']}_{tt:.1f}.jpg"), type="jpeg", quality=88)
            else:
                fp = os.path.join(work, f"s{i:02d}.mp4")
                tmp = fp[:-4] + ".part.mp4"
                ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-c:v", "mjpeg",
                                       "-framerate", str(FPS), "-i", "-", *ENC, tmp], stdin=subprocess.PIPE)
                for k in range(p["nf"]):
                    pg.evaluate(f"seek({k / FPS:.4f})")
                    ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
                ff.stdin.close()
                if ff.wait() != 0:
                    raise RuntimeError("ffmpeg failed")
                os.replace(tmp, fp)
                files.append(fp)
                print(f"  scene {i + 1}/{len(P)} {p['s']['type']} {p['D']:.1f}s", flush=True)
            t0 += p["D"]
        br.close()
    if stills:
        return
    n = int(round(total * SR))
    voice = np.zeros(n, np.float32)
    fx = np.zeros(n, np.float32)

    def put(buf, x, at):
        s = int(at * SR)
        e = min(n, s + len(x))
        if e > s and s >= 0:
            buf[s:e] += x[: e - s]
    t0 = 0.0
    for i, p in enumerate(P):
        typ = p["s"]["type"]
        for (bt, a) in p["auds"]:
            put(voice, a, t0 + bt)
        if i > 0:
            put(fx, sfx_swish(), t0 - 0.15)
        if typ == "hook_q":
            q = p["s"]["question"]
            for k in range(3, len(q)):
                put(fx, sfx_type(), t0 + k * 0.07 - 0.15)
            put(fx, sfx_soft_hit(), t0 + 0.07 * len(q) + 0.2)
        if typ == "stat":
            for k in range(14):
                put(fx, sfx_tick(2200, 0.03, 0.04), t0 + 0.45 + k * 0.075)
            put(fx, sfx_soft_hit(), t0 + 1.55)
        if typ in ("list", "nodes"):
            rows = p["s"].get("rows") or p["s"].get("nodes")
            span = max(0.25, (p["D"] - 1.0) / len(rows)) if typ == "list" else max(0.5, (p["D"] - 1.0) / len(rows))
            for k in range(len(rows)):
                put(fx, sfx_tick(1400, 0.05, 0.06), t0 + (0.35 if typ == "list" else 0.3) + k * span)
        if typ == "morph":
            _, evs = morph_events(p["s"], p["B"], p["D"], i == 0)
            for (et, kind) in evs:
                at = t0 + et
                if kind == "launch":
                    put(fx, sfx_swish() * 1.7, at - 0.05)
                elif kind == "land":
                    put(fx, sfx_soft_hit() * 0.85, at)
                    put(fx, sfx_tick(760, 0.09, 0.09), at)
                elif kind == "open":
                    put(fx, sfx_tick(2600, 0.03, 0.10), at)
                    put(fx, sfx_tick(1700, 0.05, 0.08), at + 0.06)
                elif kind == "rec":
                    put(fx, sfx_tick(2100, 0.03, 0.035), at)
                elif kind.startswith("letter"):
                    j = int(kind[6:])
                    put(fx, sfx_tick(880 * 2 ** (j / 12 * 1.5), 0.05, 0.06), at)
        if typ == "flash":
            for bt in p["B"][-len(p["s"]["items"]) + 1:]:
                put(fx, sfx_swish() * 1.3, t0 + bt - 0.2)
            put(fx, sfx_soft_hit(), t0 + 0.02)
        if typ == "globe":
            put(fx, sfx_rise(1.6), t0 + 0.6)
            put(fx, sfx_tick(1500, 0.06, 0.08), t0 + 0.1 + min(max(2.6, p["D"] - 1.4), 3.6) * 0.9)
        if typ == "summary":
            for bt in p["B"][-len(p["s"]["items"]):]:
                put(fx, sfx_tick(1500, 0.05, 0.07), t0 + bt)
        if typ == "end":
            put(fx, sfx_rise(0.6), t0 + 0.0)
            put(fx, sfx_soft_hit(), t0 + 0.6)
        t0 += p["D"]
    music = bgm(total)
    music = np.pad(music, (0, max(0, len(voice) - len(music))))[:len(voice)]  # 丸めで1サンプルずれることがある
    env = np.convolve(np.abs(voice) > 0.02, np.ones(int(SR * 0.25)) / (SR * 0.25), mode="same")
    music *= (1 - 0.5 * np.clip(env * 3, 0, 1))
    mix = voice * 0.95 + fx + music
    mix = np.clip(mix / max(1.0, np.max(np.abs(mix)) / 0.98), -1, 1)
    wav = os.path.join(work, "mix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    with open(os.path.join(work, "list.txt"), "w") as f:
        for fp in files:
            f.write(f"file '{fp}'\n")
    vid = os.path.join(work, "video.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(work, "list.txt"),
                    "-c", "copy", vid], check=True)
    tmp = out[:-4] + ".part.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vid, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    shutil.rmtree(work, ignore_errors=True)
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
