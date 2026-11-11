
# ───────── 変形＋移動の場面（v11：canvas エンジン lib/qnmorph.js） ─────────
# 時刻表（発射・着地・鍵が開く・ロゴの文字）を Python 側で一度だけ決め、映像（JS）と効果音の両方がそれを読む。
ANCHORS = [(0, 0), (1250, -260), (2500, 120), (3750, -200), (5000, 100), (6250, -180)]
FLIGHT = 0.62
_GLYPHS = None


def _glyphs():
    global _GLYPHS
    if _GLYPHS is None:
        p = os.path.join(LIB_DIR, "glyphs_qn.json")
        _GLYPHS = json.load(open(p)) if os.path.exists(p) else None
    return _GLYPHS


def morph_events(s, B, D, first=False):
    shots = s["shots"]
    n = len(shots)
    starts = list(B[-n:]) if len(B) >= n else [i * D / n for i in range(n)]
    base = s.get("anchor_offset", 0)
    out, sfx = [], []
    for i, sh in enumerate(shots):
        ax, ay = ANCHORS[(base + i) % len(ANCHORS)]
        vis = sh.get("visual", "logo" if sh.get("logo") else "")
        o = {"bg": sh.get("bg", "white"), "icon": sh.get("icon", "dot"), "visual": vis, "x": ax, "y": ay}
        if i == 0:
            o["land"], o["L"] = (0.30 if first else 0.42), None
        else:
            land = starts[i] + 0.04
            L = land - FLIGHT
            if L < out[-1]["land"] + 0.9:
                L = out[-1]["land"] + 0.9
                land = L + FLIGHT
            o["land"], o["L"] = land, L
            sfx.append((L - 0.04, "launch"))
        sfx.append((o["land"], "land"))
        if vis == "spark":
            o["land_off"], o["land_sc"] = [-380, 230], 0.6
        if sh.get("icon2"):
            o["icon2"] = sh["icon2"]
            o["t2"] = o["land"] + sh.get("icon2_at", 0.6)
            sfx.append((o["t2"], "open"))
        if vis == "records":
            t0 = o.get("t2", o["land"]) + 0.22
            for j in range(10):
                sfx.append((t0 + j * 0.07 + 0.5, "rec"))
        if vis == "logo":
            for j in range(9):
                sfx.append((o["land"] + 0.42 + j * 0.075 + 0.42, "letter%d" % j))
        for k in ("number", "prefix", "unit", "decimals", "bar_labels", "target", "hl", "pin"):
            if sh.get(k) is not None:
                o[k] = sh[k]
        out.append(o)
    return out, sfx


def t_morph(s, B, D):
    shots = s["shots"]
    n = len(shots)
    first = s.get("_first", False)
    ev, _ = morph_events(s, B, D, first)
    texts = []
    for i, (sh, e) in enumerate(zip(shots, ev)):
        bg = e["bg"]
        dark = bg in ("blue", "navy")
        ink = "#FFFFFF" if dark else "#0B1B33"
        acc = "#A9C1FF" if bg == "navy" else ("#0B1B33" if bg == "blue" else "#1F5BFF")
        sub = "rgba(255,255,255,.78)" if dark else "#5B6B82"
        tin = -1.0 if (i == 0 and first) else e["land"] + 0.03
        nxt = ev[i + 1]["L"] if i + 1 < n else None
        body = ""
        if sh.get("logo"):
            body = (f'<div class="mtag" style="animation-delay:{e["land"] + 1.25:.2f}s;color:{sub}">{esc(sh.get("tagline", "1日1分で社会がわかる"))}</div>'
                    f'<div class="mcta" style="animation-delay:{e["land"] + 1.5:.2f}s">{esc(sh.get("cta", "フォローして毎朝の習慣に"))}</div>')
        else:
            if sh.get("kicker"):
                body += f'<div class="mk" style="animation-delay:{tin:.2f}s;color:{acc}">{esc(sh["kicker"])}</div>'
            if sh.get("big"):
                body += kin(sh["big"], tin + 0.05, "mbig", 0.08, f"position:relative;left:0;right:0;font-size:{sh.get('size', 84)}px;color:{ink}").replace(
                    'class="ph acc"', f'class="ph acc" data-c="{acc}"')
            if sh.get("sub"):
                body += f'<div class="msub" style="animation-delay:{tin + 0.3:.2f}s;color:{sub}">{esc(sh["sub"])}</div>'
        out_anim = f",mtout .24s {nxt - 0.06:.2f}s cubic-bezier(.5,0,.75,0) forwards" if nxt is not None else ""
        texts.append(f'<div class="mt" style="animation:mtin .01s {(-0.1 if tin < 0 else tin):.2f}s both{out_anim}">{body}</div>')
    has_logo = any(e["visual"] == "logo" for e in ev)
    # 字幕を出す場面は、舞台と見出しを少し上げて字幕の場所をあける（締めのロゴの場面は従来どおり）
    cfg = {"shots": ev, "first": first, "tg0": s.get("_t0", 0.0), "bpm": 104, "flight": FLIGHT, "cy": 650 if has_logo else 600}
    if any(e["visual"] == "logo" for e in ev):
        cfg["glyphs"] = _glyphs()
    js = ("(function(){const R=QNMorph(document.getElementById('qnm')," + json.dumps(cfg, ensure_ascii=False) + ");__tick.push(R);"
          "document.querySelectorAll('.mbig .acc').forEach(e=>{if(e.dataset.c)e.style.color=e.dataset.c;});})();")
    body = f'<canvas id="qnm" width="1080" height="1920"></canvas><div class="mtext" style="top:{1046 if has_logo else 944}px">{"".join(texts)}</div>'
    css = """
.cam{top:0!important;bottom:0!important;animation:none!important}
#qnm{position:absolute;left:0;top:0;width:1080px;height:1920px}
.mtext{position:absolute;left:96px;right:150px;top:1046px}
.mt{position:absolute;left:0;right:0;top:0}
@keyframes mtin{from{visibility:hidden}to{visibility:visible}}
@keyframes mtout{0%{opacity:1}100%{opacity:0;transform:translateX(-160px);filter:blur(10px)}}
.mk{font-size:28px;font-weight:700;letter-spacing:.08em;margin-bottom:18px;animation:mtx .5s cubic-bezier(.2,.8,.2,1) both}
@keyframes mtx{0%{opacity:0;transform:translateX(160px)}100%{opacity:1;transform:none}}
.mbig{line-height:1.28;letter-spacing:-.02em}
.mbig .ph{animation:mph .55s cubic-bezier(.2,.9,.3,1.1) both}
@keyframes mph{0%{opacity:0;transform:translateX(180px) skewX(-12deg);filter:blur(10px)}100%{opacity:1;transform:none;filter:none}}
.msub{font-size:34px;line-height:1.5;letter-spacing:.02em;margin-top:20px;animation:mtx .5s cubic-bezier(.2,.8,.2,1) both}
.mtag{position:absolute;left:0;right:0;top:-262px;text-align:center;font-size:36px;letter-spacing:.16em;animation:fadeup .5s both}
.mcta{position:absolute;left:120px;right:120px;top:-128px;text-align:center;font-size:38px;font-weight:700;color:#0B1B33;background:#fff;border-radius:999px;padding:24px 0;animation:fadeup .5s both}
"""
    if any(e["visual"] == "logo" for e in ev):   # 締め：中央のロゴが組み上がるとき、上の小さなロゴは退く
        tl = [e for e in ev if e["visual"] == "logo"][0]["land"]
        css += ("#frame .brand{animation:hdout .35s %.2fs cubic-bezier(.5,0,.75,0) forwards}"
                "@keyframes hdout{to{opacity:0;transform:translateY(-24px);filter:blur(6px)}}.cx{animation:none!important}" % (tl + 0.3))
    return body, css, js
