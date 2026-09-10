"""تحسينات أداء قاعدة بيانات WinAdmin دون تغيير واجهة DatabaseManager."""

import sqlite3
from datetime import datetime
from .database import DatabaseManager


class OptimizedDatabaseManager(DatabaseManager):
    """طبقة توافق تضبط نمو سجل الأداء واستعلاماته الثقيلة."""

    PERFORMANCE_LOG_INTERVAL_SECONDS = 15
    HISTORY_MAX_ROWS = 5000

    def __init__(self, db_path="winadmin.db"):
        self._last_perf_log_at = None
        super().__init__(db_path)
        self._ensure_indexes()

    def _ensure_indexes(self):
        """فهارس صغيرة ذات أثر كبير على السجلات الزمنية."""
        try:
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_performance_log_timestamp "
                "ON performance_log(timestamp)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_error_log_timestamp "
                "ON error_log(timestamp)"
            )
            self.conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp_ack "
                "ON performance_alerts(timestamp, acknowledged)"
            )
            self.conn.commit()
        except sqlite3.Error:
            pass

    def log_performance(self, cpu, ram_pct, ram_used, ram_total, disk_pct,
                        disk_used, disk_total, net_sent, net_recv):
        """تسجيل عينة كل 15 ثانية بدلاً من إنشاء سجل كل دورة واجهة."""
        now = datetime.now()
        if self._last_perf_log_at is not None:
            if (now - self._last_perf_log_at).total_seconds() < self.PERFORMANCE_LOG_INTERVAL_SECONDS:
                return
        self._last_perf_log_at = now
        super().log_performance(
            cpu, ram_pct, ram_used, ram_total, disk_pct, disk_used,
            disk_total, net_sent, net_recv
        )

    def get_performance_history(self, hours=24):
        """استرجاع السجل مع أخذ عينات عند تضخم الفترة، لمنع تكدس QTableWidget."""
        try:
            since = (datetime.now().timestamp() - (hours * 3600))
            since_iso = datetime.fromtimestamp(since).isoformat()
            count = self.conn.execute(
                "SELECT COUNT(*) FROM performance_log WHERE timestamp >= ?",
                (since_iso,)
            ).fetchone()[0]

            if count <= self.HISTORY_MAX_ROWS:
                cursor = self.conn.execute(
                    "SELECT * FROM performance_log WHERE timestamp >= ? "
                    "ORDER BY timestamp ASC",
                    (since_iso,)
                )
                return [dict(row) for row in cursor.fetchall()]

            # أخذ عينات منتظمة مع الاحتفاظ بالبداية والنهاية.
            step = max(1, (count + self.HISTORY_MAX_ROWS - 1) // self.HISTORY_MAX_ROWS)
            cursor = self.conn.execute(
                """
                SELECT * FROM (
                    SELECT p.*, ROW_NUMBER() OVER (ORDER BY timestamp ASC) AS rn
                    FROM performance_log p
                    WHERE timestamp >= ?
                )
                WHERE ((rn - 1) % ?) = 0 OR rn = ?
                ORDER BY timestamp ASC
                """,
                (since_iso, step, count),
            )
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error:
            return super().get_performance_history(hours)
