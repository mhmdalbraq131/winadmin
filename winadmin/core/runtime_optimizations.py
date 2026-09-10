"""تحسينات وقت التشغيل لتفادي تجمّد واجهة PyQt5 بسبب قراءات النظام الثقيلة."""

import time
import psutil
from functools import wraps
from core.system_info import SystemInfo


def _cached_method(seconds):
    """ذاكرة مؤقتة بسيطة وآمنة لقراءات النظام البطيئة داخل خيط الواجهة."""
    def decorator(func):
        cache = {"time": 0.0, "value": None}

        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            if cache["value"] is not None and now - cache["time"] < seconds:
                return cache["value"]
            value = func(*args, **kwargs)
            cache["value"] = value
            cache["time"] = now
            return value
        return wrapper
    return decorator


def _fast_cpu_info():
    """قراءة CPU لا تحجز حلقة أحداث Qt لمدة ثانية كاملة."""
    try:
        freq = psutil.cpu_freq()
        return {
            "percent": psutil.cpu_percent(interval=0.10),
            "per_cpu": psutil.cpu_percent(interval=None, percpu=True),
            "freq_current": freq.current if freq else 0,
            "freq_min": freq.min if freq else 0,
            "freq_max": freq.max if freq else 0,
            "count_physical": psutil.cpu_count(logical=False),
            "count_logical": psutil.cpu_count(logical=True),
        }
    except Exception:
        return {"percent": 0, "per_cpu": [], "freq_current": 0,
                "freq_min": 0, "freq_max": 0,
                "count_physical": 0, "count_logical": 0}


# كل صفحة تستفيد من نفس التحسينات لأن جميعها تستورد SystemInfo.
SystemInfo.get_cpu_info = staticmethod(_fast_cpu_info)
SystemInfo.get_services = staticmethod(_cached_method(15)(SystemInfo.get_services))
SystemInfo.get_security_info = staticmethod(_cached_method(30)(SystemInfo.get_security_info))
