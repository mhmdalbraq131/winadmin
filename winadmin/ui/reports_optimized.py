"""واجهة التقارير المحسّنة: تقليل التكدس وإضافة الطباعة."""

import os
from PyQt5.QtWidgets import QPushButton, QMessageBox
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtGui import QTextDocument

from .reports import ReportsWidget as LegacyReportsWidget
from core.system_info import SystemInfo


class ReportsWidget(LegacyReportsWidget):
    """نسخة محسّنة متوافقة مع الواجهة القديمة."""

    def __init__(self, db_manager, parent=None):
        self._report_sections_for_collection = None
        super().__init__(db_manager, parent)

        try:
            reports_tab = self.tabs.widget(3)
            layout = reports_tab.layout()
            self.btn_print = QPushButton("🖨 طباعة التقرير المحدد")
            self.btn_print.setStyleSheet(
                "background: #24402a; color: #b8f5c0; border: none; "
                "padding: 6px 14px; border-radius: 4px;"
            )
            self.btn_print.clicked.connect(self._print_selected_report)
            layout.insertWidget(max(0, layout.count() - 1), self.btn_print)
        except Exception:
            self.btn_print = None

    def _collect_report_payload(self):
        """اجلب الأقسام المطلوبة فقط؛ لا تشغّل WMI/PowerShell بلا داعٍ."""
        requested = self._report_sections_for_collection
        if requested is None:
            requested = [
                "device", "cpu", "memory", "storage", "network",
                "services", "security", "processes"
            ]

        payload = {}
        providers = {
            "device": SystemInfo.get_system_overview,
            "cpu": SystemInfo.get_cpu_info,
            "memory": SystemInfo.get_memory_info,
            "storage": SystemInfo.get_disk_info,
            "network": SystemInfo.get_network_info,
            "services": SystemInfo.get_services,
            "security": SystemInfo.get_security_info,
            "processes": SystemInfo.get_processes,
        }
        for section in requested:
            getter = providers.get(section)
            if getter:
                try:
                    payload[section] = getter()
                except Exception:
                    payload[section] = {} if section not in ("storage", "services", "processes") else []

        if "network" in payload:
            payload["network"]["connections"] = []
            try:
                import psutil
                for conn in psutil.net_connections(kind="inet")[:20]:
                    payload["network"]["connections"].append({
                        "fd": conn.fd,
                        "family": str(conn.family),
                        "type": str(conn.type),
                        "status": conn.status,
                        "laddr": str(conn.laddr) if conn.laddr else "",
                        "raddr": str(conn.raddr) if conn.raddr else "",
                        "pid": conn.pid,
                    })
            except Exception:
                pass
        return payload

    def _build_bilingual_report(self, selected_sections):
        self._report_sections_for_collection = list(selected_sections)
        try:
            return super()._build_bilingual_report(selected_sections)
        finally:
            self._report_sections_for_collection = None

    def _print_selected_report(self):
        """طباعة التقرير المحفوظ المحدد عبر طابعة Windows."""
        row = self.reports_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "الطباعة", "اختر تقريراً من القائمة أولاً.")
            return

        path_item = self.reports_table.item(row, 2)
        if path_item is None:
            QMessageBox.warning(self, "الطباعة", "مسار التقرير غير متوفر.")
            return

        file_path = path_item.text().strip()
        if not file_path or not os.path.isfile(file_path):
            QMessageBox.warning(self, "الطباعة", "ملف التقرير غير موجود في المسار المسجل.")
            return

        try:
            with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            QMessageBox.critical(self, "الطباعة", f"تعذر قراءة التقرير:\n{exc}")
            return

        document = QTextDocument()
        document.setPlainText(content)
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("طباعة تقرير WinAdmin")
        if dialog.exec_() == QPrintDialog.Accepted:
            document.print_(printer)
