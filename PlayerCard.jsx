/**
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
