"""
ui/processes.py — إدارة العمليات
عرض وتصفية وإدارة جميع العمليات الجارية.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QLineEdit, QPushButton, QTableWidget,
                              QTableWidgetItem, QHeaderView, QComboBox,
                              QMessageBox, QMenu)
from PyQt5.QtCore import Qt, QTimer, QSortFilterProxyModel, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.system_info import SystemInfo


class ProcessLoadWorker(QThread):
    """تحميل العمليات خارج خيط الواجهة."""
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.finished.emit(SystemInfo.get_processes())
        except Exception as exc:
            self.failed.emit(str(exc))


class ProcessManagerWidget(QWidget):
    """إدارة العمليات الجارية — عرض، تصفية، إيقاف."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sort_column = 4  # ترتيب حسب CPU افتراضياً
        self._sort_order = Qt.DescendingOrder
        self._worker = None
        self._refresh_pending = False
        self._updates_started = False
        self._setup_ui()
        self._create_timer()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("⚙ إدارة العمليات")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ شريط الأدوات ─
        toolbar = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 بحث عن عملية...")
        self.search_input.setStyleSheet("""
            QLineEdit { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a;
                        border-radius: 4px; padding: 6px 12px; font-size: 13px; }
        """)
        self.search_input.textChanged.connect(self._filter_processes)
        toolbar.addWidget(self.search_input)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["CPU ↓", "RAM ↓", "الاسم", "PID", "الحالة"])
        self.sort_combo.setStyleSheet("""
            QComboBox { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a;
                       border-radius: 4px; padding: 6px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background: #1e1e32; color: #e0e0e0; selection-background-color: #2a2a4a; }
        """)
        self.sort_combo.currentIndexChanged.connect(self._change_sort)
        toolbar.addWidget(self.sort_combo)

        self.btn_refresh = QPushButton("🔄 تحديث")
        self.btn_refresh.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        self.btn_refresh.clicked.connect(self._update_processes)
        toolbar.addWidget(self.btn_refresh)

        self.btn_kill = QPushButton("⛔ إيقاف العملية")
        self.btn_kill.setStyleSheet("background: #4e1c1c; color: #ff8a80; border: none; padding: 6px 14px; border-radius: 4px;")
        self.btn_kill.clicked.connect(self._kill_selected)
        toolbar.addWidget(self.btn_kill)

        self.lbl_count = QLabel("0 عملية")
        self.lbl_count.setStyleSheet("color: #888; font-size: 12px;")
        toolbar.addWidget(self.lbl_count)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # ─ جدول العمليات ─
        self.proc_table = QTableWidget()
        self.proc_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e;
                           border: none; selection-background-color: #2a2a4a; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px;
                                    border: 1px solid #2a2a3e; font-weight: bold; }
            QTableWidget::item { padding: 3px; }
        """)
        self.proc_table.setColumnCount(7)
        self.proc_table.setHorizontalHeaderLabels(
            ["PID", "الاسم", "المستخدم", "CPU %", "RAM %", "RAM (MB)", "الحالة"]
        )
        self.proc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.proc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.proc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.proc_table.setSortingEnabled(False)  # فرز يدوي
        self.proc_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.proc_table.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self.proc_table)

    def _create_timer(self):
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.CoarseTimer)
        self.timer.timeout.connect(self._update_processes)

    def start_updates(self):
        """ابدأ جلب العمليات بعد أن تصبح الصفحة هي الصفحة المرئية."""
        first_start = not self._updates_started
        self._updates_started = True
        if not self.timer.isActive():
            self.timer.start(5000)
        if first_start:
            QTimer.singleShot(0, self._update_processes)

    def _update_processes(self):
        """طلب تحديث العمليات دون حجز خيط الواجهة."""
        if self._worker is not None and self._worker.isRunning():
            self._refresh_pending = True
            return
        self._refresh_pending = False
        self.btn_refresh.setEnabled(False)
        self._worker = ProcessLoadWorker()
        self._worker.finished.connect(self._on_processes_loaded)
        self._worker.failed.connect(self._on_processes_failed)
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.failed.connect(self._cleanup_worker)
        self._worker.start()

    def _on_processes_loaded(self, processes):
        try:
            search = self.search_input.text().lower()

            if search:
                processes = [p for p in processes if search in p.get("name", "").lower()
                             or search in str(p.get("pid", ""))]

            # ترتيب
            sort_map = {0: "cpu_percent", 1: "memory_percent", 2: "name", 3: "pid", 4: "status"}
            sort_key = sort_map.get(self.sort_combo.currentIndex(), "cpu_percent")
            reverse = self.sort_combo.currentIndex() in [0, 1]  # تنازلي للنسب
            processes.sort(key=lambda p: p.get(sort_key, 0) if isinstance(p.get(sort_key, 0), (int, float)) else p.get(sort_key, ""),
                          reverse=reverse)

            self.proc_table.setRowCount(len(processes))
            for i, p in enumerate(processes):
                self.proc_table.setItem(i, 0, QTableWidgetItem(str(p.get("pid", ""))))
                self.proc_table.setItem(i, 1, QTableWidgetItem(p.get("name", "")))
                self.proc_table.setItem(i, 2, QTableWidgetItem(p.get("username", "") or "—"))

                cpu_item = QTableWidgetItem(f"{p.get('cpu_percent', 0):.1f}")
                cpu_val = p.get('cpu_percent', 0)
                if cpu_val > 50:
                    cpu_item.setForeground(QColor("#f44336"))
                elif cpu_val > 20:
                    cpu_item.setForeground(QColor("#ff9800"))
                self.proc_table.setItem(i, 3, cpu_item)

                ram_item = QTableWidgetItem(f"{p.get('memory_percent', 0):.1f}")
                ram_val = p.get('memory_percent', 0)
                if ram_val > 50:
                    ram_item.setForeground(QColor("#f44336"))
                elif ram_val > 20:
                    ram_item.setForeground(QColor("#ff9800"))
                self.proc_table.setItem(i, 4, ram_item)

                self.proc_table.setItem(i, 5, QTableWidgetItem(f"{p.get('memory_mb', 0):.1f}"))
                self.proc_table.setItem(i, 6, QTableWidgetItem(p.get("status", "")))

            self.lbl_count.setText(f"{len(processes)} عملية")
        except Exception:
            self.lbl_count.setText("خطأ في عرض العمليات")
        finally:
            self.btn_refresh.setEnabled(True)

    def _on_processes_failed(self, message):
        self.btn_refresh.setEnabled(True)
        self.lbl_count.setText("تعذر تحديث العمليات")

    def _cleanup_worker(self, *_):
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        if self._refresh_pending and self.timer.isActive():
            QTimer.singleShot(0, self._update_processes)

    def _filter_processes(self, text: str):
        self._update_processes()

    def _change_sort(self, index: int):
        self._update_processes()

    def _kill_selected(self):
        """إيقاف العملية المحددة."""
        row = self.proc_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر عملية أولاً")
            return

        pid = int(self.proc_table.item(row, 0).text())
        name = self.proc_table.item(row, 1).text()

        reply = QMessageBox.question(self, "تأكيد الإيقاف",
                                      f"هل تريد إيقاف العملية\n{name} (PID: {pid})؟",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            success, msg = SystemInfo.kill_process(pid)
            if success:
                QMessageBox.information(self, "تم", msg)
                self._update_processes()
            else:
                QMessageBox.critical(self, "فشل", msg)

    def _show_context_menu(self, pos):
        """قائمة سياق بزر الفأرة الأيمن."""
        menu = QMenu()
        menu.setStyleSheet("QMenu { background: #2a2a4a; color: #e0e0e0; }"
                           "QMenu::item:selected { background: #3a3a5a; }")
        kill_action = menu.addAction("⛔ إيقاف العملية")
        detail_action = menu.addAction("📋 تفاصيل")

        action = menu.exec_(self.proc_table.mapToGlobal(pos))
        if action == kill_action:
            self._kill_selected()
        elif action == detail_action:
            row = self.proc_table.currentRow()
            if row >= 0:
                pid = self.proc_table.item(row, 0).text()
                name = self.proc_table.item(row, 1).text()
                QMessageBox.information(self, f"تفاصيل {name}",
                                        f"PID: {pid}\nالاسم: {name}")

    def stop(self):
        try:
            self.timer.stop()
            if self._worker is not None and self._worker.isRunning():
                self._worker.requestInterruption()
                self._worker.quit()
                self._worker.wait(500)
        except Exception:
            pass
