"""واجهة فحص جاهزية الجهاز والمساعد الذكي المحلي."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QProgressBar, QGroupBox, QMessageBox
)
from core.hardware_advisor import HardwareAssessmentWorker


class HardwareAdvisorDialog(QDialog):
    """فحص العتاد وعرض الاستخدامات المناسبة والتوصيات."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("فحص جاهزية الجهاز والمساعد الذكي")
        self.setMinimumSize(900, 650)
        self.setLayoutDirection(Qt.RightToLeft)
        self.worker = None
        self._build_ui()
        self.start_scan()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("🤖 المساعد الذكي — فحص جاهزية الجهاز")
        title.setStyleSheet("font-size: 21px; font-weight: bold; color: #4CAF50;")
        layout.addWidget(title)

        self.status = QLabel("جاري فحص مواصفات الجهاز…")
        self.status.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(self.status)

        self.specs = QTableWidget(0, 2)
        self.specs.setHorizontalHeaderLabels(["المكوّن", "المواصفات"])
        self.specs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.specs.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.specs.setEditTriggers(QTableWidget.NoEditTriggers)
        self.specs.setMaximumHeight(250)
        layout.addWidget(self.specs)

        self.uses_group = QGroupBox("🎯 الاستخدامات المناسبة")
        uses_layout = QVBoxLayout(self.uses_group)
        self.uses_label = QLabel("جاري التحليل…")
        self.uses_label.setWordWrap(True)
        uses_layout.addWidget(self.uses_label)
        layout.addWidget(self.uses_group)

        rec_group = QGroupBox("💡 توصيات المساعد الذكي لتحسين الأداء")
        rec_layout = QVBoxLayout(rec_group)
        self.recommendations = QTextEdit()
        self.recommendations.setReadOnly(True)
        rec_layout.addWidget(self.recommendations)
        layout.addWidget(rec_group, 1)

        buttons = QHBoxLayout()
        self.scan_button = QPushButton("🔄 إعادة الفحص")
        self.scan_button.clicked.connect(self.start_scan)
        buttons.addWidget(self.scan_button)
        buttons.addStretch()
        close = QPushButton("إغلاق")
        close.clicked.connect(self.accept)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def start_scan(self):
        if self.worker is not None and self.worker.isRunning():
            return
        self.scan_button.setEnabled(False)
        self.status.setText("جاري فحص المعالج والذاكرة والتخزين والبطاقة الرسومية…")
        self.worker = HardwareAssessmentWorker(self)
        self.worker.finished.connect(self._show_result)
        self.worker.error.connect(self._show_error)
        self.worker.start()

    def _show_result(self, result):
        self.scan_button.setEnabled(True)
        self.status.setText("اكتمل الفحص — تم تحليل مواصفات الجهاز محليًا")
        specs = result.get("specs", {})
        rows = [
            ("اسم الجهاز", specs.get("hostname", "—")),
            ("نظام التشغيل", specs.get("os", "—")),
            ("المعمارية", specs.get("architecture", "—")),
            ("المعالج", specs.get("cpu", "—")),
            ("الأنوية", f"{specs.get('physical_cores', 0)} فعلية / {specs.get('logical_cores', 0)} منطقية"),
            ("التردد الأقصى", f"{specs.get('frequency_ghz', 0)} GHz"),
            ("RAM", f"{specs.get('ram_gb', 0)} GB — المتاح {specs.get('ram_available_gb', 0)} GB"),
            ("القرص", f"{specs.get('disk_gb', 0)} GB — المتاح {specs.get('disk_free_gb', 0)} GB"),
            ("GPU", specs.get("gpu", "—")),
            ("VRAM", f"{specs.get('vram_gb', 0)} GB"),
        ]
        self.specs.setRowCount(len(rows))
        for i, (name, value) in enumerate(rows):
            self.specs.setItem(i, 0, QTableWidgetItem(name))
            self.specs.setItem(i, 1, QTableWidgetItem(str(value)))

        best = result.get("best_uses", [])
        self.uses_label.setText("\n".join(f"{i + 1}. {name} — ملاءمة تقريبية {score}%" for i, (name, score) in enumerate(best)))
        self.recommendations.setPlainText("\n".join(f"• {item}" for item in result.get("recommendations", [])))

    def _show_error(self, message):
        self.scan_button.setEnabled(True)
        self.status.setText("تعذر إكمال الفحص")
        QMessageBox.warning(self, "فشل الفحص", message)
