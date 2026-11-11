"""見本確認用：python3 peek.py script.json 場面番号 秒,秒,... 出力.jpg（縮小して横に並べる）"""
import sys, os, json, tempfile
sys.argv, args = [sys.argv[0]], sys.argv[1:]
import qn_short as q
from playwright.sync_api import sync_playwright
from PIL import Image
import io, hashlib, numpy as np
_orig_tts = q.tts
def _tts(text, speed, voice):
    k = hashlib.md5(json.dumps([text, speed, voice], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    fp = f"/tmp/claude-0/ttscache/{k}.npy"
    if os.path.exists(fp):
        return np.load(fp)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    x = _orig_tts(text, speed, voice); np.save(fp, x); return x
q.tts = _tts

W2, H2 = int(os.environ.get("PW", 360)), int(os.environ.get("PW", 360)) * 16 // 9
script, idx, times, out = args[0], int(args[1]), [float(x) for x in args[2].split(",")], args[3]
sc = json.load(open(script, encoding="utf-8"))
P = q.plan(sc, sc.get("speed", 1.15))
total = sum(p["D"] for p in P)
t0 = sum(p["D"] for p in P[:idx])
html = q.build_html(sc, P[idx], t0, total, idx == 0)
fn = os.path.join(tempfile.mkdtemp(), "s.html")
open(fn, "w", encoding="utf-8").write(html)
print("scene", idx, P[idx]["s"]["type"], "D=%.2f" % P[idx]["D"], "B=", [round(b, 2) for b in P[idx]["B"]])
with sync_playwright() as pw:
    br = pw.chromium.launch()
    pg = br.new_page(viewport={"width": 1080, "height": 1920})
    pg.on("pageerror", lambda e: print("PAGEERR", e))
    pg.on("console", lambda m: print("CONSOLE", m.type, m.text) if m.type in ("error","warning") else None)
    pg.goto("file://" + fn)
    pg.evaluate("document.fonts.ready"); pg.evaluate("seek(5)"); pg.evaluate("document.fonts.ready"); pg.wait_for_timeout(300); pg.evaluate("window.__layout&&__layout()"); print("layout", pg.evaluate("window.__layoutInfo||null"))
    ims = []
    for t in times:
        pg.evaluate(f"seek({t})")
        ims.append(Image.open(io.BytesIO(pg.screenshot(type="png"))).convert("RGB").resize((W2, H2)))
    br.close()
sheet = Image.new("RGB", (W2 * len(ims), H2), "white")
for i, im in enumerate(ims):
    sheet.paste(im, (i * W2, 0))
sheet.save(out)
