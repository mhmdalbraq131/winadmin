"""
core/database.py — إدارة قاعدة بيانات SQLite
يتولى إنشاء الجداول، الإضافة، الاستعلام، والتصدير.
"""

import sqlite3
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class DatabaseManager:
    """إدارة قاعدة بيانات SQLite لتخزين السجلات والتقارير."""

    def __init__(self, db_path: str = "winadmin.db"):
        self.db_path = db_path
        self.conn = None
        self._connect()
        self._create_tables()

    # ── الاتصال ──────────────────────────────────────────────
    def _connect(self):
        """إنشاء اتصال بقاعدة البيانات."""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            logger.info(f"تم الاتصال بقاعدة البيانات: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
            raise

    # ── إنشاء الجداول ────────────────────────────────────────
    def _create_tables(self):
        """إنشاء جميع الجداول المطلوبة."""
        try:
            cursor = self.conn.cursor()

            # جدول تنبيهات الأداء
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'warning',
                    message TEXT NOT NULL,
                    value REAL,
                    threshold REAL,
                    acknowledged INTEGER DEFAULT 0
                )
            """)

            # جدول سجل الأداء
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    cpu_percent REAL,
                    ram_percent REAL,
                    ram_used REAL,
                    ram_total REAL,
                    disk_percent REAL,
                    disk_used REAL,
                    disk_total REAL,
                    net_bytes_sent REAL,
                    net_bytes_recv REAL
                )
            """)

            # جدول سجل الأخطاء
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    source TEXT,
                    event_id INTEGER,
                    level TEXT,
                    message TEXT
                )
            """)

            # جدول الإعدادات
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # جدول الأجهزة البعيدة
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS remote_hosts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hostname TEXT NOT NULL,
                    ip_address TEXT NOT NULL,
                    port INTEGER DEFAULT 5555,
                    username TEXT,
                    auth_token TEXT,
                    last_seen TEXT,
                    status TEXT DEFAULT 'unknown'
                )
            """)

            # جدول التقارير
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    file_path TEXT,
                    summary TEXT
                )
            """)

            self.conn.commit()
            logger.info("تم إنشاء جميع الجداول بنجاح")
        except sqlite3.Error as e:
            logger.error(f"خطأ في إنشاء الجداول: {e}")
            raise

    # ── عمليات التنبيهات ─────────────────────────────────────
    def add_alert(self, alert_type: str, severity: str, message: str,
                  value: float = None, threshold: float = None):
        """إضافة تنبيه جديد."""
        try:
            self.conn.execute(
                "INSERT INTO performance_alerts (timestamp, alert_type, severity, message, value, threshold) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), alert_type, severity, message, value, threshold)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في إضافة تنبيه: {e}")

    def get_recent_alerts(self, limit: int = 50, acknowledged: bool = False) -> List[Dict]:
        """استرجاع آخر التنبيهات."""
        try:
            ack_filter = "" if acknowledged else "AND acknowledged = 0"
            cursor = self.conn.execute(
                f"SELECT * FROM performance_alerts WHERE 1=1 {ack_filter} ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع التنبيهات: {e}")
            return []

    def acknowledge_alert(self, alert_id: int):
        """تحديث حالة التنبيه كملحوظ."""
        try:
            self.conn.execute("UPDATE performance_alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في تحديث التنبيه: {e}")

    # ── عمليات سجل الأداء ────────────────────────────────────
    def log_performance(self, cpu: float, ram_pct: float, ram_used: float,
                        ram_total: float, disk_pct: float, disk_used: float,
                        disk_total: float, net_sent: float, net_recv: float):
        """تسجيل بيانات الأداء."""
        try:
            self.conn.execute(
                "INSERT INTO performance_log (timestamp, cpu_percent, ram_percent, ram_used, ram_total, disk_percent, disk_used, disk_total, net_bytes_sent, net_bytes_recv) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), cpu, ram_pct, ram_used, ram_total, disk_pct, disk_used, disk_total, net_sent, net_recv)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في تسجيل الأداء: {e}")

    def get_performance_history(self, hours: int = 24) -> List[Dict]:
        """استرجاع سجل الأداء خلال عدد ساعات محدد."""
        try:
            since = (datetime.now() - timedelta(hours=hours)).isoformat()
            cursor = self.conn.execute(
                "SELECT * FROM performance_log WHERE timestamp >= ? ORDER BY timestamp ASC",
                (since,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع سجل الأداء: {e}")
            return []

    # ── عمليات سجل الأخطاء ───────────────────────────────────
    def log_error(self, source: str, event_id: int, level: str, message: str):
        """تسجيل خطأ من Event Viewer."""
        try:
            self.conn.execute(
                "INSERT INTO error_log (timestamp, source, event_id, level, message) VALUES (?, ?, ?, ?, ?)",
                (datetime.now().isoformat(), source, event_id, level, message)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في تسجيل الخطأ: {e}")

    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """استرجاع آخر الأخطاء."""
        try:
            cursor = self.conn.execute(
                "SELECT * FROM error_log ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع الأخطاء: {e}")
            return []

    # ── عمليات الإعدادات ─────────────────────────────────────
    def get_setting(self, key: str, default: str = None) -> Optional[str]:
        """استرجاع إعداد محدد."""
        try:
            cursor = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع الإعداد: {e}")
            return default

    def set_setting(self, key: str, value: str):
        """حفظ أو تحديث إعداد."""
        try:
            self.conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في حفظ الإعداد: {e}")

    def get_all_settings(self) -> Dict[str, str]:
        """استرجاع جميع الإعدادات."""
        try:
            cursor = self.conn.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع الإعدادات: {e}")
            return {}

    # ── عمليات الأجهزة البعيدة ──────────────────────────────
    def add_remote_host(self, hostname: str, ip: str, port: int = 5555,
                        username: str = "", auth_token: str = "") -> int:
        """إضافة جهاز بعيد."""
        try:
            cursor = self.conn.execute(
                "INSERT INTO remote_hosts (hostname, ip_address, port, username, auth_token) VALUES (?, ?, ?, ?, ?)",
                (hostname, ip, port, username, auth_token)
            )
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"خطأ في إضافة جهاز بعيد: {e}")
            return -1

    def get_remote_hosts(self) -> List[Dict]:
        """استرجاع قائمة الأجهزة البعيدة."""
        try:
            cursor = self.conn.execute("SELECT * FROM remote_hosts ORDER BY hostname")
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع الأجهزة البعيدة: {e}")
            return []

    def remove_remote_host(self, host_id: int):
        """حذف جهاز بعيد."""
        try:
            self.conn.execute("DELETE FROM remote_hosts WHERE id = ?", (host_id,))
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في حذف جهاز بعيد: {e}")

    # ── عمليات التقارير ──────────────────────────────────────
    def add_report(self, report_type: str, file_path: str = "", summary: str = ""):
        """إضافة تقرير جديد."""
        try:
            self.conn.execute(
                "INSERT INTO reports (timestamp, report_type, file_path, summary) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), report_type, file_path, summary)
            )
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"خطأ في إضافة تقرير: {e}")

    def get_reports(self, limit: int = 50) -> List[Dict]:
        """استرجاع قائمة التقارير."""
        try:
            cursor = self.conn.execute("SELECT * FROM reports ORDER BY timestamp DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"خطأ في استرجاع التقارير: {e}")
            return []

    # ── تنظيف البيانات القديمة ──────────────────────────────
    def cleanup_old_data(self, days: int = 30):
        """حذف البيانات الأقدم من عدد الأيام المحدد."""
        try:
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            self.conn.execute("DELETE FROM performance_log WHERE timestamp < ?", (cutoff,))
            self.conn.execute("DELETE FROM error_log WHERE timestamp < ?", (cutoff,))
            self.conn.execute("DELETE FROM performance_alerts WHERE timestamp < ? AND acknowledged = 1", (cutoff,))
            self.conn.commit()
            logger.info(f"تم تنظيف البيانات الأقدم من {days} يوم")
        except sqlite3.Error as e:
            logger.error(f"خطأ في تنظيف البيانات: {e}")

    # ── الإغلاق ──────────────────────────────────────────────
    def close(self):
        """إغلاق اتصال قاعدة البيانات بأمان."""
        try:
            if self.conn:
                self.conn.close()
                logger.info("تم إغلاق قاعدة البيانات")
        except sqlite3.Error as e:
            logger.error(f"خطأ في إغلاق قاعدة البيانات: {e}")
