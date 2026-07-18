import time
import logging
import psutil
from typing import List, Dict

logger = logging.getLogger(__name__)


class ProcessSensor:
    def __init__(self):
        self._last_stats: List[Dict] = []
        self._last_query_time: float = 0.0
        self._query_interval: float = 5.0

    def get_stats(self, top_n: int = 10) -> List[Dict]:
        now = time.time()
        if now - self._last_query_time < self._query_interval:
            return self._last_stats

        self._last_query_time = now
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                try:
                    info = proc.info
                    cpu = info.get("cpu_percent") or 0.0
                    mem = info.get("memory_percent") or 0.0
                    name = info.get("name") or "Unknown"
                    pid = info.get("pid") or 0
                    processes.append({
                        "pid": pid,
                        "name": name,
                        "cpu_percent": round(cpu, 1),
                        "memory_percent": round(mem, 1),
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            processes.sort(key=lambda p: p["cpu_percent"], reverse=True)
            result = processes[:top_n]
            self._last_stats = result
            return result
        except Exception as e:
            logger.debug(f"Process sensor query failed: {e}")
            return self._last_stats
