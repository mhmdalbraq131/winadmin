"""
ui/storage.py — إدارة التخزين
إيجاد المجلدات الكبيرة، تنظيف الملفات المؤقتة، حجم التطبيقات.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QProgressBar, QMessageBox,
                              QLineEdit, QFileDialog, QGroupBox)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont
from core.system_info import SystemInfo


class StorageScannerThread(QThread):
    """خيط خلفي لمسح المجلدات الكبيرة."""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def __init__(self, path: str, min_size_mb: int = 500):
        super().__init__()
        self.path = path
        self.min_size_mb = min_size_mb

    def run(self):
        self.progress.emit(f"جاري المسح: {self.path}")
        result = SystemInfo.find_large_directories(self.path, self.min_size_mb)
        self.finished.emit(result)


class AppSizeThread(QThread):
    """خيط خلفي لحساب حجم التطبيقات."""
    finished = pyqtSignal(list)
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("جاري حساب حجم التطبيقات المثبتة...")
        result = SystemInfo.get_installed_apps_size()
        self.finished.emit(result)


class StorageManagerWidget(QWidget):
    """إدارة التخزين — مسح، تنظيف، توصيات."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("💾 إدارة التخزين")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ معلومات الأقراص ─
        disks = SystemInfo.get_disk_info()
        for d in disks:
            disk_group = QGroupBox(f"{d.get('device', '')} — {d.get('mountpoint', '')}")
            disk_group.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 15px; }")
            disk_layout = QVBoxLayout(disk_group)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(int(d.get("percent", 0)))
            pct = d.get("percent", 0)
            color = "#f44336" if pct >= 90 else "#ff9800" if pct >= 75 else "#4CAF50"
            bar.setStyleSheet(f"""
                QProgressBar {{ background: #1e1e32; border: none; border-radius: 4px; text-align: center; color: white; }}
                QProgressBar::chunk {{ background: {color}; border-radius: 3px; }}
            """)
            bar.setFormat(f"{pct:.1f}% — {SystemInfo.bytes_to_human(d.get('used', 0))} / {SystemInfo.bytes_to_human(d.get('total', 0))}")
            disk_layout.addWidget(bar)

            info_lbl = QLabel(f"المتاح: {SystemInfo.bytes_to_human(d.get('free', 0))} | النوع: {d.get('fstype', '—')}")
            info_lbl.setStyleSheet("color: #888; font-size: 11px;")
            disk_layout.addWidget(info_lbl)

            layout.addWidget(disk_group)

        # ─ أدوات ─
        tools_layout = QHBoxLayout()

        self.btn_scan = QPushButton("📂 البحث عن مجلدات كبيرة")
        self.btn_scan.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px;")
        self.btn_scan.clicked.connect(self._scan_large_dirs)
        tools_layout.addWidget(self.btn_scan)

        self.btn_clean = QPushButton("🧹 تنظيف الملفات المؤقتة")
        self.btn_clean.setStyleSheet("background: #3e2c1c; color: #ffcc80; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px;")
        self.btn_clean.clicked.connect(self._clean_temp)
        tools_layout.addWidget(self.btn_clean)

        self.btn_apps = QPushButton("📦 حجم التطبيقات")
        self.btn_apps.setStyleSheet("background: #1c3e2c; color: #80ffcc; border: none; padding: 8px 16px; border-radius: 4px; font-size: 12px;")
        self.btn_apps.clicked.connect(self._scan_apps)
        tools_layout.addWidget(self.btn_apps)

        tools_layout.addStretch()
        layout.addLayout(tools_layout)

        # ─ حالة المسح ─
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #aaa; font-size: 12px; padding: 4px;")
        layout.addWidget(self.lbl_status)

        # ─ جدول النتائج ─
        self.results_table = QTableWidget()
        self.results_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
        """)
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["المسار / الاسم", "الحجم", "تفاصيل"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.results_table)

        # ─ توصيات ─
        rec_group = QGroupBox("💡 توصيات لتحرير المساحة")
        rec_group.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 15px; }")
        rec_layout = QVBoxLayout(rec_group)
        self.lbl_recommendations = QLabel("اضغط على أحد الأزرار أعلاه للحصول على توصيات")
        self.lbl_recommendations.setStyleSheet("color: #aaa; font-size: 12px;")
        self.lbl_recommendations.setWordWrap(True)
        rec_layout.addWidget(self.lbl_recommendations)
        layout.addWidget(rec_group)

    def _scan_large_dirs(self):
        """المسح عن مجلدات كبيرة."""
        scan_path = "C:\\" if SystemInfo.IS_WINDOWS else "/"
        self.lbl_status.setText("جاري المسح... قد يستغرق بضع دقائق")
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 12px;")
        self.btn_scan.setEnabled(False)

        self._scanner = StorageScannerThread(scan_path)
        self._scanner.finished.connect(self._on_scan_done)
        self._scanner.progress.connect(self.lbl_status.setText)
        self._scanner.start()

    def _on_scan_done(self, result):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText(f"تم العثور على {len(result)} مجلد كبير")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-size: 12px;")

        self.results_table.setRowCount(len(result))
        for i, d in enumerate(result):
            self.results_table.setItem(i, 0, QTableWidgetItem(d.get("path", "")))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{d.get('size_gb', 0):.2f} GB"))
            self.results_table.setItem(i, 2, QTableWidgetItem(f"{d.get('size_mb', 0):.1f} MB"))

        if result:
            recs = "\n".join(f"• المجلد {d['path']} يحتل {d['size_gb']:.1f} GB — فكر في نقله أو حذف محتوياته غير الضرورية"
                       for d in result[:5])
            self.lbl_recommendations.setText(recs)
            self.lbl_recommendations.setStyleSheet("color: #ffcc80; font-size: 12px;")

    def _clean_temp(self):
        """تنظيف الملفات المؤقتة."""
        reply = QMessageBox.question(self, "تأكيد التنظيف",
                                      "سيتم حذف الملفات المؤقتة. هل تريد المتابعة؟",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return

        self.lbl_status.setText("جاري التنظيف...")
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 12px;")

        deleted, freed = SystemInfo.clean_temp_files()
        freed_str = SystemInfo.bytes_to_human(freed)
        self.lbl_status.setText(f"✅ تم حذف {deleted} ملف وتحرير {freed_str}")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-size: 12px;")

        QMessageBox.information(self, "تم التنظيف",
                                f"تم حذف {deleted} ملف مؤقت\nتم تحرير {freed_str}")

    def _scan_apps(self):
        """حساب حجم التطبيقات المثبتة."""
        self.lbl_status.setText("جاري حساب حجم التطبيقات...")
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 12px;")
        self.btn_apps.setEnabled(False)

        self._app_scanner = AppSizeThread()
        self._app_scanner.finished.connect(self._on_apps_done)
        self._app_scanner.progress.connect(self.lbl_status.setText)
        self._app_scanner.start()

    def _on_apps_done(self, result):
        self.btn_apps.setEnabled(True)
        self.lbl_status.setText(f"تم العثور على {len(result)} تطبيق مثبت")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-size: 12px;")

        self.results_table.setRowCount(len(result))
        self.results_table.setHorizontalHeaderLabels(["التطبيق", "الحجم", "الإصدار"])
        for i, app in enumerate(result):
            self.results_table.setItem(i, 0, QTableWidgetItem(app.get("name", "")))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{app.get('size_mb', 0):.1f} MB"))
            self.results_table.setItem(i, 2, QTableWidgetItem(app.get("version", "")))

        if result:
            total_size = sum(a.get("size_mb", 0) for a in result)
            top5 = sorted(result, key=lambda x: x.get("size_mb", 0), reverse=True)[:5]
            recs = f"الحجم الكلي للتطبيقات: {total_size:.0f} MB\n\n"
            recs += "\n".join(f"• {a['name']}: {a['size_mb']:.0f} MB — فكر في إزالته إن لم تعد بحاجته" for a in top5)
            self.lbl_recommendations.setText(recs)
            self.lbl_recommendations.setStyleSheet("color: #80ffcc; font-size: 12px;")

    def stop(self):
        pass
