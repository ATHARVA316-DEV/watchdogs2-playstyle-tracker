"""
Build script: generates index.html for the WD2 Player Card.
Run: python build_card.py
"""
import base64, os, textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
PORTRAIT_PATH = r"C:\Users\mpath\.gemini\antigravity-ide\brain\95865d84-5447-4f9a-add1-5a7f6c5cd088\dedsec_portrait_1783081521648.png"

with open(PORTRAIT_PATH, "rb") as f:
    portrait_b64 = base64.b64encode(f.read()).decode()
portrait_uri = "data:image/png;base64," + portrait_b64

HTML = """\
<!DOCTYPE html>
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
      --orange: #ff6600;
      --cyan:   #00d2ff;
      --dark:   #0a0a0f;
    }

    html { scroll-behavior: smooth; }

    body {
      background: var(--dark);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      font-family: 'Rajdhani', sans-serif;
      color: #fff;
      overflow-x: hidden;
    }

    /* ── background ambiance ── */
    body::before {
      content: '';
      position: fixed; inset: 0;
      background:
        radial-gradient(ellipse at 20% 50%, rgba(255,102,0,.07) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 20%, rgba(0,210,255,.05) 0%, transparent 50%);
      pointer-events: none; z-index: 0;
    }

    /* ── scanlines ── */
    .scanlines {
      position: fixed; inset: 0; z-index: 9999; pointer-events: none;
      background: repeating-linear-gradient(0deg,
        transparent, transparent 2px,
        rgba(0,0,0,.07) 2px, rgba(0,0,0,.07) 4px);
    }

    /* ════════════════════════════════════════
       PAGE LAYOUT
    ════════════════════════════════════════ */
    .page-wrapper {
      position: relative; z-index: 1;
      display: flex; flex-direction: column; align-items: center;
      padding: 48px 20px 64px;
      gap: 0;
    }

    .page-header {
      text-align: center;
      margin-bottom: 36px;
    }

    .page-header h1 {
      font-family: 'Orbitron', monospace;
      font-size: clamp(1rem, 3vw, 1.5rem);
      font-weight: 900;
      letter-spacing: .35em;
      text-transform: uppercase;
      color: var(--orange);
      text-shadow: 0 0 24px rgba(255,102,0,.65), 0 0 48px rgba(255,102,0,.3);
    }

    .page-header h1 span { color: var(--cyan); text-shadow: 0 0 20px rgba(0,210,255,.65); }

    .page-header p {
      font-family: 'Share Tech Mono', monospace;
      font-size: .65rem;
      letter-spacing: .2em;
      color: rgba(255,255,255,.3);
      margin-top: 6px;
      text-transform: uppercase;
    }

    /* ════════════════════════════════════════
       CARD
    ════════════════════════════════════════ */
    .card-wrapper { position: relative; perspective: 800px; }

    .card {
      width: 310px;
      border-radius: 18px;
      position: relative;
      overflow: hidden;
      box-shadow:
        0 0 0 1px rgba(255,255,255,.06),
        0 24px 64px rgba(0,0,0,.85),
        0 0 80px rgba(255,102,0,.18);
      transition: transform .4s cubic-bezier(.2,.8,.4,1), box-shadow .4s ease;
      transform-style: preserve-3d;
    }

    .card:hover {
      transform: rotateY(-4deg) rotateX(3deg) translateY(-10px);
      box-shadow:
        0 0 0 1px rgba(255,255,255,.12),
        0 36px 90px rgba(0,0,0,.9),
        0 0 120px rgba(255,102,0,.32);
    }

    /* rarity backgrounds */
    .card.bronze  { background: linear-gradient(148deg, #1e1005 0%, #2d1a06 45%, #120c02 100%); }
    .card.silver  { background: linear-gradient(148deg, #0e1016 0%, #1c2232 45%, #090c12 100%); }
    .card.gold    { background: linear-gradient(148deg, #121000 0%, #201d00 45%, #0c0a00 100%); }
    .card.special { background: linear-gradient(148deg, #090010 0%, #160024 45%, #06000e 100%); }

    /* metallic sheen overlay */
    .card::before {
      content: ''; position: absolute; inset: 0; border-radius: inherit;
      pointer-events: none;
    }
    .card.bronze::before  { background: linear-gradient(135deg, rgba(220,140,60,.35) 0%, transparent 55%, rgba(180,100,30,.25) 100%); }
    .card.silver::before  { background: linear-gradient(135deg, rgba(200,220,245,.28) 0%, transparent 55%, rgba(155,175,205,.2) 100%); }
    .card.gold::before    { background: linear-gradient(135deg, rgba(255,210,30,.32)  0%, transparent 55%, rgba(220,170,0,.22) 100%); }
    .card.special::before { background: linear-gradient(135deg, rgba(255,102,0,.35)   0%, transparent 45%, rgba(0,210,255,.22) 75%, rgba(180,0,255,.28) 100%); }

    /* circuit grid */
    .circuit {
      position: absolute; inset: 0; pointer-events: none;
      background-image:
        linear-gradient(rgba(255,102,0,.6) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,102,0,.6) 1px, transparent 1px),
        linear-gradient(rgba(255,102,0,.25) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,102,0,.25) 1px, transparent 1px);
      background-size: 72px 72px, 72px 72px, 18px 18px, 18px 18px;
      opacity: .055;
    }
    .card.special .circuit { opacity: .1; background-image:
        linear-gradient(rgba(255,102,0,.9) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,210,255,.9) 1px, transparent 1px),
        linear-gradient(rgba(255,102,0,.45) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,210,255,.45) 1px, transparent 1px);
    }

    /* animated glow ring for special */
    .special-ring {
      position: absolute; inset: -2px; border-radius: 20px; z-index: -1;
      background: conic-gradient(from 0deg, #ff6600, #ff00aa, #00d2ff, #00ff88, #ff6600);
      background-size: 300%;
      animation: spin-ring 3s linear infinite;
      filter: blur(6px); opacity: .55;
    }
    @keyframes spin-ring {
      to { transform: rotate(360deg); }
    }

    /* ── inner layout ── */
    .card-inner {
      position: relative; z-index: 2;
      padding: 16px 15px 14px;
      display: flex; flex-direction: column;
    }

    /* ── TOP ROW ── */
    .card-top {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 10px;
    }

    .overall-col { display: flex; flex-direction: column; align-items: center; line-height: 1; }

    .overall-num {
      font-family: 'Orbitron', monospace;
      font-weight: 900; font-size: 3.6rem;
      line-height: 1; letter-spacing: -.03em;
    }

    .archetype-pill {
      font-family: 'Orbitron', monospace;
      font-size: .44rem; font-weight: 700;
      letter-spacing: .07em; text-transform: uppercase;
      padding: 2px 6px; border-radius: 3px;
      margin-top: 4px; border: 1px solid;
      max-width: 92px; text-align: center; line-height: 1.35;
      word-break: break-word;
    }

    .right-col { display: flex; flex-direction: column; align-items: center; gap: 5px; }

    .dedsec-emblem {
      width: 46px; height: 46px;
      border-radius: 50%; border: 1px solid;
      display: flex; align-items: center; justify-content: center;
      font-family: 'Orbitron', monospace;
      font-size: .42rem; font-weight: 900;
      letter-spacing: .04em; text-align: center; line-height: 1.3;
    }

    .rarity-tag {
      font-family: 'Share Tech Mono', monospace;
      font-size: .5rem; letter-spacing: .12em;
      opacity: .75; text-transform: uppercase;
    }

    /* ── PORTRAIT ── */
    .portrait {
      width: 100%; height: 188px;
      border-radius: 10px; overflow: hidden;
      position: relative; border: 1px solid;
      margin-bottom: 10px;
    }

    .portrait img {
      width: 100%; height: 100%;
      object-fit: cover; object-position: center 10%;
      display: block;
    }

    .portrait-shade {
      position: absolute; inset: 0;
      background: linear-gradient(to bottom, transparent 45%, rgba(0,0,0,.75) 100%);
    }

    .player-name {
      position: absolute; bottom: 8px; left: 0; right: 0;
      text-align: center;
      font-family: 'Orbitron', monospace;
      font-size: 1.05rem; font-weight: 900;
      letter-spacing: .22em; text-transform: uppercase;
      text-shadow: 0 0 8px rgba(0,0,0,1), 0 0 16px rgba(0,0,0,1);
    }

    /* glitch on name */
    .glitch { position: relative; }
    .glitch::before, .glitch::after {
      content: attr(data-text);
      position: absolute; inset: 0;
      font-family: inherit; font-size: inherit;
      font-weight: inherit; letter-spacing: inherit;
    }
    .glitch::before { color: #00d2ff; animation: gc 6s infinite; }
    .glitch::after  { color: #ff4400; animation: gc 6s .12s infinite; }
    @keyframes gc {
      0%,89%,100% { clip-path: inset(0 0 100% 0); transform: translate(0); opacity: 0; }
      91% { clip-path: inset(5% 0 70% 0);  transform: translate(-3px, 1px);  opacity: 1; }
      93% { clip-path: inset(50% 0 20% 0); transform: translate(3px, -2px);  opacity: 1; }
      95% { clip-path: inset(75% 0 5% 0);  transform: translate(-2px, 3px);  opacity: 1; }
      97% { clip-path: inset(25% 0 60% 0); transform: translate(2px, -1px);  opacity: 1; }
    }

    /* portrait glow pulse on hover */
    .card:hover .portrait::after {
      content: ''; position: absolute; inset: 0;
      background: rgba(0,210,255,.06);
      animation: pfx .2s steps(2) infinite;
    }
    @keyframes pfx {
      0%   { transform: translate(0); }
      50%  { transform: translate(-2px, 1px); opacity: .8; }
      100% { transform: translate(2px, -1px); }
    }

    /* ── DIVIDER ── */
    .divider {
      height: 1px; margin: 4px 0 10px;
      background: linear-gradient(90deg, transparent, currentColor, transparent);
      opacity: .4;
    }

    /* ── STATS ── */
    .stats { display: flex; flex-direction: column; gap: 6px; }

    .stat-row {
      display: grid;
      grid-template-columns: 32px 1fr 30px;
      align-items: center; gap: 8px;
    }

    .stat-lbl {
      font-family: 'Orbitron', monospace;
      font-size: .52rem; font-weight: 700;
      letter-spacing: .06em; text-align: right; opacity: .85;
    }

    .track {
      height: 6px; border-radius: 4px;
      background: rgba(255,255,255,.06); overflow: visible; position: relative;
    }

    .fill {
      height: 100%; border-radius: 4px;
      position: relative;
      transition: width 1.2s cubic-bezier(.4,0,.2,1);
    }

    /* tip glow */
    .fill::after {
      content: ''; position: absolute; right: -1px; top: -2px; bottom: -2px; width: 6px;
      border-radius: 50%;
      background: inherit;
      filter: brightness(2) blur(2px);
    }

    .stat-val {
      font-family: 'Orbitron', monospace;
      font-size: .68rem; font-weight: 700; text-align: left;
    }

    /* ── CARD FOOTER ── */
    .card-footer {
      margin-top: 12px; padding-top: 8px;
      border-top: 1px solid rgba(255,255,255,.07);
      display: flex; justify-content: space-between; align-items: center;
    }
    .foot-txt {
      font-family: 'Share Tech Mono', monospace;
      font-size: .42rem; opacity: .35;
      letter-spacing: .1em; text-transform: uppercase;
    }

    /* ════════════════════════════════════════
       COLOR THEMING PER RARITY
    ════════════════════════════════════════ */
    /* --- bronze --- */
    .bronze .overall-num, .bronze .stat-val, .bronze .player-name { color: #e8a050; }
    .bronze .archetype-pill { color: #e8a050; border-color: rgba(200,120,40,.5); background: rgba(160,80,20,.18); }
    .bronze .dedsec-emblem  { color: #e8a050; border-color: rgba(200,120,40,.55); }
    .bronze .portrait       { border-color: rgba(180,110,40,.45); }
    .bronze .divider        { color: #b46820; }
    .bronze .stat-lbl       { color: rgba(230,155,75,.8); }
    .bronze .fill { background: linear-gradient(90deg,#7a3c0a,#e8a050); }

    /* --- silver --- */
    .silver .overall-num, .silver .stat-val, .silver .player-name { color: #c0d0e5; }
    .silver .archetype-pill { color: #c0d0e5; border-color: rgba(150,175,210,.45); background: rgba(100,130,165,.15); }
    .silver .dedsec-emblem  { color: #c0d0e5; border-color: rgba(155,180,215,.55); }
    .silver .portrait       { border-color: rgba(165,185,215,.38); }
    .silver .divider        { color: #8fa8c5; }
    .silver .stat-lbl       { color: rgba(192,210,230,.8); }
    .silver .fill { background: linear-gradient(90deg,#506080,#c0d0e5); }

    /* --- gold --- */
    .gold .overall-num, .gold .stat-val, .gold .player-name { color: #ffd700; }
    .gold .archetype-pill { color: #ffd700; border-color: rgba(210,165,0,.5); background: rgba(175,130,0,.18); }
    .gold .dedsec-emblem  { color: #ffd700; border-color: rgba(215,170,0,.6); }
    .gold .portrait       { border-color: rgba(210,170,0,.45); }
    .gold .divider        { color: #c8a000; }
    .gold .stat-lbl       { color: rgba(255,215,0,.8); }
    .gold .fill { background: linear-gradient(90deg,#906000,#ffd700); }

    /* --- special --- */
    .special .overall-num, .special .player-name { color: #ff6600; }
    .special .stat-val   { color: #00d2ff; }
    .special .archetype-pill { color: #ff6600; border-color: rgba(255,102,0,.55); background: rgba(255,102,0,.12); }
    .special .dedsec-emblem  { color: #00d2ff; border-color: rgba(0,210,255,.6); box-shadow: 0 0 14px rgba(0,210,255,.25); }
    .special .portrait       { border-color: rgba(255,102,0,.6); box-shadow: 0 0 18px rgba(255,102,0,.28); }
    .special .divider        { color: #ff6600; background: linear-gradient(90deg, transparent, #ff6600 40%, #00d2ff 60%, transparent) !important; opacity: .55; }
    .special .stat-lbl       { color: rgba(0,210,255,.85); }
    .special .overall-num    { text-shadow: 0 0 22px rgba(255,102,0,.85), 0 0 50px rgba(255,102,0,.4); }
    /* stat fills overridden per stat in JS for special */

    /* ════════════════════════════════════════
       CONTROLS BELOW CARD
    ════════════════════════════════════════ */
    .controls { display: flex; flex-direction: column; align-items: center; gap: 0; margin-top: 28px; }

    .export-btn {
      background: transparent;
      border: 1px solid rgba(255,102,0,.5);
      color: #ff6600;
      font-family: 'Orbitron', monospace;
      font-size: .62rem; font-weight: 700;
      letter-spacing: .22em; text-transform: uppercase;
      padding: 11px 30px; border-radius: 5px;
      cursor: pointer;
      transition: all .25s ease;
      display: flex; align-items: center; gap: 9px;
    }
    .export-btn:hover:not(:disabled) {
      background: rgba(255,102,0,.1);
      border-color: rgba(255,102,0,.9);
      box-shadow: 0 0 24px rgba(255,102,0,.32);
      text-shadow: 0 0 8px rgba(255,102,0,.8);
    }
    .export-btn:disabled { opacity: .45; cursor: not-allowed; }
    .export-btn svg { width: 14px; height: 14px; flex-shrink: 0; }

    /* ── JSON editor panel ── */
    .json-panel {
      margin-top: 36px; width: 380px; max-width: 95vw;
    }
    .json-panel-head {
      font-family: 'Orbitron', monospace; font-size: .58rem; font-weight: 700;
      letter-spacing: .2em; color: rgba(255,102,0,.65); text-transform: uppercase;
      margin-bottom: 8px;
      display: flex; align-items: center; gap: 8px;
    }
    .json-panel-head::before {
      content: ''; flex: 1; height: 1px;
      background: linear-gradient(90deg, rgba(255,102,0,.4), transparent);
    }

    textarea.json-edit {
      width: 100%; height: 210px;
      background: rgba(255,102,0,.03);
      border: 1px solid rgba(255,102,0,.2);
      border-radius: 8px;
      color: rgba(0,210,255,.9);
      font-family: 'Share Tech Mono', monospace;
      font-size: .7rem; padding: 12px;
      resize: vertical; outline: none; line-height: 1.55;
      transition: border-color .2s;
    }
    textarea.json-edit:focus { border-color: rgba(255,102,0,.5); }

    .load-btn {
      margin-top: 8px; width: 100%;
      background: transparent;
      border: 1px solid rgba(0,210,255,.3);
      color: rgba(0,210,255,.85);
      font-family: 'Orbitron', monospace;
      font-size: .58rem; font-weight: 700;
      letter-spacing: .15em; text-transform: uppercase;
      padding: 9px; border-radius: 5px;
      cursor: pointer; transition: all .2s;
    }
    .load-btn:hover {
      background: rgba(0,210,255,.08);
      border-color: rgba(0,210,255,.6);
      box-shadow: 0 0 14px rgba(0,210,255,.2);
    }

    .err-msg {
      margin-top: 7px;
      font-family: 'Share Tech Mono', monospace;
      font-size: .6rem; color: #ff4040;
    }

    /* quick-load presets */
    .presets {
      margin-top: 10px; display: flex; gap: 6px; flex-wrap: wrap; justify-content: center;
    }
    .preset-btn {
      background: rgba(255,255,255,.04);
      border: 1px solid rgba(255,255,255,.12);
      color: rgba(255,255,255,.55);
      font-family: 'Share Tech Mono', monospace;
      font-size: .55rem; padding: 5px 10px; border-radius: 4px;
      cursor: pointer; letter-spacing: .08em; text-transform: uppercase;
      transition: all .18s;
    }
    .preset-btn:hover { border-color: rgba(255,102,0,.5); color: #ff6600; background: rgba(255,102,0,.06); }
  </style>
</head>
<body>
  <div class="scanlines"></div>
  <div id="root"></div>

<script type="text/babel">
/* ─────────────────────────────────────────────────────────
   ASSETS
───────────────────────────────────────────────────────── */
const PORTRAIT_SRC = "__PORTRAIT_URI__";

/* ─────────────────────────────────────────────────────────
   MOCK / PRESET DATA
───────────────────────────────────────────────────────── */
const PRESETS = {
  "Digital Anarchist": {
    player_name: "Atharva", overall: 82,
    archetype: "Digital Anarchist",
    stats: { stealth:65, hacking:91, combat:58, driving:70, chaos:88 },
    sessions_analyzed: 12, generated_at: "2026-07-03T00:00:00Z"
  },
  "Ghost": {
    player_name: "Wraith", overall: 78,
    archetype: "Ghost",
    stats: { stealth:94, hacking:72, combat:31, driving:55, chaos:18 },
    sessions_analyzed: 8, generated_at: "2026-07-03T00:00:00Z"
  },
  "Enforcer": {
    player_name: "Blaze", overall: 69,
    archetype: "Enforcer",
    stats: { stealth:22, hacking:38, combat:87, driving:64, chaos:90 },
    sessions_analyzed: 5, generated_at: "2026-07-03T00:00:00Z"
  },
  "Wheelman": {
    player_name: "Torque", overall: 74,
    archetype: "Wheelman",
    stats: { stealth:45, hacking:50, combat:55, driving:93, chaos:62 },
    sessions_analyzed: 9, generated_at: "2026-07-03T00:00:00Z"
  },
  "In-Form Legend": {
    player_name: "Nexus", overall: 90,
    archetype: "Balanced Operative",
    stats: { stealth:85, hacking:92, combat:83, driving:88, chaos:75 },
    sessions_analyzed: 30, generated_at: "2026-07-03T00:00:00Z"
  },
};

/* ─────────────────────────────────────────────────────────
   HELPERS
───────────────────────────────────────────────────────── */
function getRarity(ov) {
  if (ov >= 85) return 'special';
  if (ov >= 75) return 'gold';
  if (ov >= 65) return 'silver';
  return 'bronze';
}
function getRarityTag(r) {
  return { special:'◆ IN-FORM', gold:'▲ GOLD', silver:'◈ SILVER', bronze:'◉ BRONZE' }[r];
}

const STAT_FILLS_SPECIAL = {
  stealth: 'linear-gradient(90deg,#003d80,#0088ff)',
  hacking: 'linear-gradient(90deg,#004d22,#00ff88)',
  combat:  'linear-gradient(90deg,#800000,#ff3300)',
  driving: 'linear-gradient(90deg,#4d3300,#ffaa00)',
  chaos:   'linear-gradient(90deg,#4d0055,#cc00ff)',
};
const STAT_GLOWS_SPECIAL = {
  stealth:'#0088ff', hacking:'#00ff88', combat:'#ff3300', driving:'#ffaa00', chaos:'#cc00ff',
};

const STAT_ORDER = ['stealth','hacking','combat','driving','chaos'];

/* ─────────────────────────────────────────────────────────
   COMPONENTS
───────────────────────────────────────────────────────── */
function StatRow({ name, value, rarity }) {
  const isSpecial = rarity === 'special';
  const fillStyle = isSpecial
    ? { background: STAT_FILLS_SPECIAL[name], boxShadow: `0 0 8px ${STAT_GLOWS_SPECIAL[name]}` }
    : {};

  return (
    <div className="stat-row">
      <span className="stat-lbl">{name.slice(0,3).toUpperCase()}</span>
      <div className="track">
        <div className="fill" style={{ width:`${value}%`, ...fillStyle }} />
      </div>
      <span className="stat-val">{value}</span>
    </div>
  );
}

function PlayerCard({ data }) {
  const rarity = getRarity(data.overall);
  const tag = getRarityTag(rarity);
  const date = new Date(data.generated_at).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});

  return (
    <div className="card-wrapper">
      {rarity === 'special' && <div className="special-ring" />}
      <div className={`card ${rarity}`} id="player-card">
        <div className="circuit" />
        <div className="card-inner">

          {/* TOP */}
          <div className="card-top">
            <div className="overall-col">
              <span className="overall-num">{data.overall}</span>
              <span className="archetype-pill">{data.archetype}</span>
            </div>
            <div className="right-col">
              <div className="dedsec-emblem">DED<br/>SEC</div>
              <span className="rarity-tag">{tag}</span>
              <span className="rarity-tag">{data.sessions_analyzed} sess</span>
            </div>
          </div>

          {/* PORTRAIT */}
          <div className="portrait">
            <img src={PORTRAIT_SRC} alt="DedSec Operative" />
            <div className="portrait-shade" />
            <span className="player-name glitch" data-text={data.player_name}>
              {data.player_name}
            </span>
          </div>

          {/* DIVIDER */}
          <div className="divider" />

          {/* STATS */}
          <div className="stats">
            {STAT_ORDER.map(s => (
              <StatRow key={s} name={s} value={data.stats[s] ?? 0} rarity={rarity} />
            ))}
          </div>

          {/* FOOTER */}
          <div className="card-footer">
            <span className="foot-txt">cTOS v3.1 · WD2</span>
            <span className="foot-txt">{date}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────
   APP
───────────────────────────────────────────────────────── */
function App() {
  const defaultData = PRESETS['Digital Anarchist'];
  const [cardData, setCardData] = React.useState(defaultData);
  const [jsonText, setJsonText] = React.useState(JSON.stringify(defaultData, null, 2));
  const [error, setError] = React.useState(null);
  const [exporting, setExporting] = React.useState(false);

  function loadJson() {
    try {
      const parsed = JSON.parse(jsonText);
      if (!parsed.overall || !parsed.stats) throw new Error('Missing required fields: overall, stats');
      setCardData(parsed);
      setError(null);
    } catch (e) {
      setError('⚠ ' + e.message);
    }
  }

  function loadPreset(name) {
    const d = PRESETS[name];
    setCardData(d);
    setJsonText(JSON.stringify(d, null, 2));
    setError(null);
  }

  async function exportPng() {
    setExporting(true);
    try {
      const el = document.getElementById('player-card');
      const canvas = await html2canvas(el, {
        backgroundColor: null, scale: 3,
        useCORS: true, allowTaint: true,
        ignoreElements: el => el.classList?.contains('special-ring'),
      });
      const a = document.createElement('a');
      a.download = `wd2-card-${(cardData.player_name||'operative').toLowerCase().replace(/\\s+/g,'-')}.png`;
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

      <PlayerCard data={cardData} />

      <div className="controls">
        <button id="export-png-btn" className="export-btn" onClick={exportPng} disabled={exporting}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {exporting ? 'EXPORTING…' : 'EXPORT PNG'}
        </button>

        <div className="json-panel">
          <div className="json-panel-head">Paste Player JSON</div>
          <textarea
            id="json-editor"
            className="json-edit"
            value={jsonText}
            onChange={e => setJsonText(e.target.value)}
            spellCheck={false}
          />
          {error && <div className="err-msg">{error}</div>}
          <button id="load-json-btn" className="load-btn" onClick={loadJson}>
            ⟳ &nbsp;LOAD &amp; RENDER CARD
          </button>
          <div className="presets">
            {Object.keys(PRESETS).map(k => (
              <button key={k} className="preset-btn" onClick={() => loadPreset(k)}>{k}</button>
            ))}
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

out = HTML.replace("__PORTRAIT_URI__", portrait_uri)

out_path = os.path.join(HERE, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(out)

print(f"Written {out_path}  ({len(out):,} bytes)")

# ── write PlayerCard.jsx ──────────────────────────────────────────────────────
JSX = r"""/**
 * PlayerCard.jsx -- Watch Dogs 2 Playstyle Card
 *
 * FIFA-style player card with DedSec/cTOS theme.
 *
 * Props:
 *   data: { player_name, overall (0-99), archetype,
 *           stats: { stealth, hacking, combat, driving, chaos },
 *           sessions_analyzed, generated_at }
 *   portraitSrc?: string  (URL or base64 data URI)
 *
 * Rarity: Bronze <65 | Silver 65-74 | Gold 75-84 | Special 85+
 */
import React, { useCallback, useState } from "react";

const STAT_ORDER = ["stealth", "hacking", "combat", "driving", "chaos"];

const STAT_FILLS = {
  stealth: "linear-gradient(90deg,#003d80,#0088ff)",
  hacking: "linear-gradient(90deg,#004d22,#00ff88)",
  combat:  "linear-gradient(90deg,#800000,#ff3300)",
  driving: "linear-gradient(90deg,#4d3300,#ffaa00)",
  chaos:   "linear-gradient(90deg,#4d0055,#cc00ff)",
};

const STAT_GLOWS = {
  stealth: "#0088ff", hacking: "#00ff88",
  combat: "#ff3300", driving: "#ffaa00", chaos: "#cc00ff",
};

function getRarity(ov) {
  if (ov >= 85) return "special";
  if (ov >= 75) return "gold";
  if (ov >= 65) return "silver";
  return "bronze";
}

function getRarityTag(r) {
  return { special: "\u25c6 IN-FORM", gold: "\u25b2 GOLD", silver: "\u25c8 SILVER", bronze: "\u25c9 BRONZE" }[r];
}

function StatRow({ name, value, rarity }) {
  const isSpecial = rarity === "special";
  const fillStyle = isSpecial
    ? { background: STAT_FILLS[name], boxShadow: "0 0 8px " + STAT_GLOWS[name] }
    : {};
  return (
    <div className="wd2-stat-row">
      <span className="wd2-stat-lbl">{name.slice(0, 3).toUpperCase()}</span>
      <div className="wd2-track">
        <div className="wd2-fill"
          style={{ width: Math.min(99, Math.max(0, value)) + "%", ...fillStyle }}
        />
      </div>
      <span className="wd2-stat-val">{value}</span>
    </div>
  );
}

export function PlayerCard({ data, portraitSrc }) {
  const rarity = getRarity(data.overall);
  const tag    = getRarityTag(rarity);
  const date   = new Date(data.generated_at).toLocaleDateString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <div className="wd2-card-wrapper">
      {rarity === "special" && <div className="wd2-special-ring" />}
      <div className={"wd2-card wd2-" + rarity} id="player-card">
        <div className="wd2-circuit" />
        <div className="wd2-card-inner">

          <div className="wd2-card-top">
            <div className="wd2-overall-col">
              <span className="wd2-overall-num">{data.overall}</span>
              <span className="wd2-archetype-pill">{data.archetype}</span>
            </div>
            <div className="wd2-right-col">
              <div className="wd2-dedsec-emblem">DED<br />SEC</div>
              <span className="wd2-rarity-tag">{tag}</span>
              <span className="wd2-rarity-tag">{data.sessions_analyzed} sess</span>
            </div>
          </div>

          <div className="wd2-portrait">
            {portraitSrc
              ? <img src={portraitSrc} alt="DedSec Operative" />
              : <div className="wd2-portrait-placeholder" />
            }
            <div className="wd2-portrait-shade" />
            <span className="wd2-player-name wd2-glitch" data-text={data.player_name}>
              {data.player_name}
            </span>
          </div>

          <div className="wd2-divider" />

          <div className="wd2-stats">
            {STAT_ORDER.map(s => (
              <StatRow key={s} name={s} value={data.stats[s] || 0} rarity={rarity} />
            ))}
          </div>

          <div className="wd2-card-footer">
            <span className="wd2-foot-txt">cTOS v3.1 \u00b7 WD2</span>
            <span className="wd2-foot-txt">{date}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ExportButton({ playerName }) {
  const [exporting, setExporting] = useState(false);

  const handleExport = useCallback(async () => {
    if (typeof html2canvas === "undefined") {
      console.error("html2canvas not loaded. Add CDN script.");
      return;
    }
    setExporting(true);
    try {
      const el = document.getElementById("player-card");
      const canvas = await html2canvas(el, {
        backgroundColor: null, scale: 3, useCORS: true, allowTaint: true,
        ignoreElements: el => el.classList?.contains("wd2-special-ring"),
      });
      const a = document.createElement("a");
      a.download = "wd2-card-" + (playerName || "operative").toLowerCase().replace(/\s+/g, "-") + ".png";
      a.href = canvas.toDataURL("image/png");
      a.click();
    } catch (e) {
      console.error("Export failed:", e);
    }
    setExporting(false);
  }, [playerName]);

  return (
    <button className="wd2-export-btn" onClick={handleExport} disabled={exporting}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" width="14" height="14">
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      {exporting ? "EXPORTING\u2026" : "EXPORT PNG"}
    </button>
  );
}

export default PlayerCard;
"""

jsx_path = os.path.join(HERE, "PlayerCard.jsx")
with open(jsx_path, "w", encoding="utf-8") as f:
    f.write(JSX)
print(f"Written {jsx_path}")

