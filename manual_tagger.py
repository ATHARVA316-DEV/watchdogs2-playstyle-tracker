"""
manual_tagger.py — Watch Dogs 2 Manual Session Tagger
------------------------------------------------------
A dark-themed Tkinter UI for self-reporting your WD2 session stats
at the end of a play session.

Usage:
    python manual_tagger.py

Output:
    Appends a JSON entry to  sessions/manual_YYYYMMDD.json
    Each entry matches the schema consumed by stat_engine.py

Hotkey:
    Ctrl+Enter  →  Save session
    Escape      →  Cancel / close
"""

import json
import os
import sys
import uuid
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timezone
from pathlib import Path

# ── Output directory ──────────────────────────────────────────────────────────
HERE       = Path(__file__).parent
SESSIONS_DIR = HERE / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# ── Colour palette (DedSec / cTOS) ───────────────────────────────────────────
C = {
    "bg":          "#0a0a0f",
    "bg2":         "#111118",
    "bg3":         "#1a1a26",
    "surface":     "#16161f",
    "border":      "#2a2a3d",
    "border_hi":   "#ff6600",
    "orange":      "#ff6600",
    "orange_dim":  "#cc4400",
    "cyan":        "#00d2ff",
    "cyan_dim":    "#008fb0",
    "green":       "#00ff88",
    "purple":      "#cc00ff",
    "text":        "#e8e8f0",
    "text_dim":    "#7070a0",
    "text_muted":  "#404060",
    "gold":        "#ffd700",
    "red":         "#ff3030",
}

FONT_TITLE  = ("Consolas", 16, "bold")
FONT_HEAD   = ("Consolas", 10, "bold")
FONT_BODY   = ("Consolas", 9)
FONT_SMALL  = ("Consolas", 8)
FONT_LABEL  = ("Consolas", 9, "bold")
FONT_LARGE  = ("Consolas", 28, "bold")
FONT_MONO   = ("Consolas", 8)

ARCHETYPES = [
    "Ghost",
    "Digital Anarchist",
    "Wheelman",
    "Enforcer",
    "Balanced Operative",
    "Pacifist",
    "Opportunist",
]

PLAYSTYLE_OPTS = ["Stealth", "Aggressive", "Mixed", "Hacker-first", "Driver-centric"]

EVENTS = [
    "No alerts triggered",
    "Went loud at some point",
    "High-speed police chase",
    "Drone/RC-only run",
    "Mass hack event",
    "Multiple Tier-3 alerts",
    "Completed without kills",
    "Boss fight / heist",
    "Stuck to side missions",
    "Open-world chaos run",
]

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def today_filename() -> Path:
    return SESSIONS_DIR / f"manual_{datetime.now().strftime('%Y%m%d')}.json"

def load_today_sessions() -> list:
    p = today_filename()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []

def save_session(entry: dict):
    sessions = load_today_sessions()
    sessions.append(entry)
    today_filename().write_text(
        json.dumps(sessions, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def session_output_path() -> str:
    return str(today_filename())

# ─────────────────────────────────────────────────────────────────────────────
#  CUSTOM WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

class DarkScale(tk.Frame):
    """A labelled horizontal slider with live numeric readout."""

    def __init__(self, parent, label: str, from_=0, to=99,
                 accent=None, **kwargs):
        super().__init__(parent, bg=C["bg2"], **kwargs)
        self._accent = accent or C["cyan"]
        self._var = tk.IntVar(value=(from_ + to) // 2)

        lbl = tk.Label(self, text=label, font=FONT_LABEL,
                       fg=self._accent, bg=C["bg2"], anchor="w", width=10)
        lbl.pack(side="left", padx=(0, 8))

        self._readout = tk.Label(self, text=str(self._var.get()),
                                 font=FONT_LARGE, fg=self._accent,
                                 bg=C["bg2"], width=3, anchor="e")
        self._readout.pack(side="right", padx=(8, 0))

        self._scale = tk.Scale(
            self, variable=self._var,
            from_=from_, to=to, orient="horizontal",
            showvalue=False, length=260,
            bg=C["bg2"], fg=self._accent,
            activebackground=self._accent,
            highlightthickness=0,
            troughcolor=C["bg3"],
            sliderlength=18,
            command=self._on_change,
        )
        self._scale.pack(side="left", fill="x", expand=True)
        self._var.trace_add("write", lambda *_: self._on_change(None))

    def _on_change(self, _val):
        v = self._var.get()
        self._readout.config(text=str(v))
        # colour shift: low=cyan, mid=gold, high=red/orange
        if v < 40:
            colour = C["cyan"]
        elif v < 70:
            colour = C["gold"]
        else:
            colour = C["orange"]
        self._readout.config(fg=colour)

    @property
    def value(self) -> int:
        return self._var.get()

    def set(self, v: int):
        self._var.set(v)


class ChecklistFrame(tk.LabelFrame):
    """A scrollable checklist of optional event flags."""

    def __init__(self, parent, items: list, **kwargs):
        bg_color = kwargs.pop("bg", C["bg2"])
        super().__init__(parent,
                         text=" Notable Events ",
                         font=FONT_LABEL,
                         fg=C["cyan"], bg=bg_color,
                         bd=1, relief="flat",
                         highlightbackground=C["border"],
                         highlightthickness=1,
                         **kwargs)
        self._vars: dict[str, tk.BooleanVar] = {}
        for item in items:
            var = tk.BooleanVar(value=False)
            self._vars[item] = var
            cb = tk.Checkbutton(
                self, text=item, variable=var,
                font=FONT_BODY,
                fg=C["text"], bg=bg_color,
                selectcolor=C["bg3"],
                activebackground=bg_color,
                activeforeground=C["orange"],
                anchor="w", padx=6, pady=2,
            )
            cb.pack(fill="x", padx=4)


    @property
    def selected(self) -> list[str]:
        return [k for k, v in self._vars.items() if v.get()]


class TagDropdown(tk.Frame):
    """Label + OptionMenu combo."""

    def __init__(self, parent, label: str, options: list,
                 accent=None, **kwargs):
        super().__init__(parent, bg=C["bg2"], **kwargs)
        self._var = tk.StringVar(value=options[0])
        self._accent = accent or C["orange"]

        tk.Label(self, text=label, font=FONT_LABEL,
                 fg=self._accent, bg=C["bg2"], anchor="w", width=14
                 ).pack(side="left", padx=(0, 8))

        om = tk.OptionMenu(self, self._var, *options)
        om.config(
            font=FONT_BODY, bg=C["bg3"], fg=C["text"],
            activebackground=C["border_hi"], activeforeground="#fff",
            highlightthickness=0, bd=0, relief="flat",
            indicatoron=True, width=20,
        )
        om["menu"].config(
            bg=C["bg3"], fg=C["text"],
            activebackground=C["border_hi"], activeforeground="#fff",
            font=FONT_BODY,
        )
        om.pack(side="left", fill="x", expand=True)

    @property
    def value(self) -> str:
        return self._var.get()


class SessionHistoryPanel(tk.Frame):
    """Shows today's saved sessions at the bottom."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        tk.Label(self, text="▸ TODAY'S SESSIONS", font=FONT_HEAD,
                 fg=C["text_dim"], bg=C["bg"], anchor="w"
                 ).pack(fill="x", padx=12, pady=(6, 2))

        self._text = tk.Text(
            self, height=5, state="disabled",
            bg=C["bg2"], fg=C["text_dim"],
            font=FONT_MONO, bd=0, relief="flat",
            insertbackground=C["orange"],
            selectbackground=C["border_hi"],
        )
        self._text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.refresh()

    def refresh(self):
        sessions = load_today_sessions()
        self._text.config(state="normal")
        self._text.delete("1.0", "end")
        if not sessions:
            self._text.insert("end", "  No sessions logged today yet.\n")
        for i, s in enumerate(sessions, 1):
            ts  = s.get("session_end", s.get("tagged_at", "?"))[:19].replace("T", " ")
            arc = s.get("archetype", "?")
            ov  = s.get("self_rated_overall", "?")
            mis = s.get("mission_name", "—")
            self._text.insert("end",
                f"  [{i:02d}] {ts}  |  {arc:<22}  |  OVR {ov:>2}  |  {mis}\n")
        self._text.config(state="disabled")


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────

class ManualTaggerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("WD2 Manual Session Tagger  |  cTOS v3.1")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self._session_start = now_iso()

        # ── icon (pure Tk, no file dependency) ───────────────────────────────
        try:
            self.iconbitmap(default="")          # clear default icon
        except Exception:
            pass

        self._build_ui()
        self._center()

        # keybinds
        self.bind("<Control-Return>", lambda _e: self._save())
        self.bind("<Escape>",         lambda _e: self.destroy())

    # ── layout ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── header bar ───────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg=C["orange"], height=4)
        hdr.pack(fill="x")

        title_row = tk.Frame(self, bg=C["bg"])
        title_row.pack(fill="x", padx=16, pady=(12, 4))

        tk.Label(title_row,
                 text="◆  DEDSEC SESSION LOG",
                 font=FONT_TITLE, fg=C["orange"], bg=C["bg"]
                 ).pack(side="left")

        self._clock_lbl = tk.Label(title_row, text="",
                                   font=FONT_SMALL, fg=C["text_muted"], bg=C["bg"])
        self._clock_lbl.pack(side="right")
        self._tick_clock()

        tk.Label(self,
                 text="  Fill in after each Watch Dogs 2 session  ·  Ctrl+Enter to save  ·  Esc to cancel",
                 font=FONT_SMALL, fg=C["text_muted"], bg=C["bg"]
                 ).pack(anchor="w", padx=16)

        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.pack(fill="x", padx=12, pady=8)

        # ── main two-column body ──────────────────────────────────────────────
        body = tk.Frame(self, bg=C["bg"])
        body.pack(fill="both", expand=True, padx=12)

        left  = tk.Frame(body, bg=C["bg2"], padx=12, pady=10)
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = tk.Frame(body, bg=C["bg2"], padx=12, pady=10)
        right.pack(side="left", fill="both", expand=True, padx=(6, 0))

        # ────────────────────── LEFT COLUMN ──────────────────────────────────

        tk.Label(left, text="SESSION INFO", font=FONT_HEAD,
                 fg=C["cyan"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 8))

        # player name
        self._add_entry_row(left, "Player name", "player_name", C["orange"])

        # mission / activity
        self._add_entry_row(left, "Mission / activity", "mission_name", C["cyan"])

        tk.Frame(left, bg=C["border"], height=1).pack(fill="x", pady=8)

        # duration
        tk.Label(left, text="SESSION DURATION", font=FONT_HEAD,
                 fg=C["cyan"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 6))

        dur_row = tk.Frame(left, bg=C["bg2"])
        dur_row.pack(fill="x", pady=2)
        tk.Label(dur_row, text="Duration (minutes)", font=FONT_LABEL,
                 fg=C["text_dim"], bg=C["bg2"], width=20, anchor="w"
                 ).pack(side="left")
        self._duration_var = tk.IntVar(value=30)
        dur_spin = tk.Spinbox(
            dur_row, from_=1, to=480, textvariable=self._duration_var,
            width=5, font=FONT_BODY,
            bg=C["bg3"], fg=C["gold"], insertbackground=C["orange"],
            bd=0, relief="flat", buttonbackground=C["bg3"],
        )
        dur_spin.pack(side="left")

        tk.Frame(left, bg=C["border"], height=1).pack(fill="x", pady=8)

        # dropdowns
        tk.Label(left, text="PLAYSTYLE & ARCHETYPE", font=FONT_HEAD,
                 fg=C["cyan"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 6))

        self._playstyle_dd = TagDropdown(left, "Playstyle", PLAYSTYLE_OPTS,
                                         accent=C["orange"])
        self._playstyle_dd.pack(fill="x", pady=3)

        self._archetype_dd = TagDropdown(left, "Archetype", ARCHETYPES,
                                         accent=C["purple"])
        self._archetype_dd.pack(fill="x", pady=3)

        tk.Frame(left, bg=C["border"], height=1).pack(fill="x", pady=8)

        # notes
        tk.Label(left, text="NOTES  (optional)", font=FONT_HEAD,
                 fg=C["cyan"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 4))

        self._notes = tk.Text(
            left, height=4, font=FONT_BODY,
            bg=C["bg3"], fg=C["text"],
            insertbackground=C["orange"],
            bd=0, relief="flat", padx=6, pady=6,
            wrap="word",
        )
        self._notes.pack(fill="x")
        self._notes.insert("end", "")

        # ────────────────────── RIGHT COLUMN ─────────────────────────────────

        tk.Label(right, text="STAT RATINGS  (0 – 99)", font=FONT_HEAD,
                 fg=C["cyan"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 10))

        self._stealth = DarkScale(right, "STEALTH",  accent=C["cyan"])
        self._stealth.pack(fill="x", pady=4)

        self._hacking = DarkScale(right, "HACKING",  accent=C["green"])
        self._hacking.pack(fill="x", pady=4)

        self._combat  = DarkScale(right, "COMBAT",   accent=C["red"])
        self._combat.pack(fill="x", pady=4)

        self._driving = DarkScale(right, "DRIVING",  accent=C["gold"])
        self._driving.pack(fill="x", pady=4)

        self._chaos   = DarkScale(right, "CHAOS",    accent=C["orange"])
        self._chaos.pack(fill="x", pady=4)

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", pady=8)

        # overall self-rating
        tk.Label(right, text="OVERALL (self-rated)", font=FONT_HEAD,
                 fg=C["gold"], bg=C["bg2"]
                 ).pack(anchor="w", pady=(0, 4))

        self._overall = DarkScale(right, "OVERALL", from_=1, to=99,
                                  accent=C["gold"])
        self._overall.set(75)
        self._overall.pack(fill="x", pady=4)

        tk.Frame(right, bg=C["border"], height=1).pack(fill="x", pady=8)

        # event checklist
        self._events = ChecklistFrame(right, EVENTS, bg=C["bg2"])
        self._events.pack(fill="x")

        # ────────────────────── BUTTONS ───────────────────────────────────────
        sep2 = tk.Frame(self, bg=C["border"], height=1)
        sep2.pack(fill="x", padx=12, pady=(10, 0))

        btn_row = tk.Frame(self, bg=C["bg"])
        btn_row.pack(fill="x", padx=12, pady=10)

        self._status_lbl = tk.Label(btn_row, text="", font=FONT_SMALL,
                                    fg=C["green"], bg=C["bg"], anchor="w")
        self._status_lbl.pack(side="left")

        tk.Button(
            btn_row, text="✕  CANCEL",
            font=FONT_LABEL,
            bg=C["bg3"], fg=C["text_dim"],
            activebackground=C["bg3"], activeforeground=C["text"],
            bd=0, relief="flat", padx=12, pady=6,
            cursor="hand2",
            command=self.destroy,
        ).pack(side="right", padx=(6, 0))

        tk.Button(
            btn_row, text="⟳  NEW SESSION",
            font=FONT_LABEL,
            bg=C["bg3"], fg=C["cyan_dim"],
            activebackground=C["bg3"], activeforeground=C["cyan"],
            bd=0, relief="flat", padx=12, pady=6,
            cursor="hand2",
            command=self._reset,
        ).pack(side="right", padx=(6, 0))

        self._save_btn = tk.Button(
            btn_row, text="◆  SAVE SESSION   Ctrl+↵",
            font=FONT_LABEL,
            bg=C["orange"], fg="#000",
            activebackground=C["orange_dim"], activeforeground="#000",
            bd=0, relief="flat", padx=16, pady=6,
            cursor="hand2",
            command=self._save,
        )
        self._save_btn.pack(side="right")

        # ── bottom history panel ──────────────────────────────────────────────
        sep3 = tk.Frame(self, bg=C["border"], height=1)
        sep3.pack(fill="x", padx=12)

        self._history = SessionHistoryPanel(self)
        self._history.pack(fill="x")

        # ── bottom accent bar ────────────────────────────────────────────────
        tk.Frame(self, bg=C["cyan"], height=3).pack(fill="x")

    # ── helpers ───────────────────────────────────────────────────────────────

    def _add_entry_row(self, parent, label: str, attr_name: str, accent: str):
        row = tk.Frame(parent, bg=C["bg2"])
        row.pack(fill="x", pady=3)
        tk.Label(row, text=label, font=FONT_LABEL, fg=accent,
                 bg=C["bg2"], anchor="w", width=18
                 ).pack(side="left")
        var = tk.StringVar()
        e = tk.Entry(row, textvariable=var, font=FONT_BODY,
                     bg=C["bg3"], fg=C["text"],
                     insertbackground=accent,
                     bd=0, relief="flat",
                     highlightthickness=1,
                     highlightcolor=accent,
                     highlightbackground=C["border"])
        e.pack(side="left", fill="x", expand=True, padx=(0, 2))
        setattr(self, f"_{attr_name}_var", var)

    def _center(self):
        self.update_idletasks()
        w, h   = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _tick_clock(self):
        now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        self._clock_lbl.config(text=f"[ {now} ]")
        self.after(1000, self._tick_clock)

    # ── actions ───────────────────────────────────────────────────────────────

    def _build_entry(self) -> dict:
        """Assemble the session JSON from current UI state."""
        player_name  = self._player_name_var.get().strip() or "Unknown"
        mission_name = self._mission_name_var.get().strip() or "—"
        notes        = self._notes.get("1.0", "end").strip()

        return {
            "session_id":        str(uuid.uuid4()),
            "source":            "manual_tag",
            "player_name":       player_name,
            "mission_name":      mission_name,
            "session_start":     self._session_start,
            "session_end":       now_iso(),
            "duration_minutes":  self._duration_var.get(),
            "playstyle":         self._playstyle_dd.value,
            "archetype":         self._archetype_dd.value,
            "self_rated_overall": self._overall.value,
            "stats": {
                "stealth": self._stealth.value,
                "hacking": self._hacking.value,
                "combat":  self._combat.value,
                "driving": self._driving.value,
                "chaos":   self._chaos.value,
            },
            "notable_events":    self._events.selected,
            "notes":             notes,
            "tagged_at":         now_iso(),
        }

    def _save(self):
        """Validate and persist the current session."""
        entry = self._build_entry()

        if entry["player_name"] == "Unknown":
            self._player_name_var.set("")   # visual flash
            self._status_lbl.config(
                text="⚠  Enter a player name first.", fg=C["red"])
            return

        save_session(entry)

        out_path = session_output_path()
        self._status_lbl.config(
            text=f"✓  Saved → {os.path.basename(out_path)}", fg=C["green"])

        # preview the saved JSON in a popup
        preview = json.dumps(entry, indent=2)
        self._show_saved_popup(entry, preview)

        self._history.refresh()
        self._session_start = now_iso()   # ready for next session

    def _reset(self):
        """Clear all fields for a fresh session entry."""
        self._player_name_var.set("")
        self._mission_name_var.set("")
        self._notes.delete("1.0", "end")
        self._stealth.set(50)
        self._hacking.set(50)
        self._combat.set(50)
        self._driving.set(50)
        self._chaos.set(50)
        self._overall.set(75)
        self._session_start = now_iso()
        self._status_lbl.config(text="⟳  Reset. Ready for new session.", fg=C["cyan"])

    def _show_saved_popup(self, entry: dict, preview: str):
        """Non-blocking info popup with the saved JSON."""
        popup = tk.Toplevel(self)
        popup.title("Session Saved")
        popup.configure(bg=C["bg"])
        popup.resizable(False, False)
        popup.transient(self)

        # accent stripe
        tk.Frame(popup, bg=C["green"], height=3).pack(fill="x")

        tk.Label(popup,
                 text=f"✓  SESSION SAVED",
                 font=FONT_TITLE, fg=C["green"], bg=C["bg"]
                 ).pack(padx=20, pady=(12, 2))

        tk.Label(popup,
                 text=f"Operative: {entry['player_name']}  ·  "
                      f"Archetype: {entry['archetype']}  ·  "
                      f"Overall: {entry['self_rated_overall']}",
                 font=FONT_BODY, fg=C["text_dim"], bg=C["bg"]
                 ).pack(padx=20)

        tk.Label(popup, text=f"→  {session_output_path()}",
                 font=FONT_SMALL, fg=C["text_muted"], bg=C["bg"]
                 ).pack(padx=20, pady=(4, 10))

        txt = tk.Text(popup, height=16, width=56, font=FONT_MONO,
                      bg=C["bg2"], fg=C["cyan"],
                      insertbackground=C["orange"],
                      bd=0, relief="flat", padx=10, pady=8)
        txt.pack(padx=16, pady=(0, 8))
        txt.insert("end", preview)
        txt.config(state="disabled")

        tk.Button(popup, text="  CLOSE  ",
                  font=FONT_LABEL, bg=C["orange"], fg="#000",
                  activebackground=C["orange_dim"], activeforeground="#000",
                  bd=0, relief="flat", padx=12, pady=6,
                  cursor="hand2", command=popup.destroy
                  ).pack(pady=(0, 16))

        # center over parent
        popup.update_idletasks()
        px = self.winfo_x() + (self.winfo_width() - popup.winfo_width()) // 2
        py = self.winfo_y() + (self.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{px}+{py}")
        popup.grab_set()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = ManualTaggerApp()
    app.mainloop()
