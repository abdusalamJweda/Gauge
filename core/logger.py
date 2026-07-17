import csv
import os
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class CsvLogger:
    def __init__(self, config: dict):
        self.config = config.get("logging", {})
        self.log_dir = self.config.get("log_dir", "logs")
        self.retention_days = self.config.get("retention_days", 30)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._aggregator = None
        self._csv_file = None
        self._writer = None
        self._current_date = None
        self._headers = [
            "timestamp", "cpu_usage", "cpu_temp", "cpu_freq",
            "gpu_name", "gpu_usage", "gpu_temp",
            "gpu_vram_used_mb", "gpu_vram_total_mb",
            "ram_total_gb", "ram_used_gb", "ram_percent",
        ]

    def set_aggregator(self, aggregator):
        self._aggregator = aggregator

    def _ensure_log_dir(self):
        if not os.path.isdir(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)

    def _get_csv_path(self) -> str:
        today = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(self.log_dir, f"hardware_{today}.csv")

    def _open_csv(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if self._current_date != today:
            self._close_csv()
            self._current_date = today

        path = self._get_csv_path()
        file_exists = os.path.isfile(path) and os.path.getsize(path) > 0

        self._csv_file = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._csv_file)
        if not file_exists:
            self._writer.writerow(self._headers)
            self._csv_file.flush()

    def _close_csv(self):
        if self._csv_file:
            try:
                self._csv_file.close()
            except Exception:
                pass
            self._csv_file = None
            self._writer = None

    def _write_row(self, snapshot):
        if not self._writer:
            return
        ts = datetime.fromtimestamp(snapshot.timestamp).strftime("%Y-%m-%d %H:%M:%S")
        disks = snapshot.disks
        disk_info = ""
        if disks:
            parts = [f"{d['device']}:{d['percent']}%" for d in disks[:3]]
            disk_info = " | ".join(parts)

        row = [
            ts,
            snapshot.cpu_usage,
            snapshot.cpu_temp,
            snapshot.cpu_freq,
            snapshot.gpu_name or "",
            snapshot.gpu_usage,
            snapshot.gpu_temp,
            snapshot.gpu_vram_used,
            snapshot.gpu_vram_total,
            snapshot.ram_total,
            snapshot.ram_used,
            snapshot.ram_percent,
        ]
        self._writer.writerow(row)
        self._csv_file.flush()

    def _cleanup_old_logs(self):
        try:
            self._ensure_log_dir()
            cutoff = datetime.now() - timedelta(days=self.retention_days)
            for f in os.listdir(self.log_dir):
                if f.startswith("hardware_") and f.endswith(".csv"):
                    date_str = f.replace("hardware_", "").replace(".csv", "")
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d")
                        if file_date < cutoff:
                            os.remove(os.path.join(self.log_dir, f))
                            logger.info(f"Deleted old log: {f}")
                    except ValueError:
                        continue
        except Exception as e:
            logger.debug(f"Log cleanup failed: {e}")

    def _loop(self):
        interval = self._aggregator.config.get("polling_interval_seconds", 1)
        last_cleanup = time.time()
        while self._running:
            try:
                snap = self._aggregator.snapshot
                if snap.timestamp > 0:
                    self._write_row(snap)
                if time.time() - last_cleanup > 3600:
                    self._cleanup_old_logs()
                    last_cleanup = time.time()
            except Exception as e:
                logger.debug(f"CSV log write error: {e}")
            time.sleep(interval)

    def start(self):
        if self._running:
            return
        self._ensure_log_dir()
        self._open_csv()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="csv-logger")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
            self._thread = None
        self._close_csv()
