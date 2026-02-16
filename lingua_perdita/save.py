"""JSON persistence for game state.

Saves the language seed + runtime state. On load, regenerates the
LanguageModel from the seed and restores currency/element/milestone state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from idleengine import GameRuntime

SAVE_DIR = Path.home() / ".lingua_perdita"
SAVE_FILE = SAVE_DIR / "save.json"
SAVE_VERSION = 1


def save_game(runtime: GameRuntime, seed: int) -> None:
    """Serialize current game state to JSON."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    state = runtime.get_state()

    data = {
        "version": SAVE_VERSION,
        "seed": seed,
        "time_elapsed": state.time_elapsed,
        "currencies": {
            cid: {
                "current": cs.current,
                "total_earned": cs.total_earned,
            }
            for cid, cs in state.currencies.items()
        },
        "elements": {
            eid: {"count": es.count}
            for eid, es in state.elements.items()
            if es.count > 0
        },
        "milestones_reached": dict(state.milestones_reached),
        "prestige_counts": dict(state.prestige_counts),
        "run_number": state.run_number,
    }

    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_game(runtime: GameRuntime) -> int | None:
    """Restore game state from JSON. Returns seed if loaded, None if no save.

    The caller must have already created the runtime with the correct
    definition (matching the saved seed).
    """
    if not SAVE_FILE.exists():
        return None

    with open(SAVE_FILE) as f:
        data = json.load(f)

    if data.get("version") != SAVE_VERSION:
        return None

    seed = data["seed"]
    state = runtime.get_state()

    state.time_elapsed = data.get("time_elapsed", 0.0)
    state.run_number = data.get("run_number", 1)

    # Restore currencies
    for cid, cdata in data.get("currencies", {}).items():
        if cid in state.currencies:
            state.currencies[cid].current = cdata["current"]
            state.currencies[cid].total_earned = cdata["total_earned"]

    # Restore element counts
    for eid, edata in data.get("elements", {}).items():
        if eid in state.elements:
            state.elements[eid].count = edata["count"]

    # Restore milestones
    for mid, mtime in data.get("milestones_reached", {}).items():
        state.milestones_reached[mid] = mtime

    # Restore prestige counts
    for lid, count in data.get("prestige_counts", {}).items():
        state.prestige_counts[lid] = count

    return seed


def delete_save() -> None:
    """Delete the save file."""
    if SAVE_FILE.exists():
        SAVE_FILE.unlink()


def has_save() -> bool:
    """Check if a save file exists."""
    return SAVE_FILE.exists()


def get_save_seed() -> int | None:
    """Read just the seed from the save file without loading."""
    if not SAVE_FILE.exists():
        return None
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        return data.get("seed")
    except (json.JSONDecodeError, KeyError):
        return None
