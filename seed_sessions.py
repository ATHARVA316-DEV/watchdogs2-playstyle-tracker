# seed_sessions.py — populate sessions/ with realistic test data
# Run once to get a multi-session dataset before wiring up real capture.
import json, uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta

SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

def iso(offset_hours=0):
    return (datetime.now(timezone.utc) - timedelta(hours=offset_hours)).isoformat()

MANUAL_SESSIONS = [
    # oldest → newest
    {
        "session_id": str(uuid.uuid4()), "source": "manual_tag",
        "player_name": "Atharva", "mission_name": "Haum Sweet Haum",
        "session_start": iso(48), "session_end": iso(47),
        "duration_minutes": 55, "playstyle": "Hacker-first",
        "archetype": "Digital Anarchist", "self_rated_overall": 78,
        "stats": {"stealth":60,"hacking":82,"combat":50,"driving":55,"chaos":75},
        "notable_events": ["Mass hack event","No alerts triggered"],
        "notes": "Hacked everything, barely fired a shot.", "tagged_at": iso(47),
    },
    {
        "session_id": str(uuid.uuid4()), "source": "manual_tag",
        "player_name": "Atharva", "mission_name": "Power to the Sheeple",
        "session_start": iso(36), "session_end": iso(35),
        "duration_minutes": 40, "playstyle": "Stealth",
        "archetype": "Ghost", "self_rated_overall": 74,
        "stats": {"stealth":78,"hacking":65,"combat":28,"driving":45,"chaos":22},
        "notable_events": ["No alerts triggered","Completed without kills"],
        "notes": "Ghost run, zero detections.", "tagged_at": iso(35),
    },
    {
        "session_id": str(uuid.uuid4()), "source": "manual_tag",
        "player_name": "Atharva", "mission_name": "Motherload (main story)",
        "session_start": iso(24), "session_end": iso(23),
        "duration_minutes": 70, "playstyle": "Mixed",
        "archetype": "Digital Anarchist", "self_rated_overall": 83,
        "stats": {"stealth":58,"hacking":88,"combat":60,"driving":72,"chaos":80},
        "notable_events": ["Mass hack event","Went loud at some point"],
        "notes": "Chaos endgame but hacking first.", "tagged_at": iso(23),
    },
    {
        "session_id": str(uuid.uuid4()), "source": "manual_tag",
        "player_name": "Atharva", "mission_name": "Open world grind",
        "session_start": iso(12), "session_end": iso(11),
        "duration_minutes": 90, "playstyle": "Driver-centric",
        "archetype": "Wheelman", "self_rated_overall": 76,
        "stats": {"stealth":42,"hacking":55,"combat":48,"driving":89,"chaos":60},
        "notable_events": ["High-speed police chase"],
        "notes": "Spent most of the session in vehicles.", "tagged_at": iso(11),
    },
]

INPUT_SESSIONS = [
    {
        "session_id": str(uuid.uuid4()), "source": "input_log",
        "player_name": "Atharva", "mission_name": "",
        "session_start": iso(6), "session_end": iso(5),
        "duration_seconds": 3240, "duration_minutes": 54,
        "stats": {"stealth":55,"hacking":86,"combat":48,"driving":62,"chaos":74},
        "self_rated_overall": 80,
        "archetype": "Digital Anarchist",
        "state_time_seconds": {"idle":120,"stealth":780,"hacking":1500,"combat":480,"driving":360},
        "key_event_counts": {"e":280,"w":820,"a":410,"s":390,"d":390,
                             "mouse_left":62,"mouse_right":85,"r":18,"q":44,"c":67},
        "action_counts": {"hack":280,"move_forward":820,"fire_weapon":62,"crouch":67,"cover":44},
        "mouse_clicks": {"left":62,"right":85},
        "tagged_at": iso(5),
    },
    {
        "session_id": str(uuid.uuid4()), "source": "input_log",
        "player_name": "Atharva", "mission_name": "",
        "session_start": iso(2), "session_end": iso(1),
        "duration_seconds": 2700, "duration_minutes": 45,
        "stats": {"stealth":62,"hacking":90,"combat":45,"driving":68,"chaos":82},
        "self_rated_overall": 84,
        "archetype": "Digital Anarchist",
        "state_time_seconds": {"idle":90,"stealth":600,"hacking":1620,"combat":270,"driving":120},
        "key_event_counts": {"e":320,"w":700,"a":350,"s":330,"d":330,
                             "mouse_left":38,"mouse_right":70,"r":10,"q":55,"c":80},
        "action_counts": {"hack":320,"move_forward":700,"fire_weapon":38,"crouch":80,"cover":55},
        "mouse_clicks": {"left":38,"right":70},
        "tagged_at": iso(1),
    },
]

# Write manual sessions (append to today's file)
manual_path = SESSIONS_DIR / f"manual_seed.json"
existing = []
if manual_path.exists():
    existing = json.loads(manual_path.read_text(encoding="utf-8"))
manual_path.write_text(json.dumps(existing + MANUAL_SESSIONS, indent=2), encoding="utf-8")
print(f"Wrote {len(MANUAL_SESSIONS)} manual sessions → {manual_path.name}")

# Write input sessions (one file each)
for s in INPUT_SESSIONS:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = SESSIONS_DIR / f"input_{s['session_id'][:8]}.json"
    fname.write_text(json.dumps(s, indent=2), encoding="utf-8")
    print(f"Wrote input session  → {fname.name}")

print(f"\nTotal new sessions: {len(MANUAL_SESSIONS) + len(INPUT_SESSIONS)}")
print("Run: python -X utf8 stat_engine.py --player Atharva")
