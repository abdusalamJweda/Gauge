import time
import logging
import psutil
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class NetworkSensor:
    def __init__(self):
        self._last_bytes_sent = 0
        self._last_bytes_recv = 0
        self._last_time = 0.0
        self._last_stats: Dict = {}

    def get_stats(self) -> Dict:
        try:
            counters = psutil.net_io_counters()
            now = time.time()

            if self._last_time > 0 and now > self._last_time:
                dt = now - self._last_time
                upload_speed = (counters.bytes_sent - self._last_bytes_sent) / dt
                download_speed = (counters.bytes_recv - self._last_bytes_recv) / dt
            else:
                upload_speed = 0.0
                download_speed = 0.0

            self._last_bytes_sent = counters.bytes_sent
            self._last_bytes_recv = counters.bytes_recv
            self._last_time = now

            stats = {
                "upload_speed_bps": upload_speed,
                "download_speed_bps": download_speed,
                "total_sent_gb": round(counters.bytes_sent / (1024 ** 3), 2),
                "total_recv_gb": round(counters.bytes_recv / (1024 ** 3), 2),
                "packets_sent": counters.packets_sent,
                "packets_recv": counters.packets_recv,
            }
            self._last_stats = stats
            return stats
        except Exception as e:
            logger.debug(f"Network sensor query failed: {e}")
            return self._last_stats

    @staticmethod
    def format_speed(bytes_per_sec: float) -> str:
        if bytes_per_sec >= 1024 * 1024:
            return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
        if bytes_per_sec >= 1024:
            return f"{bytes_per_sec / 1024:.1f} KB/s"
        return f"{bytes_per_sec:.0f} B/s"
