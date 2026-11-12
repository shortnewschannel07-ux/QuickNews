# 動くピクト（線画アイコン）。台本の nodes / list の icon、term の icon に名前で指定する。
# 描き順に線が引かれたあと、アイコンごとの小さな動き（煙が上がる、車輪が回る、天びんが傾く…）を続ける。
# 横に滑る動きは使わない（2026-11-12 ユーザー指定）。動きは回転・拡大・上下・点滅・線の描画だけ。
# 座標は 48x48。stroke は呼び出し側の --pw で太さを決める。
PICTO = {
 "up":      '<path class="d" d="M6,38 L18,26 L26,32 L40,16"/><path class="d hd" d="M31,15 H41 V25"/>',
 "down":    '<path class="d" d="M6,12 L18,24 L26,18 L40,34"/><path class="d hd2" d="M31,35 H41 V25"/>',
 "chip":    '<rect class="d" x="13" y="13" width="22" height="22" rx="3"/><rect class="d" x="19" y="19" width="10" height="10" rx="1"/>'
            + "".join(f'<path class="d pin" style="--k:{k}" d="M{18 + 6 * (k % 3)},{7 if k < 3 else 35} V{13 if k < 3 else 41}"/>' for k in range(6)),
 "car":     '<path class="d" d="M6,30 V24 L12,16 H32 L40,24 H43 V30 Z"/><path class="d" d="M14,24 H36"/>'
            '<g class="wh" style="transform-origin:15px 33px"><circle class="d" cx="15" cy="33" r="4.5"/><path class="d" d="M15,29 V37"/></g>'
            '<g class="wh" style="transform-origin:34px 33px"><circle class="d" cx="34" cy="33" r="4.5"/><path class="d" d="M34,29 V37"/></g>',
 "ship":    '<path class="d" d="M5,30 H43 L38,40 H10 Z"/><g class="bx"><rect class="d" x="12" y="20" width="9" height="9"/><rect class="d" x="22" y="20" width="9" height="9"/><rect class="d" x="17" y="11" width="9" height="9"/></g>',
 "factory": '<path class="d" d="M6,42 V22 L16,28 V22 L26,28 V22 L36,28 V12 H42 V42 Z"/>'
            '<circle class="d sm" style="--k:0" cx="39" cy="8" r="2.5"/><circle class="d sm" style="--k:1" cx="39" cy="8" r="2.5"/>',
 "scale":   '<path class="d" d="M24,8 V40 M16,40 H32"/><g class="bm" style="transform-origin:24px 12px"><path class="d" d="M8,12 H40"/>'
            '<path class="d" d="M8,12 L4,24 H12 Z"/><path class="d" d="M40,12 L36,24 H44 Z"/></g>',
 "coin":    '<g class="cn" style="transform-origin:24px 24px"><circle class="d" cx="24" cy="24" r="16"/><path class="d" d="M28,17 C22,15 18,18 20,21 C22,24 29,23 28,28 C27,32 21,32 18,30 M24,13 V35"/></g>',
 "yen":     '<g class="cn" style="transform-origin:24px 24px"><circle class="d" cx="24" cy="24" r="16"/><path class="d" d="M17,15 L24,25 L31,15 M24,25 V35 M18,25 H30 M18,30 H30"/></g>',
 "gov":     '<path class="d" d="M6,18 L24,8 L42,18 Z"/><path class="d" d="M10,40 H38 M8,44 H40"/>'
            + "".join(f'<path class="d col" style="--k:{k}" d="M{12 + 8 * k},22 V37"/>' for k in range(4)),
 "people":  '<g class="pp" style="--k:0"><circle class="d" cx="16" cy="17" r="6"/><path class="d" d="M5,40 Q16,24 27,40"/></g>'
            '<g class="pp" style="--k:1"><circle class="d" cx="33" cy="19" r="5"/><path class="d" d="M25,40 Q33,28 43,40"/></g>',
 "doc":     '<path class="d" d="M12,6 H30 L38,14 V42 H12 Z"/><path class="d" d="M30,6 V14 H38"/>'
            + "".join(f'<path class="d ln2" style="--k:{k}" d="M17,{21 + 6 * k} H{33 - 5 * (k % 2)}"/>' for k in range(3)),
 "bolt":    '<path class="d fl" d="M27,4 L11,27 H23 L19,44 L37,19 H25 Z"/>',
 "globe":   '<circle class="d" cx="24" cy="24" r="17"/><path class="d" d="M7,24 H41"/><ellipse class="d mer" cx="24" cy="24" rx="8" ry="17"/>',
 "vote":    '<path class="d" d="M8,24 H40 V42 H8 Z"/><path class="d" d="M18,24 H30"/><g class="pa"><path class="d" d="M19,8 H29 V22 H19 Z"/><path class="d" d="M22,14 L24,17 L27,12"/></g>',
 "gavel":   '<g class="gv" style="transform-origin:30px 32px"><rect class="d" x="14" y="10" width="16" height="9" rx="2" transform="rotate(-35 22 14)"/><path class="d" d="M24,18 L34,32"/></g><path class="d" d="M8,42 H30"/>',
 "alert":   '<path class="d" d="M24,6 L43,40 H5 Z"/><path class="d fl" d="M24,18 V29 M24,34 V35"/>',
 "home":    '<path class="d" d="M8,24 L24,10 L40,24"/><path class="d" d="M13,21 V40 H35 V21"/><path class="d" d="M21,40 V30 H27 V40"/>',
 "person":  '<g class="pp" style="--k:0"><circle class="d" cx="24" cy="16" r="8"/><path class="d" d="M8,42 Q24,24 40,42"/></g>',
 "calendar":'<rect class="d" x="7" y="10" width="34" height="30" rx="4"/><path class="d" d="M7,18 H41 M16,6 V13 M32,6 V13"/><path class="d ck" d="M17,29 L22,34 L32,24"/>',
 "key":     '<g class="cn" style="transform-origin:16px 24px"><circle class="d" cx="16" cy="24" r="8"/></g><path class="d" d="M24,24 H42 M36,24 V30 M41,24 V29"/>',
 "card":    '<rect class="d" x="5" y="12" width="38" height="26" rx="4"/><path class="d" d="M5,20 H43"/><path class="d" d="M11,31 H21"/>',
 "chart":   '<path class="d" d="M6,42 H42"/>' + "".join(f'<path class="d bar" style="--k:{k};transform-origin:{12 + 9 * k}px 42px" d="M{12 + 9 * k},42 V{30 - 7 * k}"/>' for k in range(4)),
 "plane":   '<g class="pl2"><path class="d" d="M6,30 L42,14 L36,22 L40,34 Z"/><path class="d" d="M36,22 L22,28 L24,38"/></g>',
 "phone":   '<rect class="d" x="14" y="6" width="20" height="36" rx="4"/><path class="d" d="M21,36 H27"/><path class="d fl" d="M38,12 Q42,16 38,20 M41,9 Q47,16 41,23"/>',
 "mail":    '<rect class="d" x="6" y="12" width="36" height="26" rx="4"/><path class="d" d="M8,15 L24,27 L40,15"/>',
}
PICTO_CSS = """
.pgc{border-radius:50%;background:var(--pale,#E8EFFF);display:flex;align-items:center;justify-content:center;animation:pgcin .55s var(--t,0s) cubic-bezier(.2,1.5,.4,1) both}
@keyframes pgcin{0%{transform:scale(0);opacity:0}100%{transform:none;opacity:1}}
.pg{overflow:visible}
.pg .d{fill:none;stroke:currentColor;stroke-width:var(--pw,3);stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:1;stroke-dashoffset:1;
animation:pgd .8s calc(var(--t,0s) + var(--k,0) * .08s) cubic-bezier(.4,0,.2,1) forwards}
@keyframes pgd{to{stroke-dashoffset:0}}
.pg .hd{animation:pgd .5s calc(var(--t) + .55s) forwards,pgup 1.4s calc(var(--t) + 1.1s) ease-in-out infinite}
.pg .hd2{animation:pgd .5s calc(var(--t) + .55s) forwards,pgdn 1.4s calc(var(--t) + 1.1s) ease-in-out infinite}
@keyframes pgup{0%,100%{transform:none}50%{transform:translateY(-3px)}}
@keyframes pgdn{0%,100%{transform:none}50%{transform:translateY(3px)}}
.pg .pin{animation:pgd .4s calc(var(--t) + .5s + var(--k) * .06s) forwards,pgbl 1.2s calc(var(--t) + 1s + var(--k) * .2s) steps(2) infinite}
@keyframes pgbl{50%{stroke:var(--acc,#EA6A12)}}
.pg .wh{animation:pgsp 1s calc(var(--t) + .8s) linear infinite}
@keyframes pgsp{to{transform:rotate(360deg)}}
.pg .bx{animation:pgdrop .5s calc(var(--t) + .5s) cubic-bezier(.3,1.5,.5,1) both}
@keyframes pgdrop{0%{transform:translateY(-14px);opacity:0}100%{transform:none;opacity:1}}
.pg .sm{animation:pgd .3s calc(var(--t) + .6s) forwards,pgsm 1.6s calc(var(--t) + .6s + var(--k) * .8s) ease-out infinite}
@keyframes pgsm{0%{transform:translateY(0) scale(.6);opacity:0}30%{opacity:1}100%{transform:translateY(-14px) scale(1.4);opacity:0}}
.pg .bm{animation:pgtilt 2.4s calc(var(--t) + .8s) ease-in-out infinite}
@keyframes pgtilt{0%,100%{transform:rotate(-9deg)}50%{transform:rotate(9deg)}}
.pg .cn{animation:pgpop 1.6s calc(var(--t) + .8s) ease-in-out infinite}
@keyframes pgpop{0%,100%{transform:scale(1)}50%{transform:scale(1.12)}}
.pg .col{animation:pgd .4s calc(var(--t) + .4s + var(--k) * .12s) forwards}
.pg .pp{animation:pgbob 1.8s calc(var(--t) + .7s + var(--k) * .3s) ease-in-out infinite}
@keyframes pgbob{0%,100%{transform:none}50%{transform:translateY(-3px)}}
.pg .ln2{animation:pgd .35s calc(var(--t) + .6s + var(--k) * .22s) forwards}
.pg .fl{animation:pgd .5s var(--t) forwards,pgfl 1.1s calc(var(--t) + .7s) steps(2) infinite}
@keyframes pgfl{50%{stroke:var(--acc,#EA6A12)}}
.pg .mer{animation:pgd .6s calc(var(--t) + .3s) forwards,pgmer 2.2s calc(var(--t) + .9s) ease-in-out infinite}
@keyframes pgmer{0%,100%{rx:8px}50%{rx:2px}}
.pg .pa{animation:pgvote 1.8s calc(var(--t) + .6s) cubic-bezier(.5,0,.5,1) infinite}
@keyframes pgvote{0%{transform:translateY(-6px);opacity:0}20%{opacity:1}60%,100%{transform:translateY(10px);opacity:0}}
.pg .gv{animation:pghit 1.2s calc(var(--t) + .7s) cubic-bezier(.6,0,.4,1) infinite}
@keyframes pghit{0%,100%{transform:rotate(-18deg)}40%{transform:rotate(12deg)}55%{transform:rotate(6deg)}}
.pg .ck{animation:pgd .4s calc(var(--t) + .9s) forwards}
.pg .bar{animation:pgd .4s calc(var(--t) + .3s + var(--k) * .1s) forwards,pggrow 1.8s calc(var(--t) + 1s + var(--k) * .15s) ease-in-out infinite}
@keyframes pggrow{0%,100%{transform:scaleY(1)}50%{transform:scaleY(1.18)}}
.pg .pl2{animation:pgbob 1.6s calc(var(--t) + .8s) ease-in-out infinite}
"""


def picto(name, size, t, color="var(--blue)", pw=3, cls="", style=""):
    inner = PICTO.get(name)
    if not inner:
        return ""
    return (f'<svg class="pg {cls}" width="{size}" height="{size}" viewBox="0 0 48 48" '
            f'style="--t:{t:.2f}s;--pw:{pw};color:{color};{style}">{inner}</svg>')
