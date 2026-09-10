"""
ui/reports.py — السجلات والتقارير
عرض سجلات الأداء والأخطاء، إنشاء تقارير وتصديرها.
"""

import os
import csv
import json
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTableWidget, QTableWidgetItem,
                              QHeaderView, QComboBox, QDateEdit,
                              QFileDialog, QMessageBox, QTabWidget,
                              QGroupBox, QGridLayout, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from core.system_info import SystemInfo


class ReportsWidget(QWidget):
    """السجلات والتقارير — عرض وتصدير."""

    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("📊 السجلات والتقارير")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ تبويبات ─
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a3e; background: #1a1a2e; }
            QTabBar::tab { background: #1e1e32; color: #aaa; padding: 8px 20px; border: 1px solid #2a2a3e; }
            QTabBar::tab:selected { background: #2a2a4a; color: #fff; }
        """)

        # ── تبويب سجل الأداء ──
        perf_tab = QWidget()
        perf_layout = QVBoxLayout(perf_tab)

        # خيار النطاق الزمني
        range_layout = QHBoxLayout()
        lbl_range = QLabel("الفترة:")
        lbl_range.setStyleSheet("color: #aaa; font-size: 12px;")
        range_layout.addWidget(lbl_range)

        self.perf_range = QComboBox()
        self.perf_range.addItems(["آخر ساعة", "آخر 6 ساعات", "آخر 24 ساعة", "آخر 7 أيام", "آخر 30 يوم"])
        self.perf_range.setStyleSheet("""
            QComboBox { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; border-radius: 4px; padding: 5px; }
            QComboBox QAbstractItemView { background: #1e1e32; color: #e0e0e0; }
        """)
        self.perf_range.currentIndexChanged.connect(self._load_perf_log)
        range_layout.addWidget(self.perf_range)

        btn_load = QPushButton("تحميل")
        btn_load.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 5px 12px; border-radius: 4px;")
        btn_load.clicked.connect(self._load_perf_log)
        range_layout.addWidget(btn_load)
        range_layout.addStretch()
        perf_layout.addLayout(range_layout)

        self.perf_table = QTableWidget()
        self.perf_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
        """)
        self.perf_table.setColumnCount(6)
        self.perf_table.setHorizontalHeaderLabels(["الوقت", "CPU %", "RAM %", "القرص %", "رفع", "تنزيل"])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.perf_table.setEditTriggers(QTableWidget.NoEditTriggers)
        perf_layout.addWidget(self.perf_table)

        self.tabs.addTab(perf_tab, "📈 سجل الأداء")

        # ── تبويب سجل الأخطاء ──
        error_tab = QWidget()
        error_layout = QVBoxLayout(error_tab)

        btn_load_errors = QPushButton("🔄 تحميل الأخطاء")
        btn_load_errors.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 5px 12px; border-radius: 4px;")
        btn_load_errors.clicked.connect(self._load_error_log)
        error_layout.addWidget(btn_load_errors)

        self.error_table = QTableWidget()
        self.error_table.setStyleSheet(self.perf_table.styleSheet())
        self.error_table.setColumnCount(5)
        self.error_table.setHorizontalHeaderLabels(["الوقت", "المصدر", "معرّف الحدث", "المستوى", "الرسالة"])
        self.error_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.error_table.setEditTriggers(QTableWidget.NoEditTriggers)
        error_layout.addWidget(self.error_table)

        self.tabs.addTab(error_tab, "🔴 سجل الأخطاء")

        # ── تبويب التنبيهات ──
        alert_tab = QWidget()
        alert_layout = QVBoxLayout(alert_tab)

        btn_load_alerts = QPushButton("🔄 تحميل التنبيهات")
        btn_load_alerts.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 5px 12px; border-radius: 4px;")
        btn_load_alerts.clicked.connect(self._load_alerts)
        alert_layout.addWidget(btn_load_alerts)

        self.alert_table = QTableWidget()
        self.alert_table.setStyleSheet(self.perf_table.styleSheet())
        self.alert_table.setColumnCount(5)
        self.alert_table.setHorizontalHeaderLabels(["الوقت", "النوع", "الخطورة", "الرسالة", "القيمة"])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alert_table.setEditTriggers(QTableWidget.NoEditTriggers)
        alert_layout.addWidget(self.alert_table)

        self.tabs.addTab(alert_tab, "⚠ التنبيهات")

        # ── تبويب التقارير ──
        reports_tab = QWidget()
        reports_layout = QVBoxLayout(reports_tab)

        # أزرار إنشاء التقارير
        report_btns = QHBoxLayout()

        btn_daily = QPushButton("📄 تقرير يومي")
        btn_daily.setStyleSheet("background: #1c2e3e; color: #80ccff; border: none; padding: 8px 16px; border-radius: 4px;")
        btn_daily.clicked.connect(lambda: self._generate_report("daily"))
        report_btns.addWidget(btn_daily)

        btn_weekly = QPushButton("📊 تقرير أسبوعي")
        btn_weekly.setStyleSheet("background: #2e1c3e; color: #cc80ff; border: none; padding: 8px 16px; border-radius: 4px;")
        btn_weekly.clicked.connect(lambda: self._generate_report("weekly"))
        report_btns.addWidget(btn_weekly)

        reports_layout.addLayout(report_btns)

        # خيارات التقرير: أجزاء النظام المراد تضمينها
        report_options = QGroupBox("حدد أجزاء التقرير / Select report sections")
        report_options.setStyleSheet("QGroupBox { color: #e0e0e0; border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 12px; }")
        report_opts_layout = QGridLayout(report_options)
        self.report_checkboxes = {}
        option_labels = [
            ("all", "الكل / All", True),
            ("device", "الجهاز / Device", False),
            ("cpu", "المعالج / CPU", False),
            ("memory", "الذاكرة / Memory", False),
            ("storage", "التخزين / Storage", False),
            ("network", "الشبكة / Network", False),
            ("services", "الخدمات / Services", False),
            ("security", "الأمان / Security", False),
            ("processes", "العمليات / Processes", False),
        ]
        for idx, (key, text, checked) in enumerate(option_labels):
            checkbox = QCheckBox(text)
            checkbox.setChecked(checked)
            checkbox.stateChanged.connect(lambda state, k=key: self._toggle_report_section(k, state))
            self.report_checkboxes[key] = checkbox
            report_opts_layout.addWidget(checkbox, idx // 3, idx % 3)
        reports_layout.addWidget(report_options)

        report_generation = QHBoxLayout()
        btn_custom = QPushButton("إنشاء تقرير مخصّص / Generate custom report")
        btn_custom.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 16px; border-radius: 4px;")
        btn_custom.clicked.connect(lambda: self._generate_custom_report())
        report_generation.addWidget(btn_custom)
        reports_layout.addLayout(report_generation)

        # أزرار التصدير
        export_btns = QHBoxLayout()

        btn_export_csv = QPushButton("📥 تصدير CSV")
        btn_export_csv.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        btn_export_csv.clicked.connect(self._export_csv)
        export_btns.addWidget(btn_export_csv)

        btn_export_json = QPushButton("📥 تصدير JSON")
        btn_export_json.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        btn_export_json.clicked.connect(self._export_json)
        export_btns.addWidget(btn_export_json)

        reports_layout.addLayout(export_btns)

        self.reports_table = QTableWidget()
        self.reports_table.setStyleSheet(self.perf_table.styleSheet())
        self.reports_table.setColumnCount(4)
        self.reports_table.setHorizontalHeaderLabels(["الوقت", "النوع", "المسار", "الملخص"])
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setEditTriggers(QTableWidget.NoEditTriggers)
        reports_layout.addWidget(self.reports_table)

        self.tabs.addTab(reports_tab, "📑 التقارير")

        layout.addWidget(self.tabs)

        # تحميل أولي
        self._load_perf_log()
        self._load_error_log()
        self._load_alerts()
        self._load_reports()

    def _load_perf_log(self):
        """تحميل سجل الأداء."""
        hours_map = {0: 1, 1: 6, 2: 24, 3: 168, 4: 720}
        hours = hours_map.get(self.perf_range.currentIndex(), 24)
        data = self.db.get_performance_history(hours)

        self.perf_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.perf_table.setItem(i, 0, QTableWidgetItem(row.get("timestamp", "")[:19]))
            self.perf_table.setItem(i, 1, QTableWidgetItem(f"{row.get('cpu_percent', 0):.1f}"))
            self.perf_table.setItem(i, 2, QTableWidgetItem(f"{row.get('ram_percent', 0):.1f}"))
            self.perf_table.setItem(i, 3, QTableWidgetItem(f"{row.get('disk_percent', 0):.1f}"))
            self.perf_table.setItem(i, 4, QTableWidgetItem(SystemInfo.bytes_to_human(row.get('net_bytes_sent', 0))))
            self.perf_table.setItem(i, 5, QTableWidgetItem(SystemInfo.bytes_to_human(row.get('net_bytes_recv', 0))))

    def _load_error_log(self):
        """تحميل سجل الأخطاء."""
        data = self.db.get_recent_errors(50)
        self.error_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.error_table.setItem(i, 0, QTableWidgetItem(row.get("timestamp", "")[:19]))
            self.error_table.setItem(i, 1, QTableWidgetItem(row.get("source", "")))
            self.error_table.setItem(i, 2, QTableWidgetItem(str(row.get("event_id", ""))))
            level_item = QTableWidgetItem(row.get("level", ""))
            if row.get("level", "").lower() == "error":
                level_item.setForeground(QColor("#f44336"))
            elif row.get("level", "").lower() == "warning":
                level_item.setForeground(QColor("#ff9800"))
            self.error_table.setItem(i, 3, level_item)
            self.error_table.setItem(i, 4, QTableWidgetItem((row.get("message", ""))[:150]))

    def _load_alerts(self):
        """تحميل التنبيهات."""
        data = self.db.get_recent_alerts(50, acknowledged=False)
        self.alert_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.alert_table.setItem(i, 0, QTableWidgetItem(row.get("timestamp", "")[:19]))
            self.alert_table.setItem(i, 1, QTableWidgetItem(row.get("alert_type", "")))
            sev_item = QTableWidgetItem(row.get("severity", ""))
            if row.get("severity") == "critical":
                sev_item.setForeground(QColor("#f44336"))
            else:
                sev_item.setForeground(QColor("#ff9800"))
            self.alert_table.setItem(i, 2, sev_item)
            self.alert_table.setItem(i, 3, QTableWidgetItem(row.get("message", "")))
            self.alert_table.setItem(i, 4, QTableWidgetItem(f"{row.get('value', 0):.1f}%" if row.get('value') else ""))

    def _load_reports(self):
        """تحميل قائمة التقارير السابقة."""
        data = self.db.get_reports()
        self.reports_table.setRowCount(len(data))
        for i, row in enumerate(data):
            self.reports_table.setItem(i, 0, QTableWidgetItem(row.get("timestamp", "")[:19]))
            self.reports_table.setItem(i, 1, QTableWidgetItem(row.get("report_type", "")))
            self.reports_table.setItem(i, 2, QTableWidgetItem(row.get("file_path", "")))
            self.reports_table.setItem(i, 3, QTableWidgetItem(row.get("summary", "")[:200]))

    def _toggle_report_section(self, key: str, state):
        if key == "all" and state == 2:
            for checkbox in self.report_checkboxes.values():
                if checkbox is not self.report_checkboxes["all"]:
                    checkbox.setChecked(True)
        elif key == "all" and state == 0:
            for checkbox in self.report_checkboxes.values():
                checkbox.setChecked(False)

    def _selected_report_sections(self):
        if self.report_checkboxes.get("all").isChecked():
            return [
                "device", "cpu", "memory", "storage", "network",
                "services", "security", "processes"
            ]
        return [key for key, checkbox in self.report_checkboxes.items() if key != "all" and checkbox.isChecked()]

    def _collect_report_payload(self):
        payload = {
            "device": SystemInfo.get_system_overview(),
            "cpu": SystemInfo.get_cpu_info(),
            "memory": SystemInfo.get_memory_info(),
            "storage": SystemInfo.get_disk_info(),
            "network": SystemInfo.get_network_info(),
            "services": SystemInfo.get_services(),
            "security": SystemInfo.get_security_info(),
            "processes": SystemInfo.get_processes(),
        }
        payload["network"]["connections"] = []
        try:
            import psutil
            for conn in psutil.net_connections(kind='inet')[:20]:
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
        payload = self._collect_report_payload()
        lines = []
        lines.append("WinAdmin System Report / تقرير نظام WinAdmin")
        lines.append(f"Generated at / تاريخ الإعداد: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        for section in selected_sections:
            section_data = payload.get(section, {})
            if section == "device":
                lines.append("[Device / الجهاز]")
                lines.append(f"- Hostname / اسم الجهاز: {section_data.get('hostname', 'N/A')}")
                lines.append(f"- OS / نظام التشغيل: {section_data.get('os', 'N/A')}")
                lines.append(f"- Architecture / البنية: {section_data.get('arch', 'N/A')}")
                lines.append(f"- Processor / المعالج: {section_data.get('processor', 'N/A')}")
                lines.append(f"- Uptime / زمن التشغيل: {section_data.get('uptime', 'N/A')}")
            elif section == "cpu":
                lines.append("[CPU / المعالج]")
                lines.append(f"- Usage / الاستخدام: {section_data.get('percent', 0):.1f}%")
                lines.append(f"- Logical cores / النوى المنطقية: {section_data.get('count_logical', 0)}")
                lines.append(f"- Physical cores / النوى المادية: {section_data.get('count_physical', 0)}")
                lines.append(f"- Current frequency / تردد التشغيل الحالي: {section_data.get('freq_current', 0):.1f} MHz")
            elif section == "memory":
                lines.append("[Memory / الذاكرة]")
                lines.append(f"- Total / الكلي: {SystemInfo.bytes_to_human(section_data.get('total', 0))}")
                lines.append(f"- Used / المستخدم: {SystemInfo.bytes_to_human(section_data.get('used', 0))}")
                lines.append(f"- Available / المتاح: {SystemInfo.bytes_to_human(section_data.get('available', 0))}")
                lines.append(f"- Usage / الاستخدام: {section_data.get('percent', 0):.1f}%")
            elif section == "storage":
                lines.append("[Storage / التخزين]")
                for disk in section_data:
                    lines.append(f"- {disk.get('mountpoint', 'Drive')} / {disk.get('device', '')}: {disk.get('percent', 0):.1f}% used / مستخدم | free / متاح: {SystemInfo.bytes_to_human(disk.get('free', 0))}")
            elif section == "network":
                lines.append("[Network / الشبكة]")
                lines.append(f"- Bytes Sent / البايتات المرسلة: {SystemInfo.bytes_to_human(section_data.get('bytes_sent', 0))}")
                lines.append(f"- Bytes Received / البايتات المستلمة: {SystemInfo.bytes_to_human(section_data.get('bytes_recv', 0))}")
                lines.append(f"- Packets Sent / الحزم المرسلة: {section_data.get('packets_sent', 0)}")
                lines.append(f"- Packets Received / الحزم المستلمة: {section_data.get('packets_recv', 0)}")
                lines.append(f"- Errors In / الأخطاء الداخل: {section_data.get('errin', 0)}")
                lines.append(f"- Errors Out / الأخطاء الخارج: {section_data.get('errout', 0)}")
                for iface in section_data.get('interfaces', []):
                    lines.append(f"- Interface / الواجهة: {iface.get('name', 'N/A')} | Speed / السرعة: {iface.get('speed', 0)} Mbps | Up / حالة التشغيل: {iface.get('isup', False)}")
                for conn in section_data.get('connections', [])[:10]:
                    lines.append(f"- Connection / الاتصال: {conn.get('status', 'N/A')} | Local / المحلي: {conn.get('laddr', '')} | Remote / البعيد: {conn.get('raddr', '')} | PID: {conn.get('pid', '')}")
            elif section == "services":
                lines.append("[Services / الخدمات]")
                for svc in section_data[:10]:
                    lines.append(f"- {svc.get('name', 'N/A')} | {svc.get('status', 'Unknown')} | {svc.get('start_mode', 'N/A')}")
            elif section == "security":
                lines.append("[Security / الأمان]")
                lines.append(f"- Defender / Windows Defender: {section_data.get('defender_status', 'N/A')}")
                lines.append(f"- Pending updates / التحديثات المعلقة: {len(section_data.get('pending_updates', []))}")
                lines.append(f"- Event errors / أخطاء السجل: {len(section_data.get('event_errors', []))}")
                for service in section_data.get('critical_services', [])[:5]:
                    lines.append(f"- Critical service / الخدمة الحرجة: {service.get('name', 'N/A')} | {service.get('status', 'N/A')}")
            elif section == "processes":
                lines.append("[Processes / العمليات]")
                for proc in section_data[:10]:
                    lines.append(f"- {proc.get('name', 'N/A')} | CPU: {proc.get('cpu_percent', 0):.1f}% | RAM: {proc.get('memory_percent', 0):.1f}% | PID: {proc.get('pid', 'N/A')}")
            lines.append("")

        return "\n".join(lines)

    def _generate_custom_report(self):
        sections = self._selected_report_sections()
        if not sections:
            QMessageBox.information(self, "تحديد", "يرجى اختيار قسم واحد على الأقل / Please select at least one section.")
            return
        report_text = self._build_bilingual_report(sections)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"winadmin_report_custom_{timestamp}.txt"
        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ تقرير مخصص / Save custom report", default_name, "Text Files (*.txt)")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            self.db.add_report("custom", file_path, "Custom bilingual report / تقرير مخصص ثنائي اللغة")
            self._load_reports()
            QMessageBox.information(self, "تم / Done", f"تم حفظ التقرير في:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "خطأ / Error", f"فشل إنشاء التقرير: {exc}")

    def _generate_report(self, report_type: str):
        """إنشاء تقرير يومي أو أسبوعي."""
        try:
            hours = 24 if report_type == "daily" else 168
            perf_data = self.db.get_performance_history(hours)
            alerts_data = self.db.get_recent_alerts(50)
            errors_data = self.db.get_recent_errors(50)

            if not perf_data:
                QMessageBox.information(self, "تنبيه", "لا توجد بيانات كافية لإنشاء تقرير")
                return

            cpu_avg = sum(r.get('cpu_percent', 0) for r in perf_data) / len(perf_data)
            ram_avg = sum(r.get('ram_percent', 0) for r in perf_data) / len(perf_data)
            disk_avg = sum(r.get('disk_percent', 0) for r in perf_data) / len(perf_data)
            cpu_max = max(r.get('cpu_percent', 0) for r in perf_data)
            ram_max = max(r.get('ram_percent', 0) for r in perf_data)

            summary = (
                f"تقرير {'يومي' if report_type == 'daily' else 'أسبوعي'}\n"
                f"الفترة: آخر {hours} ساعة\n"
                f"CPU: avg={cpu_avg:.1f}% max={cpu_max:.1f}%\n"
                f"RAM: avg={ram_avg:.1f}% max={ram_max:.1f}%\n"
                f"Disk avg: {disk_avg:.1f}%\n"
                f"تنبيهات: {len(alerts_data)} | أخطاء: {len(errors_data)}"
            )

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_name = f"winadmin_report_{report_type}_{timestamp}.txt"
            file_path, _ = QFileDialog.getSaveFileName(self, "حفظ التقرير", default_name,
                                                       "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)")
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(summary + "\n\n")
                    f.write("=== بيانات الأداء ===\n")
                    for r in perf_data:
                        f.write(f"{r.get('timestamp','')} | CPU: {r.get('cpu_percent',0):.1f}% | RAM: {r.get('ram_percent',0):.1f}% | Disk: {r.get('disk_percent',0):.1f}%\n")
                    f.write("\n=== التنبيهات ===\n")
                    for a in alerts_data:
                        f.write(f"{a.get('timestamp','')} [{a.get('severity','')}] {a.get('message','')}\n")
                    f.write("\n=== الأخطاء ===\n")
                    for e in errors_data:
                        f.write(f"{e.get('timestamp','')} [{e.get('source','')}] {e.get('message','')}\n")

                self.db.add_report(report_type, file_path, summary)
                self._load_reports()
                QMessageBox.information(self, "تم", f"تم حفظ التقرير في:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل إنشاء التقرير: {e}")

    def _export_csv(self):
        """تصدير سجل الأداء كـ CSV."""
        file_path, _ = QFileDialog.getSaveFileName(self, "تصدير CSV", "winadmin_perf.csv", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            data = self.db.get_performance_history(720)  # آخر 30 يوم
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "CPU %", "RAM %", "Disk %", "RAM Used",
                                "RAM Total", "Disk Used", "Disk Total", "Net Sent", "Net Recv"])
                for row in data:
                    writer.writerow([
                        row.get("timestamp", ""),
                        f"{row.get('cpu_percent', 0):.1f}",
                        f"{row.get('ram_percent', 0):.1f}",
                        f"{row.get('disk_percent', 0):.1f}",
                        row.get("ram_used", 0),
                        row.get("ram_total", 0),
                        row.get("disk_used", 0),
                        row.get("disk_total", 0),
                        row.get("net_bytes_sent", 0),
                        row.get("net_bytes_recv", 0),
                    ])
            QMessageBox.information(self, "تم", f"تم التصدير إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل التصدير: {e}")

    def _export_json(self):
        """تصدير سجل الأداء كـ JSON."""
        file_path, _ = QFileDialog.getSaveFileName(self, "تصدير JSON", "winadmin_perf.json", "JSON Files (*.json)")
        if not file_path:
            return

        try:
            data = self.db.get_performance_history(720)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            QMessageBox.information(self, "تم", f"تم التصدير إلى:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "خطأ", f"فشل التصدير: {e}")

    def stop(self):
        pass
