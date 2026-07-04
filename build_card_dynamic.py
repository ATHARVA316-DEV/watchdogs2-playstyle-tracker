"""
Build script: generates dynamic index.html for the WD2 Player Card with History.
Run: python build_card_dynamic.py
"""
import base64, os, json, sys
import stat_engine

HERE = os.path.dirname(os.path.abspath(__file__))
PORTRAIT_PATH = r"C:\Users\mpath\.gemini\antigravity-ide\brain\95865d84-5447-4f9a-add1-5a7f6c5cd088\dedsec_portrait_1783081521648.png"

# Read portrait
try:
    with open(PORTRAIT_PATH, "rb") as f:
        portrait_b64 = base64.b64encode(f.read()).decode()
    portrait_uri = "data:image/png;base64," + portrait_b64
except Exception as e:
    print(f"Warning: could not load portrait ({e})")
    portrait_uri = ""

# Compute data payloads
sessions = stat_engine.load_all_sessions(stat_engine.SESSIONS_DIR)
# Filter out fake/manual data to only use real tracked inputs
sessions = [s for s in sessions if s.get("source") in ("input_log", "ocr_capture")]

if not sessions:
    print("Warning: No sessions found. Using mock data.")
    DYNAMIC_DATA = {
        "all_time": {
            "player_name": "Operative", "overall": 75, "archetype": "Unknown",
            "stats": {"stealth": 50, "hacking": 50, "combat": 50, "driving": 50, "chaos": 50},
            "sessions_analyzed": 0, "generated_at": "2026-07-03T00:00:00Z"
        },
        "recent": None,
        "history": []
    }
else:
    all_time_card = stat_engine.generate_card_data(sessions)
    recent_sessions = sessions[-5:] if len(sessions) > 5 else sessions
    recent_card = stat_engine.generate_card_data(recent_sessions)
    
    history = []
    for i, sess in enumerate(sessions):
        cum_sessions = sessions[:i+1]
        cum_card = stat_engine.generate_card_data(cum_sessions)
        history.append({
            "label": sess.get("mission") or f"Session {i+1}",
            "stealth": cum_card["stats"]["stealth"],
            "hacking": cum_card["stats"]["hacking"],
            "combat": cum_card["stats"]["combat"],
            "driving": cum_card["stats"]["driving"],
            "chaos": cum_card["stats"]["chaos"],
        })
        
    DYNAMIC_DATA = {
        "all_time": all_time_card,
        "recent": recent_card,
        "history": history
    }

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="Watch Dogs 2 Playstyle Analyzer - Generate your DedSec player card with real stats." />
  <title>WD2 Playstyle Card | DedSec Operative</title>
  <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
  <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
  <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;500;600;700&family=Share+Tech+Mono&display=swap" rel="stylesheet" />
  <style>
    *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
      --orange: #ff6600; --cyan: #00d2ff; --dark: #070710;
      --green: #00ff88; --purple: #cc00ff;
    }
    html { scroll-behavior: smooth; }
    body {
      background: var(--dark); min-height: 100vh;
      display: flex; flex-direction: column; align-items: center;
      font-family: 'Rajdhani', sans-serif; color: #fff; overflow-x: hidden;
    }
    body::before {
      content: ''; position: fixed; inset: 0;
      background:
        radial-gradient(ellipse at 15% 60%, rgba(255,102,0,.09) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 15%, rgba(0,210,255,.06) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 100%, rgba(120,0,255,.05) 0%, transparent 50%);
      pointer-events: none; z-index: 0;
    }
    .scanlines {
      position: fixed; inset: 0; z-index: 9999; pointer-events: none;
      background: repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,.05) 2px, rgba(0,0,0,.05) 4px);
    }

    /* ── PAGE LAYOUT ─────────────────────────── */
    .page-wrapper {
      position: relative; z-index: 1; display: flex; flex-direction: column;
      align-items: center; padding: 40px 24px 72px; width: 100%;
    }
    .page-header { text-align: center; margin-bottom: 36px; }
    .page-header h1 {
      font-family: 'Orbitron', monospace; font-size: clamp(1rem, 2.8vw, 1.4rem);
      font-weight: 900; letter-spacing: .38em; text-transform: uppercase; color: var(--orange);
      text-shadow: 0 0 28px rgba(255,102,0,.7), 0 0 60px rgba(255,102,0,.3);
    }
    .page-header h1 span { color: var(--cyan); text-shadow: 0 0 24px rgba(0,210,255,.7); }
    .page-header p {
      font-family: 'Share Tech Mono', monospace; font-size: .6rem;
      letter-spacing: .22em; color: rgba(255,255,255,.25); margin-top: 8px; text-transform: uppercase;
    }

    /* ── DASHBOARD ROW ───────────────────────── */
    .dashboard-layout {
      display: flex; flex-direction: row; gap: 32px; align-items: flex-start;
      justify-content: center; width: 100%; max-width: 1040px; flex-wrap: wrap;
    }

    /* ── CARD COLUMN ─────────────────────────── */
    .card-col { display: flex; flex-direction: column; align-items: center; gap: 16px; flex-shrink: 0; }

    .wd2-card-wrapper { position: relative; perspective: 1000px; }
    .wd2-special-ring {
      position: absolute; inset: -3px; border-radius: 22px; z-index: -1;
      background: conic-gradient(from 0deg, #ff6600, #ff00aa, #00d2ff, #00ff88, #ff6600);
      animation: spin-ring 3s linear infinite; filter: blur(8px); opacity: .6;
    }
    @keyframes spin-ring { to { transform: rotate(360deg); } }

    .wd2-card {
      width: 300px; border-radius: 20px; position: relative; overflow: hidden;
      box-shadow:
        0 0 0 1px rgba(255,255,255,.07),
        0 28px 70px rgba(0,0,0,.9),
        0 0 80px rgba(255,102,0,.15);
      transition: transform .45s cubic-bezier(.2,.8,.4,1), box-shadow .45s ease;
      transform-style: preserve-3d;
    }
    .wd2-card:hover {
      transform: rotateY(-5deg) rotateX(4deg) translateY(-12px) scale(1.01);
      box-shadow:
        0 0 0 1px rgba(255,255,255,.14),
        0 40px 100px rgba(0,0,0,.95),
        0 0 140px rgba(255,102,0,.28);
    }
    .wd2-bronze  { background: linear-gradient(155deg, #1f1006 0%, #301c07 50%, #120c02 100%); }
    .wd2-silver  { background: linear-gradient(155deg, #0d0f15 0%, #1a2030 50%, #08090f 100%); }
    .wd2-gold    { background: linear-gradient(155deg, #131100 0%, #221e00 50%, #0c0a00 100%); }
    .wd2-special { background: linear-gradient(155deg, #090012 0%, #18002a 50%, #060010 100%); }
    .wd2-card::before {
      content: ''; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
    }
    .wd2-bronze::before  { background: linear-gradient(135deg, rgba(220,140,60,.3) 0%, transparent 55%, rgba(180,100,30,.2) 100%); }
    .wd2-silver::before  { background: linear-gradient(135deg, rgba(200,220,245,.22) 0%, transparent 55%, rgba(155,175,205,.16) 100%); }
    .wd2-gold::before    { background: linear-gradient(135deg, rgba(255,210,30,.28) 0%, transparent 55%, rgba(220,170,0,.18) 100%); }
    .wd2-special::before { background: linear-gradient(135deg, rgba(255,102,0,.3) 0%, transparent 42%, rgba(0,210,255,.18) 72%, rgba(180,0,255,.24) 100%); }

    .wd2-circuit {
      position: absolute; inset: 0; pointer-events: none;
      background-image:
        linear-gradient(rgba(255,102,0,.5) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,102,0,.5) 1px, transparent 1px),
        linear-gradient(rgba(255,102,0,.18) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,102,0,.18) 1px, transparent 1px);
      background-size: 72px 72px, 72px 72px, 18px 18px, 18px 18px; opacity: .05;
    }
    .wd2-special .wd2-circuit {
      opacity: .09;
      background-image:
        linear-gradient(rgba(255,102,0,.8) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,210,255,.8) 1px, transparent 1px),
        linear-gradient(rgba(255,102,0,.35) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,210,255,.35) 1px, transparent 1px);
    }

    .wd2-card-inner { position: relative; z-index: 2; padding: 18px 16px 16px; display: flex; flex-direction: column; }

    /* card top row */
    .wd2-card-top { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
    .wd2-overall-col { display: flex; flex-direction: column; align-items: center; line-height: 1; }
    .wd2-overall-num {
      font-family: 'Orbitron', monospace; font-weight: 900; font-size: 4rem; line-height: 1; letter-spacing: -.04em;
    }
    .wd2-archetype-pill {
      font-family: 'Orbitron', monospace; font-size: .4rem; font-weight: 700;
      letter-spacing: .07em; text-transform: uppercase; padding: 3px 7px; border-radius: 4px;
      margin-top: 5px; border: 1px solid; max-width: 96px; text-align: center; line-height: 1.4; word-break: break-word;
    }
    .wd2-right-col { display: flex; flex-direction: column; align-items: center; gap: 6px; }
    .wd2-dedsec-emblem {
      width: 48px; height: 48px; border-radius: 50%; border: 1.5px solid;
      display: flex; align-items: center; justify-content: center;
      font-family: 'Orbitron', monospace; font-size: .44rem; font-weight: 900;
      letter-spacing: .04em; text-align: center; line-height: 1.3;
    }
    .wd2-rarity-tag { font-family: 'Share Tech Mono', monospace; font-size: .48rem; letter-spacing: .12em; opacity: .7; text-transform: uppercase; }

    /* portrait */
    .wd2-portrait {
      width: 100%; height: 210px; border-radius: 12px; overflow: hidden;
      position: relative; border: 1px solid; margin-bottom: 12px;
    }
    .wd2-portrait img { width: 100%; height: 100%; object-fit: cover; object-position: center 10%; display: block; }
    .wd2-portrait-placeholder { width: 100%; height: 100%; background: linear-gradient(180deg, rgba(255,102,0,.08), rgba(0,0,0,.4)); }
    .wd2-portrait-shade { position: absolute; inset: 0; background: linear-gradient(to bottom, transparent 40%, rgba(0,0,0,.82) 100%); }
    .wd2-player-name {
      position: absolute; bottom: 14px; left: 0; right: 0; text-align: center;
      font-family: 'Orbitron', monospace; font-size: 1rem; font-weight: 900;
      letter-spacing: .24em; text-transform: uppercase;
      text-shadow: 0 0 8px rgba(0,0,0,1), 0 0 20px rgba(0,0,0,1); line-height: 1; margin: 0;
    }
    .wd2-glitch { position: relative; }
    .wd2-glitch::before, .wd2-glitch::after {
      content: attr(data-text); position: absolute; inset: 0;
      font-family: inherit; font-size: inherit; font-weight: inherit; letter-spacing: inherit;
    }
    .wd2-glitch::before { color: #00d2ff; animation: gc 6s infinite; }
    .wd2-glitch::after  { color: #ff4400; animation: gc 6s .12s infinite; }
    @keyframes gc {
      0%,89%,100% { clip-path: inset(0 0 100% 0); transform: translate(0); opacity: 0; }
      91% { clip-path: inset(5% 0 70% 0); transform: translate(-3px, 1px); opacity: 1; }
      93% { clip-path: inset(50% 0 20% 0); transform: translate(3px, -2px); opacity: 1; }
      95% { clip-path: inset(75% 0 5% 0); transform: translate(-2px, 3px); opacity: 1; }
      97% { clip-path: inset(25% 0 60% 0); transform: translate(2px, -1px); opacity: 1; }
    }
    .wd2-card:hover .wd2-portrait::after {
      content: ''; position: absolute; inset: 0;
      background: rgba(0,210,255,.05); animation: pfx .2s steps(2) infinite;
    }
    @keyframes pfx {
      0% { transform: translate(0); } 50% { transform: translate(-2px, 1px); opacity: .8; } 100% { transform: translate(2px, -1px); }
    }

    /* stats on card */
    .wd2-divider { height: 1px; margin: 2px 0 12px; background: linear-gradient(90deg, transparent, currentColor, transparent); opacity: .35; }
    .wd2-stats { display: flex; flex-direction: column; gap: 7px; }
    .wd2-stat-row { display: grid; grid-template-columns: 34px 1fr 28px; align-items: center; gap: 8px; }
    .wd2-stat-lbl { font-family: 'Orbitron', monospace; font-size: .5rem; font-weight: 700; letter-spacing: .06em; text-align: right; opacity: .85; }
    .wd2-track {
      height: 5px; border-radius: 3px; background: rgba(255,255,255,.05);
      overflow: visible; position: relative;
    }
    .wd2-fill { height: 100%; border-radius: 3px; position: relative; transition: width 1.4s cubic-bezier(.4,0,.2,1); }
    .wd2-fill::after {
      content: ''; position: absolute; right: -1px; top: -2px; bottom: -2px;
      width: 7px; border-radius: 50%; background: inherit; filter: brightness(2.2) blur(2px);
    }
    .wd2-stat-val { font-family: 'Orbitron', monospace; font-size: .65rem; font-weight: 700; text-align: left; }
    .wd2-card-footer {
      margin-top: 14px; padding-top: 8px; border-top: 1px solid rgba(255,255,255,.06);
      display: flex; justify-content: space-between; align-items: center;
    }
    .wd2-foot-txt { font-family: 'Share Tech Mono', monospace; font-size: .4rem; opacity: .3; letter-spacing: .1em; text-transform: uppercase; }

    /* ── THEMING ──────────────────────────────── */
    .wd2-bronze .wd2-overall-num, .wd2-bronze .wd2-stat-val, .wd2-bronze .wd2-player-name { color: #e8a050; }
    .wd2-bronze .wd2-archetype-pill { color: #e8a050; border-color: rgba(200,120,40,.5); background: rgba(160,80,20,.15); }
    .wd2-bronze .wd2-dedsec-emblem  { color: #e8a050; border-color: rgba(200,120,40,.55); }
    .wd2-bronze .wd2-portrait       { border-color: rgba(180,110,40,.4); }
    .wd2-bronze .wd2-divider        { color: #b46820; }
    .wd2-bronze .wd2-stat-lbl       { color: rgba(230,155,75,.8); }
    .wd2-bronze .wd2-fill { background: linear-gradient(90deg,#7a3c0a,#e8a050); }

    .wd2-silver .wd2-overall-num, .wd2-silver .wd2-stat-val, .wd2-silver .wd2-player-name { color: #c0d0e5; }
    .wd2-silver .wd2-archetype-pill { color: #c0d0e5; border-color: rgba(150,175,210,.45); background: rgba(100,130,165,.12); }
    .wd2-silver .wd2-dedsec-emblem  { color: #c0d0e5; border-color: rgba(155,180,215,.55); }
    .wd2-silver .wd2-portrait       { border-color: rgba(165,185,215,.35); }
    .wd2-silver .wd2-divider        { color: #8fa8c5; }
    .wd2-silver .wd2-stat-lbl       { color: rgba(192,210,230,.8); }
    .wd2-silver .wd2-fill { background: linear-gradient(90deg,#506080,#c0d0e5); }

    .wd2-gold .wd2-overall-num, .wd2-gold .wd2-stat-val, .wd2-gold .wd2-player-name { color: #ffd700; }
    .wd2-gold .wd2-archetype-pill { color: #ffd700; border-color: rgba(210,165,0,.5); background: rgba(175,130,0,.15); }
    .wd2-gold .wd2-dedsec-emblem  { color: #ffd700; border-color: rgba(215,170,0,.6); }
    .wd2-gold .wd2-portrait       { border-color: rgba(210,170,0,.42); }
    .wd2-gold .wd2-divider        { color: #c8a000; }
    .wd2-gold .wd2-stat-lbl       { color: rgba(255,215,0,.8); }
    .wd2-gold .wd2-fill { background: linear-gradient(90deg,#906000,#ffd700); }

    .wd2-special .wd2-overall-num, .wd2-special .wd2-player-name { color: #ff6600; }
    .wd2-special .wd2-stat-val   { color: #00d2ff; }
    .wd2-special .wd2-archetype-pill { color: #ff6600; border-color: rgba(255,102,0,.55); background: rgba(255,102,0,.1); }
    .wd2-special .wd2-dedsec-emblem  { color: #00d2ff; border-color: rgba(0,210,255,.6); box-shadow: 0 0 16px rgba(0,210,255,.25); }
    .wd2-special .wd2-portrait       { border-color: rgba(255,102,0,.6); box-shadow: 0 0 20px rgba(255,102,0,.25); }
    .wd2-special .wd2-divider        { color: #ff6600; background: linear-gradient(90deg, transparent, #ff6600 40%, #00d2ff 60%, transparent) !important; opacity: .5; }
    .wd2-special .wd2-stat-lbl       { color: rgba(0,210,255,.85); }
    .wd2-special .wd2-overall-num    { text-shadow: 0 0 24px rgba(255,102,0,.9), 0 0 55px rgba(255,102,0,.4); }

    /* ── EXPORT BTN ──────────────────────────── */
    .wd2-export-btn {
      background: transparent; border: 1px solid rgba(255,102,0,.5); color: #ff6600;
      font-family: 'Orbitron', monospace; font-size: .58rem; font-weight: 700;
      letter-spacing: .2em; text-transform: uppercase;
      padding: 11px 28px; border-radius: 6px; cursor: pointer;
      transition: all .25s ease; display: flex; align-items: center; gap: 9px;
      width: 100%;
    }
    .wd2-export-btn:hover:not(:disabled) {
      background: rgba(255,102,0,.1); border-color: rgba(255,102,0,.9);
      box-shadow: 0 0 26px rgba(255,102,0,.3); text-shadow: 0 0 8px rgba(255,102,0,.8);
    }
    .wd2-export-btn:disabled { opacity: .4; cursor: not-allowed; }

    /* ── PERFORMANCE PANEL ───────────────────── */
    .perf-panel {
      flex: 1; min-width: 340px; max-width: 580px;
      display: flex; flex-direction: column; gap: 18px;
    }
    .perf-section {
      background: rgba(255,255,255,.025);
      border: 1px solid rgba(255,102,0,.15);
      border-radius: 14px; padding: 20px 22px;
      backdrop-filter: blur(8px);
      box-shadow: 0 8px 32px rgba(0,0,0,.5), inset 0 0 0 1px rgba(255,255,255,.03);
      position: relative; overflow: hidden;
    }
    .perf-section::before {
      content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
      background: linear-gradient(90deg, transparent, rgba(255,102,0,.5), transparent);
    }
    .section-title {
      font-family: 'Orbitron', monospace; font-size: .55rem; font-weight: 700;
      letter-spacing: .2em; color: rgba(255,102,0,.7); text-transform: uppercase;
      margin-bottom: 18px; display: flex; align-items: center; gap: 10px;
    }
    .section-title::after { content: ''; flex: 1; height: 1px; background: linear-gradient(90deg, rgba(255,102,0,.3), transparent); }

    /* radar chart */
    .radar-wrap { display: flex; justify-content: center; padding: 4px 0 8px; }
    .radar-svg { overflow: visible; }
    .radar-grid line, .radar-grid polygon { stroke: rgba(255,255,255,.07); fill: none; }
    .radar-axis line { stroke: rgba(255,255,255,.1); }
    .radar-data-poly {
      fill: rgba(255,102,0,.15); stroke: rgba(255,102,0,.8); stroke-width: 1.5;
      filter: drop-shadow(0 0 6px rgba(255,102,0,.4));
    }
    .wd2-special .radar-data-poly {
      fill: rgba(0,210,255,.12); stroke: rgba(0,210,255,.9); stroke-width: 1.5;
      filter: drop-shadow(0 0 8px rgba(0,210,255,.5));
    }
    .radar-dot {
      fill: #ff6600; filter: drop-shadow(0 0 4px rgba(255,102,0,.8));
    }
    .radar-label {
      font-family: 'Orbitron', monospace; font-size: 8px; font-weight: 700;
      fill: rgba(255,255,255,.7); letter-spacing: .06em;
    }
    .radar-val {
      font-family: 'Orbitron', monospace; font-size: 7.5px; font-weight: 900;
      fill: #ff6600;
    }

    /* stat meters */
    .stat-meters { display: flex; flex-direction: column; gap: 12px; }
    .stat-meter-row {
      display: grid; grid-template-columns: 26px 80px 1fr 36px;
      align-items: center; gap: 10px;
    }
    .stat-icon {
      width: 26px; height: 26px; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
      font-size: 14px; flex-shrink: 0;
    }
    .stat-meter-name {
      font-family: 'Orbitron', monospace; font-size: .48rem;
      font-weight: 700; letter-spacing: .07em; text-transform: uppercase;
      opacity: .85;
    }
    .stat-meter-track {
      height: 8px; border-radius: 4px;
      background: rgba(255,255,255,.05);
      position: relative; overflow: visible;
    }
    .stat-meter-fill {
      height: 100%; border-radius: 4px; position: relative;
      transition: width 1.6s cubic-bezier(.4,0,.2,1);
    }
    .stat-meter-fill::after {
      content: ''; position: absolute; right: -2px; top: -3px; bottom: -3px;
      width: 9px; border-radius: 50%; background: inherit;
      filter: brightness(2) blur(3px);
    }
    .stat-meter-val {
      font-family: 'Orbitron', monospace; font-size: .7rem; font-weight: 900;
      text-align: right;
    }

    /* meta grid */
    .meta-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; }
    .meta-cell {
      background: rgba(0,0,0,.3); border: 1px solid rgba(255,255,255,.06);
      border-radius: 8px; padding: 10px 12px; text-align: center;
    }
    .meta-cell-val {
      font-family: 'Orbitron', monospace; font-size: 1.15rem; font-weight: 900;
      color: var(--orange); line-height: 1;
      text-shadow: 0 0 12px rgba(255,102,0,.6);
    }
    .meta-cell-lbl {
      font-family: 'Share Tech Mono', monospace; font-size: .42rem;
      opacity: .45; letter-spacing: .1em; text-transform: uppercase; margin-top: 5px;
    }

    @media (max-width: 760px) {
      .dashboard-layout { flex-direction: column; align-items: center; }
      .perf-panel { min-width: unset; width: 100%; max-width: 480px; }
    }
  </style>
</head>
<body>
  <div class="scanlines"></div>
  <div id="root"></div>

<script type="text/babel">
const PORTRAIT_SRC = "__PORTRAIT_URI__";
const DYNAMIC_DATA = __DYNAMIC_DATA__;

function getRarity(ov) {
  if (ov >= 85) return 'special'; if (ov >= 75) return 'gold'; if (ov >= 65) return 'silver'; return 'bronze';
}
function getRarityTag(r) {
  return { special:'◆ IN-FORM', gold:'▲ GOLD', silver:'◈ SILVER', bronze:'◉ BRONZE' }[r];
}

const STAT_FILLS_SPECIAL = { stealth: 'linear-gradient(90deg,#003d80,#0088ff)', hacking: 'linear-gradient(90deg,#004d22,#00ff88)', combat: 'linear-gradient(90deg,#800000,#ff3300)', driving: 'linear-gradient(90deg,#4d3300,#ffaa00)', chaos: 'linear-gradient(90deg,#4d0055,#cc00ff)' };
const STAT_GLOWS_SPECIAL = { stealth:'#0088ff', hacking:'#00ff88', combat:'#ff3300', driving:'#ffaa00', chaos:'#cc00ff' };
const STAT_ORDER = ['stealth','hacking','combat','driving','chaos'];

function StatRow({ name, value, rarity }) {
  const isSpecial = rarity === 'special';
  const fillStyle = isSpecial ? { background: STAT_FILLS_SPECIAL[name], boxShadow: `0 0 8px ${STAT_GLOWS_SPECIAL[name]}` } : {};
  return (
    <div className="wd2-stat-row">
      <span className="wd2-stat-lbl">{name.slice(0,3).toUpperCase()}</span>
      <div className="wd2-track"><div className="wd2-fill" style={{ width:`${value}%`, ...fillStyle }} /></div>
      <span className="wd2-stat-val">{Math.round(value)}</span>
    </div>
  );
}

function PlayerCard({ data }) {
  if (!data) return <div style={{ color: 'red' }}>No card data available</div>;
  const rarity = getRarity(data.overall);
  const tag = getRarityTag(rarity);
  const date = new Date(data.generated_at).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});

  return (
    <div className="wd2-card-wrapper">
      {rarity === 'special' && <div className="wd2-special-ring" />}
      <div className={`wd2-card wd2-${rarity}`} id="player-card">
        <div className="wd2-circuit" />
        <div className="wd2-card-inner">
          <div className="wd2-card-top">
            <div className="wd2-overall-col">
              <span className="wd2-overall-num">{data.overall}</span>
              <span className="wd2-archetype-pill">{data.archetype}</span>
            </div>
            <div className="wd2-right-col">
              <div className="wd2-dedsec-emblem">DED<br/>SEC</div>
              <span className="wd2-rarity-tag">{tag}</span>
              <span className="wd2-rarity-tag">{data.sessions_analyzed} sess</span>
            </div>
          </div>
          <div className="wd2-portrait">
            <img src={PORTRAIT_SRC} alt="DedSec Operative" />
            <div className="wd2-portrait-shade" />
            <span className="wd2-player-name wd2-glitch" data-text={data.player_name}>{data.player_name}</span>
          </div>
          <div className="wd2-divider" />
          <div className="wd2-stats">
            {STAT_ORDER.map(s => <StatRow key={s} name={s} value={data.stats[s] ?? 0} rarity={rarity} />)}
          </div>
          <div className="wd2-card-footer">
            <span className="wd2-foot-txt">cTOS v3.1 · WD2</span>
            <span className="wd2-foot-txt">{date}</span>
          </div>
        </div>
      </div>
    </div>
  );
}


const STAT_ICONS = { stealth:'🕵️', hacking:'💻', combat:'🔫', driving:'🚗', chaos:'💥' };
const STAT_COLORS = { stealth:'#0088ff', hacking:'#00ff88', combat:'#ff3300', driving:'#ffaa00', chaos:'#cc00ff' };

function RadarChart({ stats }) {
  if (!stats) return null;
  const size = 200; const cx = 100; const cy = 100; const r = 76;
  const labels = STAT_ORDER;
  const n = labels.length;
  const angle = (i) => (Math.PI * 2 * i / n) - Math.PI / 2;
  const pt = (i, frac) => {
    const a = angle(i);
    return [cx + r * frac * Math.cos(a), cy + r * frac * Math.sin(a)];
  };
  const gridLevels = [0.25, 0.5, 0.75, 1];
  const gridPoly = (frac) => labels.map((_,i) => pt(i, frac).join(',')).join(' ');
  const dataPoints = labels.map((l,i) => pt(i, (stats[l] ?? 0) / 100));
  const dataPoly = dataPoints.map(p => p.join(',')).join(' ');

  return (
    <div className="radar-wrap">
      <svg className="radar-svg" viewBox="0 0 200 200" width="200" height="200">
        <g className="radar-grid">
          {gridLevels.map(f => <polygon key={f} points={gridPoly(f)} />)}
          {labels.map((_,i) => { const [x,y] = pt(i,1); return <line key={i} x1={cx} y1={cy} x2={x} y2={y} className="radar-axis" />; })}
        </g>
        <polygon className="radar-data-poly" points={dataPoly} />
        {dataPoints.map(([x,y], i) => <circle key={i} className="radar-dot" cx={x} cy={y} r="4" style={{fill: STAT_COLORS[labels[i]]}} />)}
        {labels.map((l,i) => {
          const [lx, ly] = pt(i, 1.22);
          const [vx, vy] = pt(i, 1.38);
          return (
            <g key={l}>
              <text className="radar-label" x={lx} y={ly} textAnchor="middle" dominantBaseline="middle">{l.slice(0,3).toUpperCase()}</text>
              <text className="radar-val" x={vx} y={vy} textAnchor="middle" dominantBaseline="middle" style={{fill: STAT_COLORS[l]}}>{Math.round(stats[l]??0)}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function StatMeters({ stats }) {
  if (!stats) return null;
  return (
    <div className="stat-meters">
      {STAT_ORDER.map(stat => {
        const val = Math.round(stats[stat] ?? 0);
        const color = STAT_COLORS[stat];
        return (
          <div className="stat-meter-row" key={stat}>
            <div className="stat-icon" style={{background: `${color}18`}}>{STAT_ICONS[stat]}</div>
            <span className="stat-meter-name" style={{color}}>{stat}</span>
            <div className="stat-meter-track">
              <div className="stat-meter-fill" style={{width:`${val}%`, background:`linear-gradient(90deg, ${color}60, ${color})`}} />
            </div>
            <span className="stat-meter-val" style={{color}}>{val}</span>
          </div>
        );
      })}
    </div>
  );
}

function MetaGrid({ data }) {
  if (!data) return null;
  const meta = data._meta || {};
  const mins = Math.round(meta.total_play_time_minutes ?? 0);
  const hrs = (mins / 60).toFixed(1);
  return (
    <div className="meta-grid">
      <div className="meta-cell">
        <div className="meta-cell-val">{data.sessions_analyzed}</div>
        <div className="meta-cell-lbl">Sessions</div>
      </div>
      <div className="meta-cell">
        <div className="meta-cell-val">{hrs}h</div>
        <div className="meta-cell-lbl">Played</div>
      </div>
      <div className="meta-cell">
        <div className="meta-cell-val">{data.overall}</div>
        <div className="meta-cell-lbl">Overall</div>
      </div>
    </div>
  );
}

function TrendChart({ history }) {
  if (!history || history.length < 2) {
    return <div style={{fontFamily:'Share Tech Mono', fontSize:'0.6rem', color:'#fff', opacity:0.5, textAlign:'center'}}>Not enough sessions to plot trends.</div>;
  }
  
  const width = 380;
  const height = 120;
  const maxVal = 100;
  
  const getPoints = (statName) => {
    return history.map((d, i) => {
      const x = (i / (history.length - 1)) * (width - 40) + 20;
      const y = height - (d[statName] / maxVal) * (height - 40) - 20;
      return `${x},${y}`;
    }).join(' ');
  };

  return (
    <div className="panel">
      <div className="panel-head">Progression Trends</div>
      <svg className="trend-svg" viewBox={`0 0 ${width} ${height}`}>
        {STAT_ORDER.map(stat => (
          <polyline key={stat} points={getPoints(stat)} fill="none" stroke={STAT_GLOWS_SPECIAL[stat]} strokeWidth="2.5" style={{ filter: `drop-shadow(0 0 3px ${STAT_GLOWS_SPECIAL[stat]})` }} />
        ))}
        {/* Plot points */}
        {STAT_ORDER.map(stat => (
          history.map((d, i) => {
            const x = (i / (history.length - 1)) * (width - 40) + 20;
            const y = height - (d[stat] / maxVal) * (height - 40) - 20;
            return <circle key={`${stat}-${i}`} cx={x} cy={y} r="3" fill="#000" stroke={STAT_GLOWS_SPECIAL[stat]} strokeWidth="1.5" />
          })
        ))}
      </svg>
      <div style={{display:'flex',gap:'10px',justifyContent:'center',marginTop:'8px',fontFamily:'Share Tech Mono,monospace',fontSize:'0.42rem',textTransform:'uppercase',flexWrap:'wrap'}}>
        {STAT_ORDER.map(stat => (
          <div style={{display:'flex',alignItems:'center',gap:'4px'}} key={stat}>
            <div style={{ width:8,height:8,borderRadius:'50%',background:STAT_GLOWS_SPECIAL[stat],boxShadow:`0 0 5px ${STAT_GLOWS_SPECIAL[stat]}` }} />
            {stat}
          </div>
        ))}
      </div>
    </div>
  );
}

function App() {
  const [viewMode, setViewMode] = React.useState('all_time');
  const [exporting, setExporting] = React.useState(false);
  
  const cardData = viewMode === 'all_time' ? DYNAMIC_DATA.all_time : DYNAMIC_DATA.recent;

  async function exportPng() {
    setExporting(true);
    try {
      const el = document.getElementById('player-card');
      const canvas = await html2canvas(el, {
        backgroundColor: null, scale: 3, useCORS: true, allowTaint: true,
        ignoreElements: el => el.classList?.contains('wd2-special-ring'),
      });
      const a = document.createElement('a');
      a.download = `wd2-card-${(cardData.player_name||'operative').toLowerCase().replace(/\s+/g,'-')}.png`;
      a.href = canvas.toDataURL('image/png');
      a.click();
    } catch(e) { console.error('Export failed:', e); }
    setExporting(false);
  }

  return (
    <div className="page-wrapper">
      <header className="page-header">
        <h1>WD2 <span>PLAYSTYLE</span> CARD</h1>
        <p>DedSec Operative Assessment · cTOS Analytics Division</p>
      </header>

      <div className="dashboard-layout">
        {/* ── LEFT: CARD ── */}
        <div className="card-col">
          <PlayerCard data={cardData} />
          <button id="export-png-btn" className="wd2-export-btn" onClick={exportPng} disabled={exporting}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" width="14" height="14">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {exporting ? 'EXPORTING…' : 'EXPORT PNG'}
          </button>
        </div>

        {/* ── RIGHT: PERFORMANCE PANEL ── */}
        <div className="perf-panel">
          {/* View tabs */}
          <div style={{display:'flex',gap:'8px',marginBottom:'4px'}}>
            <button className={`view-btn ${viewMode === 'all_time' ? 'active' : ''}`} onClick={() => setViewMode('all_time')}>All-Time Career</button>
            {DYNAMIC_DATA.recent && (
              <button className={`view-btn ${viewMode === 'recent' ? 'active' : ''}`} onClick={() => setViewMode('recent')}>Recent Form</button>
            )}
          </div>

          {/* Radar chart */}
          <div className="perf-section">
            <div className="section-title">STAT RADAR</div>
            <RadarChart stats={cardData.stats} />
          </div>

          {/* Stat meters */}
          <div className="perf-section">
            <div className="section-title">ATTRIBUTE BREAKDOWN</div>
            <StatMeters stats={cardData.stats} />
          </div>

          {/* Session meta + trend */}
          <div className="perf-section">
            <div className="section-title">SESSION ANALYTICS</div>
            <MetaGrid data={cardData} />
            <div style={{marginTop:'16px'}}>
              <TrendChart history={DYNAMIC_DATA.history} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
</script>
</body>
</html>
"""

out = HTML.replace("__PORTRAIT_URI__", portrait_uri).replace("__DYNAMIC_DATA__", json.dumps(DYNAMIC_DATA))

out_path = os.path.join(HERE, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(out)

print(f"Written {out_path}  ({len(out):,} bytes)")
