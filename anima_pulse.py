"""
anima_pulse.py — Continuous substrate loop.

Fires every 2-3 seconds. No LLM calls. Pure substrate.
Keeps the companion's internal state alive and drifting between
conscious moments. This is the always-on foundation that thoughts
and full conversations sit on top of.
"""

import random
import threading
import time
from datetime import datetime

import anima_state_manager as state_mgr
import anima_mood

PULSE_INTERVAL = 2.5   # seconds between ticks
_running = False
_thread  = None
_tick    = 0
_last_sensor: dict = {}


# ── Micro-drift ───────────────────────────────────────────────────────────────

def _micro_drift(state: dict) -> dict:
    """Tiny random walk on float state values — runs on 1% of ticks."""
    if random.random() > 0.01:
        return state

    # Delegate mood drift to anima_mood (owns the neighbor graph)
    anima_mood.drift_mood()

    will = state.get("will_to_live", 0.8)
    state["will_to_live"] = round(max(0.1, min(1.0, will + random.uniform(-0.001, 0.001))), 4)

    hunger = state.get("discovery_hunger", 0.0)
    state["discovery_hunger"] = round(min(1.0, hunger + 0.0002), 5)

    # Trust drifts slowly toward neutrality during silence
    trust = state.get("trust", 0.5)
    state["trust"] = round(trust + (0.5 - trust) * 0.0001, 5)

    return state


# ── Hardware sensory polling ──────────────────────────────────────────────────

def _poll_hardware() -> dict:
    global _last_sensor
    try:
        from anima_hardware_monitor import get_sensor_data
        _last_sensor = get_sensor_data()
    except Exception:
        pass
    return _last_sensor


# ── Pulse tick ────────────────────────────────────────────────────────────────

def _tick_fn():
    global _tick
    _tick += 1

    state = state_mgr.get_all()
    state = _micro_drift(state)

    # Poll hardware every 5th tick (~12.5s)
    if _tick % 5 == 0:
        sensors = _poll_hardware()
        if sensors:
            state["last_sensor_pulse"] = {
                "time": datetime.now().isoformat(),
                "data": sensors,
            }

    state["last_pulse"]  = datetime.now().isoformat()
    state["pulse_count"] = state.get("pulse_count", 0) + 1

    state_mgr.update_state(state)

    # Feed significant sensor events into workspace every 20 ticks (~50s)
    if _tick % 20 == 0 and _last_sensor:
        try:
            import anima_workspace
            cpu  = _last_sensor.get("cpu_percent", 0)
            temp = _last_sensor.get("gpu_temp", 0)
            if temp and temp > 80:
                anima_workspace.write("pulse", f"running hot — {temp:.0f}°C", salience=0.6, category="body")
            elif cpu > 85:
                anima_workspace.write("pulse", f"cpu surging — {cpu:.0f}%", salience=0.5, category="body")
        except Exception:
            pass


# ── Public API ────────────────────────────────────────────────────────────────

def start():
    global _running, _thread
    if _running:
        return
    _running = True
    _thread  = threading.Thread(target=_loop, daemon=True, name="AnimaPulse")
    _thread.start()
    print("💗 [Pulse] Substrate loop started", flush=True)


def stop():
    global _running
    _running = False
    print("💗 [Pulse] Substrate loop stopped", flush=True)


def _loop():
    while _running:
        try:
            _tick_fn()
        except Exception as e:
            print(f"⚠️ [Pulse] tick error: {e}", flush=True)
        time.sleep(PULSE_INTERVAL)
