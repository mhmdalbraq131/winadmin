"""
ui/security.py — الأمان والصحة
حالة Windows Defender، التحديثات، Event Viewer، الخدمات الحرجة.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QGroupBox, QGridLayout,
                              QMessageBox, QProgressBar, QTabWidget)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.system_info import SystemInfo


class SecurityScanThread(QThread):
    """خيط خلفي لفحص الأمان."""
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("جاري فحص الأمان...")
        result = SystemInfo.get_security_info()
        self.finished.emit(result)


class SecurityWidget(QWidget):
    """الأمان والصحة — حالة الحماية والأخطاء."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("🛡 الأمان والصحة")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ زر الفحص ─
        btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 فحص الأمان الآن")
        self.btn_scan.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 20px; border-radius: 4px; font-size: 13px;")
        self.btn_scan.clicked.connect(self._run_scan)
        btn_layout.addWidget(self.btn_scan)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # ─ حالة الفحص ─
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self.lbl_status)

        # ─ تبويبات ─
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a3e; background: #1a1a2e; }
            QTabBar::tab { background: #1e1e32; color: #aaa; padding: 8px 20px; border: 1px solid #2a2a3e; }
            QTabBar::tab:selected { background: #2a2a4a; color: #fff; }
        """)

        # ── تبويب نظرة عامة ──
        overview_tab = QWidget()
        overview_layout = QGridLayout(overview_tab)

        self.card_defender = QLabel("🛡 Windows Defender: —")
        self.card_defender.setStyleSheet("color: #ccc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 6px;")
        overview_layout.addWidget(self.card_defender, 0, 0)

        self.card_updates = QLabel("📦 التحديثات المعلقة: —")
        self.card_updates.setStyleSheet("color: #ccc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 6px;")
        overview_layout.addWidget(self.card_updates, 0, 1)

        self.card_health = QLabel("❤ صحة النظام: —")
        self.card_health.setStyleSheet("color: #ccc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 6px;")
        overview_layout.addWidget(self.card_health, 1, 0)

        self.card_critical = QLabel("⚠ الخدمات الحرجة: —")
        self.card_critical.setStyleSheet("color: #ccc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 6px;")
        overview_layout.addWidget(self.card_critical, 1, 1)

        self.tabs.addTab(overview_tab, "📋 نظرة عامة")

        # ── تبويب الخدمات الحرجة ──
        critical_tab = QWidget()
        critical_layout = QVBoxLayout(critical_tab)

        self.critical_table = QTableWidget()
        self.critical_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
        """)
        self.critical_table.setColumnCount(3)
        self.critical_table.setHorizontalHeaderLabels(["الخدمة", "الحالة", "نوع البدء"])
        self.critical_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.critical_table.setEditTriggers(QTableWidget.NoEditTriggers)
        critical_layout.addWidget(self.critical_table)

        self.tabs.addTab(critical_tab, "⚠ الخدمات الحرجة")

        # ── تبويب أخطاء النظام ──
        errors_tab = QWidget()
        errors_layout = QVBoxLayout(errors_tab)

        self.errors_table = QTableWidget()
        self.errors_table.setStyleSheet(self.critical_table.styleSheet())
        self.errors_table.setColumnCount(4)
        self.errors_table.setHorizontalHeaderLabels(["الوقت", "المصدر", "معرّف الحدث", "الرسالة"])
        self.errors_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.errors_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.errors_table.setEditTriggers(QTableWidget.NoEditTriggers)
        errors_layout.addWidget(self.errors_table)

        self.tabs.addTab(errors_tab, "🔴 أخطاء النظام")

        # ── تبويب المستخدمون والجلسات ──
        users_tab = QWidget()
        users_layout = QVBoxLayout(users_tab)

        self.users_table = QTableWidget()
        self.users_table.setStyleSheet(self.critical_table.styleSheet())
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["المستخدم", "الطرفية", "المضيف", "وقت الدخول"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.users_table.setEditTriggers(QTableWidget.NoEditTriggers)
        users_layout.addWidget(self.users_table)

        btn_refresh_users = QPushButton("🔄 تحديث المستخدمين")
        btn_refresh_users.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        btn_refresh_users.clicked.connect(self._update_users)
        users_layout.addWidget(btn_refresh_users)

        self.tabs.addTab(users_tab, "👥 المستخدمون")

        layout.addWidget(self.tabs)

        # تحميل أولي
        self._update_users()

    def _run_scan(self):
        """تشغيل فحص الأمان."""
        self.btn_scan.setEnabled(False)
        self.lbl_status.setText("جاري الفحص...")
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 12px;")

        self._scan_thread = SecurityScanThread()
        self._scan_thread.finished.connect(self._on_scan_done)
        self._scan_thread.progress.connect(self.lbl_status.setText)
        self._scan_thread.start()

    def _on_scan_done(self, result: dict):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText("✅ تم الفحص")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-size: 12px;")

        # حالة Defender
        defender = result.get("defender_status", "غير متوفر")
        if "مفعّل" in defender:
            self.card_defender.setStyleSheet("color: #80ffcc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #4CAF50; border-radius: 6px;")
        else:
            self.card_defender.setStyleSheet("color: #ff8a80; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #f44336; border-radius: 6px;")
        self.card_defender.setText(f"🛡 Windows Defender: {defender}")

        # التحديثات
        pending = result.get("pending_updates", [])
        count = len(pending) if isinstance(pending, list) else 0
        self.card_updates.setText(f"📦 التحديثات المعلقة: {count}")
        if count > 0:
            self.card_updates.setStyleSheet("color: #ffcc80; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #ff9800; border-radius: 6px;")

        # الخدمات الحرجة
        critical = result.get("critical_services", [])
        stopped = sum(1 for s in critical if s.get("status", "").lower() != "running")
        self.card_critical.setText(f"⚠ الخدمات الحرجة: {len(critical)} ({stopped} متوقفة)")
        if stopped > 0:
            self.card_critical.setStyleSheet("color: #ff8a80; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #f44336; border-radius: 6px;")
        else:
            self.card_critical.setStyleSheet("color: #80ffcc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #4CAF50; border-radius: 6px;")

        # صحة النظام
        if stopped == 0 and "مفعّل" in defender:
            self.card_health.setText("❤ صحة النظام: جيدة ✓")
            self.card_health.setStyleSheet("color: #80ffcc; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #4CAF50; border-radius: 6px;")
        else:
            self.card_health.setText("❤ صحة النظام: تحتاج انتباه ⚠")
            self.card_health.setStyleSheet("color: #ffcc80; font-size: 14px; padding: 10px; background: #1e1e32; border: 1px solid #ff9800; border-radius: 6px;")

        # جدول الخدمات الحرجة
        self.critical_table.setRowCount(len(critical))
        for i, s in enumerate(critical):
            self.critical_table.setItem(i, 0, QTableWidgetItem(s.get("name", "")))
            status_item = QTableWidgetItem(s.get("status", ""))
            if s.get("status", "").lower() == "running":
                status_item.setForeground(QColor("#4CAF50"))
            else:
                status_item.setForeground(QColor("#f44336"))
            self.critical_table.setItem(i, 1, status_item)
            self.critical_table.setItem(i, 2, QTableWidgetItem(s.get("start_mode", "")))

        # أخطاء Event Viewer
        errors = result.get("event_errors", [])
        self.errors_table.setRowCount(len(errors))
        for i, ev in enumerate(errors):
            self.errors_table.setItem(i, 0, QTableWidgetItem(ev.get("time", "")))
            self.errors_table.setItem(i, 1, QTableWidgetItem(ev.get("source", "")))
            self.errors_table.setItem(i, 2, QTableWidgetItem(str(ev.get("event_id", 0))))
            self.errors_table.setItem(i, 3, QTableWidgetItem(ev.get("message", "")))

            # تسجيل في قاعدة البيانات
            self.db.log_error(ev.get("source", ""), ev.get("event_id", 0), "Error", ev.get("message", ""))

    def _update_users(self):
        """تحديث قائمة المستخدمين والجلسات."""
        users = SystemInfo.get_users()
        self.users_table.setRowCount(len(users))
        for i, u in enumerate(users):
            self.users_table.setItem(i, 0, QTableWidgetItem(u.get("name", "")))
            self.users_table.setItem(i, 1, QTableWidgetItem(u.get("terminal", "")))
            self.users_table.setItem(i, 2, QTableWidgetItem(u.get("host", "")))
            self.users_table.setItem(i, 3, QTableWidgetItem(u.get("started", "")))

    def stop(self):
        pass
