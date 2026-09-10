"""
ui/services.py — إدارة الخدمات
عرض وتحكم بخدمات النظام (تشغيل، إيقاف، تغيير نوع البدء).
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QLineEdit, QComboBox,
                              QMessageBox, QMenu)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
from core.system_info import SystemInfo


class ServiceManagerWidget(QWidget):
    """إدارة خدمات النظام."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._services = []
        self._setup_ui()
        self._start_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("🔧 إدارة الخدمات")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ شريط الأدوات ─
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث عن خدمة...")
        self.search_input.setStyleSheet("""
            QLineEdit { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a;
                        border-radius: 4px; padding: 6px 12px; font-size: 13px; }
        """)
        self.search_input.textChanged.connect(self._filter_services)
        toolbar.addWidget(self.search_input)

        # فلتر الحالة
        self.status_filter = QComboBox()
        self.status_filter.addItems(["الكل", "Running", "Stopped", "Paused"])
        self.status_filter.setStyleSheet("""
            QComboBox { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a;
                       border-radius: 4px; padding: 6px; }
            QComboBox QAbstractItemView { background: #1e1e32; color: #e0e0e0; selection-background-color: #2a2a4a; }
        """)
        self.status_filter.currentIndexChanged.connect(self._filter_services)
        toolbar.addWidget(self.status_filter)

        self.btn_refresh = QPushButton("🔄 تحديث")
        self.btn_refresh.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        self.btn_refresh.clicked.connect(self._update_services)
        toolbar.addWidget(self.btn_refresh)

        self.btn_start = QPushButton("▶ تشغيل")
        self.btn_start.setStyleSheet("background: #1c3e2c; color: #80ffcc; border: none; padding: 6px 14px; border-radius: 4px;")
        self.btn_start.clicked.connect(self._start_service)
        toolbar.addWidget(self.btn_start)

        self.btn_stop = QPushButton("⏹ إيقاف")
        self.btn_stop.setStyleSheet("background: #4e1c1c; color: #ff8a80; border: none; padding: 6px 14px; border-radius: 4px;")
        self.btn_stop.clicked.connect(self._stop_service)
        toolbar.addWidget(self.btn_stop)

        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet("color: #888; font-size: 12px;")
        toolbar.addWidget(self.lbl_count)
        toolbar.addStretch()

        layout.addLayout(toolbar)

        # ─ جدول الخدمات ─
        self.svc_table = QTableWidget()
        self.svc_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e;
                           border: none; selection-background-color: #2a2a4a; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px;
                                    border: 1px solid #2a2a3e; font-weight: bold; }
        """)
        self.svc_table.setColumnCount(5)
        self.svc_table.setHorizontalHeaderLabels(["الاسم", "العرض", "الحالة", "نوع البدء", "PID"])
        self.svc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.svc_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.svc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.svc_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.svc_table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.svc_table)

    def _start_timer(self):
        self._update_services()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_services)
        self.timer.start(10000)  # تحديث كل 10 ثواني

    def _update_services(self):
        """تحديث قائمة الخدمات."""
        try:
            self._services = SystemInfo.get_services()
            self._apply_filter()
        except Exception as e:
            self.lbl_count.setText("خطأ في التحديث")

    def _filter_services(self):
        self._apply_filter()

    def _apply_filter(self):
        """تطبيق البحث والفلتر."""
        search = self.search_input.text().lower()
        status = self.status_filter.currentText()

        filtered = self._services
        if search:
            filtered = [s for s in filtered
                        if search in s.get("name", "").lower()
                        or search in s.get("display_name", "").lower()]
        if status != "الكل":
            filtered = [s for s in filtered if s.get("status", "").lower() == status.lower()]

        self.svc_table.setRowCount(len(filtered))
        for i, s in enumerate(filtered):
            self.svc_table.setItem(i, 0, QTableWidgetItem(s.get("name", "")))
            self.svc_table.setItem(i, 1, QTableWidgetItem(s.get("display_name", "")))

            status_item = QTableWidgetItem(s.get("status", ""))
            if s.get("status", "").lower() == "running":
                status_item.setForeground(QColor("#4CAF50"))
            elif s.get("status", "").lower() == "stopped":
                status_item.setForeground(QColor("#f44336"))
            else:
                status_item.setForeground(QColor("#ff9800"))
            self.svc_table.setItem(i, 2, status_item)

            self.svc_table.setItem(i, 3, QTableWidgetItem(s.get("start_mode", "")))
            self.svc_table.setItem(i, 4, QTableWidgetItem(str(s.get("pid", 0))))

        running = sum(1 for s in filtered if s.get("status", "").lower() == "running")
        self.lbl_count.setText(f"{len(filtered)} خدمة ({running} تعمل)")

    def _get_selected_service(self) -> str:
        row = self.svc_table.currentRow()
        if row < 0:
            return ""
        return self.svc_table.item(row, 0).text()

    def _start_service(self):
        name = self._get_selected_service()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اختر خدمة أولاً")
            return
        success, msg = SystemInfo.control_service(name, "start")
        if success:
            QMessageBox.information(self, "تم", msg)
            self._update_services()
        else:
            QMessageBox.critical(self, "فشل", msg)

    def _stop_service(self):
        name = self._get_selected_service()
        if not name:
            QMessageBox.warning(self, "تنبيه", "اختر خدمة أولاً")
            return

        reply = QMessageBox.question(self, "تأكيد", f"هل تريد إيقاف الخدمة {name}؟",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, msg = SystemInfo.control_service(name, "stop")
            if success:
                QMessageBox.information(self, "تم", msg)
                self._update_services()
            else:
                QMessageBox.critical(self, "فشل", msg)

    def _show_context_menu(self, pos):
        """قائمة سياق مع خيارات تغيير نوع البدء."""
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2a2a4a; color: #e0e0e0; }"
                           "QMenu::item:selected { background: #3a3a5a; }")

        name = self._get_selected_service()
        if not name:
            return

        menu.addAction("▶ تشغيل", lambda: self._quick_control(name, "start"))
        menu.addAction("⏹ إيقاف", lambda: self._quick_control(name, "stop"))
        menu.addSeparator()
        menu.addAction("🔄 تلقائي", lambda: self._change_start_type(name, "automatic"))
        menu.addAction("✋ يدوي", lambda: self._change_start_type(name, "manual"))
        menu.addAction("🚫 معطّل", lambda: self._change_start_type(name, "disabled"))

        menu.exec_(self.svc_table.mapToGlobal(pos))

    def _quick_control(self, name: str, action: str):
        success, msg = SystemInfo.control_service(name, action)
        if not success:
            QMessageBox.critical(self, "فشل", msg)
        self._update_services()

    def _change_start_type(self, name: str, mode: str):
        success, msg = SystemInfo.set_service_start_mode(name, mode)
        if success:
            QMessageBox.information(self, "تم", msg)
        else:
            QMessageBox.critical(self, "فشل", msg)
        self._update_services()

    def stop(self):
        self.timer.stop()
