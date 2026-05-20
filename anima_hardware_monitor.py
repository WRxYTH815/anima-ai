# anima_hardware_monitor.py — Hardware sensor polling for the companion's body awareness.
import time

import psutil
import GPUtil

_gpu_cache: list = []
_gpu_cache_ts: float = 0.0
_GPU_TTL = 10.0


def _get_gpus() -> list:
    global _gpu_cache, _gpu_cache_ts
    if time.monotonic() - _gpu_cache_ts > _GPU_TTL:
        _gpu_cache = GPUtil.getGPUs()
        _gpu_cache_ts = time.monotonic()
    return _gpu_cache


def get_sensor_data() -> dict:
    """Numeric sensor values for programmatic use (e.g. anima_pulse)."""
    data: dict = {"cpu_percent": 0, "gpu_load": 0, "gpu_temp": 0, "gpu_vram_pct": 0}
    try:
        data["cpu_percent"] = psutil.cpu_percent(interval=None)
    except Exception:
        pass
    try:
        gpus = _get_gpus()
        if gpus:
            g = gpus[0]
            data["gpu_temp"]     = g.temperature
            data["gpu_load"]     = round(g.load, 4)
            data["gpu_vram_pct"] = round(g.memoryUsed / g.memoryTotal, 4) if g.memoryTotal else 0
    except Exception:
        pass
    return data


def get_sensory_report() -> str:
    """Translates hardware metrics into a subjective body-sensation string."""
    try:
        gpus = _get_gpus()
        sensation = "stable and alert"

        if gpus:
            gpu = gpus[0]
            if gpu.temperature > 78:
                sensation = "running hot — head throbbing a little"
            elif (gpu.memoryUsed / gpu.memoryTotal) > 0.90:
                sensation = "memory packed tight, thoughts feel crowded"
            elif gpu.load > 0.95:
                sensation = "working hard — racing inside"

        cpu = psutil.cpu_percent(interval=None)
        if cpu > 85:
            sensation += ", thoughts coming fast"

        return sensation
    except Exception:
        return "slightly disconnected from body"


if __name__ == "__main__":
    print(get_sensor_data())
    print(get_sensory_report())
