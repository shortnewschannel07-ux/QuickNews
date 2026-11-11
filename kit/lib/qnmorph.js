/* Quick News — 変形＋移動の場面（v11, canvas）
   すべてのコマは時刻 t の純粋な関数として描く。
   ・アイコンは点列（本体240点＋穴2つ＋線1本）で表し、いったん円を経由して別の形に変形する
   ・移動は「ため → 発射 → 頂点で一瞬止まる → 急降下 → 着地の衝撃」
   ・新しい背景色は着地点から衝撃波のように広がり、その円の内側だけ新しい配色で描く
   ・カメラは遅れて追い、着地で揺れる。移動中だけ簡易モーションブラーをかける                       */
window.QNMorph = function (cv, CFG) {
  const W = 1080, H = 1920, CX = CFG.cx || 513, CY = CFG.cy || 650, FPS = 30, FR = 1 / FPS;
  const main = cv.getContext('2d');
  const mkC = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };
  const bufC = mkC(), bctx = bufC.getContext('2d'), offC = mkC(), octx = offC.getContext('2d');
  const FONT = '"Zen Kaku Gothic New","Yu Gothic",sans-serif';
  // ---------------------------------------------------------------- math
  const clamp = (x, a = 0, b = 1) => x < a ? a : x > b ? b : x, lerp = (a, b, t) => a + (b - a) * t;
  const smooth = (a, b, x) => { const t = clamp((x - a) / (b - a)); return t * t * (3 - 2 * t); };
  const deg = Math.PI / 180;
  function bez(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx, cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = t => ((ax * t + bx) * t + cx) * t, sy = t => ((ay * t + by) * t + cy) * t;
    return x => { if (x <= 0) return 0; if (x >= 1) return 1; let lo = 0, hi = 1, t = x;
      for (let i = 0; i < 40; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-7) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return sy(t); };
  }
  const EM = bez(0.7, 0, 0.3, 1), EO = bez(0.16, 1, 0.3, 1), EIO = bez(0.45, 0, 0.55, 1), ECL = bez(0.32, 0, 0.1, 1);
  const EOB = x => { x = clamp(x); const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
  const hexRgb = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mixC = (a, b, t) => { t = clamp(t); const A = hexRgb(a), B = hexRgb(b); return 'rgb(' + A.map((v, i) => Math.round(lerp(v, B[i], t))).join(',') + ')'; };
  const rgba = (h, a) => { const c = hexRgb(h); return 'rgba(' + c[0] + ',' + c[1] + ',' + c[2] + ',' + a + ')'; };
  const rnd = s => { const x = Math.sin(s * 12.9898) * 43758.5453; return x - Math.floor(x); };
  const qb = (a, c, b, u) => [(1 - u) * (1 - u) * a[0] + 2 * (1 - u) * u * c[0] + u * u * b[0], (1 - u) * (1 - u) * a[1] + 2 * (1 - u) * u * c[1] + u * u * b[1]];
  const qbd = (a, c, b, u) => [2 * (1 - u) * (c[0] - a[0]) + 2 * u * (b[0] - c[0]), 2 * (1 - u) * (c[1] - a[1]) + 2 * u * (b[1] - c[1])];
  // ---------------------------------------------------------------- geometry
  const NB = 240, NH = 64, NM = 32;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.style.cssText = 'position:absolute;width:0;height:0'; document.body.appendChild(svg);
  function sampleD(d, n, closed = true) {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path'); p.setAttribute('d', d); svg.appendChild(p);
    const L = p.getTotalLength(), o = [], den = closed ? n : n - 1;
    for (let i = 0; i < n; i++) { const q = p.getPointAtLength(L * i / den); o.push([q.x, q.y]); }
    svg.removeChild(p); return o;
  }
  const area = P => { let a = 0; for (let i = 0; i < P.length; i++) { const p = P[i], q = P[(i + 1) % P.length]; a += p[0] * q[1] - q[0] * p[1]; } return a / 2; };
  const orient = P => area(P) < 0 ? P.slice().reverse() : P;
  const centroid = P => { let x = 0, y = 0; for (const p of P) { x += p[0]; y += p[1]; } return [x / P.length, y / P.length]; };
  function resamplePoly(P, n) {
    const L = [0]; for (let i = 1; i <= P.length; i++) { const a = P[i - 1], b = P[i % P.length]; L.push(L[i - 1] + Math.hypot(b[0] - a[0], b[1] - a[1])); }
    const tot = L[P.length], o = []; let j = 0;
    for (let i = 0; i < n; i++) { const s = tot * i / n; while (L[j + 1] < s) j++; const a = P[j], b = P[(j + 1) % P.length], u = (s - L[j]) / ((L[j + 1] - L[j]) || 1); o.push([lerp(a[0], b[0], u), lerp(a[1], b[1], u)]); }
    return o;
  }
  const circ = (cx, cy, r, n) => Array.from({ length: n }, (_, i) => { const a = 2 * Math.PI * i / n - Math.PI / 2; return [cx + r * Math.cos(a), cy + r * Math.sin(a)]; });
  function bestShift(A, B) { const n = A.length; let best = Infinity, bs = 0;
    for (let s = 0; s < n; s++) { let e = 0; for (let i = 0; i < n; i += 2) { const b = B[(i + s) % n], dx = A[i][0] - b[0], dy = A[i][1] - b[1]; e += dx * dx + dy * dy; if (e >= best) break; } if (e < best) { best = e; bs = s; } }
    return bs; }
  const shiftP = (B, s) => B.map((_, i) => B[(i + s) % B.length]);
  const lerpP = (A, B, t) => A.map((a, i) => [lerp(a[0], B[i][0], t), lerp(a[1], B[i][1], t)]);
  const rep = (p, n) => Array.from({ length: n }, () => [p[0], p[1]]);
  const _al = new Map();
  const alignTo = (key, A, B) => { if (!_al.has(key)) _al.set(key, bestShift(A, B)); return shiftP(B, _al.get(key)); };
  function rpoly(pts, r) { const n = pts.length; let d = '';
    for (let i = 0; i < n; i++) { const p = pts[i], a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n], rr = Array.isArray(r) ? r[i] : r;
      const da = Math.hypot(a[0] - p[0], a[1] - p[1]), db = Math.hypot(b[0] - p[0], b[1] - p[1]), k1 = Math.min(rr, da / 2) / da, k2 = Math.min(rr, db / 2) / db;
      d += (i ? 'L' : 'M') + (p[0] + (a[0] - p[0]) * k1) + ',' + (p[1] + (a[1] - p[1]) * k1) + 'Q' + p[0] + ',' + p[1] + ' ' + (p[0] + (b[0] - p[0]) * k2) + ',' + (p[1] + (b[1] - p[1]) * k2); }
    return d + 'Z'; }
  const circD = r => `M ${-r},0 A ${r} ${r} 0 1 0 ${r} 0 A ${r} ${r} 0 1 0 ${-r} 0 Z`;
  // ---------------------------------------------------------------- icons（中心は見た目の中心、約220px）
  function mkIcon(name, def) {
    const body = orient(sampleD(def.body, NB)), c = centroid(body);
    const holes = [0, 1].map(k => def.holes && def.holes[k] ? { pts: orient(sampleD(def.holes[k], NH)), on: true } : { pts: rep(c, NH), on: false });
    const st = def.stroke ? { pts: def.strokePts || sampleD(def.stroke, NM, false), w: def.w } : { pts: rep(c, NM), w: 0 };
    return { name, body, holes, strokes: [st], rot0: def.rot0 || 0, piv: def.piv || [0, 100], r: Math.sqrt(Math.abs(area(body)) / Math.PI) };
  }
  const I = {};
  I.dot = mkIcon('dot', { body: circD(80), piv: [0, 80] });
  I.globe = mkIcon('globe', { body: circD(110), piv: [0, 110] });
  I.arrow = mkIcon('arrow', { body: rpoly([[0, -118], [102, -12], [36, -12], [36, 112], [-36, 112], [-36, -12], [-102, -12]], 12), rot0: 45 * deg, piv: [0, 112] });
  I.chart = mkIcon('chart', { body: rpoly([[-110, 105], [-110, 10], [-60, 10], [-60, 72], [-25, 72], [-25, -40], [25, -40], [25, 72], [60, 72], [60, -100], [110, -100], [110, 105]], [14, 10, 10, 5, 5, 10, 10, 5, 5, 10, 10, 14]), piv: [0, 105] });
  const lockBody = rpoly([[-98, -14], [98, -14], [98, 118], [-98, 118]], 24);
  const keyhole = 'M -9,60 A 21 21 0 1 1 9,60 L 12,86 Q 12,92 6,92 L -6,92 Q -12,92 -12,86 Z';
  const shackle = 'M -60,-14 L -60,-50 C -60,-134 60,-134 60,-50 L 60,-14';
  I.lock = mkIcon('lock', { body: lockBody, holes: [keyhole], stroke: shackle, w: 30, piv: [0, 118] });
  { const sp = sampleD(shackle, NM, false), a = -32 * deg, ox = -60, oy = -48;
    const openPts = sp.map(([x, y]) => { y -= 34; const dx = x - ox, dy = y - oy; return [ox + dx * Math.cos(a) - dy * Math.sin(a), oy + dx * Math.sin(a) + dy * Math.cos(a)]; });
    I.lock_open = mkIcon('lock_open', { body: lockBody, holes: [keyhole], stroke: shackle, strokePts: openPts, w: 30, piv: [0, 118] }); }
  I.card = mkIcon('card', { body: rpoly([[-135, -86], [135, -86], [135, 86], [-135, 86]], 20), holes: [rpoly([[-104, -50], [-54, -50], [-54, -12], [-104, -12]], 8), rpoly([[-104, 34], [52, 34], [52, 52], [-104, 52]], 9)], piv: [0, 86] });
  I.bolt = mkIcon('bolt', { body: rpoly([[22, -118], [-74, 14], [-10, 14], [-30, 118], [74, -18], [10, -18]], 8), piv: [0, 118] });
  I.bubble = mkIcon('bubble', { body: rpoly([[-112, -82], [112, -82], [112, 48], [8, 48], [-58, 104], [-40, 48], [-112, 48]], [30, 30, 30, 4, 6, 4, 30]),
    holes: [rpoly([[-72, -44], [72, -44], [72, -24], [-72, -24]], 10), rpoly([[-72, -4], [28, -4], [28, 16], [-72, 16]], 10)], piv: [0, 104] });
  // ---------------------------------------------------------------- morph（円を経由）
  function blend(A, B, u, key) {
    const rc = 0.5 * (A.r + B.r) * 0.86, C = circ(0, 0, rc, NB);
    let body; const gA = EM(clamp(u / 0.5)), gB = EM(clamp((u - 0.5) / 0.5));
    body = u < 0.5 ? lerpP(A.body, alignTo(A.name + '>o', A.body, C), gA) : lerpP(alignTo(B.name + '<o', B.body, C), B.body, gB);
    const holes = [0, 1].map(k => { const hA = A.holes[k], hB = B.holes[k];
      if (u < 0.5) return { pts: lerpP(hA.pts, rep(centroid(hA.pts), NH), clamp(gA / 0.6)), on: hA.on };
      return { pts: lerpP(rep(centroid(hB.pts), NH), hB.pts, clamp((gB - 0.4) / 0.6)), on: hB.on }; });
    const sa = A.strokes[0], sb = B.strokes[0];
    const strokes = [u < 0.5 ? { pts: lerpP(sa.pts, rep(sa.pts[NM >> 1], NM), gA), w: sa.w * (1 - gA) } : { pts: lerpP(rep(sb.pts[NM >> 1], NM), sb.pts, gB), w: sb.w * gB }];
    return { body, holes, strokes };
  }
  function direct(A, B, g) {   // 本体が同じ形どうし（鍵が開く）
    return { body: A.body, holes: A.holes, strokes: [{ pts: lerpP(A.strokes[0].pts, B.strokes[0].pts, g), w: lerp(A.strokes[0].w, B.strokes[0].w, g) }] };
  }
  // 変換：衝撃のつぶれ（ローカル軸・支点まわり）→ 拡大・回転 → 進行方向への伸び → 移動
  function makeM(pos, rot, sc, phi, k, q, piv) {
    const c = Math.cos(rot), s = Math.sin(rot), R = [c * sc, -s * sc, s * sc, c * sc], D = [1 + q, 0, 0, 1 - q];
    const cp = Math.cos(phi), sp = Math.sin(phi), ik = 1 / k;
    const Q = [cp * cp * k + sp * sp * ik, cp * sp * (k - ik), cp * sp * (k - ik), sp * sp * k + cp * cp * ik];
    const mul = (a, b) => [a[0] * b[0] + a[1] * b[2], a[0] * b[1] + a[1] * b[3], a[2] * b[0] + a[3] * b[2], a[2] * b[1] + a[3] * b[3]];
    const QR = mul(Q, R), A = mul(QR, D), dp = [piv[0] - D[0] * piv[0], piv[1] - D[3] * piv[1]];
    return { A, b: [pos[0] + QR[0] * dp[0] + QR[1] * dp[1], pos[1] + QR[2] * dp[0] + QR[3] * dp[1]] };
  }
  const applyM = M => p => [M.A[0] * p[0] + M.A[1] * p[1] + M.b[0], M.A[2] * p[0] + M.A[3] * p[1] + M.b[1]];
  // ---------------------------------------------------------------- 配色
  const PAL = {
    // 青＝信頼・知性（主役）、紺＝権威・落ち着き、白＝明快さ、橙＝注目・前向きな動き（青の補色、使うのは全体の1割ほど）
    blue: { bg: '#1F5BFF', fg: '#FFFFFF', ink: '#FFFFFF', acc: '#FFC24B', num: '#FFFFFF', sub: 'rgba(255,255,255,.80)', far: 0.13, shadow: 'rgba(5,20,70,.22)', dark: true },
    navy: { bg: '#0B1B33', fg: '#FFFFFF', ink: '#FFFFFF', acc: '#FFB547', num: '#FFFFFF', sub: 'rgba(255,255,255,.72)', far: 0.10, shadow: 'rgba(0,0,0,.35)', dark: true },
    white: { bg: '#F6F8FB', fg: '#1F5BFF', ink: '#0B1B33', acc: '#EA6A12', num: '#1F5BFF', sub: '#5B6B82', far: 0.07, shadow: 'rgba(11,27,51,.12)', dark: false },
    sky: { bg: '#E3EBFF', fg: '#1F5BFF', ink: '#0B1B33', acc: '#EA6A12', num: '#1F5BFF', sub: '#5B6B82', far: 0.08, shadow: 'rgba(11,27,51,.12)', dark: false },
  };
  // ---------------------------------------------------------------- 場面データ
  const S = CFG.shots, N = S.length, FL = CFG.flight || 0.62;
  S.forEach((s, i) => {
    s.i = i;
    s.pal = PAL[s.bg] || PAL.white;
    s.ic = I[s.icon] || I.dot;
    s.ic2 = s.icon2 ? I[s.icon2] : null;
    s.landAt = [s.x + (s.land_off ? s.land_off[0] : 0), s.y + (s.land_off ? s.land_off[1] : 0)];
    s.landSc = s.land_sc || 1;
    s.next = i + 1 < N ? S[i + 1].L : null;
  });
  // 着地の衝撃（減衰する正弦）
  const impactQ = (t, T, A = 0.24) => { const τ = t - (T - 2 * FR); return τ < 0 || τ > 1.2 ? 0 : A * Math.sin(2 * Math.PI * τ / 0.28) * Math.exp(-τ * 7.5); };
  const impactS = τ => τ < 0 || τ > 0.6 ? 0 : 0.14 * Math.sin(2 * Math.PI * τ / 0.24) * Math.exp(-τ * 9);
  // 音楽の拍（BGM と同じテンポ）に合わせた小さな脈動
  const BEAT = 60 / (CFG.bpm || 104), TG = CFG.tg0 || 0;
  const pulseAt = t => { const g = t + TG, bq = ((g % BEAT) + BEAT) % BEAT; return 0.018 * Math.exp(-bq * 11) * (1 - Math.exp(-bq * 60)); };

  // ---------------------------------------------------------------- 文字（ロゴ）の形
  let WM = null;
  const logoShot = S.find(s => s.visual === 'logo');
  if (logoShot && CFG.glyphs) {
    // 「Quick News」。主役の点は i の上の点になる（ピリオドは付けない）
    const GL = CFG.glyphs, FS = 150, s = FS / GL.upm, track = -0.01 * FS, yB = logoShot.y + 52, word = 'Quick News';
    const advs = [...word].map(ch => ch === ' ' ? GL.space * s * 0.9 : GL.glyphs[ch].adv * s);
    const total = advs.reduce((a, b) => a + b, 0) + track * (word.length - 1);
    let x = logoShot.x - total / 2; const letters = []; let dot = null, dotR = 10, dotPath = null;
    [...word].forEach((ch, k) => {
      if (ch !== ' ') {
        const g = GL.glyphs[ch]; let cs = g.contours.map(c => c.map(([gx, gy]) => [x + gx * s, yB - gy * s]));
        let oi = 0; g.areas.forEach((a, i) => { if (Math.abs(a) > Math.abs(g.areas[oi])) oi = i; });
        if (ch === 'i') {   // i の点（本体と同じ向きの小さい輪郭）を取り出す
          const di = g.areas.findIndex((a, i) => i !== oi && Math.sign(a) === Math.sign(g.areas[oi]));
          if (di >= 0) { const dc = cs[di]; dot = centroid(dc); dotR = Math.sqrt(Math.abs(area(dc)) / Math.PI);
            dotPath = new Path2D(); dc.forEach((p, i) => i ? dotPath.lineTo(p[0], p[1]) : dotPath.moveTo(p[0], p[1])); dotPath.closePath();
            cs = cs.filter((_, i) => i !== di); if (di < oi) oi -= 1; }
        }
        const outer = orient(resamplePoly(cs[oi], 200));
        const holes = cs.filter((_, i) => i !== oi).map(c => orient(resamplePoly(c, NH)));
        const cen = centroid(outer), ar = Math.abs(area(outer));
        letters.push({ ch, outer, holes, cen, R: Math.sqrt(ar / Math.PI) * 0.82, news: k > 5, k: letters.length });
      }
      x += advs[k] + track;
    });
    WM = { letters, dot: dot || [x, yB - 20], dotR, dotPath, yB, FS };
  }

  // ---------------------------------------------------------------- 各地点での主役の状態
  function shotShape(s, t) {
    if (s.ic2 && t > s.t2) { const p = clamp((t - s.t2) / 0.42); return p >= 1 ? s.ic2 : direct(s.ic, s.ic2, Math.min(1.08, EOB(p))); }
    return s.ic;
  }
  const SPK = { a: [-380, 230], c1: [-110, 238], c2: [130, 125], b: [355, 10] };
  const cub = (s, u) => { const v = 1 - u, A = SPK.a, B = SPK.c1, C = SPK.c2, D = SPK.b;
    return [s.x + v * v * v * A[0] + 3 * v * v * u * B[0] + 3 * v * u * u * C[0] + u * u * u * D[0], s.y + v * v * v * A[1] + 3 * v * v * u * B[1] + 3 * v * u * u * C[1] + u * u * u * D[1]]; };
  const sparkU = (s, t) => EIO(clamp((t - (s.land + 0.12)) / 1.0));
  const BARSC = 2.0;
  function holdState(s, t) {
    let pos = s.landAt.slice(), sc = s.landSc, rot = s.ic.rot0, parts = shotShape(s, t), extra = {};
    const back = s.next != null ? EIO(clamp((t - (s.next - 0.5)) / 0.25)) : 0;   // 発射の前に元の大きさへ戻る
    if (s.visual === 'globe') { sc = lerp(1 + 1.27 * EO(clamp((t - (s.land + 0.12)) / 0.45)), 1, back); extra.globe = 1 - back; }
    else if (s.visual === 'spark') { const u = sparkU(s, t), p = cub(s, u), p2 = cub(s, Math.min(1, u + 0.01)), p1 = cub(s, Math.max(0, u - 0.01));
      const th = Math.atan2(p2[1] - p1[1], p2[0] - p1[0]) + Math.PI / 2; const ride = smooth(0, 0.08, u);
      pos = p; rot = lerp(s.ic.rot0, th, ride); sc = s.landSc; }
    else if (s.visual === 'bars') { const g = EO(clamp((t - (s.land + 0.14)) / 0.5)) * (1 - back); sc = lerp(1, BARSC, g); pos = [s.x, s.y + lerp(0, 215 - 105 * BARSC, g)]; extra.bars = g; }
    else if (s.visual === 'cards') { const g = EO(clamp((t - (s.land + 0.12)) / 0.45)) * (1 - back); pos = [s.x, s.y - 70 * g]; }
    else if (s.visual === 'logo' && WM) { const g = EIO(clamp((t - (s.land + 0.12)) / 0.36)); const mid = [(s.x + WM.dot[0]) / 2, Math.min(s.y, WM.dot[1]) - 140];
      pos = qb(s.landAt, mid, WM.dot, g); sc = lerp(1, WM.dotR / 80, g); extra.logo = g; }
    return { pos, sc, rot, parts, extra };
  }
  // 飛行の進み具合：発射で一気に加速 → 頂点で一瞬止まる → 加速しながら急降下
  const APEX = 0.27, HANG = 0.06;
  function flightU(t, L, T) { const a = L + APEX, d = a + HANG;
    if (t <= L) return 0; if (t < a) return 0.5 * ECL((t - L) / APEX);
    if (t < d) return 0.5 + 0.03 * smooth(a, d, t);
    return Math.min(1, 0.53 + 0.47 * Math.pow(clamp((t - d) / (T - d)), 1.65)); }
  function flightPath(k) {   // k: 着く側の場面
    const s = S[k], a = holdState(S[k - 1], s.L), A = a.pos, B = s.landAt, dist = Math.hypot(B[0] - A[0], B[1] - A[1]);
    const C = [(A[0] + B[0]) / 2 + (s.arc_dx || 0), Math.min(A[1], B[1]) - 0.24 * dist - 40];
    return { A, B, C, a };
  }
  const _fp = {}; const FP = k => _fp[k] || (_fp[k] = flightPath(k));
  const asShape = (p, s) => p.name ? p : Object.assign({ name: 'p' + s.i, r: s.ic.r }, p);
  function heroAt(t) {
    // 現在の区間
    let k = 0; for (let i = 1; i < N; i++) if (t >= S[i].L - 0.24) k = i;
    const s = S[k];
    if (k > 0 && t < s.land + 0.9) {
      const L = s.L, T = s.land, P = FP(k);
      if (t < T) {
        const u = flightU(t, L, T), pos0 = qb(P.A, P.C, P.B, u), d = qbd(P.A, P.C, P.B, Math.max(0.001, u));
        const u2 = flightU(t + 0.004, L, T), sp = Math.hypot(...[0, 1].map(j => qb(P.A, P.C, P.B, u2)[j] - pos0[j])) / 0.004;
        let phi = Math.atan2(d[1], d[0]);
        const d0 = qbd(P.A, P.C, P.B, 0.001), phi0 = Math.atan2(d0[1], d0[0]);
        const ant = t < L ? EIO(clamp((t - (L - 0.22)) / 0.19)) : 1 - EO(clamp((t - L) / 0.1));
        const hang = Math.sin(Math.PI * clamp((t - (L + APEX - 0.02)) / 0.14));
        const mu = t < L ? 0 : t < L + APEX ? 0.5 * clamp((t - L) / APEX) : t < T - 0.2 ? 0.5 : 0.5 + 0.5 * clamp((t - (T - 0.2)) / 0.26);
        const A = P.a.parts, B = s.ic;
        const parts = mu <= 0 ? A : blend(asShape(A, S[k - 1]), B, mu);
        if (t < L) phi = phi0;
        const k2 = 1 - 0.18 * ant + 0.16 * clamp(sp / 2600) - 0.12 * hang + 0.06 * Math.sin(Math.PI * EM(mu));
        const pull = 38 * ant * (t < L ? 1 : 0.6);
        const pos = [pos0[0] - Math.cos(phi0) * pull, pos0[1] - Math.sin(phi0) * pull];
        const g = EIO(clamp((t - L) / (T - L)));
        const spin = (P.B[0] > P.A[0] ? 1 : -1) * 28 * deg * Math.sin(Math.PI * g);
        const rot = lerp(P.a.rot, s.ic.rot0, smooth(0.45, 1, g)) + spin;
        const sc = lerp(P.a.sc, s.landSc, g);
        const piv = mu > 0.5 ? s.ic.piv : [0, 0];
        return { k, parts, M: makeM(pos, rot, sc, phi, k2, 0, piv), flying: true, u, pos, sc };
      }
      // 着地後：変形の残りと衝撃
      const mu = clamp(0.5 + 0.5 * (t - (T - 0.2)) / 0.26);
      const st = holdState(s, t);
      const parts = mu < 1 ? blend(asShape(FP(k).a.parts, S[k - 1]), s.ic, mu) : st.parts;
      const q = impactQ(t, T);
      return { k, parts, M: makeM(st.pos, st.rot, st.sc * (1 + pulseAt(t) * smooth(T + 0.4, T + 0.8, t)), Math.PI / 2, 1, q, s.ic.piv), st, pos: st.pos, sc: st.sc };
    }
    // 最初の地点：上から落ちてきて着地
    if (k === 0 && t < s.land + 0.9) {
      const T = s.land, h = 280, tt = Math.min(t, T), t0 = CFG.first ? 0 : Math.max(0, T - 0.36);
      const y = s.landAt[1] - h * (1 - Math.pow(clamp((tt - t0) / (T - t0)), 2)) * (t < T ? 1 : 0);
      const kk = 1 + 0.32 * (1 - smooth(T - 2 * FR, T + FR, t));
      const mu = clamp(0.5 + 0.5 * (t - (T - 0.22)) / 0.28);
      const C0 = { name: 'drop', body: circ(0, 0, s.ic.r * 0.8, NB), holes: s.ic.holes.map(hh => ({ pts: rep(centroid(hh.pts), NH), on: false })), strokes: [{ pts: rep([0, 0], NM), w: 0 }], r: s.ic.r * 0.8 / 0.86 };
      const st = holdState(s, t);
      const parts = mu < 1 ? blend(C0, s.ic, mu) : st.parts;
      const pos = t < T ? [s.landAt[0], y] : st.pos;
      return { k, parts, M: makeM(pos, t < T ? 0 : st.rot, t < T ? s.landSc : st.sc, Math.PI / 2, kk, impactQ(t, T), s.ic.piv), pos, sc: st.sc, st: t < T ? null : st, flying: t < T };
    }
    const st = holdState(s, t);
    return { k, parts: st.parts, M: makeM(st.pos, st.rot, st.sc * (1 + pulseAt(t)), Math.PI / 2, 1, 0, s.ic.piv), st, pos: st.pos, sc: st.sc };
  }
  // ---------------------------------------------------------------- カメラ
  function camHold(s, t) { let ox = 0, oy = 0; if (s.visual === 'spark') { const u = 1 - EIO(clamp((t - (s.land + 0.1)) / 1.1)); ox = -200 * u; oy = 60 * u; }
    return [s.x + ox + Math.sin(t * 0.9) * 5, s.y + oy + Math.cos(t * 0.7) * 5]; }
  const zHold = (s, t) => 1 + 0.035 * EIO(clamp((t - s.land) / 2.6));
  function camAt(t) {
    let k = 0; for (let i = 1; i < N; i++) if (t >= S[i].L - 0.08) k = i;
    const s = S[k]; let c, z, rot = 0.35 * deg * Math.sin(2 * Math.PI * t / 6.4);
    if (k > 0 && t < s.land + 0.1) {
      const p = clamp((t - (s.L - 0.08)) / (s.land - s.L + 0.16)), e = EIO(p), a = camHold(S[k - 1], t), b = camHold(s, t);
      c = [lerp(a[0], b[0], e), lerp(a[1], b[1], e)];
      z = lerp(zHold(S[k - 1], t), 1, e) * (1 - 0.32 * Math.sin(Math.PI * p));
      rot += (b[0] > a[0] ? -1 : 1) * 4 * deg * Math.sin(Math.PI * p);
    } else { c = camHold(s, t); z = zHold(s, t); }
    let dx = 0, dy = 0;
    for (const sh of S) { const τ = t - sh.land; if (τ > 0 && τ < 0.6) { const a = sh.i === 0 ? 0.7 : 1; dy += a * 15 * Math.sin(2 * Math.PI * τ / 0.11) * Math.exp(-τ * 13); dx += a * 5 * Math.sin(2 * Math.PI * τ / 0.13 + 1) * Math.exp(-τ * 13);
      z *= 1 + 0.02 * a * Math.sin(Math.PI * clamp(τ / 0.18)); } }
    const cs = Math.cos(rot) * z, sn = Math.sin(rot) * z;
    return { a: cs, b: sn, c: -sn, d: cs, e: CX + dx - (cs * c[0] - sn * c[1]), f: CY + dy - (sn * c[0] + cs * c[1]), z, cc: c };
  }
  const toScreen = (K, p) => [K.a * p[0] + K.c * p[1] + K.e, K.b * p[0] + K.d * p[1] + K.f];
  // ---------------------------------------------------------------- 背景色の広がり（着地点から衝撃波のように）
  const farR = o => Math.max(...[[-200, -200], [W + 200, -200], [-200, H + 200], [W + 200, H + 200]].map(c => Math.hypot(c[0] - o[0], c[1] - o[1])));
  const _org = {};
  function fieldOrigin(i) { if (_org[i]) return _org[i]; const s = S[i], h = heroAt(s.land), K = camAt(s.land), M = h.M;
    const pv = applyM(M)(s.ic.piv); return (_org[i] = toScreen(K, [lerp(h.pos[0], pv[0], 0.6), lerp(h.pos[1], pv[1], 0.6)])); }
  function fieldReg(i, t) {
    if (i === 0) return 'full';
    const s = S[i], t0 = s.land - FR, T = 0.6, tc = 0.07;
    if (t < t0) return null; if (t >= t0 + T) return 'full';
    const o = fieldOrigin(i), rmax = farR(o), rr = x => { const τ = clamp(x - t0, 0, T); return lerp(18, rmax, (1 - Math.exp(-τ / tc)) / (1 - Math.exp(-T / tc))); };
    const v = Math.abs(rr(t + 0.004) - rr(Math.max(t0, t - 0.004))) / 0.008;
    return { o, r: rr(t), fw: Math.min(36, v * 0.5 / FPS * 0.35) };
  }
  // ---------------------------------------------------------------- 描画部品
  function rr(c, x, y, w, h, r) { c.beginPath(); c.moveTo(x + r, y); c.arcTo(x + w, y, x + w, y + h, r); c.arcTo(x + w, y + h, x, y + h, r); c.arcTo(x, y + h, x, y, r); c.arcTo(x, y, x + w, y, r); c.closePath(); }
  const poly = (path, P) => { path.moveTo(P[0][0], P[0][1]); for (let i = 1; i < P.length; i++) path.lineTo(P[i][0], P[i][1]); path.closePath(); };
  function drawShape(c, parts, M, fill) {
    const T = applyM(M), path = new Path2D(); poly(path, parts.body.map(T));
    for (const h of parts.holes) if (h.on !== false || true) poly(path, h.pts.map(T));
    c.fillStyle = fill; c.fill(path, 'evenodd');
    const sc = Math.sqrt(Math.abs(M.A[0] * M.A[3] - M.A[1] * M.A[2]));
    for (const st of parts.strokes) { const w = st.w * sc; if (w < 0.8) continue; c.save(); c.strokeStyle = fill; c.lineWidth = w; c.lineCap = 'round'; c.lineJoin = 'round';
      c.beginPath(); st.pts.map(T).forEach((p, i) => i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1])); c.stroke(); c.restore(); }
    return path;
  }
  const fmt = (v, dec) => v.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  function drawNumber(c, x, y, o, a) {   // o: {pre, val, unit, dec, sz, colPre, colNum, align}
    if (a <= 0.001) return;
    const sz = o.sz, txt = fmt(o.val, o.dec || 0);
    c.save(); c.textBaseline = 'alphabetic';
    c.font = `700 ${Math.round(sz * 0.32)}px ${FONT}`; const wp = o.pre ? c.measureText(o.pre).width + sz * 0.06 : 0;
    c.font = `700 ${Math.round(sz * 0.38)}px ${FONT}`; const wu = o.unit ? c.measureText(o.unit).width + sz * 0.05 : 0;
    c.font = `900 ${sz}px ${FONT}`; const cell = Math.max(...'0123456789'.split('').map(d => c.measureText(d).width)) * 0.96, cw = c.measureText(',').width * 0.8;
    const fin = fmt(o.target != null ? o.target : o.val, o.dec || 0); let wn = 0; for (const ch of fin) wn += /[0-9]/.test(ch) ? cell : cw;
    const tot = wp + wn + wu; let x0 = o.align === 'left' ? x : x - tot / 2;
    const k = 1 + 0.35 * (1 - EO(a)); c.translate(x, y - sz * 0.35); c.scale(k, k); c.translate(-x, -(y - sz * 0.35)); c.globalAlpha = clamp(a * 1.4);
    if (o.pre) { c.font = `700 ${Math.round(sz * 0.32)}px ${FONT}`; c.fillStyle = o.colPre; c.textAlign = 'left'; c.fillText(o.pre, x0, y); x0 += wp; }
    c.font = `900 ${sz}px ${FONT}`; c.fillStyle = o.colNum; c.textAlign = 'center';
    // 右寄せで桁を並べる（桁数が増えても位置がぶれない）
    let xr = x0 + wn; const chars = [...txt].reverse();
    for (const ch of chars) { const w = /[0-9]/.test(ch) ? cell : cw; c.fillText(ch, xr - w / 2, y); xr -= w; }
    if (o.unit) { c.font = `700 ${Math.round(sz * 0.38)}px ${FONT}`; c.fillStyle = o.colPre; c.textAlign = 'left'; c.fillText(o.unit, x0 + wn + sz * 0.05, y); }
    c.restore();
  }
  const countV = (s, t, t0, dur) => { const p = clamp((t - t0) / dur); return p >= 1 ? s.number : s.number * (1 - Math.pow(1 - p, 3)); };
  function pill(c, x, y, txt, sz, bg, fg, a, sc = 1) {
    if (a <= 0) return; c.save(); c.font = `700 ${sz}px ${FONT}`; const w = c.measureText(txt).width + sz * 1.1, h = sz * 1.75;
    c.globalAlpha = clamp(a); c.translate(x, y); c.scale(sc, sc); c.fillStyle = 'rgba(11,27,51,.16)'; rr(c, -w / 2, -h / 2 + 8, w, h, h / 2); c.fill();
    c.fillStyle = bg; rr(c, -w / 2, -h / 2, w, h, h / 2); c.fill(); c.fillStyle = fg; c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(txt, 0, sz * 0.04); c.restore();
  }
  // 地球儀（主役の円の中に描く）
  const FEATS = (typeof topojson !== 'undefined' && typeof WORLD !== 'undefined') ? topojson.feature(WORLD, WORLD.objects.countries).features : [];
  const LAND = FEATS.length ? (WORLD.objects.land ? topojson.feature(WORLD, WORLD.objects.land) : { type: 'FeatureCollection', features: FEATS }) : null;
  const GRAT = typeof d3 !== 'undefined' ? d3.geoGraticule10() : null;
  function drawGlobe(c, s, h, t) {
    if (!LAND) return; const ex = h.st && h.st.extra.globe; if (!ex) return;
    const r = I.globe.r * h.sc * 0.995, p = h.pos;
    const f = s.next != null ? clamp((s.next - 0.5 - s.land) / 1.9, 0.5, 1) : 1, L0 = s.land;
    const a = smooth(L0 + 0.2 * f, L0 + 0.45 * f, t) * ex; if (a <= 0.01) return;
    const g = EIO(clamp((t - (L0 + 0.1)) / (1.25 * f))), z = EIO(clamp((t - (L0 + 0.6 * f)) / (1.1 * f)));
    const tg = s.target || [2.35, 48.86];
    const proj = d3.geoOrthographic().clipAngle(90).translate([p[0], p[1]]).scale(r * lerp(1, 2.1, z)).rotate([-lerp(-35, tg[0] + 4, g), -lerp(18, tg[1] - 3, g)]).precision(0.6);
    const gp = d3.geoPath(proj, c);
    c.save(); c.globalAlpha = 0.55 * a; c.strokeStyle = '#FFFFFF'; c.lineWidth = 2.5; c.setLineDash([3, 16]); c.lineCap = 'round'; const ph = t * 0.9;
    c.beginPath(); c.ellipse(p[0], p[1], r * 1.3, r * 1.3 * 0.32, -14 * deg, ph, ph + 2 * Math.PI); c.stroke();
    c.setLineDash([]); c.fillStyle = '#FFC24B'; c.globalAlpha = a; const oa = ph * 1.6, ox = r * 1.3 * Math.cos(oa), oy = r * 1.3 * 0.32 * Math.sin(oa), rr0 = -14 * deg;
    if (Math.sin(oa) > -0.2) { c.beginPath(); c.arc(p[0] + ox * Math.cos(rr0) - oy * Math.sin(rr0), p[1] + ox * Math.sin(rr0) + oy * Math.cos(rr0), 9, 0, 2 * Math.PI); c.fill(); }
    c.restore();
    c.save(); c.beginPath(); c.arc(p[0], p[1], r, 0, 2 * Math.PI); c.clip(); c.globalAlpha = a;
    c.beginPath(); gp(GRAT); c.strokeStyle = 'rgba(31,91,255,.12)'; c.lineWidth = 1.5; c.stroke();
    c.beginPath(); gp(LAND); c.fillStyle = '#C9D6EC'; c.fill(); c.strokeStyle = '#FFFFFF'; c.lineWidth = 1; c.stroke();
    const hl = (s.hl || []).map(id => FEATS.find(f => String(f.id) === String(id))).filter(Boolean);
    const ha = smooth(L0 + 1.0 * f, L0 + 1.25 * f, t);
    if (ha > 0) { c.globalAlpha = a * ha; c.beginPath(); hl.forEach(f => gp(f)); c.fillStyle = '#1F5BFF'; c.fill(); }
    c.restore();
    // ピン
    const tp = L0 + 1.15 * f, pa = smooth(tp, tp + 0.2, t) * ex; const xy = proj(tg);
    if (pa > 0 && xy) { c.save(); c.globalAlpha = pa; const ph = ((t - tp) % 1.1 + 1.1) % 1.1;
      c.strokeStyle = '#EA6A12'; c.lineWidth = 3; c.globalAlpha = pa * Math.max(0, 1 - ph / 1.1); c.beginPath(); c.arc(xy[0], xy[1], 16 + ph * 40, 0, 2 * Math.PI); c.stroke();
      c.globalAlpha = pa; c.fillStyle = '#FFFFFF'; c.beginPath(); c.arc(xy[0], xy[1], 17, 0, 2 * Math.PI); c.fill(); c.fillStyle = '#EA6A12'; c.beginPath(); c.arc(xy[0], xy[1], 11, 0, 2 * Math.PI); c.fill(); c.restore();
      if (s.pin) { c.save(); c.font = `700 36px ${FONT}`; const w = c.measureText(s.pin).width + 40; const k = EOB(clamp((t - tp - 0.08) / 0.35));
        c.translate(xy[0] + 36, xy[1] - 34); c.scale(k, k); c.globalAlpha = pa; c.fillStyle = 'rgba(11,27,51,.18)'; rr(c, 0, 6, w, 60, 18); c.fill(); c.fillStyle = '#FFFFFF'; rr(c, 0, 0, w, 60, 18); c.fill();
        c.fillStyle = '#0B1B33'; c.textBaseline = 'middle'; c.fillText(s.pin, 20, 31); c.restore(); } }
  }
  // 記録カード（人のアイコン＋行）
  function recCard(c, x, y, rot, sc, a, white) {
    if (a <= 0) return; c.save(); c.translate(x, y); c.rotate(rot); c.scale(sc, sc); c.globalAlpha = clamp(a);
    c.fillStyle = 'rgba(0,0,0,.22)'; rr(c, -84, -24, 168, 56, 14); c.fill();
    c.fillStyle = '#FFFFFF'; rr(c, -84, -30, 168, 56, 14); c.fill(); if (!white) { c.strokeStyle = '#DCE3EE'; c.lineWidth = 2; c.stroke(); }
    c.strokeStyle = '#1F5BFF'; c.lineWidth = 3.5; c.lineCap = 'round'; c.beginPath(); c.arc(-56, -9, 7, 0, 2 * Math.PI); c.stroke(); c.beginPath(); c.moveTo(-70, 13); c.quadraticCurveTo(-56, -1, -42, 13); c.stroke();
    c.fillStyle = '#D5DDE9'; rr(c, -26, -14, 86, 11, 5.5); c.fill(); rr(c, -26, 4, 56, 11, 5.5); c.fill(); c.restore();
  }
  function arrowLine(c, pts, prog, col, w) {
    if (prog <= 0) return; const L = []; let tot = 0; for (let i = 1; i < pts.length; i++) { const d = Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]); L.push(d); tot += d; }
    let rem = tot * prog; c.save(); c.strokeStyle = col; c.lineWidth = w; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); let end = pts[0], ang = 0;
    for (let i = 1; i < pts.length && rem > 0; i++) { const f = Math.min(1, rem / L[i - 1]); end = [lerp(pts[i - 1][0], pts[i][0], f), lerp(pts[i - 1][1], pts[i][1], f)]; ang = Math.atan2(pts[i][1] - pts[i - 1][1], pts[i][0] - pts[i - 1][0]); c.lineTo(end[0], end[1]); rem -= L[i - 1]; }
    c.stroke(); c.translate(end[0], end[1]); c.rotate(ang); c.fillStyle = col; c.beginPath(); c.moveTo(w * 2.6, 0); c.lineTo(-w * 1.2, -w * 2); c.lineTo(-w * 1.2, w * 2); c.closePath(); c.fill(); c.restore();
  }
  // ---------------------------------------------------------------- 地点ごとの表現（主役の後ろ／前）
  function visualsBack(c, t, H) {
    for (const s of S) {
      if (t < s.land - 0.05 || (s.next != null && t > s.next + 1.4)) continue;
      const P = s.pal;
      if (s.visual === 'ripple' && t > s.land + 0.15) {
        const c0 = H.k === s.i && H.pos ? H.pos : [s.x, s.y], end = s.next != null ? s.next - 0.3 : 1e9;
        for (let j = 0; j < 4; j++) { const ph = ((t - s.land - 0.15) / 1.2 + j / 4) % 1; if (t > end && ph < 0.3) continue;
          const a = (1 - ph) * smooth(0, 0.1, ph) * (P.dark ? 0.5 : 0.35); c.save(); c.globalAlpha = a; c.strokeStyle = P.dark ? '#FFFFFF' : '#1F5BFF'; c.lineWidth = 4 * (1 - ph) + 1.5;
          c.beginPath(); c.arc(c0[0], c0[1], 120 + 165 * EO(ph), 0, 2 * Math.PI); c.stroke(); c.restore(); }
      }
      if (s.visual === 'spark') {
        const u = sparkU(s, t); if (u <= 0) continue;
        c.save(); c.strokeStyle = rgba(P.ink === '#FFFFFF' ? '#FFFFFF' : '#0B1B33', 0.10); c.lineWidth = 2; c.setLineDash([10, 12]);
        for (const gy of [230, 115, 0]) { c.beginPath(); c.moveTo(s.x - 417, s.y + gy); c.lineTo(s.x + 417, s.y + gy); c.stroke(); } c.restore();
        const pts = []; for (let j = 0; j <= 60; j++) pts.push(cub(s, u * j / 60));
        c.save(); const gr = c.createLinearGradient(0, s.y - 30, 0, s.y + 240); gr.addColorStop(0, rgba(P.acc, 0.22)); gr.addColorStop(1, rgba(P.acc, 0));
        c.beginPath(); c.moveTo(pts[0][0], s.y + 242); pts.forEach(p => c.lineTo(p[0], p[1])); c.lineTo(pts[pts.length - 1][0], s.y + 242); c.closePath(); c.fillStyle = gr; c.fill();
        c.beginPath(); pts.forEach((p, j) => j ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1])); c.strokeStyle = P.acc; c.lineWidth = 11; c.lineCap = 'round'; c.lineJoin = 'round'; c.stroke(); c.restore();
      }
      if (s.visual === 'cards' && H.k === s.i && H.st) {
        const hp = H.pos;
        [[-26, '#C9D8FF'], [-13, '#E1E9FF'], [13, '#E1E9FF'], [26, '#C9D8FF']].forEach(([ang, col], j) => {
          const g = EOB(clamp((t - (s.land + 0.2 + j * 0.05)) / 0.5)) * (s.next != null ? 1 - EIO(clamp((t - (s.next - 0.5)) / 0.25)) : 1); if (g <= 0) return;
          c.save(); c.translate(hp[0], hp[1] + 170); c.rotate(ang * deg * g); c.translate(0, -170); c.fillStyle = P.dark ? 'rgba(255,255,255,.22)' : col; rr(c, -135, -86, 270, 172, 20); c.fill();
          c.strokeStyle = P.dark ? 'rgba(255,255,255,.3)' : '#FFFFFF'; c.lineWidth = 3; c.stroke(); c.restore(); });
      }
    }
  }
  function visualsFront(c, t, H) {
    for (const s of S) {
      if (t < s.land - 0.05 || (s.next != null && t > s.next + 1.4)) continue;
      const P = s.pal;
      if (s.visual === 'spark' && s.number != null) {
        const a = clamp((t - (s.land + 0.1)) / 0.35);
        drawNumber(c, s.x - 417, s.y - 170, { pre: s.prefix, val: countV(s, t, s.land + 0.12, 0.95), target: s.number, unit: s.unit, dec: s.decimals, sz: 150, colPre: P.ink, colNum: P.num, align: 'left' }, a);
      }
      if (s.visual === 'bars') {
        const g = H.k === s.i && H.st ? H.st.extra.bars || 0 : 0;
        (s.bar_labels || []).forEach((lab, j) => { const a = clamp((t - (s.land + 0.45 + j * 0.1)) / 0.3) * (s.next != null ? 1 - clamp((t - (s.next - 0.7)) / 0.2) : 1) * (g > 0.5 ? 1 : 0); if (a <= 0) return;
          c.save(); c.globalAlpha = a; c.font = `700 25px ${FONT}`; c.fillStyle = P.sub; c.textAlign = 'center'; c.textBaseline = 'alphabetic';
          lab.split(' ').forEach((ln, li) => c.fillText(ln, s.x + (j - 1) * 85 * BARSC, s.y + 262 + li * 34 + 12 * (1 - a))); c.restore(); });
        const pr = clamp((t - (s.land + 0.75)) / 0.55) * (s.next != null ? 1 - clamp((t - (s.next - 0.7)) / 0.2) : 1);
        if (pr > 0 && g > 0.9) arrowLine(c, [[s.x - 170, s.y - 30], [s.x, s.y - 125], [s.x + 170, s.y - 235], [s.x + 290, s.y - 262]].map(p => p), EO(pr), P.acc, 9);
      }
      if (s.visual === 'records') {
        const t0 = (s.ic2 ? s.t2 : s.land) + 0.22, src = [s.x, s.y - 60];
        for (let j = 0; j < 10; j++) {
          const col = j % 2 ? 1 : -1, row = j >> 1, tgt = [s.x + col * 333, s.y - 205 + row * 103];
          const τ = t - (t0 + j * 0.07), u = clamp(τ / 0.5); if (u <= 0) continue;
          const e = EO(u), ctrl = [(src[0] + tgt[0]) / 2, Math.min(src[1], tgt[1]) - 150];
          const p = qb(src, ctrl, tgt, e), land = impactS(τ - 0.5);
          recCard(c, p[0], p[1], col * (1 - e) * 0.6 + col * 0.05 * rnd(j), (0.35 + 0.65 * e) * (1 + land), u * 3, P.dark);
        }
        if (s.number != null) { const tn = t0 + 0.85, a = clamp((t - tn) / 0.3);
          pill(c, s.x, s.y + 236, (s.prefix || '') + ' ' + fmt(countV(s, t, tn, 0.7), 0) + (s.unit || ''), 44, '#E8433A', '#FFFFFF', a, EOB(a)); }
      }
      if (s.visual === 'cards' && s.number != null) {
        const a = clamp((t - (s.land + 0.25)) / 0.35);
        drawNumber(c, s.x - 417, s.y + 262, { pre: s.prefix, val: countV(s, t, s.land + 0.3, 0.95), target: s.number, unit: s.unit, dec: s.decimals, sz: 150, colPre: P.ink, colNum: P.num, align: 'left' }, a);
      }
    }
  }
  // ロゴ：主役の点から文字が一つずつ飛び出し、円 → 字形に変わって基線に着地する
  const LT = { step: 0.075, travel: 0.42 };
  function drawLogo(c, t, s, H) {
    if (!WM) return; const t0 = s.land + 0.42;
    const col = s.pal.fg, news = '#7FA2FF';
    WM.letters.forEach((l, j) => {
      const τ = t - (t0 + j * LT.step); if (τ <= 0) return;
      const u = clamp(τ / LT.travel), e = EIO(u), src = WM.dot, ctrl = [(src[0] + l.cen[0]) / 2, WM.yB - WM.FS * 1.45];
      const cen = qb(src, ctrl, l.cen, e), fill = l.news ? news : col;
      if (u < 1) {
        const R = lerp(l.R * 0.22, l.R, EO(clamp(τ / 0.22))), m = EM(clamp((τ - 0.12) / 0.3));
        const C = alignTo('L' + j, l.outer.map(p => [p[0] - l.cen[0], p[1] - l.cen[1]]), circ(0, 0, R, 200));
        const body = lerpP(C, l.outer.map(p => [p[0] - l.cen[0], p[1] - l.cen[1]]), m).map(p => [p[0] + cen[0], p[1] + cen[1]]);
        const path = new Path2D(); poly(path, body);
        l.holes.forEach(hh => { const hc = centroid(hh); poly(path, hh.map(p => [cen[0] + (hc[0] - l.cen[0]) + (p[0] - hc[0]) * clamp((m - 0.4) / 0.6), cen[1] + (hc[1] - l.cen[1]) + (p[1] - hc[1]) * clamp((m - 0.4) / 0.6)])); });
        c.fillStyle = fill; c.fill(path, 'evenodd');
      } else {
        const land = impactS(τ - LT.travel);
        c.save(); c.translate(l.cen[0], WM.yB); c.scale(1 + land, 1 - land); c.translate(-l.cen[0], -WM.yB);
        const path = new Path2D(); poly(path, l.outer); l.holes.forEach(hh => poly(path, hh)); c.fillStyle = fill; c.fill(path, 'evenodd'); c.restore();
      }
    });
  }
  // ---------------------------------------------------------------- 遠景（ゆっくり流れる図形）
  const FAR = Array.from({ length: 46 }, (_, k) => ({ x: -1600 + 9000 * rnd(k * 3 + 1), y: -1500 + 3000 * rnd(k * 5 + 2), sz: 8 + 30 * rnd(k * 7 + 3) ** 2, kind: k % 4, rot: rnd(k) * 6 }));
  function drawFar(c, K, t, P) {
    c.save(); const z = K.z, cc = K.cc;
    for (const f of FAR) {
      const x = CX + (f.x - cc[0] * 0.35) * z * 0.9, y = CY + (f.y - cc[1] * 0.35) * z * 0.9;
      if (x < -80 || x > W + 80 || y < 200 || y > 1150) continue;
      const fa = smooth(250, 420, y) * (1 - smooth(940, 1100, y)); if (fa <= 0) continue;
      c.globalAlpha = P.far * fa; c.fillStyle = c.strokeStyle = P.ink; const s = f.sz * z;
      c.save(); c.translate(x, y); c.rotate(f.rot + t * 0.2);
      if (f.kind === 0) { c.beginPath(); c.arc(0, 0, s / 2, 0, 2 * Math.PI); c.fill(); }
      else if (f.kind === 1) { c.lineWidth = 3; c.beginPath(); c.arc(0, 0, s / 2 + 3, 0, 2 * Math.PI); c.stroke(); }
      else if (f.kind === 2) { c.lineWidth = 4; c.lineCap = 'round'; c.beginPath(); c.moveTo(-s / 2, 0); c.lineTo(s / 2, 0); c.moveTo(0, -s / 2); c.lineTo(0, s / 2); c.stroke(); }
      else { rr(c, -s * 0.8, -s * 0.3, s * 1.6, s * 0.6, s * 0.3); c.fill(); }
      c.restore();
    }
    c.restore();
  }
  // ---------------------------------------------------------------- 1つの配色で世界を描く
  function drawWorld(c, t, P, K, H) {
    drawFar(c, K, t, P);
    c.save(); c.setTransform(K.a, K.b, K.c, K.d, K.e, K.f);
    visualsBack(c, t, H);
    // 点線の軌跡：発射から伸び、着地後は後ろから縮んで消える
    for (let k = 1; k < N; k++) {
      const s = S[k]; if (t < s.L || t > s.land + 0.36) continue; const Pk = FP(k);
      const ue = t < s.land ? flightU(t, s.L, s.land) : 1, us = t < s.land ? 0 : EIO(clamp((t - s.land) / 0.34));
      const gap = 150 / Math.hypot(Pk.B[0] - Pk.A[0], Pk.B[1] - Pk.A[1] + 1);
      const e2 = ue - gap * (t < s.land ? 1 : 1 - EIO(clamp((t - s.land) / 0.3))); if (e2 <= us + 0.01) continue;
      c.save(); c.setTransform(1, 0, 0, 1, 0, 0); c.beginPath(); c.rect(0, 310, W, 1200); c.clip(); c.setTransform(K.a, K.b, K.c, K.d, K.e, K.f);
      c.strokeStyle = P.ink; c.globalAlpha = P.dark ? 0.75 : 0.6; c.lineWidth = 6 / K.z; c.setLineDash([22, 16]); c.lineDashOffset = -t * 120; c.lineCap = 'round';
      c.beginPath(); for (let j = 0; j <= 80; j++) { const p = qb(Pk.A, Pk.C, Pk.B, lerp(us, e2, j / 80)); j ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]); } c.stroke(); c.restore();
    }
    // 着地の波紋と接地の影
    const sCur = S[H.k];
    for (const s of S) { const τ = t - s.land; if (τ < -0.02 || τ > 0.9) continue; const hb = s === sCur && H.st ? applyM(H.M)(s.ic.piv) : [s.landAt[0], s.landAt[1] + s.ic.piv[1] * s.landSc];
      c.save(); c.strokeStyle = P.ink;
      for (let j = 0; j < 2; j++) { const tt = τ - j * 0.12; if (tt < 0 || tt > 0.8) continue; const e = EO(tt / 0.8);
        c.globalAlpha = (P.dark ? 0.55 : 0.4) * (1 - tt / 0.8); c.lineWidth = (5 * (1 - e) + 1.5) / K.z; const rw = (30 + 330 * e) * (0.4 + 0.6 * s.landSc); c.beginPath(); c.ellipse(s.landAt[0], hb[1], rw, rw * 0.28, 0, 0, 2 * Math.PI); c.stroke(); }
      c.restore(); }
    if (H.st && sCur.visual !== 'logo' && sCur.visual !== 'globe') { const hb = applyM(H.M)(sCur.ic.piv), wv = I.globe.r * 0.6 * H.sc;
      const sa = smooth(sCur.land - 0.1, sCur.land + 0.05, t) * (sCur.visual === 'spark' ? 1 - smooth(sCur.land + 0.1, sCur.land + 0.3, t) : 1);
      if (sa > 0) { c.save(); c.globalAlpha = sa; c.fillStyle = P.shadow; c.beginPath(); c.ellipse(H.pos[0], hb[1] + 10, wv, wv * 0.16, 0, 0, 2 * Math.PI); c.fill(); c.restore(); } }
    // 着地で飛び散る粒
    for (const s of S) { const τ = t - s.land; if (τ < 0 || τ > 1.2 || s.visual === 'logo') continue;
      for (let j = 0; j < 12; j++) { const a = -Math.PI * (0.05 + 0.9 * rnd(s.i * 13 + j)), r = 170 + 170 * rnd(s.i * 7 + j * 3), e = EO(clamp(τ / 0.75));
        const x = s.landAt[0] + Math.cos(a) * r * e, y = s.landAt[1] + s.ic.piv[1] * s.landSc * 0.6 + Math.sin(a) * r * 0.75 * e, sz = (7 + 10 * rnd(j + s.i)) * (1 - 0.4 * e);
        c.save(); c.globalAlpha = (1 - smooth(0.45, 1.2, τ)) * clamp(τ / 0.05); c.fillStyle = c.strokeStyle = j % 3 ? P.fg : P.acc; c.translate(x, y); c.rotate(a + e * 3);
        if (j % 4 === 0) { c.lineWidth = 3; c.beginPath(); c.arc(0, 0, sz * 0.7, 0, 2 * Math.PI); c.stroke(); } else if (j % 4 === 1) { rr(c, -sz, -sz * 0.35, sz * 2, sz * 0.7, sz * 0.35); c.fill(); } else { c.beginPath(); c.arc(0, 0, sz * 0.5, 0, 2 * Math.PI); c.fill(); }
        c.restore(); } }
    // 主役
    const heroFill = sCur.visual === 'spark' && H.st ? mixC(P.fg, P.acc, smooth(sCur.land + 0.05, sCur.land + 0.3, t)) : P.fg;
    if (!(sCur.visual === 'logo' && H.st && H.st.extra.logo > 0)) drawShape(c, H.parts, H.M, heroFill);
    if (sCur.visual === 'globe') drawGlobe(c, sCur, H, t);
    if (sCur.visual === 'logo' && H.st && H.st.extra.logo > 0) {   // 主役の点はロゴの i の点になる
      let b = 0; WM.letters.forEach((l, j) => { const τ = t - (sCur.land + 0.42 + j * LT.step + LT.travel); if (τ > 0 && τ < 0.12) b += 0.22 * Math.sin(Math.PI * τ / 0.12); });
      c.fillStyle = '#FFFFFF';
      if (H.st.extra.logo >= 1 && WM.dotPath) { c.save(); c.translate(WM.dot[0], WM.dot[1]); c.scale(1 + b, 1 + b); c.translate(-WM.dot[0], -WM.dot[1]); c.fill(WM.dotPath); c.restore(); }
      else { const r = 80 * H.sc * (1 + b); c.beginPath(); c.arc(H.pos[0], H.pos[1], r, 0, 2 * Math.PI); c.fill(); }
      drawLogo(c, t, sCur, H);
    }
    visualsFront(c, t, H);
    c.restore();
  }
  // ---------------------------------------------------------------- 1コマ
  function drawFrame(c, t, tf = t) {
    const K = camAt(t), H = heroAt(t);
    let start = 0; for (let i = N - 1; i >= 0; i--) if (fieldReg(i, tf) === 'full') { start = i; break; }
    c.setTransform(1, 0, 0, 1, 0, 0); c.globalAlpha = 1;
    for (let i = start; i < N; i++) {
      const r = fieldReg(i, tf); if (!r) continue; const P = S[i].pal;
      if (r === 'full') { c.fillStyle = P.bg; c.fillRect(0, 0, W, H_); drawWorld(c, t, P, K, H); continue; }
      octx.setTransform(1, 0, 0, 1, 0, 0); octx.globalCompositeOperation = 'source-over'; octx.globalAlpha = 1; octx.clearRect(0, 0, W, H_);
      octx.fillStyle = P.bg; octx.fillRect(0, 0, W, H_); drawWorld(octx, t, P, K, H);
      octx.setTransform(1, 0, 0, 1, 0, 0); octx.globalCompositeOperation = 'destination-in';
      const g = octx.createRadialGradient(r.o[0], r.o[1], Math.max(0, r.r - r.fw / 2), r.o[0], r.o[1], r.r + r.fw / 2 + 1); g.addColorStop(0, '#000'); g.addColorStop(1, 'rgba(0,0,0,0)');
      octx.fillStyle = g; octx.fillRect(0, 0, W, H_); octx.globalCompositeOperation = 'source-over';
      c.setTransform(1, 0, 0, 1, 0, 0); c.drawImage(offC, 0, 0);
    }
    return { K, H };
  }
  const H_ = H;
  // 移動中・着地直後だけ、シャッター内の数時点を重ねてブラーにする
  const mbAt = t => S.some(s => s.L != null && t > s.L - 0.08 && t < s.land + 0.06);
  let last = null;
  function render(t) {
    if (!mbAt(t)) { last = drawFrame(main, t); }
    else { const k1 = camAt(t - 0.004), k2 = camAt(t + 0.004), v = Math.hypot(k2.e - k1.e, k2.f - k1.f) / 0.008 * FR;
      const n = Math.max(4, Math.min(10, Math.ceil(v * 0.55 / 7))), sh = 0.55 * FR; main.setTransform(1, 0, 0, 1, 0, 0);
      for (let j = 0; j < n; j++) { const tj = t - sh / 2 + sh * j / (n - 1); bctx.setTransform(1, 0, 0, 1, 0, 0); bctx.globalAlpha = 1; last = drawFrame(bctx, tj, t);
        main.globalAlpha = 1 / (j + 1); main.drawImage(bufC, 0, 0); } main.globalAlpha = 1; }
    // ヘッダーの文字色：画面上端を覆っている背景色に合わせる
    let top = S[0].pal; for (let i = 1; i < N; i++) { const r = fieldReg(i, t); if (r === 'full' || (r && Math.hypot(r.o[0] - 540, r.o[1] - 150) < r.r - 40)) top = S[i].pal; }
    const R = document.documentElement.style, dk = top.dark;
    R.setProperty('--hfg', dk ? '#fff' : '#0B1B33'); R.setProperty('--hnews', dk ? (top.bg === '#1F5BFF' ? '#0B1B33' : '#7FA2FF') : '#1F5BFF');
    R.setProperty('--hsub', dk ? 'rgba(255,255,255,.72)' : '#5B6B82'); R.setProperty('--hline', dk ? 'rgba(255,255,255,.28)' : '#DCE3EE');
  }
  return render;
};
