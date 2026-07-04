"""
stat_engine.py — Watch Dogs 2 Playstyle Stat Engine
----------------------------------------------------
Ingests all session JSON files (manual_tagger + input_logger),
aggregates across a rolling window, normalises stats to 0-99,
and outputs a card-ready JSON.

Usage:
  python stat_engine.py                         # all sessions, all players
  python stat_engine.py --player Atharva        # filter by player name
  python stat_engine.py --sessions 5            # last N sessions only
  python stat_engine.py --list                  # list all available sessions
  python stat_engine.py --output card_data.json # custom output path
  python stat_engine.py --no-save               # print only, don't write file

Output (default): card_data.json   (drop into the PlayerCard JSON editor)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── paths ─────────────────────────────────────────────────────────────────────
HERE         = Path(__file__).parent
SESSIONS_DIR = HERE / "sessions"
DEFAULT_OUT  = HERE / "card_data.json"

# ── ANSI colours ──────────────────────────────────────────────────────────────
CYAN   = "\033[96m"
ORANGE = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
PURPLE = "\033[95m"
GOLD   = "\033[33m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

STAT_COLOURS = {
    "stealth": CYAN,
    "hacking": GREEN,
    "combat":  RED,
    "driving": ORANGE,
    "chaos":   PURPLE,
}

# ── Overall rating weights (must sum to 1.0) ──────────────────────────────────
DEFAULT_WEIGHTS = {
    "stealth": 0.22,
    "hacking": 0.28,
    "combat":  0.18,
    "driving": 0.15,
    "chaos":   0.17,
}

# ── Source trust weights ──────────────────────────────────────────────────────
# manual_tag  = self-reported → slightly less objective
# input_log   = computed from actual keystrokes → more objective
SOURCE_TRUST = {
    "manual_tag": 0.70,
    "input_log":  1.00,
}
DEFAULT_SOURCE_TRUST = 0.75   # for unknown/future sources


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION LOADING
# ─────────────────────────────────────────────────────────────────────────────

def _load_file(path: Path) -> list[dict]:
    """Load one session file; handles both single-dict and list-of-dicts."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"{RED}⚠  Could not parse {path.name}: {exc}{RESET}")
        return []
    if isinstance(raw, dict):
        return [raw]
    if isinstance(raw, list):
        return raw
    return []


def load_all_sessions(sessions_dir: Path = SESSIONS_DIR) -> list[dict]:
    """Load every session from every file in the sessions directory."""
    if not sessions_dir.exists():
        return []
    all_sessions: list[dict] = []
    for f in sorted(sessions_dir.glob("*.json")):
        entries = _load_file(f)
        for e in entries:
            e["_source_file"] = f.name
        all_sessions.extend(entries)
    return all_sessions


def filter_sessions(
    sessions: list[dict],
    player: str = "",
    last_n: int = 0,
) -> list[dict]:
    """Filter by player name and/or take last N sessions."""
    if player:
        player_lower = player.strip().lower()
        sessions = [
            s for s in sessions
            if s.get("player_name", "").lower() == player_lower
        ]
    # Sort by tagged_at / session_end chronologically
    def _sort_key(s: dict) -> str:
        return (s.get("tagged_at")
                or s.get("session_end")
                or s.get("session_start")
                or "0")
    sessions = sorted(sessions, key=_sort_key)
    if last_n > 0:
        sessions = sessions[-last_n:]
    return sessions


# ─────────────────────────────────────────────────────────────────────────────
#  STAT EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

STAT_KEYS = ["stealth", "hacking", "combat", "driving", "chaos"]


def _extract_stats(session: dict) -> Optional[dict[str, float]]:
    """Pull the five stats out of a session, normalised to 0-99."""
    raw = session.get("stats", {})
    if not raw:
        return None
    result: dict[str, float] = {}
    for k in STAT_KEYS:
        v = raw.get(k)
        if v is None:
            return None   # skip incomplete sessions
        result[k] = float(max(0, min(99, v)))
    return result


def _session_weight(session: dict) -> float:
    """
    A scalar weight for this session's contribution to the aggregate.
    Combines:
      - source trust (manual = 0.7, input_log = 1.0)
      - recency boost (most recent = 1.0, older = decays toward 0.5)
      - duration signal (longer sessions = slightly more reliable)
    """
    trust  = SOURCE_TRUST.get(session.get("source", ""), DEFAULT_SOURCE_TRUST)
    dur    = session.get("duration_minutes", 30)
    dur_w  = min(1.0, dur / 60.0) * 0.3 + 0.7   # 0.7 → 1.0 over 60 min
    return trust * dur_w


# ─────────────────────────────────────────────────────────────────────────────
#  AGGREGATION
# ─────────────────────────────────────────────────────────────────────────────

def aggregate(sessions: list[dict]) -> dict[str, float]:
    """
    Weighted average of each stat across all sessions.
    Returns raw 0-99 floats (not yet normalised to spread).
    """
    totals   = {k: 0.0 for k in STAT_KEYS}
    weight_sum = 0.0

    for i, session in enumerate(sessions):
        stats = _extract_stats(session)
        if stats is None:
            continue
        # Recency decay: most recent session = 1.0, index 0 = 0.5
        n     = len(sessions)
        decay = 0.5 + 0.5 * (i / max(1, n - 1))
        w     = _session_weight(session) * decay

        for k in STAT_KEYS:
            totals[k] += stats[k] * w
        weight_sum += w

    if weight_sum == 0:
        return {k: 50.0 for k in STAT_KEYS}

    return {k: totals[k] / weight_sum for k in STAT_KEYS}


# ─────────────────────────────────────────────────────────────────────────────
#  NORMALISATION  (stretch to 0-99 range with configurable floor/ceiling)
# ─────────────────────────────────────────────────────────────────────────────

def normalise(
    raw: dict[str, float],
    floor: float = 10.0,
    ceiling: float = 99.0,
) -> dict[str, int]:
    """
    Linearly remap the raw weighted averages so they fill the
    floor→ceiling band, preserving relative differences.
    This ensures cards always look interesting (no all-50 cards).
    If all stats are identical, apply a small jitter.
    """
    vals   = list(raw.values())
    lo     = min(vals)
    hi     = max(vals)

    if hi - lo < 5:
        # Flat session — spread minimally so bars look differentiated
        spread = 5.0
        lo     = lo - spread / 2
        hi     = lo + spread

    band = ceiling - floor

    def remap(v: float) -> int:
        normalised = (v - lo) / (hi - lo)  # 0.0 → 1.0
        remapped   = floor + normalised * band
        return max(0, min(99, round(remapped)))

    return {k: remap(v) for k, v in raw.items()}


# ─────────────────────────────────────────────────────────────────────────────
#  OVERALL RATING
# ─────────────────────────────────────────────────────────────────────────────

def compute_overall(stats: dict[str, int],
                    weights: dict[str, float] = DEFAULT_WEIGHTS) -> int:
    """
    Weighted average → clamped to 0-99.
    Weights don't need to sum to 1.0 exactly; they're normalised here.
    """
    total_weight = sum(weights.values())
    raw = sum(stats[k] * weights.get(k, 0) for k in STAT_KEYS) / total_weight
    return max(0, min(99, round(raw)))


# ─────────────────────────────────────────────────────────────────────────────
#  ARCHETYPE PICKER
# ─────────────────────────────────────────────────────────────────────────────

def pick_archetype(stats: dict[str, int]) -> str:
    ranked = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    top_stat, top_val     = ranked[0]
    second_stat, sec_val  = ranked[1]
    bottom_val            = ranked[-1][1]

    # Tight cluster → no dominant skill
    if top_val < 40:
        return "Balanced Operative"
    if (top_val - bottom_val) < 15:
        return "Balanced Operative"

    if top_stat == "stealth":
        if stats["chaos"] < 40:
            return "Ghost"
        return "Shadow Agent"   # stealthy but chaotic

    if top_stat == "hacking":
        if stats["chaos"] > 60:
            return "Digital Anarchist"
        return "Netrunner"

    if top_stat == "combat":
        if stats["stealth"] < 35:
            return "Enforcer"
        return "Tactical Aggressor"

    if top_stat == "driving":
        if stats["combat"] > 65:
            return "Wheelman"
        return "Ghost Driver"

    if top_stat == "chaos":
        if stats["combat"] > 65:
            return "Enforcer"
        if stats["hacking"] > 60:
            return "Digital Anarchist"
        return "Chaos Agent"

    # No clear winner
    if abs(top_val - sec_val) < 10:
        return "Balanced Operative"
    return "Opportunist"


# ─────────────────────────────────────────────────────────────────────────────
#  TREND ANALYSIS  (bonus insight for multi-session runs)
# ─────────────────────────────────────────────────────────────────────────────

def compute_trends(sessions: list[dict]) -> dict[str, str]:
    """
    Compare first half vs second half of session window.
    Returns per-stat trend: "up" | "down" | "stable".
    """
    if len(sessions) < 4:
        return {k: "stable" for k in STAT_KEYS}

    mid   = len(sessions) // 2
    early = [s for s in sessions[:mid]  if _extract_stats(s)]
    late  = [s for s in sessions[mid:]  if _extract_stats(s)]

    if not early or not late:
        return {k: "stable" for k in STAT_KEYS}

    def avg_stat(group: list[dict], key: str) -> float:
        vals = [_extract_stats(s)[key] for s in group]
        return sum(vals) / len(vals)

    trends: dict[str, str] = {}
    for k in STAT_KEYS:
        e = avg_stat(early, k)
        l = avg_stat(late,  k)
        delta = l - e
        if delta >  4: trends[k] = "up"
        elif delta < -4: trends[k] = "down"
        else:           trends[k] = "stable"

    return trends


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION METADATA SUMMARY
# ─────────────────────────────────────────────────────────────────────────────

def session_metadata(sessions: list[dict]) -> dict:
    """Extract counts, date range, and source mix for reporting."""
    if not sessions:
        return {}

    manual_count = sum(1 for s in sessions if s.get("source") == "manual_tag")
    input_count  = sum(1 for s in sessions if s.get("source") == "input_log")
    other_count  = len(sessions) - manual_count - input_count

    dates = []
    for s in sessions:
        d = s.get("tagged_at") or s.get("session_end") or s.get("session_start")
        if d:
            try:
                dates.append(datetime.fromisoformat(d.replace("Z", "+00:00")))
            except Exception:
                pass

    total_mins = sum(
        s.get("duration_minutes", 0) or
        (s.get("duration_seconds", 0) / 60)
        for s in sessions
    )

    players = list({s.get("player_name", "Unknown") for s in sessions})

    return {
        "total_sessions":  len(sessions),
        "manual_sessions": manual_count,
        "input_sessions":  input_count,
        "other_sessions":  other_count,
        "total_play_time_minutes": round(total_mins, 1),
        "date_first": min(dates).isoformat() if dates else None,
        "date_last":  max(dates).isoformat() if dates else None,
        "players":    players,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    player: str        = "",
    last_n: int        = 0,
    weights: dict      = None,
    floor: float       = 10.0,
    ceiling: float     = 99.0,
    verbose: bool      = True,
) -> dict:
    """
    Full pipeline: load → filter → aggregate → normalise → output.
    Returns the card-ready dict.
    """
    weights = weights or DEFAULT_WEIGHTS

    # ── 1. Load ───────────────────────────────────────────────────────────────
    all_sessions = load_all_sessions()
    if not all_sessions:
        print(f"{ORANGE}⚠  No sessions found in {SESSIONS_DIR}{RESET}")
        print(f"   Run manual_tagger.py or input_logger.py to record sessions first.")
        return _empty_card(player or "Operative")

    # ── 2. Filter ─────────────────────────────────────────────────────────────
    sessions = filter_sessions(all_sessions, player=player, last_n=last_n)
    if not sessions:
        desc = f"player='{player}'" if player else "all players"
        print(f"{ORANGE}⚠  No sessions matched ({desc}).{RESET}")
        return _empty_card(player or "Operative")

    return generate_card_data(
        sessions, 
        player=player, 
        weights=weights, 
        floor=floor, 
        ceiling=ceiling, 
        verbose=verbose
    )

def generate_card_data(
    sessions: list[dict],
    player: str        = "",
    weights: dict      = None,
    floor: float       = 10.0,
    ceiling: float     = 99.0,
    verbose: bool      = False,
) -> dict:
    """
    Generate card dictionary for a specific list of sessions.
    """
    weights = weights or DEFAULT_WEIGHTS
    
    if not sessions:
        return _empty_card(player or "Operative")

    # ── 3. Aggregate + Normalise ──────────────────────────────────────────────
    raw_stats    = aggregate(sessions)
    norm_stats   = normalise(raw_stats, floor=floor, ceiling=ceiling)
    overall      = compute_overall(norm_stats, weights)
    archetype    = pick_archetype(norm_stats)
    trends       = compute_trends(sessions)
    meta         = session_metadata(sessions)

    # ── 4. Infer player name ──────────────────────────────────────────────────
    inferred_player = (
        player
        or _most_common(s.get("player_name", "") for s in sessions)
        or "Operative"
    )

    # ── 5. Build output ───────────────────────────────────────────────────────
    card = {
        "player_name":      inferred_player,
        "overall":          overall,
        "archetype":        archetype,
        "stats":            norm_stats,
        "sessions_analyzed": len(sessions),
        "generated_at":     _now_iso(),
        "_raw_stats":       {k: round(v, 1) for k, v in raw_stats.items()},
        "_trends":          trends,
        "_meta":            meta,
        "_weights_used":    weights,
    }

    if verbose:
        _print_report(card, sessions, trends, meta)

    return card

def _empty_card(player: str) -> dict:
    return {
        "player_name": player,
        "overall":     50,
        "archetype":   "Unknown",
        "stats":       {k: 50 for k in STAT_KEYS},
        "sessions_analyzed": 0,
        "generated_at": _now_iso(),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _most_common(iterable) -> str:
    counts: dict[str, int] = {}
    for item in iterable:
        if item:
            counts[item] = counts.get(item, 0) + 1
    if not counts:
        return ""
    return max(counts, key=lambda k: counts[k])


# ─────────────────────────────────────────────────────────────────────────────
#  CONSOLE REPORT
# ─────────────────────────────────────────────────────────────────────────────

_BAR_W = 32
_TREND_ICON = {"up": f"{GREEN}▲{RESET}", "down": f"{RED}▼{RESET}", "stable": f"{DIM}─{RESET}"}

def _bar(value: int, colour: str) -> str:
    filled = int(_BAR_W * value / 99)
    return colour + "█" * filled + DIM + "░" * (_BAR_W - filled) + RESET


def _rarity_label(overall: int) -> str:
    if overall >= 85: return f"{PURPLE}◆ IN-FORM / SPECIAL{RESET}"
    if overall >= 75: return f"{GOLD}▲ GOLD{RESET}"
    if overall >= 65: return f"{DIM}◈ SILVER{RESET}"
    return f"◉ BRONZE"


def _print_report(card: dict, sessions: list[dict],
                  trends: dict, meta: dict):
    stats    = card["stats"]
    overall  = card["overall"]
    archetype = card["archetype"]
    raw      = card.get("_raw_stats", {})

    print()
    print(f"  {BOLD}{ORANGE}◆ WD2 STAT ENGINE REPORT  ──────────────────────────────────────{RESET}")
    print(f"  Operative    :  {BOLD}{CYAN}{card['player_name']}{RESET}")
    print(f"  Archetype    :  {BOLD}{PURPLE}{archetype}{RESET}")
    print(f"  Overall      :  {BOLD}{overall}{RESET}  {_rarity_label(overall)}")
    print(f"  Sessions     :  {meta.get('total_sessions', len(sessions))}  "
          f"({meta.get('manual_sessions', 0)} manual · {meta.get('input_sessions', 0)} input_log)")
    if meta.get("total_play_time_minutes"):
        h = int(meta["total_play_time_minutes"] // 60)
        m = int(meta["total_play_time_minutes"] % 60)
        print(f"  Total time   :  {h}h {m}m")
    print()
    print(f"  {'STAT':<9}  {'SCORE':>5}  {'BAR':^{_BAR_W+2}}  {'RAW':>5}  TREND")
    print(f"  {'─'*9}  {'─'*5}  {'─'*(_BAR_W+2)}  {'─'*5}  {'─'*5}")

    for k in STAT_KEYS:
        col   = STAT_COLOURS.get(k, RESET)
        val   = stats[k]
        rv    = raw.get(k, val)
        trend = _TREND_ICON.get(trends.get(k, "stable"), "─")
        print(f"  {col}{k.upper():<9}{RESET}  "
              f"{col}{val:>5}{RESET}  "
              f"  {_bar(val, col)}  "
              f"{DIM}{rv:>5.1f}{RESET}  "
              f"{trend}")

    print()
    print(f"  {DIM}Generated : {card['generated_at']}{RESET}")
    print(f"  {ORANGE}◆────────────────────────────────────────────────────────────────{RESET}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION LISTING  (--list)
# ─────────────────────────────────────────────────────────────────────────────

def list_sessions(player: str = ""):
    all_sessions = load_all_sessions()
    sessions     = filter_sessions(all_sessions, player=player)

    if not sessions:
        print(f"{ORANGE}No sessions found.{RESET}")
        return

    print(f"\n  {BOLD}{ORANGE}◆ SESSION LIST  ({len(sessions)} entries)  ─────────────────────────────{RESET}")
    print(f"  {'#':>3}  {'SOURCE':<12}  {'PLAYER':<14}  {'ARCHETYPE':<22}  {'OVR':>3}  DATE")
    print(f"  {'─'*3}  {'─'*12}  {'─'*14}  {'─'*22}  {'─'*3}  {'─'*19}")

    for i, s in enumerate(sessions, 1):
        src  = s.get("source", "?")[:12]
        plr  = s.get("player_name", "?")[:14]
        arc  = s.get("archetype", "?")[:22]
        ovr  = s.get("self_rated_overall", "?")
        date = (s.get("tagged_at") or s.get("session_end") or "?")[:19].replace("T", " ")
        file = s.get("_source_file", "")
        print(f"  {i:>3}  {src:<12}  {plr:<14}  {arc:<22}  {str(ovr):>3}  {date}  {DIM}{file}{RESET}")

    print()


# ─────────────────────────────────────────────────────────────────────────────
#  CARD DATA UPDATE  (writes card_data.json + optional copy to sessions dir)
# ─────────────────────────────────────────────────────────────────────────────

def save_card(card: dict, path: Path = DEFAULT_OUT):
    """Write the card-ready JSON (private _* fields stripped for the card)."""
    public_card = {k: v for k, v in card.items() if not k.startswith("_")}
    path.write_text(json.dumps(public_card, indent=2), encoding="utf-8")
    print(f"  {GREEN}✓  Card data saved →  {path}{RESET}")
    print(f"  {DIM}Paste this JSON into the player card editor, or open{RESET}")
    print(f"  {DIM}index.html and click any preset, then paste from card_data.json{RESET}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Enable ANSI on Windows
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="WD2 Stat Engine — aggregate sessions into a player card")
    parser.add_argument("--player",   "-p", default="",
                        help="Filter by player name")
    parser.add_argument("--sessions", "-n", type=int, default=0,
                        help="Use only the last N sessions (0 = all)")
    parser.add_argument("--output",   "-o", default=str(DEFAULT_OUT),
                        help=f"Output JSON path (default: {DEFAULT_OUT})")
    parser.add_argument("--no-save",  action="store_true",
                        help="Print report but do not write card_data.json")
    parser.add_argument("--list",     "-l", action="store_true",
                        help="List all recorded sessions and exit")
    parser.add_argument("--floor",    type=float, default=10.0,
                        help="Minimum normalised stat value (default 10)")
    parser.add_argument("--ceiling",  type=float, default=99.0,
                        help="Maximum normalised stat value (default 99)")
    parser.add_argument("--weights",  "-w", default="",
                        help='JSON string of custom weights e.g. \'{"hacking":0.4}\'')
    args = parser.parse_args()

    if args.list:
        list_sessions(player=args.player)
        return

    # Parse custom weights
    weights = dict(DEFAULT_WEIGHTS)
    if args.weights:
        try:
            user_w = json.loads(args.weights)
            weights.update(user_w)
        except Exception as exc:
            print(f"{RED}⚠  Could not parse --weights: {exc}{RESET}")

    card = run_pipeline(
        player   = args.player,
        last_n   = args.sessions,
        weights  = weights,
        floor    = args.floor,
        ceiling  = args.ceiling,
        verbose  = True,
    )

    if not args.no_save and card.get("sessions_analyzed", 0) > 0:
        save_card(card, Path(args.output))


if __name__ == "__main__":
    main()
