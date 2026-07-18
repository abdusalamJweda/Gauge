import time
import logging

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, config: dict):
        alerts_cfg = config.get("alerts", {})
        self.cpu_threshold = alerts_cfg.get("cpu_temp_threshold_c", 85)
        self.gpu_threshold = alerts_cfg.get("gpu_temp_threshold_c", 83)
        self.cooldown = alerts_cfg.get("cooldown_seconds", 300)
        self._last_cpu_alert = 0.0
        self._last_gpu_alert = 0.0

    def check(self, snapshot) -> list:
        alerts = []
        now = time.time()

        if snapshot.cpu_temp is not None and snapshot.cpu_temp >= self.cpu_threshold:
            if now - self._last_cpu_alert >= self.cooldown:
                self._last_cpu_alert = now
                alerts.append({
                    "sensor": "CPU",
                    "value": snapshot.cpu_temp,
                    "threshold": self.cpu_threshold,
                    "message": f"CPU temperature: {snapshot.cpu_temp}°C (threshold: {self.cpu_threshold}°C)",
                })

        if snapshot.gpu_temp is not None and snapshot.gpu_temp >= self.gpu_threshold:
            if now - self._last_gpu_alert >= self.cooldown:
                self._last_gpu_alert = now
                alerts.append({
                    "sensor": "GPU",
                    "value": snapshot.gpu_temp,
                    "threshold": self.gpu_threshold,
                    "message": f"GPU temperature: {snapshot.gpu_temp}°C (threshold: {self.gpu_threshold}°C)",
                })

        return alerts


def send_notification(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Gauge",
            timeout=10,
        )
    except ImportError:
        logger.debug("plyer not installed. pip install plyer")
    except Exception as e:
        logger.debug(f"Notification failed: {e}")
