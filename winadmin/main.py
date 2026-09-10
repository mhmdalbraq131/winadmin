"""main.py — نقطة البداية الرئيسية لتطبيق WinAdmin."""

import sys
import os
import logging
import ctypes
import subprocess
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.optimized_database import OptimizedDatabaseManager
from core.alerts import AlertManager
from ui.dashboard import DashboardWidget
from ui.monitors import ResourceMonitorWidget
from ui.processes import ProcessManagerWidget
from ui.storage import StorageManagerWidget
from ui.services import ServiceManagerWidget
from ui.security import SecurityWidget
from ui.reports_optimized import ReportsWidget
from ui.commands import CommandsWidget
from ui.settings import SettingsWidget
from ui.hardware_advisor import HardwareAdvisorDialog

log_dir = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f"winadmin_{datetime.now().strftime('%Y%m%d')}.log"), encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("WinAdmin")


def is_admin() -> bool:
    if os.name != "nt":
        return True
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    if os.name != "nt":
        return False
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = ' '.join(subprocess.list2cmdline(arg) for arg in sys.argv[1:])
        command = f'"{script_path}" {params}'.strip()
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, command, None, 1)
        return result > 32
    except Exception:
        logger.exception("Error while relaunching as admin")
        return False


DARK_STYLE = """QMainWindow { background-color: #1a1a2e; }
QWidget { background-color: #1a1a2e; color: #e0e0e0; font-family: 'Segoe UI', Arial; font-size: 12px; }
QPushButton { background-color: #2a2a4a; color: #e0e0e0; border: 1px solid #3a3a5a; padding: 6px 14px; border-radius: 4px; }
QPushButton:hover { background-color: #3a3a5a; }
QPushButton:pressed { background-color: #4a4a6a; }
QLineEdit { background-color: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; border-radius: 3px; }
QTableWidget { background-color: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
QHeaderView::section { background-color: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
QScrollBar:vertical { background: #1a1a2e; width: 10px; }
QScrollBar::handle:vertical { background: #2a2a4a; border-radius: 4px; min-height: 20px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QGroupBox { border: 1px solid #2a2a3e; border-radius: 6px; margin-top: 10px; padding-top: 15px; color: #e0e0e0; }
QTabWidget::pane { border: 1px solid #2a2a3e; background: #1a1a2e; }
QTabBar::tab { background: #1e1e32; color: #aaa; padding: 8px 16px; border: 1px solid #2a2a3e; }
QTabBar::tab:selected { background: #2a2a4a; color: #fff; }
QProgressBar { background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 4px; text-align: center; color: white; }
QProgressBar::chunk { border-radius: 3px; }
QComboBox { background-color: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; border-radius: 3px; }
QComboBox QAbstractItemView { background: #1e1e32; color: #e0e0e0; selection-background-color: #2a2a4a; }
QSpinBox { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; }
QCheckBox { color: #ccc; spacing: 6px; }
QDateEdit { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; }
QLabel { color: #e0e0e0; }
QScrollArea { border: none; background: #1a1a2e; }
"""

LIGHT_STYLE = """QMainWindow { background-color: #f5f5f5; }
QWidget { background-color: #f5f5f5; color: #333; font-family: 'Segoe UI', Arial; font-size: 12px; }
QPushButton { background-color: #e0e0e0; color: #333; border: 1px solid #ccc; padding: 6px 14px; border-radius: 4px; }
QPushButton:hover { background-color: #d0d0d0; }
QLineEdit { background-color: #fff; color: #333; border: 1px solid #ccc; padding: 5px; border-radius: 3px; }
QTableWidget { background-color: #fff; color: #333; gridline-color: #ddd; border: none; }
QHeaderView::section { background-color: #e8e8e8; color: #333; padding: 5px; border: 1px solid #ddd; }
QScrollBar:vertical { background: #f0f0f0; width: 10px; }
QScrollBar::handle:vertical { background: #ccc; border-radius: 4px; min-height: 20px; }
QGroupBox { border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 15px; color: #333; }
QTabWidget::pane { border: 1px solid #ddd; background: #f5f5f5; }
QTabBar::tab { background: #e8e8e8; color: #666; padding: 8px 16px; border: 1px solid #ddd; }
QTabBar::tab:selected { background: #fff; color: #333; }
QProgressBar { background: #e8e8e8; border: 1px solid #ddd; border-radius: 4px; text-align: center; color: #333; }
QProgressBar::chunk { background: #4CAF50; border-radius: 3px; }
QComboBox { background: #fff; color: #333; border: 1px solid #ccc; padding: 5px; }
QSpinBox { background: #fff; color: #333; border: 1px solid #ccc; padding: 5px; }
QCheckBox { color: #333; }
QLabel { color: #333; }
"""


class NavButton(QPushButton):
    def __init__(self, text: str, icon: str = "", page_index: int = 0, parent=None):
        super().__init__(f"{icon}  {text}" if icon else text, parent)
        self.page_index = page_index
        self._selected = False
        self.setCheckable(True)
        self.setMinimumHeight(44)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self.setChecked(selected)
        self._update_style()

    def _update_style(self):
        if self._selected:
            self.setStyleSheet("""QPushButton { background-color: #2a2a4a; color: #ffffff; border: none;
                border-right: 3px solid #4CAF50; text-align: right; padding: 10px 16px;
                font-size: 13px; font-weight: bold; border-radius: 0; }""")
        else:
            self.setStyleSheet("""QPushButton { background-color: transparent; color: #aaa; border: none;
                border-right: 3px solid transparent; text-align: right; padding: 10px 16px;
                font-size: 13px; border-radius: 0; }
                QPushButton:hover { background-color: #1e1e32; color: #ddd; }""")


class SidebarWidget(QFrame):
    navigation_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.RightToLeft)
        self.setFixedWidth(230)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setStyleSheet("SidebarWidget { background-color: #12122a; border-left: 1px solid #2a2a3e; }")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        logo = QLabel("🖥 WinAdmin")
        logo.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        logo.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold; padding: 20px 16px 10px 16px;")
        layout.addWidget(logo)
        subtitle = QLabel("أداة إدارة النظام")
        subtitle.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        subtitle.setStyleSheet("color: #666; font-size: 10px; padding: 0 16px 20px 16px;")
        layout.addWidget(subtitle)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #2a2a3e; max-height: 1px;")
        layout.addWidget(line)
        self.nav_buttons = []
        pages = [("لوحة التحكم", "📊", 0), ("مراقبة الموارد", "📈", 1), ("إدارة العمليات", "⚙", 2),
                 ("إدارة التخزين", "💾", 3), ("إدارة الخدمات", "🔧", 4), ("الأمان والصحة", "🛡", 5),
                 ("السجلات والتقارير", "📋", 6), ("الأوامر", "💻", 7), ("الإعدادات", "⚙", 8)]
        for name, icon, idx in pages:
            btn = NavButton(name, icon, idx)
            btn.clicked.connect(lambda checked=False, i=idx: self.navigation_requested.emit(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)
        layout.addStretch()
        version = QLabel("v1.0.0 | Python")
        version.setLayoutDirection(Qt.LeftToRight)
        version.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        version.setStyleSheet("color: #555; font-size: 9px; padding: 10px 16px;")
        layout.addWidget(version)
        self.set_selected(0)

    def set_selected(self, index: int):
        for btn in self.nav_buttons:
            btn.set_selected(btn.page_index == index)


class MainWindow(QMainWindow):
    PAGE_TITLES = ("لوحة التحكم", "مراقبة الموارد", "إدارة العمليات", "إدارة التخزين",
                   "إدارة الخدمات", "الأمان والصحة", "السجلات والتقارير", "الأوامر", "الإعدادات")

    def __init__(self):
        super().__init__()
        self.setLayoutDirection(Qt.RightToLeft)
        self.setWindowTitle("WinAdmin — أداة إدارة النظام")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)
        appdata = os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~')
        db_dir = os.path.join(appdata, 'WinAdmin')
        os.makedirs(db_dir, exist_ok=True)
        self.db = OptimizedDatabaseManager(os.path.join(db_dir, 'winadmin.db'))
        self.alert_manager = AlertManager(self.db)
        self._apply_theme(self.db.get_setting("theme", "dark"))
        self._setup_ui()
        logger.info("تم تشغيل WinAdmin بنجاح")

    def _setup_ui(self):
        central = QWidget()
        central.setLayoutDirection(Qt.LeftToRight)
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setDirection(QHBoxLayout.LeftToRight)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_frame = QFrame()
        content_frame.setLayoutDirection(Qt.RightToLeft)
        content_frame.setStyleSheet("QFrame { background: #1a1a2e; }")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        top_bar = QFrame()
        top_bar.setLayoutDirection(Qt.RightToLeft)
        top_bar.setFixedHeight(48)
        top_bar.setStyleSheet("background: #12122a; border-bottom: 1px solid #2a2a3e;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(15, 0, 15, 0)
        top_layout.setSpacing(10)

        self.lbl_top_title = QLabel(self.PAGE_TITLES[0])
        self.lbl_top_title.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_top_title.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
        top_layout.addWidget(self.lbl_top_title)
        top_layout.addStretch()

        self.btn_hardware = QPushButton("🤖 فحص الجهاز والمساعد الذكي")
        self.btn_hardware.setToolTip("تحليل مواصفات الجهاز وتحديد أفضل الاستخدامات والتوصيات")
        self.btn_hardware.setMinimumHeight(34)
        self.btn_hardware.setStyleSheet("QPushButton { background: #234b35; color: #dfffe9; border: 1px solid #35734e; padding: 6px 14px; border-radius: 5px; font-weight: bold; } QPushButton:hover { background: #2d6245; }")
        self.btn_hardware.clicked.connect(self._open_hardware_advisor)
        top_layout.addWidget(self.btn_hardware)

        self.lbl_time = QLabel("")
        self.lbl_time.setLayoutDirection(Qt.LeftToRight)
        self.lbl_time.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl_time.setStyleSheet("color: #888; font-size: 11px; min-width: 145px;")
        top_layout.addWidget(self.lbl_time)
        content_layout.addWidget(top_bar)

        self.stack = QStackedWidget()
        self.stack.setLayoutDirection(Qt.RightToLeft)
        self.stack.setStyleSheet("QStackedWidget { background: #1a1a2e; }")
        self.page_factories = (
            lambda: DashboardWidget(self.db, self.alert_manager), lambda: ResourceMonitorWidget(),
            lambda: ProcessManagerWidget(), lambda: StorageManagerWidget(), lambda: ServiceManagerWidget(),
            lambda: SecurityWidget(self.db), lambda: ReportsWidget(self.db), lambda: CommandsWidget(),
            lambda: SettingsWidget(self.db, self.alert_manager),
        )
        self.pages = [None] * len(self.page_factories)
        content_layout.addWidget(self.stack, 1)

        self.sidebar = SidebarWidget()
        self.sidebar.navigation_requested.connect(self._switch_page)
        main_layout.addWidget(content_frame, 1)
        main_layout.addWidget(self.sidebar, 0)
        self._ensure_page(0)

        self._time_timer = QTimer(self)
        self._time_timer.setTimerType(Qt.CoarseTimer)
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)
        self._update_time()

    def _open_hardware_advisor(self):
        """فتح الفحص العام من أي صفحة دون تنفيذ العمل الثقيل في خيط الواجهة."""
        try:
            dialog = HardwareAdvisorDialog(self)
            dialog.exec_()
        except Exception as exc:
            logger.exception("Failed to open hardware advisor")
            QMessageBox.critical(self, "خطأ", f"تعذر فتح فحص الجهاز.\n\n{exc}")

    def _ensure_page(self, index: int):
        if not (0 <= index < len(self.page_factories)):
            return None
        if self.pages[index] is not None:
            return self.pages[index]
        try:
            page = self.page_factories[index]()
            if page is None:
                raise RuntimeError(f"Page factory returned None for index {index}")
            page.setLayoutDirection(Qt.RightToLeft)
            self.pages[index] = page
            self.stack.addWidget(page)
            return page
        except Exception as exc:
            self.pages[index] = None
            logger.exception("Failed to create page %s (%s)", index, self.PAGE_TITLES[index])
            QMessageBox.critical(self, "خطأ في فتح الصفحة", f"تعذر فتح صفحة «{self.PAGE_TITLES[index]}».\n\n{exc}")
            return None

    @staticmethod
    def _stop_page_timers(page):
        for name in ("timer", "timer_slow"):
            timer = getattr(page, name, None)
            try:
                if timer is not None and timer.isActive():
                    timer.stop()
            except RuntimeError:
                pass

    @staticmethod
    def _resume_page_timers(page):
        for name in ("timer", "timer_slow"):
            timer = getattr(page, name, None)
            try:
                if timer is not None and not timer.isActive():
                    timer.start()
            except RuntimeError:
                pass

    def _switch_page(self, index: int):
        if not (0 <= index < len(self.page_factories)):
            return
        page = self._ensure_page(index)
        if page is None:
            return
        for other in self.pages:
            if other is not None and other is not page:
                self._stop_page_timers(other)
        try:
            self.stack.setCurrentWidget(page)
        except RuntimeError:
            logger.exception("QStackedWidget was unavailable while switching page %s", index)
            return
        self._resume_page_timers(page)
        self.lbl_top_title.setText(self.PAGE_TITLES[index])
        self.sidebar.set_selected(index)

    def _update_time(self):
        try:
            label = getattr(self, "lbl_time", None)
            if label is None:
                return
            label.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        except RuntimeError:
            return

    def _apply_theme(self, theme: str):
        QApplication.instance().setStyleSheet(LIGHT_STYLE if theme == "light" else DARK_STYLE)

    def closeEvent(self, event):
        logger.info("جاري إغلاق WinAdmin...")
        try:
            if hasattr(self, "_time_timer"):
                self._time_timer.stop()
                try:
                    self._time_timer.timeout.disconnect(self._update_time)
                except (TypeError, RuntimeError):
                    pass
        except (RuntimeError, AttributeError):
            pass
        for page in getattr(self, "pages", []):
            if page is None:
                continue
            try:
                if hasattr(page, "stop"):
                    page.stop()
            except Exception:
                logger.exception("Error stopping page %s", type(page).__name__)
        try:
            self.db.close()
        except Exception:
            logger.exception("Error closing database")
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setApplicationDisplayName("WinAdmin")
    app.setApplicationName("WinAdmin")
    app.setApplicationVersion("1.0.0")
    if os.name == "nt" and not is_admin():
        reply = QMessageBox.question(None, "تحتاج صلاحيات المدير",
            "هذا التطبيق يفضل التشغيل بصلاحيات Administrator لعمل بعض الأدوات.\nهل تريد إعادة التشغيل بصلاحيات الإدارة؟",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes and relaunch_as_admin():
            return
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
