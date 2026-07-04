"""
ocr_capture.py — Watch Dogs 2 OCR Screen Capture Module
---------------------------------------------------------
Captures designated screen regions, runs Tesseract OCR on them,
extracts numeric/text gameplay stats, and saves timestamped JSON entries.

WORKFLOW:
  1. Run with --calibrate to define screen regions by clicking+dragging
  2. Run normally to start the capture loop (auto-detects mission-end screens)
  3. Press F8 at any time to force-capture the current screen
  4. Press Escape or close to stop

OUTPUTS:
  sessions/ocr_YYYYMMDD_HHMMSS.json   — one file per captured screen
  ocr_regions.json                     — saved region calibrations

USAGE:
  python ocr_capture.py --calibrate          # define regions interactively
  python ocr_capture.py                      # start capture loop
  python ocr_capture.py --watch 3            # poll every 3 seconds
  python ocr_capture.py --once               # one-shot capture + exit
  python ocr_capture.py --preview            # show what the last capture saw
  python ocr_capture.py --test-ocr image.png # test OCR on an existing image

NOTE: Tesseract must be installed.
  Windows installer: https://github.com/UB-Mannheim/tesseract/wiki
  Default path auto-detected: C:/Program Files/Tesseract-OCR/tesseract.exe
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── ANSI colours ──────────────────────────────────────────────────────────────
try:
    import ctypes
    ctypes.windll.kernel32.SetConsoleMode(
        ctypes.windll.kernel32.GetStdHandle(-11), 7)
except Exception:
    pass

# Force UTF-8 output so Unicode box-drawing chars (◆ ─ ✓ ►) don't crash
# on Windows terminals that default to cp1252.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CYAN   = "\033[96m";  ORANGE = "\033[93m";  GREEN  = "\033[92m"
RED    = "\033[91m";  PURPLE = "\033[95m";  DIM    = "\033[2m"
BOLD   = "\033[1m";   RESET  = "\033[0m"

# ─────────────────────────────────────────────────────────────────────────────
#  PATHS & CONFIG
# ─────────────────────────────────────────────────────────────────────────────
HERE         = Path(__file__).parent
SESSIONS_DIR = HERE / "sessions"
REGIONS_FILE = HERE / "ocr_regions.json"
CAPTURES_DIR = HERE / "captures"

SESSIONS_DIR.mkdir(exist_ok=True)
CAPTURES_DIR.mkdir(exist_ok=True)

# Default Tesseract path on Windows (auto-detected)
TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\{user}\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]

# ─────────────────────────────────────────────────────────────────────────────
#  REGION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Region:
    name:        str           # e.g. "kills"
    label:       str           # human label e.g. "Kills"
    stat_type:   str           # what WD2 stat this maps to
    left:        int           # screen coords
    top:         int
    width:       int
    height:      int
    value_type:  str = "int"   # "int" | "float" | "bool" | "text"
    hint:        str = ""      # what to look for (regex or keyword)
    preprocess:  str = "auto"  # "auto"|"digits"|"dark_bg"|"light_bg"|"thresh"

    def to_mss_dict(self) -> dict:
        return {"left": self.left, "top": self.top,
                "width": self.width, "height": self.height}


# ── Built-in region templates (calibrate to override) ────────────────────────
# These are approximate; run --calibrate to set exact coords for YOUR setup.

REGION_TEMPLATES: list[dict] = [
    # Mission-end summary screen
    {"name": "kills",         "label": "Kills",            "stat_type": "combat",
     "left": 860, "top": 310, "width": 160, "height": 40,
     "value_type": "int",   "hint": r"\d+",      "preprocess": "digits"},

    {"name": "headshots",     "label": "Headshots",        "stat_type": "combat",
     "left": 860, "top": 360, "width": 160, "height": 40,
     "value_type": "int",   "hint": r"\d+",      "preprocess": "digits"},

    {"name": "headshot_pct",  "label": "Headshot %",       "stat_type": "combat",
     "left": 860, "top": 410, "width": 160, "height": 40,
     "value_type": "float", "hint": r"\d+\.?\d*", "preprocess": "digits"},

    {"name": "hacks",         "label": "Hacks Performed",  "stat_type": "hacking",
     "left": 860, "top": 460, "width": 160, "height": 40,
     "value_type": "int",   "hint": r"\d+",      "preprocess": "digits"},

    {"name": "vehicles",      "label": "Vehicles Stolen",  "stat_type": "driving",
     "left": 860, "top": 510, "width": 160, "height": 40,
     "value_type": "int",   "hint": r"\d+",      "preprocess": "digits"},

    {"name": "alerts",        "label": "Alerts Triggered", "stat_type": "chaos",
     "left": 860, "top": 560, "width": 160, "height": 40,
     "value_type": "int",   "hint": r"\d+",      "preprocess": "digits"},

    {"name": "detection",     "label": "Detected",         "stat_type": "stealth",
     "left": 860, "top": 610, "width": 300, "height": 40,
     "value_type": "bool",  "hint": "detected|undetected", "preprocess": "auto"},

    {"name": "mission_time",  "label": "Mission Time",     "stat_type": "meta",
     "left": 860, "top": 660, "width": 200, "height": 40,
     "value_type": "text",  "hint": r"\d+:\d+",  "preprocess": "digits"},

    {"name": "mission_name",  "label": "Mission Name",     "stat_type": "meta",
     "left": 200, "top": 100, "width": 700, "height": 70,
     "value_type": "text",  "hint": "",           "preprocess": "auto"},
]


def load_regions() -> list[Region]:
    """Load calibrated regions from file, or fall back to templates."""
    if REGIONS_FILE.exists():
        try:
            data = json.loads(REGIONS_FILE.read_text(encoding="utf-8"))
            regions = [Region(**r) for r in data]
            print(f"  {GREEN}Loaded {len(regions)} calibrated regions from {REGIONS_FILE.name}{RESET}")
            return regions
        except Exception as exc:
            print(f"  {ORANGE}Could not load {REGIONS_FILE.name}: {exc} — using templates{RESET}")
    return [Region(**t) for t in REGION_TEMPLATES]


def save_regions(regions: list[Region]):
    REGIONS_FILE.write_text(
        json.dumps([asdict(r) for r in regions], indent=2), encoding="utf-8")
    print(f"  {GREEN}Saved {len(regions)} regions to {REGIONS_FILE.name}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
#  TESSERACT SETUP
# ─────────────────────────────────────────────────────────────────────────────

def _find_tesseract() -> str:
    import shutil
    # Check PATH first
    if shutil.which("tesseract"):
        return "tesseract"
    # Check known Windows paths
    user = os.environ.get("USERNAME", "")
    for cand in TESSERACT_CANDIDATES:
        p = Path(cand.format(user=user))
        if p.exists():
            return str(p)
    return ""


def setup_tesseract() -> bool:
    """Configure pytesseract and return True if ready."""
    try:
        import pytesseract
        tess_path = _find_tesseract()
        if not tess_path:
            print(f"{RED}⚠  Tesseract not found.{RESET}")
            print(f"   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
            print(f"   Install to: C:\\Program Files\\Tesseract-OCR\\")
            return False
        pytesseract.pytesseract.tesseract_cmd = tess_path
        # Quick test
        ver = pytesseract.get_tesseract_version()
        print(f"  {GREEN}Tesseract {ver} ready ({tess_path}){RESET}")
        return True
    except Exception as exc:
        print(f"{RED}⚠  Tesseract setup failed: {exc}{RESET}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
#  IMAGE PREPROCESSING
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_image(img, mode: str = "auto"):
    """
    Prepare a PIL image for OCR.
    WD2 UI is typically white/orange text on dark backgrounds.
    """
    from PIL import Image, ImageFilter, ImageOps, ImageEnhance
    import io

    # Scale up for better OCR (Tesseract works best at ~300dpi equivalent)
    w, h = img.size
    scale = max(2, min(4, 600 // max(h, 1)))
    if scale > 1:
        img = img.resize((w * scale, h * scale), Image.LANCZOS)

    # Greyscale
    grey = img.convert("L")

    if mode == "digits":
        # High-contrast threshold — works well for numeric HUD readouts
        from PIL import ImageFilter
        grey = grey.filter(ImageFilter.SHARPEN)
        # Adaptive threshold: invert if background is dark (WD2 style)
        avg = sum(grey.getdata()) / (grey.width * grey.height)
        if avg < 128:
            grey = ImageOps.invert(grey)
        # Binary threshold
        return grey.point(lambda p: 255 if p > 140 else 0)

    elif mode == "dark_bg":
        grey = ImageOps.invert(grey)
        return grey.point(lambda p: 255 if p > 100 else 0)

    elif mode == "light_bg":
        return grey.point(lambda p: 255 if p > 120 else 0)

    elif mode == "thresh":
        avg = sum(grey.getdata()) / (grey.width * grey.height)
        threshold = max(80, min(180, int(avg * 0.8)))
        return grey.point(lambda p: 255 if p > threshold else 0)

    else:  # auto
        avg = sum(grey.getdata()) / (grey.width * grey.height)
        if avg < 100:   # dark background (WD2 default)
            grey = ImageOps.invert(grey)
        enhancer = ImageEnhance.Contrast(grey)
        grey = enhancer.enhance(2.5)
        return grey.point(lambda p: 255 if p > 128 else 0)


# ─────────────────────────────────────────────────────────────────────────────
#  OCR EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

# Tesseract configs
_TESS_DIGITS = "--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789.:% "
_TESS_TEXT   = "--psm 6 --oem 3"
_TESS_SINGLE = "--psm 8 --oem 3"


def _run_ocr(pil_img, region: Region) -> str:
    """Run Tesseract on a preprocessed image, return raw text."""
    import pytesseract
    processed = preprocess_image(pil_img, region.preprocess)

    if region.value_type in ("int", "float"):
        config = _TESS_DIGITS
    elif region.value_type == "bool":
        config = _TESS_TEXT
    else:
        config = _TESS_TEXT

    raw = pytesseract.image_to_string(processed, config=config)
    return raw.strip()


def _parse_value(raw_text: str, region: Region):
    """Parse the OCR'd text into a typed Python value."""
    text = raw_text.strip()
    if not text:
        return None

    if region.value_type == "int":
        nums = re.findall(r"\d+", text)
        if nums:
            return int(nums[0])
        return None

    elif region.value_type == "float":
        nums = re.findall(r"\d+\.?\d*", text)
        if nums:
            return float(nums[0])
        return None

    elif region.value_type == "bool":
        low = text.lower()
        if re.search(r'\bundetected\b', low) or re.search(r'\bno detect\b', low):
            return False   # not detected → good for stealth
        if re.search(r'\bdetected\b', low) or re.search(r'\bcompromised\b', low):
            return True    # detected → bad for stealth
        # "GHOST" as a lone word on the screen (WD2 end-screen badge)
        if re.fullmatch(r'ghost', low.strip()):
            return False
        return None


    else:
        return text if text else None


@dataclass
class CaptureResult:
    region_name:  str
    label:        str
    stat_type:    str
    raw_text:     str
    parsed_value: object
    confidence:   float    # 0.0 – 1.0 heuristic
    timestamp:    str


def _confidence(raw: str, parsed, region: Region) -> float:
    """Heuristic confidence: did we get something plausible?"""
    if parsed is None:
        return 0.0
    if region.value_type == "int":
        if isinstance(parsed, int) and 0 <= parsed <= 9999:
            return 0.85
        return 0.3
    if region.value_type == "float":
        if isinstance(parsed, float) and 0 <= parsed <= 100:
            return 0.85
        return 0.3
    if region.value_type == "bool":
        return 0.9
    return 0.7 if len(str(parsed)) > 1 else 0.4


# ─────────────────────────────────────────────────────────────────────────────
#  SCREEN CAPTURE
# ─────────────────────────────────────────────────────────────────────────────

def capture_region(region: Region,
                   save_image: bool = False) -> Optional[CaptureResult]:
    """Screenshot one region, run OCR, return result."""
    try:
        import mss
        from PIL import Image
        import io

        with mss.MSS() as sct:
            monitor = region.to_mss_dict()
            shot    = sct.grab(monitor)
            img     = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

        if save_image:
            img_path = CAPTURES_DIR / f"{region.name}_{_ts_file()}.png"
            img.save(str(img_path))

        raw   = _run_ocr(img, region)
        parsed = _parse_value(raw, region)
        conf  = _confidence(raw, parsed, region)

        return CaptureResult(
            region_name=region.name,
            label=region.label,
            stat_type=region.stat_type,
            raw_text=raw,
            parsed_value=parsed,
            confidence=conf,
            timestamp=_now_iso(),
        )

    except Exception as exc:
        print(f"  {RED}Capture error [{region.name}]: {exc}{RESET}")
        return None


def capture_all(regions: list[Region],
                save_images: bool = False,
                min_confidence: float = 0.0) -> list[CaptureResult]:
    """Capture all defined regions and return valid results."""
    results = []
    for r in regions:
        res = capture_region(r, save_image=save_images)
        if res and res.confidence >= min_confidence:
            results.append(res)
    return results


def capture_screen_to_file(regions: list[Region],
                            player_name: str = "",
                            save_images: bool = True) -> Path:
    """Full capture cycle → save JSON session entry."""
    ts_str  = _ts_file()
    results = capture_all(regions, save_images=save_images)

    # ── Build structured output ───────────────────────────────────────────────
    raw_values: dict = {}
    for res in results:
        raw_values[res.region_name] = {
            "value":       res.parsed_value,
            "raw_text":    res.raw_text,
            "confidence":  round(res.confidence, 2),
            "stat_type":   res.stat_type,
        }

    # ── Derive WD2 stats from captured values ─────────────────────────────────
    stats = _derive_stats(raw_values)

    # ── Get mission name ───────────────────────────────────────────────────────
    mission = ""
    if "mission_name" in raw_values:
        mission = str(raw_values["mission_name"].get("value") or "")

    entry = {
        "session_id":   str(uuid.uuid4()),
        "source":       "ocr_capture",
        "player_name":  player_name,
        "mission_name": mission,
        "captured_at":  _now_iso(),
        "stats":        stats,
        "raw_captures": raw_values,
        "capture_file": ts_str,
    }

    out_path = SESSIONS_DIR / f"ocr_{ts_str}.json"
    out_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return out_path


def _derive_stats(raw: dict) -> dict[str, int]:
    """
    Convert raw OCR captures into the 5 normalised stats (0-99).
    These are intentionally conservative — the stat_engine will blend them
    with other sources and renormalise.
    """
    _MISSING = object()

    def val(key: str, default=0):
        v = raw.get(key, {}).get("value", _MISSING)
        return default if v is _MISSING else v

    kills      = int(val("kills",       0))
    headshots  = int(val("headshots",   0))
    hs_pct     = float(val("headshot_pct", 0))
    hacks      = int(val("hacks",       0))
    vehicles   = int(val("vehicles",    0))
    alerts     = int(val("alerts",      0))
    detected   = val("detection",  None)  # True/False/None

    # Stealth: undetected bonus, low alerts bonus
    stealth_score = 50
    if detected is False:           stealth_score += 35   # ghost run
    elif detected is True:          stealth_score -= 20
    stealth_score -= min(alerts * 5, 30)
    stealth_score  = max(5, min(99, stealth_score))

    # Hacking: hacks performed, scaled generously
    hack_score = min(99, 20 + hacks * 4)

    # Combat: kills + headshot %
    combat_score = min(99, 20 + kills * 2 + int(hs_pct * 0.4))

    # Driving: vehicles stolen/used
    drive_score = min(99, 20 + vehicles * 8)

    # Chaos: alerts + kills blended
    chaos_score = min(99, 15 + alerts * 8 + kills * 1)

    return {
        "stealth": stealth_score,
        "hacking": hack_score,
        "combat":  combat_score,
        "driving": drive_score,
        "chaos":   chaos_score,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  CHANGE DETECTION  (auto-trigger on mission-end screens)
# ─────────────────────────────────────────────────────────────────────────────

class ScreenWatcher:
    """
    Monitors a sentinel region for significant brightness/content changes.
    When a change is detected (e.g. mission-end screen appearing),
    it triggers a full capture.
    """
    SENTINEL_REGION = Region(
        name="sentinel", label="Screen Sentinel", stat_type="meta",
        left=860, top=280, width=200, height=30,
        value_type="text", preprocess="auto"
    )

    def __init__(self, regions: list[Region], player_name: str = "",
                 poll_seconds: float = 2.0):
        self.regions      = regions
        self.player_name  = player_name
        self.poll_s       = poll_seconds
        self._last_hash   = None
        self._captures    = 0
        self._running     = False

    def _screen_hash(self) -> Optional[int]:
        """Quick perceptual hash of the sentinel region."""
        try:
            import mss
            from PIL import Image
            with mss.MSS() as sct:
                shot = sct.grab(self.SENTINEL_REGION.to_mss_dict())
                img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            grey = img.convert("L").resize((16, 8))
            pixels = list(grey.getdata())
            avg    = sum(pixels) / len(pixels)
            return sum(1 << i for i, p in enumerate(pixels) if p > avg)
        except Exception:
            return None

    def _changed(self) -> bool:
        h = self._screen_hash()
        if h is None:
            return False
        if self._last_hash is None:
            self._last_hash = h
            return False
        # Hamming distance on 128-bit perceptual hash
        diff  = bin(h ^ self._last_hash).count("1")
        self._last_hash = h
        return diff > 20   # threshold: >20 bits changed = new screen

    def run(self, stop_event: threading.Event):
        print(f"  {CYAN}Screen watcher running — polling every {self.poll_s}s{RESET}")
        print(f"  {DIM}Press F8 to force capture, Esc to stop{RESET}\n")
        while not stop_event.is_set():
            try:
                if self._changed():
                    print(f"\n  {GREEN}► Screen change detected — capturing!{RESET}")
                    # Small delay to let the UI settle
                    time.sleep(0.8)
                    out = capture_screen_to_file(
                        self.regions, self.player_name, save_images=True)
                    self._captures += 1
                    print(f"  {GREEN}✓  Capture #{self._captures} saved → {out.name}{RESET}\n")
            except Exception as exc:
                print(f"  {RED}Watcher error: {exc}{RESET}")
            time.sleep(self.poll_s)


# ─────────────────────────────────────────────────────────────────────────────
#  CALIBRATION UI
# ─────────────────────────────────────────────────────────────────────────────

def run_calibration(existing_regions: list[Region]) -> list[Region]:
    """
    Tkinter overlay: user draws rectangles over game regions.
    Each rectangle is tagged with a region name from the template list.
    """
    import tkinter as tk
    from tkinter import ttk, messagebox
    import mss
    from PIL import Image, ImageTk

    print(f"\n  {CYAN}CALIBRATION MODE{RESET}")
    print(f"  {DIM}A full-screen overlay will appear.")
    print(f"  Click+drag to mark each region. Press ENTER to confirm, ESC to cancel.{RESET}\n")

    # ── Grab current full screen ──────────────────────────────────────────────
    with mss.MSS() as sct:
        monitor = sct.monitors[1]   # primary monitor
        shot    = sct.grab(monitor)
        bg_img  = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    sw, sh = bg_img.size

    # Dim the screenshot for the overlay
    from PIL import ImageEnhance
    bg_dark = ImageEnhance.Brightness(bg_img).enhance(0.35)

    calibrated: list[Region] = []
    # Work through template list, one at a time
    templates_to_do = [Region(**t) for t in REGION_TEMPLATES]

    root = tk.Tk()
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="black")
    root.title("WD2 OCR Calibration")

    canvas = tk.Canvas(root, bg="black", cursor="crosshair",
                       highlightthickness=0)
    canvas.pack(fill="both", expand=True)

    # Draw background
    bg_photo = ImageTk.PhotoImage(bg_dark)
    canvas.create_image(0, 0, anchor="nw", image=bg_photo)

    # Draw existing regions as green overlays
    for r in existing_regions:
        canvas.create_rectangle(
            r.left, r.top, r.left + r.width, r.top + r.height,
            outline="#00ff88", width=1, dash=(4, 4))
        canvas.create_text(
            r.left + 4, r.top + 4,
            text=r.label, anchor="nw",
            fill="#00ff88", font=("Consolas", 9))

    # State
    state = {"idx": 0, "x0": 0, "y0": 0, "rect": None, "done": False}

    def current_template():
        if state["idx"] < len(templates_to_do):
            return templates_to_do[state["idx"]]
        return None

    def update_prompt():
        tmpl = current_template()
        canvas.delete("prompt")
        if tmpl:
            msg = (f"  [{state['idx']+1}/{len(templates_to_do)}]  "
                   f"Draw: {tmpl.label.upper()}  "
                   f"({tmpl.stat_type})  —  "
                   "Click & drag the region on screen  |  "
                   "SPACE = skip  |  ENTER = done  |  ESC = cancel")
        else:
            msg = "  All regions marked! Press ENTER to save, ESC to cancel."
        canvas.create_rectangle(0, 0, sw, 40,
                                 fill="#0a0a0f", outline="", tags="prompt")
        canvas.create_text(10, 20, anchor="w", text=msg,
                           fill="#ff6600", font=("Consolas", 11, "bold"),
                           tags="prompt")

    update_prompt()

    def on_press(event):
        state["x0"] = event.x
        state["y0"] = event.y
        if state["rect"]:
            canvas.delete(state["rect"])

    def on_drag(event):
        if state["rect"]:
            canvas.delete(state["rect"])
        state["rect"] = canvas.create_rectangle(
            state["x0"], state["y0"], event.x, event.y,
            outline="#ff6600", width=2, fill="#ff660022")

    def on_release(event):
        tmpl = current_template()
        if tmpl is None:
            return
        x0, y0 = min(state["x0"], event.x), min(state["y0"], event.y)
        x1, y1 = max(state["x0"], event.x), max(state["y0"], event.y)
        if abs(x1 - x0) < 10 or abs(y1 - y0) < 10:
            return   # too small, ignore

        # Save region
        new_r = Region(
            name=tmpl.name, label=tmpl.label, stat_type=tmpl.stat_type,
            left=x0, top=y0, width=x1-x0, height=y1-y0,
            value_type=tmpl.value_type, hint=tmpl.hint,
            preprocess=tmpl.preprocess)
        calibrated.append(new_r)

        # Draw confirmed region in orange
        canvas.create_rectangle(x0, y0, x1, y1,
                                 outline="#ff6600", width=2, fill="#ff660015")
        canvas.create_text(x0+4, y0+4, anchor="nw",
                           text=tmpl.label, fill="#ff6600",
                           font=("Consolas", 9, "bold"))

        state["idx"] += 1
        state["rect"] = None
        update_prompt()

    def on_key(event):
        if event.keysym == "space":
            # Skip this region (keep template default)
            tmpl = current_template()
            if tmpl:
                calibrated.append(tmpl)
                state["idx"] += 1
                update_prompt()
        elif event.keysym == "Return":
            state["done"] = True
            root.destroy()
        elif event.keysym == "Escape":
            root.destroy()

    canvas.bind("<ButtonPress-1>",   on_press)
    canvas.bind("<B1-Motion>",       on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    root.bind("<Key>",               on_key)
    root.focus_set()
    root.mainloop()

    if state["done"] and calibrated:
        # Fill any un-drawn regions with template defaults
        calibrated_names = {r.name for r in calibrated}
        for tmpl in templates_to_do:
            if tmpl.name not in calibrated_names:
                calibrated.append(tmpl)
        save_regions(calibrated)
        return calibrated

    print(f"  {ORANGE}Calibration cancelled — keeping previous regions.{RESET}")
    return existing_regions


# ─────────────────────────────────────────────────────────────────────────────
#  PREVIEW / TEST HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def preview_capture(regions: list[Region]):
    """Take one capture, display a rich table of what was found."""
    print(f"\n  {ORANGE}◆ OCR PREVIEW CAPTURE  ─────────────────────────────────────────{RESET}")
    results = capture_all(regions, save_images=True)

    if not results:
        print(f"  {RED}No results — check region coordinates and Tesseract setup.{RESET}")
        return

    print(f"  {'REGION':<18}  {'TYPE':<8}  {'VALUE':<14}  {'CONF':>5}  RAW TEXT")
    print(f"  {'─'*18}  {'─'*8}  {'─'*14}  {'─'*5}  {'─'*30}")
    for r in results:
        conf_col = GREEN if r.confidence > 0.7 else (ORANGE if r.confidence > 0.4 else RED)
        val_str  = str(r.parsed_value)[:14] if r.parsed_value is not None else "(none)"
        raw_str  = r.raw_text[:30].replace("\n", " ")
        print(f"  {r.label:<18}  {r.stat_type:<8}  {val_str:<14}  "
              f"{conf_col}{r.confidence:>4.0%}{RESET}  {DIM}{raw_str}{RESET}")

    print(f"\n  {DIM}Screenshots saved to {CAPTURES_DIR}{RESET}")
    print(f"  {ORANGE}◆─────────────────────────────────────────────────────────────{RESET}\n")


def test_ocr_on_image(image_path: str, regions: list[Region]):
    """
    Run all region OCR patches against an existing screenshot file.
    Useful for tuning without needing the game running.
    """
    from PIL import Image
    import pytesseract

    img = Image.open(image_path)
    w, h = img.size
    print(f"\n  {ORANGE}◆ OCR TEST ON IMAGE: {image_path}  ({w}x{h}){RESET}")
    print(f"  {'REGION':<18}  {'VALUE':<14}  {'CONF':>5}  RAW")
    print(f"  {'─'*18}  {'─'*14}  {'─'*5}  {'─'*30}")

    for region in regions:
        # Crop the region from the image
        box = (region.left, region.top,
               region.left + region.width, region.top + region.height)
        try:
            cropped = img.crop(box)
            raw     = _run_ocr(cropped, region)
            parsed  = _parse_value(raw, region)
            conf    = _confidence(raw, parsed, region)
            conf_col = GREEN if conf > 0.7 else (ORANGE if conf > 0.4 else RED)
            val_str  = str(parsed)[:14] if parsed is not None else "(none)"
            raw_str  = raw[:30].replace("\n", " ")
            print(f"  {region.label:<18}  {val_str:<14}  "
                  f"{conf_col}{conf:>4.0%}{RESET}  {DIM}{raw_str}{RESET}")
        except Exception as exc:
            print(f"  {RED}{region.label:<18}  ERROR: {exc}{RESET}")

    print(f"\n  {ORANGE}◆──────────────────────────────────────────────────────────{RESET}\n")


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _ts_file() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────────────
#  CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="WD2 OCR Capture — screenshot + extract gameplay stats")
    parser.add_argument("--calibrate", "-c", action="store_true",
                        help="Open calibration overlay to define screen regions")
    parser.add_argument("--preview",   "-p", action="store_true",
                        help="Take one capture, print OCR results and exit")
    parser.add_argument("--once",            action="store_true",
                        help="Capture once, save JSON, and exit")
    parser.add_argument("--watch",     "-w", type=float, default=0,
                        metavar="SECONDS",
                        help="Poll every N seconds for screen changes (default: off)")
    parser.add_argument("--player",          default="",
                        help="Player name to embed in JSON output")
    parser.add_argument("--test-ocr",        default="", metavar="IMAGE",
                        help="Test OCR on an existing screenshot file")
    parser.add_argument("--save-images",     action="store_true",
                        help="Save each captured region as a PNG in captures/")
    args = parser.parse_args()

    print(f"\n  {BOLD}{ORANGE}◆ WD2 OCR CAPTURE  ─────────────────────────────────────────────{RESET}")

    # ── Tesseract check ───────────────────────────────────────────────────────
    if not args.calibrate:
        if not setup_tesseract():
            sys.exit(1)

    # ── Load regions ──────────────────────────────────────────────────────────
    regions = load_regions()

    # ── Dispatch ──────────────────────────────────────────────────────────────
    if args.calibrate:
        regions = run_calibration(regions)

    elif args.test_ocr:
        test_ocr_on_image(args.test_ocr, regions)

    elif args.preview:
        preview_capture(regions)

    elif args.once:
        out = capture_screen_to_file(regions, args.player,
                                     save_images=args.save_images)
        print(f"\n  {GREEN}✓  Saved → {out}{RESET}\n")

    elif args.watch > 0:
        # ── F8 force-capture hotkey in background ─────────────────────────────
        try:
            from pynput import keyboard as kb
            stop = threading.Event()

            def on_key(key):
                try:
                    from pynput.keyboard import Key
                    if key == Key.f8:
                        print(f"\n  {CYAN}F8 pressed — force capture!{RESET}")
                        out = capture_screen_to_file(regions, args.player,
                                                     save_images=True)
                        print(f"  {GREEN}✓  {out.name}{RESET}\n")
                    elif key == Key.esc:
                        stop.set()
                        return False
                except Exception:
                    pass

            listener = kb.Listener(on_press=on_key)
            listener.start()
        except ImportError:
            stop = threading.Event()
            listener = None
            print(f"  {DIM}(pynput not available — use Ctrl+C to stop){RESET}")

        watcher = ScreenWatcher(regions, args.player, poll_seconds=args.watch)
        watcher_thread = threading.Thread(
            target=watcher.run, args=(stop,), daemon=True)
        watcher_thread.start()

        print(f"  {DIM}Watching for screen changes...  F8=Force capture  Esc=Stop{RESET}\n")
        try:
            while not stop.is_set():
                time.sleep(0.25)
        except KeyboardInterrupt:
            stop.set()

        if listener:
            listener.stop()
        print(f"\n  {DIM}Watcher stopped. {watcher._captures} captures saved.{RESET}\n")

    else:
        parser.print_help()
        print(f"\n  {DIM}Quick start:{RESET}")
        print(f"    python ocr_capture.py --calibrate")
        print(f"    python ocr_capture.py --watch 2 --player Atharva")
        print(f"    python ocr_capture.py --preview")


if __name__ == "__main__":
    main()
