"""
core/alerts.py — نظام التنبيهات
يتولى مراقبة العتبات وإرسال التنبيهات عبر الواجهة والبريد الإلكتروني.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Optional, Callable

logger = logging.getLogger(__name__)


class AlertManager:
    """نظام تنبيهات يراقب عتبات الموارد ويُرسل إشعارات."""

    def __init__(self, db_manager):
        self.db = db_manager
        self.thresholds: Dict[str, float] = {
            "cpu_percent": 90.0,
            "ram_percent": 90.0,
            "disk_percent": 90.0,
        }
        self.email_settings: Dict = {
            "enabled": False,
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "use_tls": True,
            "sender": "",
            "password": "",
            "recipients": [],
        }
        self._callbacks = []
        self._cooldown: Dict[str, datetime] = {}
        self._cooldown_seconds = 300  # 5 دقائق بين كل تنبيه من نفس النوع
        self._load_settings()

    def _load_settings(self):
        """تحميل الإعدادات من قاعدة البيانات."""
        try:
            for key in self.thresholds:
                val = self.db.get_setting(f"threshold_{key}")
                if val:
                    self.thresholds[key] = float(val)

            email_enabled = self.db.get_setting("email_enabled")
            if email_enabled:
                self.email_settings["enabled"] = email_enabled.lower() == "true"
            for ekey in ["smtp_server", "smtp_port", "sender", "password"]:
                val = self.db.get_setting(f"email_{ekey}")
                if val:
                    self.email_settings[ekey] = val if ekey != "smtp_port" else int(val)
            recipients = self.db.get_setting("email_recipients")
            if recipients:
                self.email_settings["recipients"] = [r.strip() for r in recipients.split(",") if r.strip()]
        except Exception as e:
            logger.error(f"خطأ في تحميل إعدادات التنبيهات: {e}")

    def register_callback(self, callback: Callable):
        """تسجيل دالة تُستدعى عند كل تنبيه جديد (لعرضه في الواجهة)."""
        self._callbacks.append(callback)

    def check_thresholds(self, cpu: float, ram: float, disk: float):
        """فحص تجاوز العتبات وإطلاق التنبيهات."""
        checks = {
            "cpu_percent": ("CPU", cpu),
            "ram_percent": ("RAM", ram),
            "disk_percent": ("Disk", disk),
        }
        for key, (label, value) in checks.items():
            threshold = self.thresholds.get(key, 90.0)
            if value >= threshold:
                # تحقق من فترة التهدئة
                last_alert = self._cooldown.get(key)
                if last_alert and (datetime.now() - last_alert).total_seconds() < self._cooldown_seconds:
                    continue

                severity = "critical" if value >= threshold + 5 else "warning"
                message = f"⚠ {label} تجاوز العتبة: {value:.1f}% (العتبة: {threshold:.0f}%)"

                # تسجيل في قاعدة البيانات
                self.db.add_alert(key, severity, message, value, threshold)

                # إطلاق الاستدعاءات
                for cb in self._callbacks:
                    try:
                        cb(key, severity, message)
                    except Exception as e:
                        logger.error(f"خطأ في استدعاء التنبيه: {e}")

                # إرسال بريد إلكتروني
                if self.email_settings.get("enabled"):
                    self._send_email_alert(label, value, threshold)

                self._cooldown[key] = datetime.now()
                logger.warning(message)

    def _send_email_alert(self, resource: str, value: float, threshold: float):
        """إرسال تنبيه عبر البريد الإلكتروني."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"⚠ WinAdmin Alert: {resource} at {value:.1f}%"
            msg["From"] = self.email_settings["sender"]
            msg["To"] = ", ".join(self.email_settings["recipients"])

            body = f"""<h2>⚠ Resource Alert</h2>
<p><strong>{resource}</strong> usage has exceeded the threshold.</p>
<ul><li>Current: <strong>{value:.1f}%</strong></li>
<li>Threshold: <strong>{threshold:.0f}%</strong></li>
<li>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</li></ul>
<p><em>— WinAdmin System Monitor</em></p>"""
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.email_settings["smtp_server"],
                              self.email_settings["smtp_port"]) as server:
                if self.email_settings.get("use_tls", True):
                    server.starttls()
                server.login(self.email_settings["sender"],
                             self.email_settings["password"])
                server.sendmail(self.email_settings["sender"],
                                self.email_settings["recipients"],
                                msg.as_string())
            logger.info(f"تم إرسال تنبيه بالبريد عن {resource}")
        except Exception as e:
            logger.error(f"خطأ في إرسال بريد التنبيه: {e}")

    def update_threshold(self, key: str, value: float):
        """تحديث عتبة تنبيه."""
        self.thresholds[key] = value
        self.db.set_setting(f"threshold_{key}", str(value))

    def update_email_settings(self, settings: Dict):
        """تحديث إعدادات البريد الإلكتروني."""
        self.email_settings.update(settings)
        for k, v in settings.items():
            if k == "recipients":
                self.db.set_setting("email_recipients", ",".join(v))
            elif k == "smtp_port":
                self.db.set_setting(f"email_{k}", str(v))
            else:
                self.db.set_setting(f"email_{k}", str(v))

    def test_email(self) -> tuple:
        """اختبار إعدادات البريد."""
        try:
            msg = MIMEText("This is a test email from WinAdmin.", "plain")
            msg["Subject"] = "WinAdmin — Test Email"
            msg["From"] = self.email_settings["sender"]
            msg["To"] = ", ".join(self.email_settings["recipients"])

            with smtplib.SMTP(self.email_settings["smtp_server"],
                              self.email_settings["smtp_port"]) as server:
                if self.email_settings.get("use_tls", True):
                    server.starttls()
                server.login(self.email_settings["sender"],
                             self.email_settings["password"])
                server.sendmail(self.email_settings["sender"],
                                self.email_settings["recipients"],
                                msg.as_string())
            return True, "تم إرسال رسالة الاختبار بنجاح"
        except Exception as e:
            return False, f"فشل الإرسال: {e}"
