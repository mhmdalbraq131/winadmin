"""واجهة التقارير المحسّنة: تقليل التكدس وإضافة الطباعة."""

import os
import csv
import json
from PyQt5.QtWidgets import QPushButton, QMessageBox, QFileDialog
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
        requested = self._report_sections_for_collection or [
            "device", "cpu", "memory", "storage", "network",
            "services", "security", "processes"
        ]
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
        payload = {}
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
                        "fd": conn.fd, "family": str(conn.family), "type": str(conn.type),
                        "status": conn.status,
                        "laddr": str(conn.laddr) if conn.laddr else "",
                        "raddr": str(conn.raddr) if conn.raddr else "", "pid": conn.pid,
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

    def _export_csv(self):
        """تصدير كامل السجل، مع إبقاء أخذ العينات مقتصراً على عرض الجدول."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "تصدير CSV", "winadmin_perf.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            data = self.db.get_performance_history_raw(720) if hasattr(self.db, "get_performance_history_raw") else self.db.get_performance_history(720)
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "CPU %", "RAM %", "Disk %", "RAM Used", "RAM Total", "Disk Used", "Disk Total", "Net Sent", "Net Recv"])
                for row in data:
                    writer.writerow([
                        row.get("timestamp", ""), f"{row.get('cpu_percent', 0):.1f}",
                        f"{row.get('ram_percent', 0):.1f}", f"{row.get('disk_percent', 0):.1f}",
                        row.get("ram_used", 0), row.get("ram_total", 0), row.get("disk_used", 0),
                        row.get("disk_total", 0), row.get("net_bytes_sent", 0), row.get("net_bytes_recv", 0),
                    ])
            QMessageBox.information(self, "تم", f"تم التصدير إلى:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"فشل التصدير: {exc}")

    def _export_json(self):
        """تصدير كامل السجل بصيغة JSON."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "تصدير JSON", "winadmin_perf.json", "JSON Files (*.json)"
        )
        if not file_path:
            return
        try:
            data = self.db.get_performance_history_raw(720) if hasattr(self.db, "get_performance_history_raw") else self.db.get_performance_history(720)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "تم", f"تم التصدير إلى:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ", f"فشل التصدير: {exc}")

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
