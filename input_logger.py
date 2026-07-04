"""
input_logger.py — Watch Dogs 2 Input Session Logger
----------------------------------------------------
Passively monitors OS-level keyboard/mouse events while you play WD2.
Classifies input into four playstyle states and builds per-session stats.

HOTKEYS (global, work even when the game window is focused):
  F9   →  Start recording a new session
  F10  →  Stop recording + save JSON
  F11  →  Print live stats to console (without stopping)
  F12  →  Quit the logger entirely

DOES NOT read game memory or inject code. Pure OS input events only.

Output:
  sessions/input_YYYYMMDD_HHMMSS.json   (one file per stopped session)

Usage:
  python input_logger.py [--config path/to/keybinds.json]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── optional coloured terminal output ────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

CYAN    = "\033[96m"
ORANGE  = "\033[93m"
GREEN   = "\033[92m"
RED     = "\033[91m"
PURPLE  = "\033[95m"
DIM     = "\033[2m"
BOLD    = "\033[1m"
RESET   = "\033[0m"

# ─────────────────────────────────────────────────────────────────────────────
#  DEFAULT KEY BINDINGS  (Watch Dogs 2 PC defaults)
#  Edit keybinds.json to override any of these.
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_KEYBINDS: dict[str, list[str]] = {
    # ── combat ──────────────────────────────────────────────────────────────
    "fire_weapon":      ["mouse_left"],        # LMB = shoot
    "aim_weapon":       ["mouse_right"],       # RMB = ADS
    "reload":           ["r"],
    "melee":            ["v"],

    # ── stealth ─────────────────────────────────────────────────────────────
    "crouch":           ["c", "ctrl"],         # C or Left Ctrl
    "cover":            ["q"],
    "whistle":          ["z"],                 # distract NPC
    "takedown":         ["f"],                 # non-lethal melee

    # ── hacking ─────────────────────────────────────────────────────────────
    "hack":             ["e"],                 # primary hack
    "mass_hack":        ["g"],                 # environmental hack
    "camera":           ["n"],                 # switch to camera / drone
    "netrunner":        ["tab"],               # open hack map

    # ── driving ─────────────────────────────────────────────────────────────
    "enter_vehicle":    ["f"],                 # same as takedown (context)
    "drive_forward":    ["w"],
    "drive_back":       ["s"],
    "drive_left":       ["a"],
    "drive_right":      ["d"],
    "handbrake":        ["space"],

    # ── movement (neutral) ──────────────────────────────────────────────────
    "move_forward":     ["w"],
    "move_back":        ["s"],
    "move_left":        ["a"],
    "move_right":       ["d"],
    "sprint":           ["shift"],
    "jump":             ["space"],
}

# ─────────────────────────────────────────────────────────────────────────────
#  PLAYSTYLE STATES
# ─────────────────────────────────────────────────────────────────────────────
class State:
    IDLE    = "idle"
    STEALTH = "stealth"
    HACKING = "hacking"
    COMBAT  = "combat"
    DRIVING = "driving"


# Weight of each action group toward its state (used in burst detection)
STATE_WEIGHTS = {
    State.COMBAT:  ["fire_weapon", "aim_weapon", "reload", "melee"],
    State.STEALTH: ["crouch", "cover", "whistle", "takedown"],
    State.HACKING: ["hack", "mass_hack", "camera", "netrunner"],
    State.DRIVING: ["drive_forward", "drive_back", "drive_left",
                    "drive_right", "handbrake", "enter_vehicle"],
}

HERE         = Path(__file__).parent
SESSIONS_DIR = HERE / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

CONFIG_PATH  = HERE / "keybinds.json"

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def ts() -> float:
    return time.monotonic()

def _key_name(key) -> str:
    """Normalise a pynput Key/KeyCode to a lowercase string token."""
    from pynput.keyboard import Key, KeyCode
    if isinstance(key, KeyCode):
        if key.char:
            return key.char.lower()
        return repr(key)
    # Special keys
    name_map = {
        Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
        Key.shift:  "shift", Key.shift_r: "shift",
        Key.space:  "space",
        Key.tab:    "tab",
        Key.f1:  "f1",  Key.f2:  "f2",  Key.f3:  "f3",  Key.f4:  "f4",
        Key.f5:  "f5",  Key.f6:  "f6",  Key.f7:  "f7",  Key.f8:  "f8",
        Key.f9:  "f9",  Key.f10: "f10", Key.f11: "f11", Key.f12: "f12",
        Key.enter: "enter",
        Key.esc:   "esc",
    }
    return name_map.get(key, str(key).lower().replace("key.", ""))


def load_keybinds() -> dict[str, list[str]]:
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            merged = {**DEFAULT_KEYBINDS, **user}
            return merged
        except Exception as exc:
            print(f"{RED}⚠ Could not load keybinds.json: {exc}{RESET}")
    return DEFAULT_KEYBINDS


def save_default_keybinds():
    """Write default keybinds.json if it doesn't exist yet."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_KEYBINDS, indent=2), encoding="utf-8")
        print(f"{DIM}  Created default keybinds.json — edit to customise.{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
#  BURST DETECTOR
#  Looks at the last N seconds of presses; decides the dominant state.
# ─────────────────────────────────────────────────────────────────────────────

class BurstDetector:
    """Sliding-window activity detector (last WINDOW_S seconds)."""
    WINDOW_S = 4.0

    def __init__(self, keybinds: dict[str, list[str]]):
        # action_name → set of bound key tokens
        self._binds: dict[str, set[str]] = {
            action: set(keys) for action, keys in keybinds.items()
        }
        # recent press timestamps per action
        self._events: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def record(self, key_token: str):
        now = ts()
        with self._lock:
            for action, keys in self._binds.items():
                if key_token in keys:
                    self._events[action].append(now)

    def state(self) -> str:
        """Return current dominant state based on recent events."""
        cutoff = ts() - self.WINDOW_S
        scores: dict[str, int] = {}
        with self._lock:
            for state, actions in STATE_WEIGHTS.items():
                count = 0
                for action in actions:
                    # prune old events
                    self._events[action] = [
                        t for t in self._events[action] if t >= cutoff]
                    count += len(self._events[action])
                scores[state] = count

        # Need at least 2 presses in window to claim a state
        best_state  = max(scores, key=lambda s: scores[s])
        best_score  = scores[best_state]
        return best_state if best_score >= 2 else State.IDLE


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION RECORDER
# ─────────────────────────────────────────────────────────────────────────────

class SessionRecorder:
    """Accumulates all per-session counters and state durations."""

    def __init__(self, keybinds: dict[str, list[str]], player_name: str = ""):
        self.session_id   = str(uuid.uuid4())
        self.player_name  = player_name
        self.start_time   = now_iso()
        self._start_ts    = ts()

        self.key_counts:  dict[str, int]   = defaultdict(int)  # raw key token counts
        self.action_counts: dict[str, int] = defaultdict(int)  # action name counts
        self.state_time:  dict[str, float] = {
            State.IDLE:    0.0,
            State.STEALTH: 0.0,
            State.HACKING: 0.0,
            State.COMBAT:  0.0,
            State.DRIVING: 0.0,
        }
        self.mouse_clicks: dict[str, int] = defaultdict(int)

        self._current_state      = State.IDLE
        self._state_entered_at   = ts()
        self._lock               = threading.Lock()

        # build reverse map: key_token → [action, ...]
        self._key_to_actions: dict[str, list[str]] = defaultdict(list)
        for action, keys in keybinds.items():
            for k in keys:
                self._key_to_actions[k].append(action)

    # ── update ───────────────────────────────────────────────────────────────

    def on_key_press(self, key_token: str):
        with self._lock:
            self.key_counts[key_token] += 1
            for action in self._key_to_actions.get(key_token, []):
                self.action_counts[action] += 1

    def on_mouse_click(self, button_name: str):
        with self._lock:
            self.mouse_clicks[button_name] += 1
            token = f"mouse_{button_name}"
            self.key_counts[token] += 1
            for action in self._key_to_actions.get(token, []):
                self.action_counts[action] += 1

    def update_state(self, new_state: str):
        """Called periodically by the polling thread."""
        now = ts()
        with self._lock:
            elapsed = now - self._state_entered_at
            self.state_time[self._current_state] += elapsed
            if new_state != self._current_state:
                self._current_state   = new_state
                self._state_entered_at = now

    def flush_state(self):
        """Finalise the current open state window before saving."""
        self.update_state(self._current_state)

    # ── computed stats ────────────────────────────────────────────────────────

    def elapsed_seconds(self) -> float:
        return ts() - self._start_ts

    def _active_seconds(self) -> float:
        return max(1.0, self.elapsed_seconds() - self.state_time[State.IDLE])

    def _stat_stealth(self) -> int:
        """High if lots of stealth time + low combat ratio."""
        active = self._active_seconds()
        stealth_ratio = self.state_time[State.STEALTH] / active
        cover_presses = self.action_counts.get("cover", 0) + \
                        self.action_counts.get("crouch", 0)
        takedowns     = self.action_counts.get("takedown", 0)
        shots         = self.action_counts.get("fire_weapon", 0)
        # favour low shots, high cover, high stealth time
        score = (stealth_ratio * 55) + \
                min(cover_presses * 0.8, 20) + \
                min(takedowns * 2, 10) - \
                min(shots * 0.3, 15)
        return max(0, min(99, int(score)))

    def _stat_hacking(self) -> int:
        active = self._active_seconds()
        hack_ratio = self.state_time[State.HACKING] / active
        hacks      = self.action_counts.get("hack", 0) + \
                     self.action_counts.get("mass_hack", 0)
        cameras    = self.action_counts.get("camera", 0)
        netrunner  = self.action_counts.get("netrunner", 0)
        score = (hack_ratio * 55) + \
                min(hacks * 1.2, 25) + \
                min(cameras * 0.6, 10) + \
                min(netrunner * 0.5, 9)
        return max(0, min(99, int(score)))

    def _stat_combat(self) -> int:
        active = self._active_seconds()
        combat_ratio = self.state_time[State.COMBAT] / active
        shots   = self.action_counts.get("fire_weapon", 0)
        reloads = self.action_counts.get("reload", 0)
        aims    = self.action_counts.get("aim_weapon", 0)
        score = (combat_ratio * 55) + \
                min(shots * 0.5, 25) + \
                min(reloads * 1.5, 10) + \
                min(aims * 0.3, 9)
        return max(0, min(99, int(score)))

    def _stat_driving(self) -> int:
        active = self._active_seconds()
        drive_ratio = self.state_time[State.DRIVING] / active
        wasd_drive  = sum(self.action_counts.get(a, 0)
                          for a in ["drive_forward","drive_back",
                                    "drive_left","drive_right"])
        handbrake   = self.action_counts.get("handbrake", 0)
        score = (drive_ratio * 55) + \
                min(wasd_drive * 0.15, 25) + \
                min(handbrake * 1.5, 10) + \
                min(self.action_counts.get("enter_vehicle", 0) * 3, 9)
        return max(0, min(99, int(score)))

    def _stat_chaos(self) -> int:
        """Derives chaos from combat burst frequency + shots fired."""
        shots   = self.action_counts.get("fire_weapon", 0)
        melee   = self.action_counts.get("melee", 0)
        # Transition count (switching state many times = chaotic play)
        score = min(shots * 0.6, 40) + \
                min(melee * 2, 15) + \
                self._stat_combat() * 0.3 + \
                (100 - self._stat_stealth()) * 0.15
        return max(0, min(99, int(score)))

    def build_output(self) -> dict:
        self.flush_state()
        elapsed = self.elapsed_seconds()

        stats = {
            "stealth": self._stat_stealth(),
            "hacking": self._stat_hacking(),
            "combat":  self._stat_combat(),
            "driving": self._stat_driving(),
            "chaos":   self._stat_chaos(),
        }

        overall = int(
            stats["stealth"] * 0.22 +
            stats["hacking"] * 0.28 +
            stats["combat"]  * 0.18 +
            stats["driving"] * 0.15 +
            stats["chaos"]   * 0.17
        )
        overall = max(0, min(99, overall))

        return {
            "session_id":         self.session_id,
            "source":             "input_log",
            "player_name":        self.player_name,
            "session_start":      self.start_time,
            "session_end":        now_iso(),
            "duration_seconds":   round(elapsed, 1),
            "duration_minutes":   round(elapsed / 60, 1),
            "stats":              stats,
            "self_rated_overall": overall,
            "archetype":          _pick_archetype(stats),
            "state_time_seconds": {k: round(v, 1)
                                   for k, v in self.state_time.items()},
            "key_event_counts":   dict(self.key_counts),
            "action_counts":      dict(self.action_counts),
            "mouse_clicks":       dict(self.mouse_clicks),
            "tagged_at":          now_iso(),
        }


# ─────────────────────────────────────────────────────────────────────────────
#  ARCHETYPE PICKER  (mirrors stat_engine logic)
# ─────────────────────────────────────────────────────────────────────────────

def _pick_archetype(stats: dict) -> str:
    ranked = sorted(stats.items(), key=lambda x: x[1], reverse=True)
    top_stat, top_val = ranked[0]
    second_stat, second_val = ranked[1]

    # No dominant stat → balanced
    if top_val < 40:
        return "Balanced Operative"

    # Very tight cluster → balanced
    if abs(top_val - ranked[-1][1]) < 15:
        return "Balanced Operative"

    if top_stat == "stealth" and stats["chaos"] < 40:
        return "Ghost"
    if top_stat == "hacking":
        return "Digital Anarchist" if stats["chaos"] > 55 else "Netrunner"
    if top_stat == "combat":
        return "Enforcer"
    if top_stat == "driving":
        return "Wheelman"
    if top_stat == "chaos":
        # chaos-first but combat also high → Enforcer flavour
        if stats["combat"] > 65:
            return "Enforcer"
        return "Digital Anarchist"

    # No clear winner
    if abs(top_val - second_val) < 12:
        return "Balanced Operative"
    return "Opportunist"



# ─────────────────────────────────────────────────────────────────────────────
#  LIVE DASHBOARD  (console)
# ─────────────────────────────────────────────────────────────────────────────

_BAR_WIDTH = 30

def _bar(value: int, colour: str = CYAN) -> str:
    filled = int(_BAR_WIDTH * value / 99)
    return colour + "█" * filled + DIM + "░" * (_BAR_WIDTH - filled) + RESET

def _fmt_time(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

STATE_COLOURS = {
    State.IDLE:    DIM,
    State.STEALTH: CYAN,
    State.HACKING: GREEN,
    State.COMBAT:  RED,
    State.DRIVING: ORANGE,
}
STATE_ICONS = {
    State.IDLE:    "◌",
    State.STEALTH: "◈",
    State.HACKING: "◆",
    State.COMBAT:  "⚡",
    State.DRIVING: "▶",
}

def print_dashboard(recorder: SessionRecorder, detector: BurstDetector,
                    recording: bool):
    rec = recorder
    stats_now = {
        "stealth": rec._stat_stealth(),
        "hacking": rec._stat_hacking(),
        "combat":  rec._stat_combat(),
        "driving": rec._stat_driving(),
        "chaos":   rec._stat_chaos(),
    }
    st = detector.state()
    sc = STATE_COLOURS.get(st, RESET)
    si = STATE_ICONS.get(st, "?")
    elapsed = rec.elapsed_seconds()

    STAT_COLOURS_MAP = {
        "stealth": CYAN,
        "hacking": GREEN,
        "combat":  RED,
        "driving": ORANGE,
        "chaos":   PURPLE,
    }

    lines = [
        "",
        f"  {BOLD}{ORANGE}◆ WD2 INPUT LOGGER  ──────────────────────────────────────────{RESET}",
        f"  {'●' if recording else '○'}  {'RECORDING' if recording else 'STANDBY'}"
        f"    {DIM}session {rec.session_id[:8]}…{RESET}"
        f"    {CYAN}elapsed: {_fmt_time(elapsed)}{RESET}",
        "",
        f"  {sc}{si} Current state: {BOLD}{st.upper():<10}{RESET}",
        "",
        "  STAT BREAKDOWN ─────────────────────────────────────────────",
    ]
    for name, val in stats_now.items():
        col = STAT_COLOURS_MAP.get(name, RESET)
        lines.append(
            f"  {col}{name.upper():<8}{RESET}  {_bar(val, col)}  {BOLD}{col}{val:>2}{RESET}"
        )

    lines += [
        "",
        "  TIME IN STATE ──────────────────────────────────────────────",
    ]
    for state in [State.STEALTH, State.HACKING, State.COMBAT,
                  State.DRIVING, State.IDLE]:
        t   = rec.state_time[state]
        col = STATE_COLOURS.get(state, RESET)
        ico = STATE_ICONS.get(state, "?")
        pct = int(100 * t / max(1.0, elapsed))
        lines.append(f"  {col}{ico} {state:<8}{RESET}  {_fmt_time(t)}  ({pct:>3}%)")

    top5 = sorted(rec.key_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    if top5:
        lines += ["", "  TOP KEYS ──────────────────────────────────────────────────"]
        for k, c in top5:
            lines.append(f"    {DIM}{k:<16}{RESET}  {CYAN}{c:>4}x{RESET}")

    lines += [
        "",
        f"  {DIM}F9=Start  F10=Stop+Save  F11=Refresh  F12=Quit{RESET}",
        f"  {ORANGE}◆ WD2 INPUT LOGGER  ────────────────────────────────────────────{RESET}",
        "",
    ]
    # Clear screen then print
    os.system("cls" if sys.platform == "win32" else "clear")
    print("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class InputLogger:
    POLL_INTERVAL = 0.5   # seconds between state updates

    def __init__(self, player_name: str = ""):
        self.player_name = player_name
        self.keybinds    = load_keybinds()
        self._recording  = False
        self._recorder: Optional[SessionRecorder] = None
        self._detector: Optional[BurstDetector]   = None
        self._running    = True
        self._lock       = threading.Lock()
        self._kb_listener  = None
        self._mouse_listener = None

    # ── hotkey actions ────────────────────────────────────────────────────────

    def start_session(self):
        with self._lock:
            if self._recording:
                print(f"\n{ORANGE}⚠  Session already running.{RESET}")
                return
            self._recorder  = SessionRecorder(self.keybinds, self.player_name)
            self._detector  = BurstDetector(self.keybinds)
            self._recording = True
        print(f"\n{GREEN}▶  Session STARTED — play WD2 now!{RESET}")
        print(f"   {DIM}Session ID: {self._recorder.session_id}{RESET}")

    def stop_session(self, quiet: bool = False) -> Optional[dict]:
        with self._lock:
            if not self._recording:
                if not quiet:
                    print(f"\n{ORANGE}⚠  No session running.{RESET}")
                return None
            self._recording = False
            rec = self._recorder
            self._recorder  = None
            self._detector  = None

        output  = rec.build_output()
        outfile = self._save(output)
        if not quiet:
            self._print_summary(output, outfile)
        return output

    def _save(self, data: dict) -> Path:
        ts_str  = datetime.now().strftime("%Y%m%d_%H%M%S")
        outfile = SESSIONS_DIR / f"input_{ts_str}.json"
        outfile.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return outfile

    def _print_summary(self, data: dict, outfile: Path):
        stats = data["stats"]
        print(f"\n{ORANGE}◆ SESSION SAVED ────────────────────────────────────────{RESET}")
        print(f"  {GREEN}✓{RESET} {outfile}")
        print(f"  Duration : {data['duration_minutes']} min")
        print(f"  Archetype: {CYAN}{data['archetype']}{RESET}")
        print(f"  Overall  : {BOLD}{data['self_rated_overall']}{RESET}")
        print(f"\n  Stats:")
        STAT_COLOURS_MAP = {
            "stealth": CYAN, "hacking": GREEN,
            "combat": RED, "driving": ORANGE, "chaos": PURPLE,
        }
        for k, v in stats.items():
            col = STAT_COLOURS_MAP.get(k, RESET)
            print(f"    {col}{k.upper():<8}{RESET}  {_bar(v, col)}  {col}{v}{RESET}")
        print(f"\n{ORANGE}◆─────────────────────────────────────────────────────{RESET}\n")

    def print_live(self):
        with self._lock:
            if not self._recording or not self._recorder or not self._detector:
                print(f"{ORANGE}⚠  No session running — press F9 to start.{RESET}")
                return
            rec = self._recorder
            det = self._detector
        print_dashboard(rec, det, self._recording)

    def quit(self):
        self._running = False
        self.stop_session(quiet=True)
        print(f"\n{DIM}  Logger stopped. Goodbye.{RESET}\n")

    # ── pynput callbacks ──────────────────────────────────────────────────────

    def _on_key_press(self, key):
        from pynput.keyboard import Key
        token = _key_name(key)

        # Hotkeys
        if token == "f9":
            self.start_session()
            return
        if token == "f10":
            self.stop_session()
            return
        if token == "f11":
            self.print_live()
            return
        if token == "f12":
            self.quit()
            return False   # stop listener

        # Record
        with self._lock:
            rec = self._recorder
            det = self._detector
        if rec and det:
            rec.on_key_press(token)
            det.record(token)

    def _on_mouse_click(self, x, y, button, pressed):
        if not pressed:
            return
        from pynput.mouse import Button
        name = {Button.left: "left", Button.right: "right",
                Button.middle: "middle"}.get(button, str(button))
        with self._lock:
            rec = self._recorder
            det = self._detector
        if rec and det:
            rec.on_mouse_click(name)
            det.record(f"mouse_{name}")

    # ── state polling thread ──────────────────────────────────────────────────

    def _poll_loop(self):
        while self._running:
            time.sleep(self.POLL_INTERVAL)
            with self._lock:
                rec = self._recorder
                det = self._detector
            if rec and det:
                new_state = det.state()
                rec.update_state(new_state)

    # ── run ───────────────────────────────────────────────────────────────────

    def run(self):
        from pynput import keyboard, mouse

        save_default_keybinds()

        print(f"\n{BOLD}{ORANGE}◆ WD2 INPUT LOGGER  ─────────────────────────────────────────────{RESET}")
        print(f"  Player : {CYAN}{self.player_name or '(not set)'}{RESET}")
        print(f"  Output : {DIM}{SESSIONS_DIR}{RESET}")
        print(f"\n  {GREEN}F9{RESET}  Start session")
        print(f"  {ORANGE}F10{RESET} Stop + save")
        print(f"  {CYAN}F11{RESET} Live dashboard")
        print(f"  {RED}F12{RESET} Quit")
        print(f"\n  {DIM}Waiting… (press F9 when you start playing){RESET}")
        print(f"{ORANGE}◆─────────────────────────────────────────────────────────────────{RESET}\n")

        # Start background poll thread
        poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        poll_thread.start()

        # Start listeners (non-blocking so we can handle quit)
        kb_listener = keyboard.Listener(on_press=self._on_key_press)
        ms_listener = mouse.Listener(on_click=self._on_mouse_click)
        kb_listener.start()
        ms_listener.start()

        # Block until quit
        try:
            while self._running:
                time.sleep(0.25)
        except KeyboardInterrupt:
            self.quit()
        finally:
            kb_listener.stop()
            ms_listener.stop()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WD2 Input Logger — passive playstyle tracker")
    parser.add_argument(
        "--player", "-p", default="",
        help="Your player name (embedded in session JSON)")
    parser.add_argument(
        "--config", "-c", default="",
        help="Path to custom keybinds JSON (default: keybinds.json)")
    args = parser.parse_args()

    if args.config:
        global CONFIG_PATH
        CONFIG_PATH = Path(args.config)

    logger = InputLogger(player_name=args.player)
    logger.run()


if __name__ == "__main__":
    main()
