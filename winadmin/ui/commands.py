"""مركز أدوات مدير النظام — تنفيذ غير متزامن وتنقل واضح."""

import os
import subprocess
import sys
import time
from typing import Dict, List, Optional

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QStackedWidget, QVBoxLayout, QWidget
)

from ui.processes import ProcessManagerWidget
from ui.services import ServiceManagerWidget
from ui.storage import StorageManagerWidget


def is_user_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


class CommandRunner(QThread):
    output = pyqtSignal(str)
    finished = pyqtSignal(int, float)
    error = pyqtSignal(str)

    def __init__(self, argv: List[str], timeout: int = 120):
        super().__init__()
        self.argv = argv
        self.timeout = timeout

    def run(self):
        started = time.perf_counter()
        try:
            process = subprocess.Popen(
                self.argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                shell=False,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            try:
                output, _ = process.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                output, _ = process.communicate()
                if output:
                    self.output.emit(output)
                self.error.emit(f"انتهت مهلة التنفيذ ({self.timeout} ثانية).")
                self.finished.emit(124, time.perf_counter() - started)
                return

            if output:
                self.output.emit(output)
            self.finished.emit(process.returncode, time.perf_counter() - started)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit(1, time.perf_counter() - started)


class EmbeddedPage(QWidget):
    def __init__(self, title: str, widget: QWidget, back_callback, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        back = QPushButton("⬅ رجوع")
        back.clicked.connect(back_callback)
        header.addWidget(back)
        label = QLabel(title)
        label.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(label, 1)
        layout.addLayout(header)
        layout.addWidget(widget, 1)
        self._child = widget

    def stop(self):
        if hasattr(self._child, "stop"):
            self._child.stop()


class CommandToolPage(QWidget):
    def __init__(self, title: str, description: str, commands: List[Dict], back_callback, parent=None):
        super().__init__(parent)
        self.commands = commands
        self._back_callback = back_callback
        self._runner: Optional[CommandRunner] = None
        self._run_buttons: List[QPushButton] = []
        self._setup_ui(title, description)

    def _setup_ui(self, title: str, description: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        header = QHBoxLayout()
        back = QPushButton("⬅ رجوع")
        back.clicked.connect(self._back_callback)
        header.addWidget(back)
        heading = QLabel(title)
        heading.setStyleSheet("font-size: 20px; font-weight: bold;")
        header.addWidget(heading, 1)
        root.addLayout(header)

        if description:
            desc = QLabel(description)
            desc.setWordWrap(True)
            root.addWidget(desc)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("نتيجة التنفيذ ستظهر هنا...")
        root.addWidget(self.output, 1)

        toolbar = QHBoxLayout()
        clear = QPushButton("مسح")
        clear.clicked.connect(self.output.clear)
        toolbar.addWidget(clear)
        copy = QPushButton("نسخ")
        copy.clicked.connect(self._copy_output)
        toolbar.addWidget(copy)
        export = QPushButton("تصدير")
        export.clicked.connect(self._export_output)
        toolbar.addWidget(export)
        self.status = QLabel("جاهز")
        toolbar.addWidget(self.status, 1)
        root.addLayout(toolbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(8)

        for index, item in enumerate(self.commands):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 4, 6, 4)
            row_layout.setSpacing(8)

            info = QVBoxLayout()
            name = QLabel(item["name"])
            name.setStyleSheet("font-weight: bold;")
            info.addWidget(name)
            text = QLabel(item.get("description", ""))
            text.setWordWrap(True)
            info.addWidget(text)
            row_layout.addLayout(info, 1)

            if "parameter" in item:
                parameter = item["parameter"]
                field = QLineEdit(parameter.get("default", ""))
                field.setPlaceholderText(parameter.get("placeholder", ""))
                field.setMinimumWidth(150)
                row_layout.addWidget(field)
                item["_input"] = field

            button = QPushButton("تنفيذ")
            button.clicked.connect(lambda _checked=False, command=item: self._execute(command))
            row_layout.addWidget(button)
            self._run_buttons.append(button)
            grid.addWidget(row, index, 0)

        scroll.setWidget(content)
        root.addWidget(scroll, 2)

    def _build_argv(self, item: Dict) -> List[str]:
        argv = list(item["argv"])
        parameter = item.get("parameter")
        if not parameter:
            return argv
        field = item.get("_input")
        value = field.text().strip() if field is not None else parameter.get("default", "")
        if not value:
            raise ValueError("أدخل قيمة صالحة أولاً")
        validator = parameter.get("validator")
        if validator and not validator(value):
            raise ValueError("القيمة المدخلة غير صالحة")
        return [part.replace("{value}", value) for part in argv]

    def _execute(self, item: Dict):
        if self._runner is not None and self._runner.isRunning():
            return
        if item.get("admin_required") and not is_user_admin():
            QMessageBox.warning(self, "صلاحيات المدير", "هذا الأمر يحتاج تشغيل التطبيق بصلاحيات Administrator.")
            return
        if item.get("confirm"):
            answer = QMessageBox.question(
                self, "تأكيد", f"هل تريد تنفيذ:\n\n{item['name']}؟",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if answer != QMessageBox.Yes:
                return

        try:
            argv = self._build_argv(item)
        except ValueError as exc:
            QMessageBox.warning(self, "بيانات غير صالحة", str(exc))
            return

        self.output.appendPlainText(f">>> {item['name']}\n")
        self.status.setText("جارٍ التنفيذ...")
        for button in self._run_buttons:
            button.setEnabled(False)

        self._runner = CommandRunner(argv, item.get("timeout", 120))
        self._runner.output.connect(self.output.appendPlainText)
        self._runner.error.connect(lambda msg: self.output.appendPlainText(f"[ERROR] {msg}\n"))
        self._runner.finished.connect(self._finished)
        self._runner.start()

    def _finished(self, code: int, elapsed: float):
        self.output.appendPlainText(f"\n<<< Exit Code: {code} | Time: {elapsed:.2f}s\n")
        self.status.setText(f"اكتمل التنفيذ | {elapsed:.2f} ثانية | الكود {code}")
        for button in self._run_buttons:
            button.setEnabled(True)
        self._runner = None

    def _copy_output(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _export_output(self):
        text = self.output.toPlainText()
        if not text:
            QMessageBox.information(self, "لا توجد بيانات", "لا توجد نتيجة لتصديرها.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "تصدير النتيجة", "command_result.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)

    def stop(self):
        if self._runner is not None and self._runner.isRunning():
            self._runner.terminate()
            self._runner.wait(1000)


def host_validator(value: str) -> bool:
    import re
    if re.fullmatch(r"\d{1,3}(?:\.\d{1,3}){3}", value):
        return all(0 <= int(part) <= 255 for part in value.split("."))
    return bool(re.fullmatch(r"[A-Za-z0-9.-]+", value))


def ps(script: str) -> List[str]:
    return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script]


class CommandsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages: Dict[str, QWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.stack = QStackedWidget()
        self.overview_page = self._build_overview()
        self.stack.addWidget(self.overview_page)
        layout.addWidget(self.stack)

    def _build_overview(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(3, 3, 3, 3)

        title = QLabel("🧰 مركز الأوامر")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        desc = QLabel("مركز أدوات مدير النظام — اختر القسم المطلوب")
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(desc)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)
        quick_actions = [
            ("فحص صحة النظام", lambda: self.show_page("diagnostics")),
            ("مسح DNS", lambda: self.show_page("network")),
            ("اختبار الشبكة", lambda: self.show_page("network")),
            ("عرض العمليات", lambda: self.show_page("processes")),
            ("عرض الخدمات", lambda: self.show_page("services")),
        ]
        for label, callback in quick_actions:
            button = QPushButton(label)
            button.setMinimumHeight(38)
            button.clicked.connect(callback)
            actions_layout.addWidget(button)
        layout.addWidget(actions)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(12)

        categories = [
            ("🌐 الشبكة", "أدوات الشبكة والاتصال", "network"),
            ("⚙️ العمليات", "إدارة العمليات", "processes"),
            ("🛠️ الخدمات", "إدارة خدمات Windows", "services"),
            ("💾 التخزين", "الأقراص ومساحات التخزين", "storage"),
            ("🖥️ معلومات النظام", "معلومات الجهاز والنظام", "system"),
            ("🔐 الأمان", "الأمان والحماية", "security"),
            ("📋 السجلات", "سجلات Windows", "events"),
            ("👤 المستخدمون", "المستخدمون والصلاحيات", "users"),
            ("🔧 الإصلاح", "أدوات إصلاح Windows", "repair"),
            ("🔄 التحديثات", "Windows Update", "updates"),
            ("🧹 الصيانة", "الصيانة والتنظيف", "maintenance"),
            ("🧪 التشخيص", "فحوصات وتشخيص النظام", "diagnostics"),
        ]

        for index, (label, description, key) in enumerate(categories):
            card = QWidget()
            card.setMinimumHeight(105)
            card.setStyleSheet(
                "QWidget { background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 8px; }"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(6)

            card_label = QLabel(label)
            card_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0e0e0; border: none;")
            card_layout.addWidget(card_label)

            card_desc = QLabel(description)
            card_desc.setStyleSheet("font-size: 11px; color: #aaa; border: none;")
            card_layout.addWidget(card_desc)

            button = QPushButton("فتح القسم")
            button.setStyleSheet(
                "QPushButton { background: #2a2a4a; color: #e0e0e0; border: none; padding: 7px 12px; border-radius: 4px; }"
                "QPushButton:hover { background: #3a3a5a; }"
            )
            button.clicked.connect(lambda _checked=False, k=key: self.show_page(k))
            card_layout.addWidget(button)
            grid.addWidget(card, index // 3, index % 3)

        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        return page

    def show_page(self, key: str):
        valid_keys = {
            "network", "processes", "services", "storage", "system", "security",
            "events", "users", "repair", "updates", "maintenance", "diagnostics"
        }
        if key not in valid_keys:
            return
        if key not in self._pages:
            self._pages[key] = self._create_page(key)
            self.stack.addWidget(self._pages[key])
        self.stack.setCurrentWidget(self._pages[key])

    def show_overview(self):
        self.stack.setCurrentWidget(self.overview_page)

    def _create_page(self, key: str) -> QWidget:
        builders = {
            "network": self._network_page,
            "processes": self._processes_page,
            "services": self._services_page,
            "storage": self._storage_page,
            "system": self._system_page,
            "security": self._security_page,
            "events": self._events_page,
            "users": self._users_page,
            "repair": self._repair_page,
            "updates": self._updates_page,
            "maintenance": self._maintenance_page,
            "diagnostics": self._diagnostics_page,
        }
        return builders[key]()

    def _command_page(self, title, description, commands):
        return CommandToolPage(title, description, commands, self.show_overview)

    def _network_page(self):
        commands = [
            {"name": "ipconfig", "description": "إعدادات الشبكة", "argv": ["ipconfig"]},
            {"name": "ipconfig /all", "description": "تفاصيل الشبكة", "argv": ["ipconfig", "/all"]},
            {"name": "ipconfig /renew", "description": "تجديد IP", "argv": ["ipconfig", "/renew"]},
            {"name": "ipconfig /release", "description": "تحرير IP", "argv": ["ipconfig", "/release"]},
            {"name": "ipconfig /flushdns", "description": "مسح DNS", "argv": ["ipconfig", "/flushdns"]},
            {"name": "ping", "description": "اختبار الاتصال", "argv": ["ping", "{value}", "-n", "4"], "parameter": {"placeholder": "8.8.8.8", "default": "8.8.8.8", "validator": host_validator}, "timeout": 30},
            {"name": "tracert", "description": "تتبع المسار", "argv": ["tracert", "{value}"], "parameter": {"placeholder": "8.8.8.8", "default": "8.8.8.8", "validator": host_validator}, "timeout": 60},
            {"name": "pathping", "description": "تحليل مسار الشبكة", "argv": ["pathping", "{value}"], "parameter": {"placeholder": "8.8.8.8", "default": "8.8.8.8", "validator": host_validator}, "timeout": 120},
            {"name": "nslookup", "description": "استعلام DNS", "argv": ["nslookup", "{value}"], "parameter": {"placeholder": "example.com", "default": "example.com", "validator": host_validator}, "timeout": 30},
            {"name": "netstat -ano", "description": "الاتصالات النشطة", "argv": ["netstat", "-ano"]},
            {"name": "arp -a", "description": "جدول ARP", "argv": ["arp", "-a"]},
            {"name": "route print", "description": "جداول التوجيه", "argv": ["route", "print"]},
            {"name": "hostname", "description": "اسم الجهاز", "argv": ["hostname"]},
            {"name": "getmac", "description": "عناوين MAC", "argv": ["getmac"]},
            {"name": "whoami", "description": "المستخدم الحالي", "argv": ["whoami"]},
        ]
        return self._command_page("🌐 أدوات الشبكة", "فحوصات الشبكة بدون تجميد الواجهة.", commands)

    def _processes_page(self):
        return EmbeddedPage("⚙️ إدارة العمليات", ProcessManagerWidget(), self.show_overview)

    def _services_page(self):
        return EmbeddedPage("🛠️ إدارة الخدمات", ServiceManagerWidget(), self.show_overview)

    def _storage_page(self):
        return EmbeddedPage("💾 إدارة التخزين", StorageManagerWidget(), self.show_overview)

    def _system_page(self):
        commands = [
            {"name": "systeminfo", "description": "معلومات Windows", "argv": ["systeminfo"], "timeout": 60},
            {"name": "hostname", "description": "اسم الجهاز", "argv": ["hostname"]},
            {"name": "whoami", "description": "المستخدم الحالي", "argv": ["whoami"]},
            {"name": "ver", "description": "إصدار Windows", "argv": ["cmd", "/c", "ver"]},
            {"name": "Get-ComputerInfo", "description": "تفاصيل النظام", "argv": ps("Get-ComputerInfo | Select-Object WindowsVersion, WindowsBuildLabEx, OsName, CsName, CsManufacturer, CsModel | Format-List"), "timeout": 60},
            {"name": "Win32_OperatingSystem", "description": "معلومات نظام التشغيل", "argv": ps("Get-CimInstance Win32_OperatingSystem | Select-Object Name, Version, BuildNumber, BootDevice, CSName | Format-List"), "timeout": 30},
            {"name": "Win32_ComputerSystem", "description": "معلومات الجهاز", "argv": ps("Get-CimInstance Win32_ComputerSystem | Select-Object Name, Manufacturer, Model, TotalPhysicalMemory | Format-List"), "timeout": 30},
            {"name": "Win32_Processor", "description": "معلومات المعالج", "argv": ps("Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | Format-List"), "timeout": 30},
        ]
        return self._command_page("🖥️ معلومات النظام", "قراءة معلومات الجهاز والنظام.", commands)

    def _security_page(self):
        commands = [
            {"name": "whoami /all", "description": "الصلاحيات الحالية", "argv": ["whoami", "/all"]},
            {"name": "net user", "description": "المستخدمون", "argv": ["net", "user"]},
            {"name": "Administrators", "description": "أعضاء Administrators", "argv": ["net", "localgroup", "administrators"]},
            {"name": "Get-LocalUser", "description": "المستخدمون المحليون", "argv": ps("Get-LocalUser | Select-Object Name, Enabled, Description | Format-Table -AutoSize")},
            {"name": "Get-LocalGroup", "description": "المجموعات المحلية", "argv": ps("Get-LocalGroup | Select-Object Name, Description | Format-Table -AutoSize")},
            {"name": "Defender Status", "description": "حالة Defender", "argv": ps("Get-MpComputerStatus | Select-Object RealTimeProtectionEnabled, AntivirusEnabled, AntispywareEnabled | Format-List"), "timeout": 30},
            {"name": "Defender Threats", "description": "التهديدات المسجلة", "argv": ps("Get-MpThreat | Select-Object ThreatName, Severity, CategoryName | Format-Table -AutoSize"), "timeout": 30},
            {"name": "BitLocker", "description": "حالة BitLocker", "argv": ps("Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, EncryptionPercentage | Format-Table -AutoSize"), "timeout": 30},
        ]
        return self._command_page("🔐 أدوات الأمان", "فحوصات الأمان والحماية.", commands)

    def _events_page(self):
        commands = [
            {"name": "Application", "description": "آخر 20 حدثاً", "argv": ps("Get-WinEvent -LogName Application -MaxEvents 20 | Select-Object TimeCreated, LevelDisplayName, Id, ProviderName, Message | Format-Table -Wrap"), "timeout": 30},
            {"name": "System", "description": "آخر 20 حدثاً", "argv": ps("Get-WinEvent -LogName System -MaxEvents 20 | Select-Object TimeCreated, LevelDisplayName, Id, ProviderName, Message | Format-Table -Wrap"), "timeout": 30},
            {"name": "Security", "description": "آخر 20 حدثاً", "argv": ps("Get-WinEvent -LogName Security -MaxEvents 20 | Select-Object TimeCreated, LevelDisplayName, Id, ProviderName, Message | Format-Table -Wrap"), "admin_required": True, "timeout": 30},
        ]
        return self._command_page("📋 سجلات Windows", "عرض آخر الأحداث بدون تحميل السجل كاملاً.", commands)

    def _users_page(self):
        commands = [
            {"name": "net user", "description": "قائمة المستخدمين", "argv": ["net", "user"]},
            {"name": "Get-LocalUser", "description": "تفاصيل المستخدمين", "argv": ps("Get-LocalUser | Select-Object Name, Enabled, Description | Format-Table -AutoSize")},
            {"name": "Get-LocalGroup", "description": "قائمة المجموعات", "argv": ps("Get-LocalGroup | Select-Object Name, Description | Format-Table -AutoSize")},
            {"name": "Administrators", "description": "أعضاء مجموعة الإدارة", "argv": ps("Get-LocalGroupMember Administrators | Select-Object Name, PrincipalSource | Format-Table -AutoSize"), "timeout": 30},
        ]
        return self._command_page("👤 المستخدمون والصلاحيات", "قراءة المستخدمين والمجموعات.", commands)

    def _repair_page(self):
        commands = [
            {"name": "SFC /scannow", "description": "فحص وإصلاح ملفات Windows", "argv": ["sfc", "/scannow"], "admin_required": True, "confirm": True, "timeout": 900},
            {"name": "DISM CheckHealth", "description": "فحص سريع لصورة النظام", "argv": ["DISM", "/Online", "/Cleanup-Image", "/CheckHealth"], "admin_required": True, "timeout": 120},
            {"name": "DISM ScanHealth", "description": "فحص عميق لصورة النظام", "argv": ["DISM", "/Online", "/Cleanup-Image", "/ScanHealth"], "admin_required": True, "confirm": True, "timeout": 900},
            {"name": "DISM RestoreHealth", "description": "إصلاح صورة النظام", "argv": ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"], "admin_required": True, "confirm": True, "timeout": 1800},
            {"name": "chkdsk C:", "description": "فحص نظام الملفات", "argv": ["chkdsk", "C:"], "admin_required": True, "confirm": True, "timeout": 900},
        ]
        return self._command_page("🔧 إصلاح Windows", "عمليات الإصلاح قد تستغرق وقتاً؛ الواجهة تبقى قابلة للاستخدام.", commands)

    def _updates_page(self):
        commands = [
            {"name": "Windows Update Service", "description": "حالة خدمة Windows Update", "argv": ps("Get-Service wuauserv | Select-Object Name, Status, StartType | Format-List")},
            {"name": "Recent HotFixes", "description": "آخر التحديثات المثبتة", "argv": ps("Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 20 HotFixID, InstalledOn, Description | Format-Table -AutoSize"), "timeout": 30},
        ]
        return self._command_page("🔄 Windows Update", "استعلامات سريعة عن التحديثات والخدمة.", commands)

    def _maintenance_page(self):
        commands = [
            {"name": "cleanmgr", "description": "فتح أداة تنظيف القرص", "argv": ["cleanmgr"]},
            {"name": "Get-PSDrive", "description": "مساحات محركات الأقراص", "argv": ps("Get-PSDrive -PSProvider FileSystem | Select-Object Name, Root, Used, Free | Format-Table -AutoSize")},
            {"name": "Clear User Temp", "description": "حذف الملفات المؤقتة للمستخدم", "argv": ps("Get-ChildItem $env:TEMP -Force -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"), "confirm": True, "timeout": 120},
        ]
        return self._command_page("🧹 الصيانة", "أدوات صيانة محددة وآمنة بدون shell.", commands)

    def _diagnostics_page(self):
        commands = [
            {"name": "Quick Diagnostic", "description": "فحص أساسي سريع", "argv": ps('$a=hostname; $b=whoami; $c=(Get-CimInstance Win32_OperatingSystem).Caption; "Hostname: $a`nUser: $b`nOS: $c"')},
            {"name": "Ping 8.8.8.8", "description": "اختبار الإنترنت", "argv": ["ping", "8.8.8.8", "-n", "4"], "timeout": 30},
            {"name": "netstat -ano", "description": "الاتصالات النشطة", "argv": ["netstat", "-ano"]},
            {"name": "tasklist", "description": "العمليات الحالية", "argv": ["tasklist"]},
            {"name": "Get-Service", "description": "حالة الخدمات", "argv": ps("Get-Service | Select-Object Name, Status, StartType | Format-Table -AutoSize"), "timeout": 60},
        ]
        return self._command_page("🧪 التشخيص", "فحوصات مختصرة لتحديد المشكلة بسرعة.", commands)

    def stop(self):
        for page in self._pages.values():
            if hasattr(page, "stop"):
                page.stop()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CommandsWidget()
    window.resize(1100, 750)
    window.show()
    sys.exit(app.exec_())
