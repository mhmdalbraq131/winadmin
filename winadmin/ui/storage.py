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
import os
from core.system_info import SystemInfo


class DiskInfoThread(QThread):
    """قراءة معلومات الأقراص خارج خيط الواجهة."""
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self):
        try:
            self.finished.emit(SystemInfo.get_disk_info())
        except Exception as exc:
            self.failed.emit(str(exc))


class StorageScannerThread(QThread):
    """مسح مجلدات المستوى الأول في الخلفية مع إمكانية الإلغاء."""
    finished = pyqtSignal(list)
    failed = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, path: str, min_size_mb: int = 500):
        super().__init__()
        self.path = path
        self.min_size_mb = min_size_mb

    def run(self):
        try:
            threshold = self.min_size_mb * 1024 * 1024
            results = []
            entries = []
            with os.scandir(self.path) as it:
                entries = [e for e in it if e.is_dir(follow_symlinks=False)]

            for index, entry in enumerate(entries, 1):
                if self.isInterruptionRequested():
                    return
                total = 0
                try:
                    for root, dirs, files in os.walk(entry.path, topdown=True):
                        if self.isInterruptionRequested():
                            return
                        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(root, d))]
                        for name in files:
                            if self.isInterruptionRequested():
                                return
                            try:
                                total += os.path.getsize(os.path.join(root, name))
                            except (OSError, PermissionError):
                                continue
                        # لا نحتاج حساب مجلدات ضخمة جدًا بدقة كاملة؛ هذا يمنع فحص القرص لساعات.
                        if total >= threshold * 10:
                            break
                except (OSError, PermissionError):
                    continue

                if total >= threshold:
                    results.append({
                        "path": entry.path,
                        "size_mb": round(total / (1024 * 1024), 1),
                        "size_gb": round(total / (1024 * 1024 * 1024), 2),
                    })
                self.progress.emit(f"جاري المسح... {index}/{len(entries)}")

            if not self.isInterruptionRequested():
                self.finished.emit(sorted(results, key=lambda x: x["size_mb"], reverse=True))
        except Exception as exc:
            self.failed.emit(str(exc))


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
        self._scanner = None
        self._app_scanner = None
        self._disk_worker = None
        self._updates_started = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("💾 إدارة التخزين")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # معلومات الأقراص: تُحمّل بعد ظهور الصفحة حتى لا يتباطأ الانتقال.
        self.disks_layout = QVBoxLayout()
        self.disks_layout.setSpacing(8)
        loading = QLabel("جاري قراءة معلومات الأقراص...")
        loading.setStyleSheet("color:#aaa; padding:8px;")
        self.disks_layout.addWidget(loading)
        layout.addLayout(self.disks_layout)

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

    def start_updates(self):
        """ابدأ جمع بيانات التخزين بعد ظهور الصفحة."""
        if self._updates_started:
            return
        self._updates_started = True
        self._load_disk_info()

    def _load_disk_info(self):
        if self._disk_worker is not None and self._disk_worker.isRunning():
            return
        self._disk_worker = DiskInfoThread()
        self._disk_worker.finished.connect(self._on_disk_info)
        self._disk_worker.failed.connect(self._on_disk_failed)
        self._disk_worker.finished.connect(lambda *_: self._clear_disk_worker())
        self._disk_worker.failed.connect(lambda *_: self._clear_disk_worker())
        self._disk_worker.start()

    def _clear_disk_worker(self):
        worker = self._disk_worker
        self._disk_worker = None
        if worker is not None:
            worker.deleteLater()

    def _on_disk_failed(self, message):
        self.disks_layout.itemAt(0).widget().setText("تعذر قراءة معلومات الأقراص.")

    def _on_disk_info(self, disks):
        while self.disks_layout.count():
            item = self.disks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for d in disks:
            disk_group = QGroupBox(f"{d.get('device', '')} — {d.get('mountpoint', '')}")
            disk_group.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 15px; }")
            disk_layout = QVBoxLayout(disk_group)
            bar = QProgressBar()
            bar.setMaximum(100)
            pct = d.get("percent", 0)
            bar.setValue(int(pct))
            color = "#f44336" if pct >= 90 else "#ff9800" if pct >= 75 else "#4CAF50"
            bar.setStyleSheet(f"QProgressBar {{ background:#1e1e32; border:none; border-radius:4px; text-align:center; color:white; }} QProgressBar::chunk {{ background:{color}; border-radius:3px; }}")
            bar.setFormat(f"{pct:.1f}% — {SystemInfo.bytes_to_human(d.get('used',0))} / {SystemInfo.bytes_to_human(d.get('total',0))}")
            disk_layout.addWidget(bar)
            info_lbl = QLabel(f"المتاح: {SystemInfo.bytes_to_human(d.get('free',0))} | النوع: {d.get('fstype','—')}")
            info_lbl.setStyleSheet("color:#888; font-size:11px;")
            disk_layout.addWidget(info_lbl)
            self.disks_layout.addWidget(disk_group)
        self.disks_layout.addStretch()

    def _scan_large_dirs(self):
        """المسح عن مجلدات كبيرة."""
        scan_path = "C:\\" if SystemInfo.IS_WINDOWS else "/"
        self.lbl_status.setText("جاري المسح... قد يستغرق بضع دقائق")
        self.lbl_status.setStyleSheet("color: #ff9800; font-size: 12px;")
        self.btn_scan.setEnabled(False)

        self._scanner = StorageScannerThread(scan_path)
        self._scanner.finished.connect(self._on_scan_done)
        self._scanner.failed.connect(self._on_scan_failed)
        self._scanner.progress.connect(self.lbl_status.setText)
        self._scanner.start()

    def _on_scan_failed(self, message):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText("تعذر فحص المجلدات")
        self.lbl_status.setStyleSheet("color: #f44336; font-size: 12px;")
        self._scanner = None

    def _on_scan_done(self, result):
        self.btn_scan.setEnabled(True)
        self.lbl_status.setText(f"تم العثور على {len(result)} مجلد كبير")
        self.lbl_status.setStyleSheet("color: #4CAF50; font-size: 12px;")

        self.results_table.setRowCount(len(result))
        for i, d in enumerate(result):
            self.results_table.setItem(i, 0, QTableWidgetItem(d.get("path", "")))
            self.results_table.setItem(i, 1, QTableWidgetItem(f"{d.get('size_gb', 0):.2f} GB"))
            self.results_table.setItem(i, 2, QTableWidgetItem(f"{d.get('size_mb', 0):.1f} MB"))

        self._scanner = None
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
        for attr in ("_scanner", "_app_scanner", "_disk_worker"):
            worker = getattr(self, attr, None)
            if worker is not None and worker.isRunning():
                try:
                    worker.requestInterruption()
                    worker.quit()
                    worker.wait(1000)
                except Exception:
                    pass
            setattr(self, attr, None)
