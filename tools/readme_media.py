#!/usr/bin/env python3
"""Make the figures of the READMEs (docs/media/) and check them against the manuscript's data.

Usage:
  python3 -I tools/readme_media.py --check   compare the SVG figures in docs/media/ with what this script makes from
                                             paper/figdata/ (standard library only); exit 1 if any differs
  python3 tools/readme_media.py --write      write the SVG figures and the GIFs, in English and Japanese (*_ja); the
                                             GIFs need Pillow (tools/requirements-media.txt)

No figure uses a real writer's data. results*.svg plot the aggregate values of Figure 3 of the manuscript
(paper/figdata/fig2_p15_*.csv: medians over the 17 writers of the 15-session CoAuthor panel). symbols*.gif run the
kit's symbolizer on a made-up key-press sequence (seed 20261120); they illustrate the coding and are not results.
"""
import csv
import math
import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEDIA = os.path.join(ROOT, "docs", "media")
FIGDATA = os.path.join(ROOT, "paper", "figdata")
FONT = "Inter, -apple-system, 'Segoe UI', 'Hiragino Sans', 'Noto Sans JP', 'Yu Gothic', Helvetica, Arial, sans-serif"
INK, MUTED, GRID, CARD = "#1f2937", "#6b7280", "#e5e7eb", "#ffffff"
COLORS = {"hmm3": "#e11d48", "ar1": "#0d9488", "ar3": "#4f46e5", "joint": "#d97706"}
MODELS = ("hmm3", "ar1", "ar3", "joint")
TX = {
    "en": {
        "labels": {"hmm3": "3-state HMM (τ chosen)", "ar1": "1-state AR-HMM (τ chosen)",
                   "ar3": "3-state AR-HMM (τ chosen)", "joint": "joint choice of structure and τ"},
        "label_w": 6.2,
        "r_title": "What remains of the per-person gain",
        "r_sub": "CoAuthor, 15-session panel (17 writers), median over writers, nats per held-out symbol "
                 "(Figure 3 of the paper)",
        "r_panels": ("(a) Per-person minus the same-structure shared model", "(b) Per-person minus the writer's own chain"),
        "r_x": "k (number of training units)",
        "p_title": "From key presses to the comparison of three models",
        "p_boxes": (("Public keystrokes", ("CoAuthor (co-writing)", "CS1 2021 (programming)", "time and key category")),
                    ("kit/symbols", ("one symbol per second", "from the last 30 s", "26 symbols")),
                    ("Earlier sessions", ("fit three models", "for each writer", "(k = 1 to 30)")),
                    ("Later sessions", ("score each model by the", "log-probability of the next", "symbol (nats per symbol)"))),
        "p_models": (("Per-person model", "pulled toward the shared one"),
                     ("Shared model", "same structure, other writers"),
                     ("Writer's own Markov chain", "next symbol from the current one")),
        "p_chosen": ("Chosen on other writers:", "the structure (HMMs with 3 or 10 states, AR-HMMs with 1 to 3 states) "
                     "and the shrinkage τ, never on the held-out units"),
        "p_checked": ("Checked afterwards:", "synthetic writers with planted differences, two nulls, other "
                      "symbolizations, smoothing of both models"),
        "g_title": "One symbol per second from the key presses of the last 30 s",
        "g_sub": "made-up key presses (no real writer); kit/symbols/symbolizer.py",
        "g_window": "30 s window",
        "g_legend": ("letter", "space", "deletion"),
        "g_grid": "symbol = cell of (x, y)",
        "g_xy": "x, y: two smoothed composites",
        "g_25": "25: first typing after a deletion run",
        "g_seq": "symbol sequence (what the models predict)",
        "g_foot": ("Each model gives a probability to the next symbol; a model is scored by the mean log-probability",
                   "of a writer's later symbols. t = %d s"),
    },
    "ja": {
        "labels": {"hmm3": "3 状態 HMM（τ を選ぶ）", "ar1": "1 状態 AR-HMM（τ を選ぶ）",
                   "ar3": "3 状態 AR-HMM（τ を選ぶ）", "joint": "構造と τ を同時に選ぶ"},
        "label_w": 11.5,
        "r_title": "本人のモデルの利得は、強い相手と比べると何が残るか",
        "r_sub": "CoAuthor の 15 セッションのパネル（17 人）・書き手の中央値・取り置いた記号 1 つあたりの nats（原稿の図 3）",
        "r_panels": ("(a) 本人 − 同じ構造の共通のモデル", "(b) 本人 − 書き手自身の連鎖"),
        "r_x": "k（学習の単位の数）",
        "p_title": "打鍵から 3 つのモデルの比べまで",
        "p_boxes": (("公開の打鍵データ", ("CoAuthor（共同執筆）", "CS1 2021（プログラミング）", "時刻とキーの種類だけ")),
                    ("kit/symbols", ("1 秒ごとに 1 記号", "直前の 30 秒から", "26 種類の記号")),
                    ("前のセッション", ("書き手ごとに", "3 つのモデルを当てはめる", "（k = 1〜30）")),
                    ("後のセッション", ("次の記号の対数確率で", "各モデルを採点する", "（1 記号あたり nats）"))),
        "p_models": (("本人のモデル", "共通のモデルに寄せて当てはめる"),
                     ("共通のモデル", "同じ構造・他の書き手で当てはめる"),
                     ("書き手自身のマルコフ連鎖", "今の記号から次の記号を予測する")),
        "p_chosen": ("他の書き手で選ぶ:", "構造（3・10 状態の HMM、1〜3 状態の AR-HMM）と縮約 τ。"
                     "採点する書き手の取り置いた単位では選ばない"),
        "p_checked": ("後の確かめ:", "違いを植えた合成の書き手・2 つの帰無・別の記号化・両方のモデルの平滑"),
        "g_title": "直前の 30 秒の打鍵から、1 秒ごとに 1 つの記号",
        "g_sub": "作った打鍵（実在の書き手ではない）・kit/symbols/symbolizer.py",
        "g_window": "30 秒の窓",
        "g_legend": ("文字", "空白", "削除"),
        "g_grid": "記号 = (x, y) のあるマス",
        "g_xy": "x, y: 平滑した 2 つの合成値",
        "g_25": "25: 削除の連打の後の最初の入力",
        "g_seq": "記号の列（モデルが予測するもの）",
        "g_foot": ("各モデルは次の記号に確率を与え、書き手の後の記号の",
                   "対数確率の平均で採点される。t = %d 秒"),
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def read_fig2():
    out = {}
    for m in MODELS:
        with open(os.path.join(FIGDATA, "fig2_p15_%s.csv" % m), newline="") as fh:
            out[m] = [(int(r["k"]), float(r["pp_minus_shared"]), float(r["pp_minus_chain"])) for r in csv.DictReader(fh)]
    return out


def svg_open(W, H, title):
    return ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">'
            % (W, H, W, H, FONT), "<title>%s</title>" % esc(title),
            '<rect x="0.5" y="0.5" width="%d" height="%d" rx="16" fill="%s" stroke="%s"/>' % (W - 1, H - 1, CARD, GRID)]


def results_svg(lang):
    """Two panels: per-person minus shared (log scale) and per-person minus the writer's own chain (linear)."""
    t = TX[lang]
    d = read_fig2()
    W, H, top, bot = 960, 470, 92, 74
    pw, gap, left = 380, 110, 82
    ks = [1, 2, 3, 5, 8, 12, 15]
    def xpos(i, k):
        return left + i * (pw + gap) + (math.log(k) / math.log(15)) * pw
    ph = H - top - bot
    ylo, yhi = math.log10(1e-4), math.log10(0.3)
    def y1(v):
        return top + ph * (1 - (math.log10(v) - ylo) / (yhi - ylo))
    clo, chi = -0.6, 0.3
    def y2(v):
        return top + ph * (1 - (v - clo) / (chi - clo))
    s = svg_open(W, H, t["r_title"])
    s.append('<text x="%d" y="38" font-size="19" font-weight="700" fill="%s">%s</text>' % (left - 40, INK, esc(t["r_title"])))
    s.append('<text x="%d" y="62" font-size="13" fill="%s">%s</text>' % (left - 40, MUTED, esc(t["r_sub"])))
    for i in range(2):
        x0 = left + i * (pw + gap)
        s.append('<text x="%d" y="%d" font-size="13" font-weight="600" fill="%s">%s</text>'
                 % (x0, top - 12, INK, esc(t["r_panels"][i])))
        ticks = [1e-4, 1e-3, 1e-2, 1e-1] if i == 0 else [-0.6, -0.4, -0.2, 0.0, 0.2]
        for v in ticks:
            y = y1(v) if i == 0 else y2(v)
            lab = ("10<tspan dy='-6' font-size='9'>%d</tspan>" % round(math.log10(v))) if i == 0 else ("%+.1f" % v if v else "0")
            plain = i == 0 or v
            s.append('<line x1="%d" x2="%d" y1="%.1f" y2="%.1f" stroke="%s" %s/>'
                     % (x0, x0 + pw, y, y, GRID if plain else "#9ca3af", "" if plain else 'stroke-dasharray="4 3"'))
            s.append('<text x="%d" y="%.1f" font-size="11" fill="%s" text-anchor="end">%s</text>' % (x0 - 8, y + 4, MUTED, lab))
        for k in ks:
            s.append('<text x="%.1f" y="%d" font-size="11" fill="%s" text-anchor="middle">%d</text>'
                     % (xpos(i, k), H - bot + 18, MUTED, k))
        s.append('<text x="%d" y="%d" font-size="12" fill="%s" text-anchor="middle">%s</text>'
                 % (x0 + pw // 2, H - bot + 38, MUTED, esc(t["r_x"])))
        for m in MODELS:
            pts = [(xpos(i, k), y1(a) if i == 0 else y2(b)) for k, a, b in d[m]]
            dash = ' stroke-dasharray="6 4"' if m == "joint" else ""
            s.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="2.5"%s/>'
                     % (" ".join("%.1f,%.1f" % p for p in pts), COLORS[m], dash))
            for p in pts:
                s.append('<circle cx="%.1f" cy="%.1f" r="3.6" fill="%s" stroke="%s" stroke-width="1.5"/>'
                         % (p[0], p[1], CARD if m == "joint" else COLORS[m], COLORS[m]))
    lx, ly = left - 40, H - 16
    for m in MODELS:
        s.append('<rect x="%d" y="%d" width="14" height="4" rx="2" fill="%s"/>' % (lx, ly - 6, COLORS[m]))
        s.append('<text x="%d" y="%d" font-size="11.5" fill="%s">%s</text>' % (lx + 20, ly, INK, esc(t["labels"][m])))
        lx += 30 + int(t["label_w"] * len(t["labels"][m]))
    s.append("</svg>")
    return "\n".join(s) + "\n"


def box(s, x, y, w, h, title, sub, fill, stroke):
    s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="%s" stroke="%s" stroke-width="1.5"/>'
             % (x, y, w, h, fill, stroke))
    s.append('<text x="%d" y="%d" font-size="14" font-weight="700" fill="%s" text-anchor="middle">%s</text>'
             % (x + w // 2, y + 26, INK, esc(title)))
    for j, line in enumerate(sub):
        s.append('<text x="%d" y="%d" font-size="11.5" fill="%s" text-anchor="middle">%s</text>'
                 % (x + w // 2, y + 46 + 16 * j, MUTED, esc(line)))


def pipeline_svg(lang):
    t = TX[lang]
    W, H = 960, 330
    s = svg_open(W, H, t["p_title"])
    s.insert(2, '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#9ca3af"/></marker></defs>')
    geo = ((24, 170, "#f8fafc", "#cbd5e1"), (236, 190, "#eef2ff", "#a5b4fc"), (468, 190, "#f0fdfa", "#5eead4"),
           (700, 236, "#fff7ed", "#fdba74"))
    for (x, w, fill, stroke), (title, sub) in zip(geo, t["p_boxes"]):
        box(s, x, 40, w, 104, title, sub, fill, stroke)
    for a, b in ((194, 236), (426, 468), (658, 700)):
        s.append('<line x1="%d" y1="92" x2="%d" y2="92" stroke="#9ca3af" stroke-width="2" marker-end="url(#a)"/>'
                 % (a + 2, b - 4))
    for j, ((title, sub), c) in enumerate(zip(t["p_models"], (COLORS["ar3"], COLORS["ar1"], COLORS["hmm3"]))):
        x = 24 + j * 308
        s.append('<rect x="%d" y="182" width="292" height="58" rx="12" fill="%s" fill-opacity="0.08" stroke="%s"/>' % (x, c, c))
        s.append('<circle cx="%d" cy="211" r="7" fill="%s"/>' % (x + 22, c))
        s.append('<text x="%d" y="206" font-size="13.5" font-weight="700" fill="%s">%s</text>' % (x + 40, INK, esc(title)))
        s.append('<text x="%d" y="225" font-size="11.5" fill="%s">%s</text>' % (x + 40, MUTED, esc(sub)))
    for y, (head, body) in ((276, t["p_chosen"]), (300, t["p_checked"])):
        s.append('<text x="24" y="%d" font-size="12.5" fill="%s"><tspan font-weight="700">%s</tspan> %s</text>'
                 % (y, INK, esc(head), esc(body)))
    s.append("</svg>")
    return "\n".join(s) + "\n"


def logo_svg():
    """A row of symbol tiles over a line: one symbol per second, then a model of the sequence."""
    W, H = 700, 120
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="%s">'
         % (W, H, W, H, FONT), '<title>per-person-keystroke-models</title>',
         '<defs><linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="#4f46e5"/>'
         '<stop offset="0.55" stop-color="#0d9488"/><stop offset="1" stop-color="#d97706"/></linearGradient></defs>',
         '<rect x="0.5" y="0.5" width="%d" height="%d" rx="18" fill="%s" stroke="%s"/>' % (W - 1, H - 1, CARD, GRID)]
    rng = random.Random(7)
    for i in range(9):
        h = 14 + rng.randint(0, 26)
        s.append('<rect x="%d" y="%d" width="10" height="%d" rx="3" fill="url(#g)" opacity="%.2f"/>'
                 % (24 + i * 13, 74 - h, h, 0.45 + 0.06 * i))
    s.append('<path d="M24,92 C50,80 74,100 100,86 C114,79 130,70 144,78" fill="none" stroke="url(#g)" '
             'stroke-width="3.5" stroke-linecap="round"/>')
    s.append('<text x="170" y="60" font-size="30" letter-spacing="-0.5"><tspan font-weight="800" fill="#4f46e5">'
             'per-person</tspan><tspan font-weight="400" fill="#475569"> keystroke models</tspan></text>')
    s.append('<text x="172" y="90" font-size="14" fill="#64748b">How much does fitting a model to one writer add?</text>')
    s.append("</svg>")
    return "\n".join(s) + "\n"


def synthetic_presses(seed=20261120):
    """A made-up session: typing, a run of deletions, a short pause, fast typing, a long pause, typing."""
    rng = random.Random(seed)
    t, out = 1000, []
    def typing(n, lo, hi):
        nonlocal t
        for _ in range(n):
            t += rng.randint(lo, hi)
            out.append((t, "space" if rng.random() < 0.17 else "alphabetic"))
    typing(90, 120, 320)
    for _ in range(16):
        t += rng.randint(90, 160)
        out.append((t, "backspace"))
    typing(40, 140, 360)
    t += 9000
    typing(110, 80, 200)
    t += 26000
    typing(60, 150, 420)
    return 0, out


def symbols_gif(path, lang):
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415  (only for --write)
    sys.path.insert(0, os.path.join(ROOT, "kit", "symbols"))
    from symbolizer import symbolize  # noqa: PLC0415
    t = TX[lang]
    t0, presses = synthetic_presses()
    rows = symbolize(t0, presses)
    def font(sz, bold=False):
        names = (["/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc" if bold else "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"]
                 if lang == "ja" else []) + ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc",
                                             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
        for name in names:
            if os.path.exists(name):
                idx = 1 if bold and "Helvetica" in name else 0
                return ImageFont.truetype(name, sz, index=idx)
        return ImageFont.load_default()
    W, H, S = 960, 420, 2  # drawn at twice the size, then reduced
    tl_x0, tl_x1, tl_y = 40, 600, 120
    span = 60000
    grid_x, grid_y, cell = 680, 70, 46
    frames = []
    for fi in range(30, len(rows), 2):
        tnow = rows[fi][0]
        im = Image.new("RGB", (W * S, H * S), "white")
        dr = ImageDraw.Draw(im)
        def sc(v):
            return [int(round(a * S)) for a in v]
        dr.rounded_rectangle(sc((1, 1, W - 2, H - 2)), radius=16 * S, outline="#e5e7eb", width=2 * S)
        dr.text(sc((40, 22)), t["g_title"], fill=INK, font=font(19 * S, True))
        dr.text(sc((40, 50)), t["g_sub"], fill=MUTED, font=font(13 * S))
        lo = tnow - span
        def tx(v):
            return tl_x0 + (v - lo) / span * (tl_x1 - tl_x0)
        dr.rounded_rectangle(sc((tx(tnow - 30000), tl_y - 34, tx(tnow), tl_y + 34)), radius=8 * S, fill="#eef2ff")
        dr.text(sc((tx(tnow - 30000) + 6, tl_y - 54)), t["g_window"], fill="#4f46e5", font=font(13 * S))
        dr.line(sc((tl_x0, tl_y, tl_x1, tl_y)), fill="#cbd5e1", width=2 * S)
        for v, cat in presses:
            if lo <= v <= tnow:
                c = {"backspace": "#e11d48", "space": "#94a3b8"}.get(cat, "#0d9488")
                dr.line(sc((tx(v), tl_y - 20, tx(v), tl_y + 20)), fill=c, width=2 * S)
        dr.line(sc((tx(tnow), tl_y - 40, tx(tnow), tl_y + 40)), fill=INK, width=2 * S)
        for lab, c, xx in zip(t["g_legend"], ("#0d9488", "#94a3b8", "#e11d48"), (40, 120, 200)):
            dr.rectangle(sc((xx, 176, xx + 12, 188)), fill=c)
            dr.text(sc((xx + 18, 173)), lab, fill=MUTED, font=font(13 * S))
        dr.text(sc((grid_x, grid_y - 32)), t["g_grid"], fill=INK, font=font(15 * S, True))
        sym = rows[fi][3]
        for gx in range(5):
            for gy in range(5):
                k = gx * 5 + gy
                X, Y = grid_x + gx * cell, grid_y + (4 - gy) * cell
                on = k == sym
                dr.rounded_rectangle(sc((X + 2, Y + 2, X + cell - 2, Y + cell - 2)), radius=6 * S,
                                     fill="#4f46e5" if on else "#f1f5f9")
                dr.text(sc((X + 14, Y + 14)), str(k), fill="white" if on else "#94a3b8", font=font(13 * S))
        trail = rows[max(0, fi - 20):fi + 1]
        pts = [(grid_x + min(max(r[1], 0), 1) * 5 * cell, grid_y + (1 - min(max(r[2], 0), 1)) * 5 * cell) for r in trail]
        if len(pts) > 1:
            dr.line([tuple(sc(p)) for p in pts], fill="#d97706", width=3 * S)
        px, py = pts[-1]
        dr.ellipse(sc((px - 6, py - 6, px + 6, py + 6)), fill="#d97706")
        dr.text(sc((grid_x, grid_y + 5 * cell + 8)), t["g_xy"], fill=MUTED, font=font(12 * S))
        if sym == 25:
            dr.text(sc((grid_x, grid_y + 5 * cell + 28)), t["g_25"], fill="#e11d48", font=font(12 * S, True))
        seq = [r[3] for r in rows[max(0, fi - 21):fi + 1]]
        dr.text(sc((40, 228)), t["g_seq"], fill=INK, font=font(15 * S, True))
        for j, v in enumerate(seq):
            X = 40 + j * 27
            last = j == len(seq) - 1
            dr.rounded_rectangle(sc((X, 258, X + 24, 290)), radius=5 * S, fill="#4f46e5" if last else "#e0e7ff")
            dr.text(sc((X + 4, 266)), "%d" % v, fill="white" if last else "#3730a3", font=font(12 * S))
        dr.rounded_rectangle(sc((40 + len(seq) * 27, 258, 64 + len(seq) * 27, 290)), radius=5 * S, outline="#a5b4fc",
                             width=2 * S)
        dr.text(sc((46 + len(seq) * 27, 266)), "?", fill="#4f46e5", font=font(12 * S, True))
        dr.text(sc((40, 318)), t["g_foot"][0], fill=MUTED, font=font(13 * S))
        dr.text(sc((40, 340)), t["g_foot"][1] % ((tnow - t0) // 1000), fill=MUTED, font=font(13 * S))
        frames.append(im.resize((W, H), Image.LANCZOS).convert("P", palette=Image.ADAPTIVE, colors=64))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=120, loop=0, optimize=True)
    return len(frames)


def svgs():
    out = {"logo.svg": logo_svg()}
    for lang, suf in (("en", ""), ("ja", "_ja")):
        out["results%s.svg" % suf] = results_svg(lang)
        out["pipeline%s.svg" % suf] = pipeline_svg(lang)
    return out


def main(argv):
    made = svgs()
    if argv == ["--check"]:
        bad = []
        for name, text in made.items():
            p = os.path.join(MEDIA, name)
            if not os.path.exists(p) or open(p, encoding="utf-8").read() != text:
                bad.append(name)
        n = sum(len(v) for v in read_fig2().values())
        if n == 0:
            bad.append("paper/figdata (no data points)")
        print("compared %d points of paper/figdata with %d figures in docs/media; %s"
              % (n, len(made), "differs: %s" % bad if bad else "identical"))
        return 1 if bad else 0
    if argv == ["--write"]:
        os.makedirs(MEDIA, exist_ok=True)
        for name, text in made.items():
            with open(os.path.join(MEDIA, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        n = [symbols_gif(os.path.join(MEDIA, "symbols%s.gif" % suf), lang) for lang, suf in (("en", ""), ("ja", "_ja"))]
        print("wrote %s and symbols.gif, symbols_ja.gif (%d frames each)" % (", ".join(made), n[0]))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
