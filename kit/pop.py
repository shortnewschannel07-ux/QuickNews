# ───────── ポップ演出（2026-11-20〜。台本の上位に "style": "pop" を書くと有効） ─────────
# 離脱分析（Instagram リールの最初の3秒のスキップ率が 63〜100%、平均視聴 1〜10秒）を受けて、
# 冒頭と場面の切り替わりで目を止めるための「色」と「動き」を足す。ユーザー指定：テイストはそろえきらなくてよい、色を使ってよい。
# 守ること：場面全体が揺れる・振動する動きは使わない（動くのは場面の中の要素だけ）。上 400px と字幕の帯には置かない。
# qn_short.py の shell() から pop_deco / pop_css / pop_overlay / pop_js が呼ばれる。scene の "bg" に下の色名を書ける。

POP_BG = {"orange": "#FF6A1F", "coral": "#FF4D6D", "violet": "#6A4CFF", "yellow": "#FFD43B", "mint": "#19D3A2", "sun": "#FFB020"}
POP_DARK = {"orange", "coral", "violet"}          # 白い文字にする色
_POP_LIGHT = {"yellow", "mint", "sun"}           # 紺の文字にする色


def _theme(bg):
    if bg in POP_DARK or bg in ("blue", "navy"):
        fg = POP_BG.get(bg, {"blue": "#1F5BFF", "navy": "#0B1B33"}.get(bg))
        return (":root{--ink:#fff;--sub:rgba(255,255,255,.86);--blue:#FFE14D;--line:rgba(255,255,255,.35);"
                f"--hfg:#fff;--hnews:#FFE14D;--hsub:rgba(255,255,255,.85);--hline:rgba(255,255,255,.4);--boxbg:#fff;--boxfg:{fg}}}"
                ".kf{color:rgba(255,255,255,.88)!important}.flab{background:#0B1B33!important}#src{color:rgba(255,255,255,.85)!important}"
                ".pgc svg,.kic svg{color:#fff!important}")
    if bg in _POP_LIGHT:
        return (":root{--ink:#0B1B33;--sub:#26334A;--blue:#1438C8;--line:rgba(11,27,51,.22);"
                "--hfg:#0B1B33;--hnews:#1438C8;--hsub:#26334A;--hline:rgba(11,27,51,.28);--boxbg:#0B1B33;--boxfg:#fff}"
                ".kf{color:#26334A!important}.flab{background:#0B1B33!important}#src{color:#26334A!important}")
    return ":root{--boxbg:#1F5BFF;--boxfg:#fff}"


POP_THEME = {k: _theme(k) for k in list(POP_BG) + ["blue", "navy"]}


def _pop_on(sc):
    return sc.get("style") == "pop"


def pop_deco(bg, D, sc):
    """色の背景のストライプ。2026-11-21 ユーザー指定で廃止（背景にストライプは入れない）。"""
    return ""
    if bg in ("blue", "navy") and not _pop_on(sc):
        return ""
    light = bg in _POP_LIGHT
    c = "rgba(11,27,51,.06)" if light else "rgba(255,255,255,.08)"
    return (f'<div class="pdeco" style="background:repeating-linear-gradient(-30deg,{c} 0 46px,transparent 46px 120px)"></div>')


def pop_css(sc, bg, prev_bg, first, D):
    if not _pop_on(sc):
        return ".pdeco{display:none}"
    return """
:root{--boxbg:#1F5BFF;--boxfg:#fff}
""" + POP_THEME.get(bg, "") + """
.pdeco{position:absolute;inset:-200px;animation:pdrift 8s linear infinite}
@keyframes pdrift{to{transform:translateX(-240px)}}
/* テロップの重要語：マーカーではなく、色の箱に白抜き（どの背景でも読める） */
.kc.ka{background:var(--boxbg)!important;color:var(--boxfg)!important;padding:0 .05em;margin:0;border-radius:0;display:inline-block;line-height:1.14}
.kf.ka{color:var(--ink)!important}
#cap .cap{color:#0B1B33!important}
.kp{transform-origin:0 60%}
@keyframes kpop{0%{transform:translateX(70px) scale(1.35)}55%{transform:translateX(-6px) scale(.96)}100%{transform:none}}
.kic svg{animation:kicpop .5s cubic-bezier(.2,1.7,.4,1) both;animation-delay:var(--t)}
@keyframes kicpop{0%{transform:scale(0) rotate(-30deg)}100%{transform:none}}
/* 場面の頭の色のワイプ（3本の帯が横切る。場面全体は動かさない） */
#pw{position:absolute;inset:0;z-index:55;pointer-events:none;overflow:hidden}
#pw i{position:absolute;top:-300px;bottom:-300px;width:520px;transform:skewX(-18deg) translateX(1300px);animation:pwipe .5s cubic-bezier(.6,0,.3,1) both}
@keyframes pwipe{0%{transform:skewX(-18deg) translateX(1300px)}100%{transform:skewX(-18deg) translateX(-1500px)}}
"""


def pop_overlay(sc, bg, prev_bg, first):
    if not _pop_on(sc) or first:
        return ""
    cols = ["#FFD43B", "#FF6A1F", "#1F5BFF"] if bg not in ("orange", "yellow", "sun") else ["#1F5BFF", "#0B1B33", "#FFD43B"]
    return '<div id="pw">' + "".join(f'<i style="background:{c};animation-delay:{i * 0.05:.2f}s;left:{i * 160}px"></i>' for i, c in enumerate(cols)) + "</div>"


def pop_js(sc):
    if not _pop_on(sc):
        return ""
    # テロップの各行を、出る時刻（data-at）に合わせて弾むように入れる（行ごとの動き）
    return r"""document.querySelectorAll('.kp').forEach(p=>{p.style.animation='kpop .42s cubic-bezier(.2,.9,.3,1) both';p.style.animationDelay=(+p.dataset.at)+'s';});"""


def _pop_line(text, size, delay):
    """1行：*…* は色の箱に白抜き。行は横から勢いよく入る（1コマ目でも読めるよう、開始は少し前倒し）。"""
    out = []
    for t, a in chunks(text):
        t = t.strip() if a else t
        out.append(f'<span class="pk{" pa" if a else ""}">{esc(t)}</span>')
    return f'<div class="pl" style="font-size:{size}px;animation-delay:{delay:.2f}s">{"".join(out)}</div>'


def t_pop(s, B, D):
    """冒頭のフック（2026-11-20〜）：色の背景いっぱいに大見出しを1コマ目から出す。
    項目：bg（orange/coral/violet/yellow/mint/sun/blue/navy）、kicker（上の小さな札）、text（\\n で改行、*…* は箱で強調）、size、
    sub（下の補足1行）、icon（右上の動くピクト）、number/prefix/unit/decimals（数が数え上がる）、marquee（背景を流れる大きな文字＝そのニュースの語）。"""
    size = s.get("size", 124)
    lines = s["text"].split("\n")
    top = 300
    body = []
    if s.get("marquee"):
        m = (esc(s["marquee"]) + "　") * 6
        body.append(f'<div class="pmq" style="top:{s.get("marquee_top", 860)}px"><span>{m}</span></div>')
    if s.get("kicker"):
        body.append(f'<div class="pkick">{esc(s["kicker"])}</div>')
    if s.get("icon"):
        body.append(f'<div class="pico">{picto(s["icon"], 190, 0.0, "currentColor", 2.4)}</div>')
    y = top + 96
    hl = "".join(_pop_line(ln, size, -0.42 + i * 0.06) for i, ln in enumerate(lines))
    body.append(f'<div class="pblk" style="top:{y}px">{hl}<div class="pbar"></div></div>')
    y2 = y + int(len(lines) * size * 1.22) + 60
    js = ""
    if s.get("number") is not None:
        body.append(f'<div class="pnum mono" style="top:{y2}px"><small>{esc(s.get("prefix", ""))}</small><b id="pn">0</b><small>{esc(s.get("unit", ""))}</small></div>')
        js = counter_js("pn", s["number"], 0.35, 0.9, s.get("decimals", 0))
        y2 += 190
    if s.get("sub"):
        body.append(f'<div class="psub" style="top:{y2}px">{esc(s["sub"])}</div>')
    css = """
.pkick{position:absolute;left:96px;top:300px;font-size:38px;font-weight:900;letter-spacing:.06em;color:var(--boxfg);background:var(--boxbg);padding:10px 26px;border-radius:12px;animation:kick .45s cubic-bezier(.2,1.6,.4,1) both;animation-delay:-.1s}
@keyframes kick{0%{transform:translateY(-30px) scale(.7)}100%{transform:none}}
.pico{position:absolute;right:120px;top:250px;color:var(--ink);animation:pico .6s cubic-bezier(.2,1.6,.4,1) both;animation-delay:-.15s}
@keyframes pico{0%{transform:scale(.3) rotate(-40deg)}100%{transform:none}}
.pblk{position:absolute;left:96px;right:96px}
.pl{display:block;white-space:nowrap;font-weight:900;line-height:1.2;letter-spacing:-.04em;color:var(--ink);animation:plin .55s cubic-bezier(.15,.9,.25,1) both}
@keyframes plin{0%{transform:translateX(160px) scale(1.08)}100%{transform:none}}
.pk.pa{display:inline-block;background:var(--boxbg);color:var(--boxfg);padding:0 .12em;margin:.06em .04em;border-radius:.08em;transform:rotate(-2.5deg);animation:stamp .5s cubic-bezier(.2,1.7,.4,1) both;animation-delay:-.32s}
@keyframes stamp{0%{transform:rotate(-2.5deg) scale(1.45)}100%{transform:rotate(-2.5deg)}}
.pbar{height:14px;width:0;margin-top:26px;background:var(--ink);border-radius:7px;animation:pbar .7s .15s cubic-bezier(.6,0,.2,1) both}
@keyframes pbar{to{width:62%}}
.pnum{position:absolute;left:96px;white-space:nowrap;color:var(--ink);font-weight:900;animation:fadeup .4s .3s both}
.pnum b{font-size:170px;letter-spacing:-.03em}
.pnum small{font-size:60px;margin:0 8px}
.psub{position:absolute;left:96px;right:120px;font-size:44px;font-weight:800;color:var(--sub);line-height:1.5;animation:fadeup .45s .55s both}
.pmq{position:absolute;left:0;width:1080px;height:330px;overflow:hidden;opacity:.9}
.pmq span{position:absolute;left:0;top:0;white-space:nowrap;font-size:300px;font-weight:900;line-height:1;color:transparent;-webkit-text-stroke:3px var(--line);animation:pmq 9s linear both}
@keyframes pmq{from{transform:translateX(0)}to{transform:translateX(-2600px)}}
"""
    return "".join(body), css, js


TEMPLATES["pop"] = t_pop
