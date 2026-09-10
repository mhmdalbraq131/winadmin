"""
ui/commands.py — مركز أدوات مدير النظام (System Administrator Toolkit)
"""

import csv
import ctypes
import io
import json
import os
import re
import shlex
import subprocess
import sys
import time
from typing import Dict, List, Optional

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout,
    QWidget, QFileDialog, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox
)

from core.system_info import SystemInfo
from ui.processes import ProcessManagerWidget
from ui.services import ServiceManagerWidget
from ui.storage import StorageManagerWidget


def is_user_admin() -> bool:
    """تحقق إن المستخدم لديه صلاحية Administrator على Windows."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    """إعادة تشغيل التطبيق بصلاحيات Administrator عند الحاجة."""
    if os.name != "nt":
        return False
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = ' '.join(subprocess.list2cmdline(arg) for arg in sys.argv[1:])
        command = f'"{script_path}" {params}'.strip()
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, command, None, 1
        )
        return result > 32
    except Exception:
        return False


ALLOWLIST_PATTERNS = {
    "READ_ONLY": [
        r'^ipconfig(?:\s+/all|\s+/renew|\s+/release|\s+/flushdns)?$',
        r'^hostname$',
        r'^whoami(?:\s+/all)?$',
        r'^systeminfo$',
        r'^ver$',
        r'^winver$',
        r'^ping\s+[A-Za-z0-9.-]+(?:\s+-n\s+\d+)?$',
        r'^tracert\s+[A-Za-z0-9.-]+$',
        r'^pathping\s+[A-Za-z0-9.-]+$',
        r'^nslookup\s+[A-Za-z0-9.-]+$',
        r'^netstat\s+-ano$',
        r'^arp\s+-a$',
        r'^route\s+print$',
        r'^getmac$',
        r'^tasklist(?:\s+/svc)?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-ComputerInfo\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-CimInstance\s+Win32_(OperatingSystem|ComputerSystem|Processor)\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-Service\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-Volume\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-Disk\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-LocalUser\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-LocalGroup\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-MpComputerStatus\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-BitLockerVolume\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-HotFix\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-WUList\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-WinEvent\b.*"?$',
    ],
    "SAFE_ACTION": [
        r'^ipconfig\s+/flushdns$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-PSDrive\b.*"?$',
        r'^powershell\s+-NoProfile\s+-Command\s+"?Get-WinEvent\s+-LogName\s+\'.*\'\b.*"?$',
    ],
    "ADMIN_ACTION": [
        r'^sfc\s+/scannow$',
        r'^DISM\s+/Online\s+/Cleanup-Image\s+/CheckHealth$',
        r'^DISM\s+/Online\s+/Cleanup-Image\s+/ScanHealth$',
        r'^DISM\s+/Online\s+/Cleanup-Image\s+/RestoreHealth$',
        r'^chkdsk\s+[A-Za-z]:$',
        r'^net\s+localgroup\s+administrators$',
        r'^net\s+user$',
    ],
    "HIGH_RISK": [
        r'^taskkill\s+(/F\s+)?/PID\s+\d+$',
        r'^Stop-Process\s+-Id\s+\d+$',
        r'^Start-Process\s+.*$',
        r'^sc\s+config\s+\S+\s+start=\S+$',
        r'^cleanmgr$',
    ],
}

COMMAND_ALLOWLIST = {
    "READ_ONLY": {
        "ipconfig": {"allowed_args": ["/all", "/renew", "/release", "/flushdns"], "allow_no_args": True},
        "hostname": {"allow_no_args": True},
        "whoami": {"allowed_args": ["/all"], "allow_no_args": True},
        "systeminfo": {"allow_no_args": True},
        "ver": {"allow_no_args": True},
        "winver": {"allow_no_args": True},
        "ping": {"requires_target": True, "allowed_args": ["-n", "-w"]},
        "tracert": {"requires_target": True},
        "pathping": {"requires_target": True},
        "nslookup": {"requires_target": True},
        "netstat": {"allowed_args": ["-ano"]},
        "arp": {"allowed_args": ["-a"]},
        "route": {"allowed_args": ["print"]},
        "getmac": {"allow_no_args": True},
        "tasklist": {"allow_no_args": True, "allowed_args": ["/svc"]},
        "powershell": {"allow_script": True},
    },
    "SAFE_ACTION": {
        "ipconfig": {"allowed_args": ["/flushdns"]},
    },
    "ADMIN_ACTION": {
        "sfc": {"allowed_args": ["/scannow"]},
        "DISM": {"allowed_args": ["/Online", "/Cleanup-Image", "/CheckHealth", "/ScanHealth", "/RestoreHealth"]},
        "chkdsk": {"requires_drive": True},
    },
    "HIGH_RISK": {
        "taskkill": {"allow_no_args": False, "requires_pid": True},
        "Stop-Process": {"requires_id": True},
        "Start-Process": {"allow_no_args": False},
        "sc": {"allowed_args": ["config", "start", "stop", "query"]},
        "cleanmgr": {"allow_no_args": True},
    },
}


def build_system_health_report() -> Dict:
    """بناء تقرير صحي كامل يعتمد على البيانات الفعلية من SystemInfo."""
    overview = SystemInfo.get_system_overview()
    cpu = SystemInfo.get_cpu_info()
    memory = SystemInfo.get_memory_info()
    disks = SystemInfo.get_disk_info()
    network = SystemInfo.get_network_info()
    services = SystemInfo.get_services()
    security = SystemInfo.get_security_info()
    processes = SystemInfo.get_processes()

    status_checks = {
        "CPU": "GOOD",
        "RAM": "GOOD",
        "Disk": "GOOD",
        "Network": "GOOD",
        "Services": "GOOD",
        "Security": "GOOD",
        "Event Logs": "GOOD",
    }
    reasons = []

    if cpu.get("percent", 0) > 80:
        status_checks["CPU"] = "WARNING"
        reasons.append("High CPU usage detected.")
    if memory.get("percent", 0) > 80:
        status_checks["RAM"] = "WARNING"
        reasons.append("High memory usage detected.")

    if disks:
        low_disk = [d for d in disks if d.get("percent", 0) >= 85]
        if low_disk:
            status_checks["Disk"] = "WARNING"
            reasons.append("One or more drives are nearing capacity.")
    if network.get("errin", 0) > 0 or network.get("errout", 0) > 0:
        status_checks["Network"] = "WARNING"
        reasons.append("Network errors detected on interfaces.")

    stopped_services = [s for s in services if str(s.get("status", "")).lower() in {"stopped", "stop pending"}]
    if stopped_services:
        status_checks["Services"] = "WARNING"
        reasons.append(f"{len(stopped_services)} services are stopped.")

    if security.get("defender_status", "") and str(security.get("defender_status")).lower() not in {"مفعّل", "enabled", "on", "active"}:
        status_checks["Security"] = "WARNING"
        reasons.append("Windows Defender protection may be disabled or unavailable.")

    event_errors = security.get("event_errors", [])
    if event_errors:
        status_checks["Event Logs"] = "WARNING"
        reasons.append(f"{len(event_errors)} recent errors found in system logs.")

    critical = ["CRITICAL" if value in {"WARNING", "CRITICAL"} else "GOOD" for value in status_checks.values()]
    overall = "GOOD"
    if any(v == "WARNING" for v in status_checks.values()):
        overall = "WARNING"
    if any(v == "CRITICAL" for v in status_checks.values()):
        overall = "CRITICAL"

    report = {
        "overall_status": overall,
        "checks": status_checks,
        "hostname": overview.get("hostname", "N/A"),
        "os": overview.get("os", "N/A"),
        "uptime": overview.get("uptime", "N/A"),
        "cpu_percent": cpu.get("percent", 0),
        "ram_percent": memory.get("percent", 0),
        "disk_percent": max((d.get("percent", 0) for d in disks), default=0),
        "top_processes_cpu": sorted(processes, key=lambda p: float(p.get('cpu_percent', 0) or 0), reverse=True)[:5],
        "top_processes_ram": sorted(processes, key=lambda p: float(p.get('memory_percent', 0) or 0), reverse=True)[:5],
        "services": services,
        "stopped_services": stopped_services,
        "recommendations": reasons,
        "security": security,
    }
    return report


class HealthCheckRunner(QThread):
    """يحسب تقرير الصحة بشكل غير متزامن."""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        self.progress.emit('Collecting system overview...')
        try:
            report = build_system_health_report()
            self.finished.emit(report)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit({'overall_status': 'WARNING', 'checks': {}, 'recommendations': [str(exc)]})


def _strip_matching_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def _is_valid_host(value: str) -> bool:
    value = value.strip()
    if not value or value.lower() in ('localhost',):
        return True
    if re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){3}', value):
        octets = [int(p) for p in value.split('.')]
        return all(0 <= part <= 255 for part in octets)
    if re.fullmatch(r'[A-Za-z0-9.-]+', value):
        return True
    return False


class CommandRunner(QThread):
    """تنفيذ أوامر Windows بشكل غير متزامن."""

    output = pyqtSignal(str)
    finished = pyqtSignal(int, float)
    error = pyqtSignal(str)

    @staticmethod
    def validate_allowlist(cmd: str) -> str:
        command = (cmd or '').strip()
        if not command:
            raise ValueError("الأمر فارغ")

        if command.lower().startswith('powershell'):
            match = re.search(r'(?i)^powershell\s+-NoProfile\s+-Command\s+(.+)$', command)
            if not match:
                raise ValueError("أمر PowerShell غير مسموح")
            script = _strip_matching_quotes(match.group(1)).strip()
            if not script:
                raise ValueError("نص PowerShell فارغ")
            if re.search(r'&&|;|>|<', script, re.IGNORECASE):
                raise ValueError("تم رفض الأمر: يحتوي على عوامل shell غير مسموحة")
            if any(re.fullmatch(pattern, command, re.I) for group in ALLOWLIST_PATTERNS.values() for pattern in group):
                return command
            raise ValueError("هذا الأمر غير موجود في Allowlist")

        if re.search(r'&&|\|\||\||;|&|>|<', command, re.IGNORECASE):
            raise ValueError("تم رفض الأمر: يحتوي على عوامل shell غير مسموحة")

        try:
            parts = shlex.split(command, posix=False)
        except ValueError as exc:
            raise ValueError("صيغة الأمر غير صالحة") from exc
        if not parts:
            raise ValueError("الأمر فارغ")

        executable = parts[0].lower()
        safe_patterns = [pattern for group in ALLOWLIST_PATTERNS.values() for pattern in group]
        if any(re.fullmatch(pattern, command, re.I) for pattern in safe_patterns):
            return command

        if executable == 'ping':
            if len(parts) < 2 or not _is_valid_host(parts[1]):
                raise ValueError("PING يتطلب Host/IP صالح")
            if all(part.lower() not in {'-n', '-w'} for part in parts[2:]):
                return command
            return command

        raise ValueError("هذا الأمر غير مسموح به من قبل التطبيق")

    @staticmethod
    def _build_safe_command(cmd: str):
        """بناء قائمة معاملات آمنة دون استخدام shell=True."""
        command = (cmd or '').strip()
        if not command:
            raise ValueError("الأمر فارغ")
        CommandRunner.validate_allowlist(command)

        if command.lower().startswith('powershell'):
            match = re.search(r'(?i)^powershell\s+-NoProfile\s+-Command\s+(.+)$', command)
            if not match:
                raise ValueError("PowerShell command not allowed")
            script = _strip_matching_quotes(match.group(1)).strip()
            return ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', script]

        if command.lower().startswith('cmd /c') or command.lower().startswith('cmd.exe /c'):
            parts = shlex.split(command, posix=False)
            return ['cmd.exe', '/c', ' '.join(parts[2:]) if len(parts) > 2 else '']

        try:
            parts = shlex.split(command, posix=False)
        except ValueError as exc:
            raise ValueError("صيغة الأمر غير صالحة") from exc
        return parts if parts else [command]

    def __init__(self, cmd: str, cwd: str = None, shell: bool = False):
        super().__init__()
        self.cmd = cmd
        self.cwd = cwd
        self.shell = shell

    def run(self):
        start = time.perf_counter()
        try:
            safe_cmd = self._build_safe_command(self.cmd)
            proc = subprocess.Popen(
                safe_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                cwd=self.cwd,
                text=False,
            )

            while True:
                out = proc.stdout.readline()
                err = proc.stderr.readline()
                if not out and not err and proc.poll() is not None:
                    break
                if out:
                    self.output.emit(out.decode(errors='ignore'))
                if err:
                    self.output.emit(err.decode(errors='ignore'))

            remaining_err = proc.stderr.read()
            if remaining_err:
                self.output.emit(remaining_err.decode(errors='ignore'))
            remaining_out = proc.stdout.read()
            if remaining_out:
                self.output.emit(remaining_out.decode(errors='ignore'))

            proc.wait()
            self.finished.emit(proc.returncode, time.perf_counter() - start)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit(1, time.perf_counter() - start)


class NetworkDiagnosticWidget(QWidget):
    """Wizard بسيط لفحص شبكة Windows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel('Network Diagnostic')
        title.setStyleSheet('font-size: 16px; font-weight: bold;')
        layout.addWidget(title)

        self.steps = [
            ('Step 1: Network Adapter Status', 'powershell -NoProfile -Command "Get-NetAdapter | Select-Object Name, Status, InterfaceDescription, MacAddress | Format-Table -AutoSize"'),
            ('Step 2: IP Configuration', 'ipconfig /all'),
            ('Step 3: Gateway Connectivity', 'ping 127.0.0.1 -n 2'),
            ('Step 4: Internet Connectivity', 'ping 8.8.8.8 -n 2'),
            ('Step 5: DNS Resolution', 'nslookup example.com'),
            ('Step 6: Route Check', 'route print'),
            ('Step 7: Active Connections', 'netstat -ano'),
        ]

        self.progress = QPlainTextEdit()
        self.progress.setReadOnly(True)
        layout.addWidget(self.progress, 1)

        self.run_btn = QPushButton('Run Network Diagnostic')
        self.run_btn.clicked.connect(self._run)
        layout.addWidget(self.run_btn)

    def _run(self):
        self.progress.clear()
        self.progress.appendPlainText('NETWORK DIAGNOSTIC\n')
        self._runner = QThread()
        # لا نستخدم thread مستقل هنا لأن الفحوصات قصيرة، لكن نلتزم بتشغيلها بشكل غير متزامن مع QThread.
        from PyQt5.QtCore import QObject
        class _DiagWorker(QObject):
            progress = pyqtSignal(str)
            finished = pyqtSignal(dict)
            def __init__(self, steps):
                super().__init__()
                self.steps = steps
            def run(self):
                results = []
                for step_name, cmd in self.steps:
                    self.progress.emit(f'{step_name}...')
                    try:
                        safe = CommandRunner._build_safe_command(cmd)
                        proc = subprocess.Popen(safe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                        stdout, stderr = proc.communicate(timeout=25)
                        out = stdout.decode(errors='ignore')
                        err = stderr.decode(errors='ignore')
                        results.append({'step': step_name, 'success': proc.returncode == 0, 'output': out, 'error': err})
                    except Exception as exc:
                        results.append({'step': step_name, 'success': False, 'output': '', 'error': str(exc)})
                self.finished.emit({'steps': results, 'overall_status': 'WARNING' if any(not r['success'] for r in results) else 'OK'})

        worker = _DiagWorker(self.steps)
        thread = QThread()
        worker.moveToThread(thread)
        worker.progress.connect(self.progress.appendPlainText)
        worker.finished.connect(self._show_result)
        thread.started.connect(worker.run)
        thread.start()
        self._runner = thread

    def _show_result(self, payload):
        self.progress.appendPlainText('\nNETWORK DIAGNOSTIC SUMMARY\n')
        for idx, step in enumerate(payload['steps'], start=1):
            self.progress.appendPlainText(f'{idx}. {step["step"]}: {"OK" if step["success"] else "Failed"}\n')
            if step['error']:
                self.progress.appendPlainText(f'   Error: {step["error"][:300]}\n')
            if step['output']:
                self.progress.appendPlainText(f'   Output: {step["output"][:300]}\n')
        self.progress.appendPlainText(f'\nOverall Status: {payload["overall_status"]}\n')
        self._runner.quit()
        self._runner.wait(1000)


class EventLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_rows = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.log_combo = QComboBox()
        self.log_combo.addItems(['Application', 'System', 'Security'])
        top.addWidget(QLabel('Log'))
        top.addWidget(self.log_combo)

        self.level_combo = QComboBox()
        self.level_combo.addItems(['All', 'Error', 'Warning', 'Information', 'Critical'])
        top.addWidget(QLabel('Level'))
        top.addWidget(self.level_combo)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(10, 500)
        self.count_spin.setValue(50)
        top.addWidget(QLabel('Count'))
        top.addWidget(self.count_spin)

        self.event_id_edit = QLineEdit()
        self.event_id_edit.setPlaceholderText('Event ID filter')
        top.addWidget(self.event_id_edit)

        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText('Source filter')
        top.addWidget(self.source_edit)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText('Search in Message')
        top.addWidget(self.search_edit)

        self.search_btn = QPushButton('Search')
        self.search_btn.clicked.connect(self._load_events)
        top.addWidget(self.search_btn)

        self.clear_btn = QPushButton('Clear Filter')
        self.clear_btn.clicked.connect(self._clear_filters)
        top.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton('Refresh')
        self.refresh_btn.clicked.connect(self._load_events)
        top.addWidget(self.refresh_btn)

        self.export_btn = QPushButton('Export')
        self.export_btn.clicked.connect(self._export_events)
        top.addWidget(self.export_btn)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(['Date/Time', 'Level', 'Event ID', 'Source', 'User', 'Message', 'Details'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellClicked.connect(self._show_selected_event)
        layout.addWidget(self.table, 2)

        self.detail_box = QPlainTextEdit()
        self.detail_box.setReadOnly(True)
        self.detail_box.setPlaceholderText('Event details will appear here')
        layout.addWidget(self.detail_box)

        self._load_events()

    def _clear_filters(self):
        self.level_combo.setCurrentText('All')
        self.event_id_edit.clear()
        self.source_edit.clear()
        self.search_edit.clear()
        self._load_events()

    def _build_ps_command(self):
        log_name = self.log_combo.currentText()
        count = self.count_spin.value()
        level = self.level_combo.currentText()
        term = self.search_edit.text().strip()
        event_id = self.event_id_edit.text().strip()
        source = self.source_edit.text().strip()

        filters = []
        if level != 'All':
            filters.append(f"$_.LevelDisplayName -eq '{level}'")
        if event_id:
            filters.append(f"$_.Id -eq {event_id}")
        if source:
            safe_source = source.replace("'", "''")
            filters.append(f"$_.ProviderName -match '{safe_source}'")
        if term:
            safe_term = term.replace("'", "''")
            filters.append(f"$_.Message -match '{safe_term}'")

        where_clause = ''
        if filters:
            where_clause = ' | Where-Object {' + ' -and '.join(filters) + '}'

        script = (
            f"Get-WinEvent -LogName '{log_name}' -MaxEvents {count} -ErrorAction SilentlyContinue"
            f"{where_clause} | Select-Object TimeCreated, LevelDisplayName, Id, ProviderName, "
            "@{Name='User';Expression={$_.Properties[0].Value}}, Message | ConvertTo-Csv -NoTypeInformation"
        )
        return "powershell -NoProfile -Command \"" + script + "\""

    def _load_events(self):
        self.detail_box.clear()
        cmd = self._build_ps_command()
        self._runner = CommandRunner(cmd)
        self._runner.output.connect(self._handle_log_output)
        self._runner.finished.connect(self._handle_finished)
        self._runner.error.connect(self._handle_error)
        self._runner.start()

    def _handle_error(self, msg):
        self.detail_box.appendPlainText(f'[ERROR] {msg}\n')

    def _handle_log_output(self, text):
        raw = text.strip()
        if not raw:
            return
        try:
            rows = list(csv.reader(io.StringIO(raw)))
            if len(rows) < 2:
                self.detail_box.appendPlainText(text)
                return
            self._last_rows = rows
            header = [h.strip() for h in rows[0]]
            data_rows = rows[1:]
            self.table.setRowCount(min(len(data_rows), 200))
            for row_index, row in enumerate(data_rows[:200]):
                values = list(row[:len(header)]) + [''] * (len(header) - len(row))
                if len(values) < 6:
                    continue
                self.table.setItem(row_index, 0, QTableWidgetItem(values[0] if len(values) > 0 else ''))
                self.table.setItem(row_index, 1, QTableWidgetItem(values[1] if len(values) > 1 else ''))
                self.table.setItem(row_index, 2, QTableWidgetItem(values[2] if len(values) > 2 else ''))
                self.table.setItem(row_index, 3, QTableWidgetItem(values[3] if len(values) > 3 else ''))
                self.table.setItem(row_index, 4, QTableWidgetItem(values[4] if len(values) > 4 else ''))
                self.table.setItem(row_index, 5, QTableWidgetItem(values[5] if len(values) > 5 else ''))
                self.table.setItem(row_index, 6, QTableWidgetItem('View'))
        except Exception:
            self.detail_box.appendPlainText(text)

    def _handle_finished(self, code, elapsed):
        self.detail_box.appendPlainText(f'\n[Exit Code: {code}] [Time: {elapsed:.2f}s]')

    def _show_selected_event(self, row, col):
        try:
            text = self.table.item(row, 5).text() if self.table.item(row, 5) else ''
            self.detail_box.setPlainText(text)
        except Exception:
            pass

    def _export_events(self):
        text = self.detail_box.toPlainText() or self._export_table_data()
        if not text:
            QMessageBox.information(self, 'No data', 'No event data to export.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Export Event Log', 'event_log.txt', 'Text Files (*.txt);;CSV Files (*.csv)')
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(text)

    def _export_table_data(self):
        rows = []
        for r in range(self.table.rowCount()):
            row = []
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                row.append(item.text() if item else '')
            rows.append(','.join(row))
        return '\n'.join(rows)


class WindowsUpdateWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        title = QLabel('Windows Update')
        title.setStyleSheet('font-size: 18px; font-weight: bold;')
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        self.refresh_btn = QPushButton('Refresh')
        self.refresh_btn.clicked.connect(self._refresh)
        toolbar.addWidget(self.refresh_btn)
        self.check_btn = QPushButton('Check for Updates')
        self.check_btn.clicked.connect(self._check_updates)
        toolbar.addWidget(self.check_btn)
        self.history_btn = QPushButton('Update History')
        self.history_btn.clicked.connect(self._load_history)
        toolbar.addWidget(self.history_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.status_lbl = QLabel('Service status: pending')
        self.status_lbl.setStyleSheet('color: #80ffcc; font-weight: bold;')
        layout.addWidget(self.status_lbl)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        self._refresh()

    def _run(self, command, label=None):
        if label:
            self.output.appendPlainText(f'## {label}\n')
        self.output.appendPlainText(f'>>> {command}\n')
        runner = CommandRunner(command)
        runner.output.connect(self.output.appendPlainText)
        runner.error.connect(lambda msg: self.output.appendPlainText(f'[ERROR] {msg}\n'))
        runner.finished.connect(lambda code, elapsed: self.output.appendPlainText(f'\n<<< Exit Code: {code} | Time: {elapsed:.2f}s\n'))
        runner.start()

    def _refresh(self):
        self.output.clear()
        self.status_lbl.setText('Service status: refreshing')
        self._run('powershell -NoProfile -Command "Get-Service wuauserv | Select-Object Name, Status, StartType | Format-Table -AutoSize"', 'Windows Update Service Status')
        self._run('powershell -NoProfile -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID, InstalledOn, Description | Format-Table -AutoSize"', 'Recent Installed Updates')
        self.status_lbl.setText('Service status: refreshed')

    def _check_updates(self):
        self.output.clear()
        self.status_lbl.setText('Checking for available updates')
        self._run('powershell -NoProfile -Command "Get-WUList -IsInstalled 0 | Select-Object Title, KBArticleIDs | Format-Table -AutoSize"', 'Available Updates')
        self.status_lbl.setText('Update check complete')

    def _load_history(self):
        self.output.clear()
        self._run('powershell -NoProfile -Command "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object HotFixID, InstalledOn, Description | Format-Table -AutoSize"', 'Update History')


class WindowsRepairWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._runner = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        for name, cmd, desc, admin_required, dangerous in [
            ('System File Checker', 'sfc /scannow', 'Физическая проверка системных файлов и восстановление повреждённых файлов.', True, False),
            ('DISM CheckHealth', 'DISM /Online /Cleanup-Image /CheckHealth', 'Быстрая проверка состояния Component Store.', True, False),
            ('DISM ScanHealth', 'DISM /Online /Cleanup-Image /ScanHealth', 'Более глубокая проверка Component Store.', True, False),
            ('DISM RestoreHealth', 'DISM /Online /Cleanup-Image /RestoreHealth', 'Попытка восстановления образа системы и Component Store.', True, True),
            ('chkdsk', 'chkdsk C:', 'Проверка диска на ошибки файловой системы.', True, True),
        ]:
            box = QGroupBox(name)
            box_layout = QVBoxLayout(box)
            label = QLabel(desc)
            label.setWordWrap(True)
            box_layout.addWidget(label)
            btn = QPushButton('Execute')
            btn.clicked.connect(lambda _checked, c=cmd, a=admin_required, d=dangerous, n=name: self._execute(c, a, d, n))
            box_layout.addWidget(btn)
            layout.addWidget(box)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

    def _execute(self, command, admin_required, dangerous, name):
        if admin_required and not is_user_admin():
            QMessageBox.warning(self, 'Administrator required', 'This command requires Administrator rights.')
            return
        if dangerous:
            reply = QMessageBox.question(self, 'Confirm repair', f'Run {name}?\n\n{command}', QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        self.output.appendPlainText(f'>>> {command}\n')
        self._runner = CommandRunner(command)
        self._runner.output.connect(self.output.appendPlainText)
        self._runner.error.connect(lambda msg: self.output.appendPlainText(f'[ERROR] {msg}\n'))
        self._runner.finished.connect(lambda code, elapsed: self.output.appendPlainText(f'\n<<< Exit Code: {code} | Execution Time: {elapsed:.2f}s\n'))
        self._runner.start()


class DiagnosticRunner(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.tests = [
            ('hostname', 'hostname'),
            ('whoami', 'whoami'),
            ('systeminfo', 'systeminfo'),
            ('ipconfig', 'ipconfig /all'),
            ('ping', 'ping 127.0.0.1 -n 2'),
            ('route', 'route print'),
            ('netstat', 'netstat -ano'),
            ('nslookup', 'nslookup 127.0.0.1'),
            ('tasklist', 'tasklist'),
            ('services', 'powershell -NoProfile -Command "Get-Service | Select-Object Name, Status, StartType | Format-Table -AutoSize"'),
            ('volumes', 'powershell -NoProfile -Command "Get-Volume | Select-Object DriveLetter, FileSystemLabel, FileSystem, SizeRemaining, Size | Format-Table -AutoSize"'),
            ('disks', 'powershell -NoProfile -Command "Get-Disk | Select-Object Number, FriendlyName, HealthStatus, OperationalStatus | Format-Table -AutoSize"'),
            ('security', 'powershell -NoProfile -Command "Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled | Format-List"'),
        ]
        self.results = []

    def run(self):
        for index, (name, command) in enumerate(self.tests, start=1):
            self.progress.emit(f'Running Diagnostic {index}/{len(self.tests)}: {name}')
            start = time.perf_counter()
            try:
                proc = subprocess.Popen(CommandRunner._build_safe_command(command), stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
                stdout, stderr = proc.communicate(timeout=30)
                out = stdout.decode(errors='ignore')
                err = stderr.decode(errors='ignore')
                elapsed = time.perf_counter() - start
                self.results.append({
                    'name': name,
                    'success': proc.returncode == 0,
                    'output': out,
                    'error': err,
                    'exit_code': proc.returncode,
                    'execution_time': round(elapsed, 2),
                })
            except Exception as exc:
                self.results.append({
                    'name': name,
                    'success': False,
                    'output': '',
                    'error': str(exc),
                    'exit_code': 1,
                    'execution_time': round(time.perf_counter() - start, 2),
                })
        self.finished.emit({'tests': self.results, 'summary': self._build_summary(self.results)})

    @staticmethod
    def _build_summary(results):
        total = len(results)
        successful = sum(1 for r in results if r['success'])
        failed = total - successful
        warnings = sum(1 for r in results if 'warning' in (r['error'] + r['output']).lower())
        return {'total': total, 'successful': successful, 'failed': failed, 'warnings': warnings}


class DiagnosticsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        btn_row = QHBoxLayout()
        btn = QPushButton('Run System Diagnostic')
        btn.clicked.connect(self._run_diagnostics)
        btn_row.addWidget(btn)

        health_btn = QPushButton('Run Full System Health Check')
        health_btn.clicked.connect(self._run_health_check)
        btn_row.addWidget(health_btn)

        report_btn = QPushButton('Generate System Report')
        report_btn.clicked.connect(self._generate_system_report)
        btn_row.addWidget(report_btn)

        layout.addLayout(btn_row)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output, 1)

        self.export_btn = QPushButton('Export Diagnostic Report')
        self.export_btn.clicked.connect(self._export_report)
        layout.addWidget(self.export_btn)

    def _run_diagnostics(self):
        self.output.clear()
        self.runner = DiagnosticRunner()
        self.runner.progress.connect(lambda msg: self.output.appendPlainText(msg + '\n'))
        self.runner.finished.connect(self._on_finished)
        self.runner.error.connect(lambda msg: self.output.appendPlainText(f'[ERROR] {msg}\n'))
        self.runner.start()

    def _run_health_check(self):
        self.output.clear()
        self.output.appendPlainText('Running Full System Health Check...\n')
        self.health_runner = HealthCheckRunner()
        self.health_runner.progress.connect(lambda msg: self.output.appendPlainText(msg + '\n'))
        self.health_runner.finished.connect(self._on_health_finished)
        self.health_runner.error.connect(lambda msg: self.output.appendPlainText(f'[ERROR] {msg}\n'))
        self.health_runner.start()

    def _on_health_finished(self, payload):
        status = payload.get('overall_status', 'GOOD')
        checks = payload.get('checks', {})
        recommendations = payload.get('recommendations', [])
        self.output.appendPlainText('\nSYSTEM HEALTH\n')
        self.output.appendPlainText(f'Overall Status: {status}\n')
        for name, value in checks.items():
            self.output.appendPlainText(f'{name}: {value}\n')
        if recommendations:
            self.output.appendPlainText('\nRecommendations:\n')
            for item in recommendations:
                self.output.appendPlainText(f'- {item}\n')

    def _generate_system_report(self):
        report = build_system_health_report()
        text = [
            '## System Overview',
            f"Hostname: {report.get('hostname', 'N/A')}",
            f"OS: {report.get('os', 'N/A')}",
            f"Uptime: {report.get('uptime', 'N/A')}",
            '',
            '## Hardware',
            f"CPU: {report.get('cpu_percent', 0)}%",
            f"RAM: {report.get('ram_percent', 0)}%",
            f"Disk: {report.get('disk_percent', 0)}%",
            '',
            '## Recommendations',
        ]
        for item in report.get('recommendations', []):
            text.append(f'- {item}')
        text.append('')
        text.append(f"Overall Health: {report.get('overall_status', 'GOOD')}")
        content = '\n'.join(text)
        self.output.appendPlainText('\n' + content + '\n')
        path, _ = QFileDialog.getSaveFileName(self, 'Save System Report', 'system_report.txt', 'Text Files (*.txt);;JSON Files (*.json)')
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(content)

    def _on_finished(self, payload):
        summary = payload['summary']
        self.output.appendPlainText('\n## Diagnostic Summary\n')
        self.output.appendPlainText(f'Total Tests: {summary["total"]}\n')
        self.output.appendPlainText(f'Successful: {summary["successful"]}\n')
        self.output.appendPlainText(f'Failed: {summary["failed"]}\n')
        self.output.appendPlainText(f'Warnings: {summary["warnings"]}\n')
        self.output.appendPlainText('\n### Detailed Results\n')
        for item in payload['tests']:
            self.output.appendPlainText(f"- {item['name']}: {'Success' if item['success'] else 'Failed'} | Exit Code: {item['exit_code']} | Time: {item['execution_time']}s\n")
            if item['error']:
                self.output.appendPlainText(f"  Error: {item['error']}\n")
            if item['output']:
                self.output.appendPlainText(f"  Output: {item['output'][:300]}\n")

    def _export_report(self):
        content = self.output.toPlainText()
        if not content:
            QMessageBox.information(self, 'No content', 'No diagnostic report to export.')
            return
        path, _ = QFileDialog.getSaveFileName(self, 'Save Diagnostic Report', 'diagnostic_report.txt', 'Text Files (*.txt);;JSON Files (*.json)')
        if path:
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(content)


class CommandToolPage(QWidget):
    """صفحة أداة واحدة داخل قسم Commands."""

    def __init__(self, title: str, description: str = "", commands: List[Dict] = None, parent=None, back_callback=None):
        super().__init__(parent)
        self.title = title
        self.commands = commands or []
        self._runner = None
        self.back_callback = back_callback
        self._setup_ui(description)

    def _setup_ui(self, description: str):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(15, 15, 15, 15)

        header = QHBoxLayout()
        self.back_btn = QPushButton("⬅ رجوع")
        self.back_btn.clicked.connect(self._go_back)
        header.addWidget(self.back_btn)

        title = QLabel(self.title)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0e0;")
        header.addWidget(title, 1)
        content_layout.addLayout(header)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #aaa; font-size: 12px;")
            content_layout.addWidget(desc)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("background: #0e0e18; color: #e0e0e0; font-family: Consolas, monospace; font-size: 11px;")
        self.output.setPlaceholderText("نتيجة التنفيذ ستظهر هنا...")
        self.output.setMinimumHeight(180)
        content_layout.addWidget(self.output, 1)

        toolbar = QHBoxLayout()
        self.clear_btn = QPushButton("مسح")
        self.clear_btn.clicked.connect(self.output.clear)
        toolbar.addWidget(self.clear_btn)

        self.copy_btn = QPushButton("نسخ")
        self.copy_btn.clicked.connect(self._copy_output)
        toolbar.addWidget(self.copy_btn)

        self.export_btn = QPushButton("Export Result")
        self.export_btn.clicked.connect(self._export_output)
        toolbar.addWidget(self.export_btn)

        self.status_lbl = QLabel("جاهز")
        self.status_lbl.setStyleSheet("color: #80ffcc; font-size: 11px;")
        toolbar.addWidget(self.status_lbl, 1)
        content_layout.addLayout(toolbar)

        cmd_group = QGroupBox("الأوامر")
        cmd_group.setStyleSheet("QGroupBox { border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 15px; color: #e0e0e0; }")
        cmd_layout = QVBoxLayout(cmd_group)
        cmd_layout.setSpacing(10)

        for item in self.commands:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setSpacing(10)
            row_layout.setContentsMargins(0, 0, 0, 0)

            info = QWidget()
            info_layout = QVBoxLayout(info)
            info_layout.setContentsMargins(0, 0, 0, 0)
            title_lbl = QLabel(item["name"])
            title_lbl.setStyleSheet("font-weight: bold; color: #e0e0e0; font-size: 12px;")
            info_layout.addWidget(title_lbl)
            desc_lbl = QLabel(item.get("description", ""))
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
            info_layout.addWidget(desc_lbl)
            row_layout.addWidget(info, 1)

            params = item.get("parameters", [])
            if params:
                inputs = QWidget()
                inputs_layout = QHBoxLayout(inputs)
                inputs_layout.setContentsMargins(0, 0, 0, 0)
                self._input_fields = getattr(self, "_input_fields", {})
                for param in params:
                    param_name = param["name"]
                    field = QLineEdit(param.get("default", ""))
                    field.setPlaceholderText(param.get("placeholder", param_name))
                    field.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 6px; border-radius: 4px;")
                    inputs_layout.addWidget(QLabel(f"{param_name}:"))
                    inputs_layout.addWidget(field)
                    self._input_fields[f"{self.title}_{len(self._input_fields)}"] = field
                row_layout.addWidget(inputs)

            run_btn = QPushButton("Execute")
            run_btn.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 16px; border-radius: 4px;")
            run_btn.clicked.connect(lambda _checked, payload=item: self._run_command(payload))
            row_layout.addWidget(run_btn)
            cmd_layout.addWidget(row)

        content_layout.addWidget(cmd_group)
        content_layout.addStretch()
        scroll.setWidget(content_widget)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

    def _go_back(self):
        if self.back_callback is not None:
            self.back_callback()
            return
        parent = self.parent()
        while parent is not None:
            if hasattr(parent, "show_overview"):
                parent.show_overview()
                return
            parent = parent.parent()

    def _request_admin(self):
        if os.name != "nt":
            QMessageBox.warning(self, "صلاحيات الإدارة", "هذه الميزة تتطلب Windows وامتيازات المدير.")
            return
        if is_user_admin():
            return
        reply = QMessageBox.question(
            self,
            "صلاحيات الإدارة",
            "هذا الأمر يحتاج صلاحيات Administrator.\nهل تريد إعادة تشغيل التطبيق كمسؤول؟",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes and relaunch_as_admin():
            self.window().close()

    def _build_command(self, item: Dict) -> str:
        cmd = item["command"]
        params = item.get("parameters", [])
        for param in params:
            key = param["name"]
            value = param.get("default", "")
            for widget in self.findChildren(QLineEdit):
                if widget.placeholderText() == param.get("placeholder", key):
                    value = widget.text().strip() or value
                    break
            if "{value}" in cmd:
                cmd = cmd.replace("{value}", value)
            elif param.get("position") == "suffix":
                cmd = f"{cmd} {value}".strip()
        return cmd.strip()

    def _run_command(self, item: Dict):
        if item.get("admin_required") and not is_user_admin():
            self._request_admin()
            return
        if item.get("dangerous"):
            confirm = QMessageBox.question(self, "تأكيد العملية", f"هل أنت متأكد من تنفيذ الأمر التالي؟\n\n{item['name']}\n\n{item['command']}", QMessageBox.Yes | QMessageBox.No)
            if confirm != QMessageBox.Yes:
                return

        cmd = self._build_command(item)
        self.output.appendPlainText(f">>> {cmd}\n")
        self.output.ensureCursorVisible()
        self.status_lbl.setText("جارٍ التنفيذ...")
        self._runner = CommandRunner(cmd, shell=False)
        self._runner.output.connect(self.output.appendPlainText)
        self._runner.error.connect(lambda msg: self.output.appendPlainText(f"[ERROR] {msg}\n"))
        self._runner.finished.connect(self._on_finished)
        self._runner.start()

    def _on_finished(self, code: int, elapsed: float):
        self.output.appendPlainText(f"\n<<< Exit Code: {code} | Time: {elapsed:.2f}s")
        self.status_lbl.setText(f"تم التنفيذ | الكود: {code} | الزمن: {elapsed:.2f}s")

    def _copy_output(self):
        text = self.output.toPlainText()
        if text:
            try:
                from PyQt5.QtWidgets import QApplication
                QApplication.instance().clipboard().setText(text)
            except Exception:
                pass

    def _export_output(self):
        text = self.output.toPlainText()
        if not text:
            QMessageBox.information(self, "لا توجد بيانات", "لا توجد بيانات لتصديرها.")
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "حفظ النتيجة", f"{self.title.replace(' ', '_')}.txt", "Text Files (*.txt);;JSON Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text)
            QMessageBox.information(self, "تم", f"تم حفظ النتيجة إلى:\n{file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "فشل الحفظ", str(exc))

    def stop(self):
        if self._runner and self._runner.isRunning():
            self._runner.terminate()
            self._runner.wait(1000)


class CommandsWidget(QWidget):
    """مركز أدوات مدير النظام.

    يتألف من شاشة رئيسية تحتوي على بطاقات الأقسام وداخلها صفحات مستقلة لكل قسم.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages = {}
        self._page_builders = {
            "network": self._build_network_page,
            "processes": self._build_processes_page,
            "services": self._build_services_page,
            "storage": self._build_storage_page,
            "system": self._build_system_page,
            "security": self._build_security_page,
            "events": self._build_event_page,
            "users": self._build_users_page,
            "repair": self._build_repair_page,
            "updates": self._build_updates_page,
            "maintenance": self._build_maintenance_page,
            "diagnostics": self._build_diagnostics_page,
        }
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        title = QLabel("🧰 Commands Center")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        self.stack = QStackedWidget()
        self.overview_page = self._build_overview_page()
        self.stack.addWidget(self.overview_page)
        layout.addWidget(self.stack)

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setSpacing(12)

        desc = QLabel("مركز أدوات مدير النظام — اختر القسم المطلوب")
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        page_layout.addWidget(desc)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setSpacing(10)
        for label, callback in [
            ("Run Full System Health Check", lambda: self._run_full_health_check_from_overview()),
            ("Flush DNS", lambda: self._run_quick_action('ipconfig /flushdns')),
            ("Test Network", lambda: self._run_quick_action('ping 127.0.0.1 -n 2')),
            ("View Processes", lambda: self.show_page('processes')),
            ("View Services", lambda: self.show_page('services')),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(callback)
            actions_layout.addWidget(btn)
        page_layout.addWidget(actions)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scrolled = QWidget()
        grid = QGridLayout(scrolled)
        grid.setSpacing(12)

        categories = [
            ("🌐 Network", "أدوات الشبكة", "network"),
            ("⚙️ Processes", "إدارة العمليات", "processes"),
            ("🛠️ Services", "إدارة الخدمات", "services"),
            ("💾 Storage", "الأقراص والتخزين", "storage"),
            ("🖥️ System Info", "معلومات النظام", "system"),
            ("🔐 Security", "الأمان", "security"),
            ("📋 Event Logs", "سجلات الأنظمة", "events"),
            ("👤 Users", "المستخدمون والصلاحيات", "users"),
            ("🔧 Repair", "إصلاح Windows", "repair"),
            ("🔄 Updates", "Windows Update", "updates"),
            ("🧹 Maintenance", "الصيانة والتنظيف", "maintenance"),
            ("🧪 Diagnostics", "التشخيص", "diagnostics"),
        ]

        for idx, (title, desc_txt, key) in enumerate(categories):
            card = QWidget()
            card.setMinimumHeight(100)
            card.setStyleSheet("QWidget { background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 8px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_label = QLabel(title)
            card_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #e0e0e0;")
            card_layout.addWidget(card_label)
            card_desc = QLabel(desc_txt)
            card_desc.setStyleSheet("font-size: 11px; color: #aaa;")
            card_layout.addWidget(card_desc)
            btn = QPushButton("Open")
            btn.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 12px; border-radius: 4px;")
            btn.clicked.connect(lambda _checked, k=key: self.show_page(k))
            card_layout.addWidget(btn)
            grid.addWidget(card, idx // 3, idx % 3)

        scroll.setWidget(scrolled)
        page_layout.addWidget(scroll)
        return page

    def show_page(self, key: str):
        if key not in self._page_builders:
            return
        if key not in self._pages:
            self._pages[key] = self._page_builders[key]()
            self.stack.addWidget(self._pages[key])
        self.stack.setCurrentWidget(self._pages[key])

    def show_overview(self):
        self.stack.setCurrentWidget(self.overview_page)

    def _run_quick_action(self, command: str):
        page = self._pages.get('diagnostics')
        if page is None:
            return
        if hasattr(page, 'output'):
            page.output.clear()
            page.output.appendPlainText(f'>>> {command}\n')
        runner = CommandRunner(command)
        if hasattr(page, 'output'):
            runner.output.connect(page.output.appendPlainText)
            runner.error.connect(lambda msg: page.output.appendPlainText(f'[ERROR] {msg}\n'))
            runner.finished.connect(lambda code, elapsed: page.output.appendPlainText(f'\n<<< Exit Code: {code} | Time: {elapsed:.2f}s\n'))
        runner.start()
        self.stack.setCurrentWidget(page)

    def _run_full_health_check_from_overview(self):
        diagnostics_page = self._pages.get('diagnostics')
        if diagnostics_page is not None:
            self.stack.setCurrentWidget(diagnostics_page)
            if hasattr(diagnostics_page, '_run_health_check'):
                diagnostics_page._run_health_check()

    def _build_network_page(self) -> QWidget:
        commands = [
            {"name": "ipconfig", "description": "عرض إعدادات الشبكة الحالية", "command": "ipconfig", "parameters": []},
            {"name": "ipconfig /all", "description": "تفاصيل كاملة عن الشبكة", "command": "ipconfig /all", "parameters": []},
            {"name": "ipconfig /renew", "description": "تجديد عنوان IP", "command": "ipconfig /renew", "parameters": []},
            {"name": "ipconfig /release", "description": "إطلاق عنوان IP", "command": "ipconfig /release", "parameters": []},
            {"name": "ipconfig /flushdns", "description": "مسح ذاكرة DNS", "command": "ipconfig /flushdns", "parameters": []},
            {"name": "ping", "description": "اختبار الاتصال", "command": "ping {value} -n 4", "parameters": [{"name": "Target", "placeholder": "8.8.8.8", "default": "8.8.8.8"}]},
            {"name": "tracert", "description": "تتبع المسار", "command": "tracert {value}", "parameters": [{"name": "Target", "placeholder": "8.8.8.8", "default": "8.8.8.8"}]},
            {"name": "pathping", "description": "اختبار مسار الشبكة", "command": "pathping {value}", "parameters": [{"name": "Target", "placeholder": "8.8.8.8", "default": "8.8.8.8"}]},
            {"name": "nslookup", "description": "استعلام DNS", "command": "nslookup {value}", "parameters": [{"name": "Domain", "placeholder": "example.com", "default": "example.com"}]},
            {"name": "netstat", "description": "عرض الاتصالات", "command": "netstat -ano", "parameters": []},
            {"name": "arp -a", "description": "عرض جدول ARP", "command": "arp -a", "parameters": []},
            {"name": "route print", "description": "عرض جداول التوجيه", "command": "route print", "parameters": []},
            {"name": "hostname", "description": "اسم الجهاز", "command": "hostname", "parameters": []},
            {"name": "getmac", "description": "عرض MAC Address", "command": "getmac", "parameters": []},
            {"name": "whoami", "description": "اسم المستخدم الحالي", "command": "whoami", "parameters": []},
            {"name": "Test-NetConnection", "description": "اختبار الاتصال بالشبكة", "command": "powershell -NoProfile -Command \"Test-NetConnection -ComputerName {value} -InformationLevel Detailed\"", "parameters": [{"name": "Host", "placeholder": "8.8.8.8", "default": "8.8.8.8"}]},
            {"name": "Resolve-DnsName", "description": "حل اسم DNS", "command": "powershell -NoProfile -Command \"Resolve-DnsName {value}\"", "parameters": [{"name": "Domain", "placeholder": "example.com", "default": "example.com"}]},
        ]
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        content_layout.addWidget(CommandToolPage("🌐 أدوات الشبكة", "إدارة الاتصال والشبكة", commands, back_callback=self.show_overview))
        content_layout.addWidget(NetworkDiagnosticWidget())

        scroll.setWidget(content)
        layout.addWidget(scroll)
        return page

    def _build_processes_page(self) -> QWidget:
        process_widget = ProcessManagerWidget()
        return process_widget

    def _build_services_page(self) -> QWidget:
        service_widget = ServiceManagerWidget()
        return service_widget

    def _build_storage_page(self) -> QWidget:
        storage_widget = StorageManagerWidget()
        return storage_widget

    def _build_system_page(self) -> QWidget:
        commands = [
            {"name": "systeminfo", "description": "معلومات النظام", "command": "systeminfo", "parameters": []},
            {"name": "hostname", "description": "اسم الجهاز", "command": "hostname", "parameters": []},
            {"name": "whoami", "description": "مستخدم التشغيل", "command": "whoami", "parameters": []},
            {"name": "ver", "description": "إصدار Windows", "command": "ver", "parameters": []},
            {"name": "winver", "description": "نافذة معلومات الإصدار", "command": "winver", "parameters": []},
            {"name": "Get-ComputerInfo", "description": "معلومات الحاسب", "command": "powershell -NoProfile -Command \"Get-ComputerInfo | Select-Object -Property WindowsVersion, WindowsBuildLabEx, OsName, CsName, CsManufacturer, CsModel\"", "parameters": []},
            {"name": "Get-CimInstance Win32_OperatingSystem", "description": "معلومات نظام التشغيل", "command": "powershell -NoProfile -Command \"Get-CimInstance Win32_OperatingSystem | Select-Object Name, Version, BuildNumber, BootDevice, CSName\"", "parameters": []},
            {"name": "Get-CimInstance Win32_ComputerSystem", "description": "معلومات جهاز الحاسب", "command": "powershell -NoProfile -Command \"Get-CimInstance Win32_ComputerSystem | Select-Object Name, Manufacturer, Model, TotalPhysicalMemory\"", "parameters": []},
            {"name": "Get-CimInstance Win32_Processor", "description": "معلومات المعالج", "command": "powershell -NoProfile -Command \"Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed\"", "parameters": []},
        ]
        return CommandToolPage("🖥️ معلومات النظام", "معلومات الحاسب والتشغيل", commands, back_callback=self.show_overview)

    def _build_security_page(self) -> QWidget:
        commands = [
            {"name": "whoami /all", "description": "تفاصيل المستخدم والصلاحيات", "command": "whoami /all", "parameters": []},
            {"name": "net user", "description": "عرض المستخدمين", "command": "net user", "parameters": []},
            {"name": "net localgroup administrators", "description": "عرض أعضاء Administrators", "command": "net localgroup administrators", "parameters": []},
            {"name": "Get-LocalUser", "description": "عرض المستخدمين المحليين", "command": "powershell -NoProfile -Command \"Get-LocalUser | Select-Object Name, Enabled, Description\"", "parameters": []},
            {"name": "Get-LocalGroup", "description": "عرض المجموعات المحلية", "command": "powershell -NoProfile -Command \"Get-LocalGroup | Select-Object Name, Description\"", "parameters": []},
            {"name": "Get-LocalGroupMember Administrators", "description": "أعضاء مجموعة الإدارة", "command": "powershell -NoProfile -Command \"Get-LocalGroupMember Administrators | Select-Object Name, PrincipalSource\"", "parameters": []},
            {"name": "Get-MpComputerStatus", "description": "حالة Windows Defender", "command": "powershell -NoProfile -Command \"Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled\"", "parameters": []},
            {"name": "Get-MpThreat", "description": "الأخطار الحالية", "command": "powershell -NoProfile -Command \"Get-MpThreat | Select-Object ThreatName, Severity, CategoryName\"", "parameters": []},
            {"name": "Get-BitLockerVolume", "description": "حالة BitLocker", "command": "powershell -NoProfile -Command \"Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, EncryptionPercentage\"", "parameters": []},
        ]
        return CommandToolPage("🔐 أدوات الأمان", "استعلامات الأمان وسجل الحماية", commands, back_callback=self.show_overview)

    def _build_event_page(self) -> QWidget:
        commands = [
            {"name": "Application Events", "description": "أحداث التطبيق", "command": "powershell -NoProfile -Command \"Get-EventLog -LogName Application -Newest 20 | Select-Object TimeGenerated, EntryType, Source, EventID, Message | Format-Table -AutoSize\"", "parameters": []},
            {"name": "System Events", "description": "أحداث النظام", "command": "powershell -NoProfile -Command \"Get-EventLog -LogName System -Newest 20 | Select-Object TimeGenerated, EntryType, Source, EventID, Message | Format-Table -AutoSize\"", "parameters": []},
            {"name": "Security Events", "description": "أحداث الأمان", "command": "powershell -NoProfile -Command \"Get-EventLog -LogName Security -Newest 20 | Select-Object TimeGenerated, EntryType, Source, EventID, Message | Format-Table -AutoSize\"", "parameters": []},
        ]
        return CommandToolPage("📋 Event Viewer", "استعراض السجلات", commands, back_callback=self.show_overview)

    def _build_users_page(self) -> QWidget:
        commands = [
            {"name": "net user", "description": "قائمة المستخدمين", "command": "net user", "parameters": []},
            {"name": "Get-LocalUser", "description": "المستخدمون المحليون", "command": "powershell -NoProfile -Command \"Get-LocalUser | Select-Object Name, Enabled, Description\"", "parameters": []},
            {"name": "Get-LocalGroup", "description": "قائمة المجموعات", "command": "powershell -NoProfile -Command \"Get-LocalGroup | Select-Object Name, Description\"", "parameters": []},
            {"name": "Get-LocalGroupMember Administrators", "description": "أعضاء المجموعات", "command": "powershell -NoProfile -Command \"Get-LocalGroupMember Administrators | Select-Object Name, SID\"", "parameters": []},
        ]
        return CommandToolPage("👤 المستخدمون والصلاحيات", "استعراض المستخدمين والمجموعات", commands, back_callback=self.show_overview)

    def _build_repair_page(self) -> QWidget:
        commands = [
            {"name": "sfc /scannow", "description": "فحص ملفات النظام", "command": "sfc /scannow", "admin_required": True, "dangerous": False, "parameters": []},
            {"name": "DISM /CheckHealth", "description": "فحص صورة النظام", "command": "DISM /Online /Cleanup-Image /CheckHealth", "admin_required": True, "dangerous": False, "parameters": []},
            {"name": "DISM /ScanHealth", "description": "فحص أعمق للحالة", "command": "DISM /Online /Cleanup-Image /ScanHealth", "admin_required": True, "dangerous": False, "parameters": []},
            {"name": "DISM /RestoreHealth", "description": "إصلاح صورة النظام", "command": "DISM /Online /Cleanup-Image /RestoreHealth", "admin_required": True, "dangerous": True, "parameters": []},
            {"name": "chkdsk", "description": "فحص القرص", "command": "chkdsk C:", "admin_required": True, "dangerous": True, "parameters": []},
        ]
        return CommandToolPage("🔧 إصلاح Windows", "أدوات الفحص والإصلاح الآمنة", commands, back_callback=self.show_overview)

    def _build_updates_page(self) -> QWidget:
        commands = [
            {"name": "Get-WUList", "description": "العناصر المعلقة", "command": "powershell -NoProfile -Command \"Get-WUList -IsInstalled 0 | Select-Object Title, KBArticleIDs | Format-Table -AutoSize\"", "parameters": []},
            {"name": "Get-Service wuauserv", "description": "حالة خدمة Windows Update", "command": "powershell -NoProfile -Command \"Get-Service wuauserv | Select-Object Name, Status, StartType\"", "parameters": []},
            {"name": "Get-HotFix", "description": "عرض آخر التحديثات المثبتة", "command": "powershell -NoProfile -Command \"Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 HotFixID, InstalledOn\"", "parameters": []},
        ]
        return CommandToolPage("🔄 Windows Update", "استعلام عن التحديثات وحالة الخدمة", commands, back_callback=self.show_overview)

    def _build_maintenance_page(self) -> QWidget:
        commands = [
            {"name": "cleanmgr", "description": "تنظيف القرص", "command": "cleanmgr", "admin_required": True, "dangerous": False, "parameters": []},
            {"name": "del /q /f %TEMP%\\*", "description": "حذف الملفات المؤقتة", "command": "cmd /c del /q /f %TEMP%\\*", "parameters": []},
            {"name": "PowerShell Temp Cleanup", "description": "تنظيف tmp للمستخدم الحالي", "command": "powershell -NoProfile -Command \"Get-ChildItem $env:TEMP -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue; Get-ChildItem $env:LOCALAPPDATA\\Temp -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue\"", "parameters": []},
            {"name": "Get-PSDrive", "description": "عرض محركات الأقراص", "command": "powershell -NoProfile -Command \"Get-PSDrive | Select-Object Name, Root, Used, Free, Provider\"", "parameters": []},
        ]
        return CommandToolPage("🧹 الصيانة والتنظيف", "أدوات الصيانة الآمنة", commands, back_callback=self.show_overview)

    def _build_diagnostics_page(self) -> QWidget:
        page = CommandToolPage("🧪 أدوات التشخيص", "تشخيص شامل لأجزاء النظام", [
            {"name": "Run System Diagnostic", "description": "تشغيل مجموعة فحوصات آمنة", "command": "powershell -NoProfile -Command \"$results = @(); $results += \"--- ipconfig ---\"; ipconfig | Out-String; $results += \"--- hostname ---\"; hostname; $results += \"--- systeminfo ---\"; systeminfo | Select-Object -First 20; $results | Out-String\"", "parameters": []},
            {"name": "ping 8.8.8.8", "description": "اختبار اتصال الإنترنت", "command": "ping 8.8.8.8 -n 4", "parameters": []},
            {"name": "netstat -ano", "description": "عرض الاتصالات النشطة", "command": "netstat -ano", "parameters": []},
            {"name": "tasklist", "description": "قائمة العمليات", "command": "tasklist", "parameters": []},
            {"name": "Get-Service", "description": "حالة الخدمات الرئيسية", "command": "powershell -NoProfile -Command \"Get-Service | Select-Object Name, Status, StartType | Format-Table -AutoSize\"", "parameters": []},
        ], back_callback=self.show_overview)
        return page

    def stop(self):
        for page in self._pages.values():
            if hasattr(page, 'stop'):
                page.stop()


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    win = CommandsWidget()
    win.show()
    sys.exit(app.exec_())
