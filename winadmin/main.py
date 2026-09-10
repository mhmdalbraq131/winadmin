"""main.py — WinAdmin entry point with RTL/LTR and bilingual UI."""
import sys, os, logging, ctypes, subprocess
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QSizePolicy, QMessageBox, QComboBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.optimized_database import OptimizedDatabaseManager
from core.alerts import AlertManager
from core.i18n import LANGUAGE_AR, LANGUAGE_EN, normalize_language, tr, apply_language
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

log_dir = os.path.join(os.path.dirname(__file__), "logs"); os.makedirs(log_dir, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.FileHandler(os.path.join(log_dir, f"winadmin_{datetime.now().strftime('%Y%m%d')}.log"), encoding="utf-8"), logging.StreamHandler()])
logger = logging.getLogger("WinAdmin")


def is_admin():
    if os.name != "nt": return True
    try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception: return False


def relaunch_as_admin():
    if os.name != "nt": return False
    try:
        script_path = os.path.abspath(sys.argv[0])
        params = " ".join(subprocess.list2cmdline(arg) for arg in sys.argv[1:])
        result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script_path}" {params}'.strip(), None, 1)
        return result > 32
    except Exception:
        logger.exception("Error while relaunching as admin"); return False

DARK_STYLE = """QMainWindow{background:#1a1a2e} QWidget{background:#1a1a2e;color:#e0e0e0;font-family:'Segoe UI',Arial;font-size:12px}
QPushButton{background:#2a2a4a;color:#e0e0e0;border:1px solid #3a3a5a;padding:6px 14px;border-radius:4px}
QPushButton:hover{background:#3a3a5a} QPushButton:pressed{background:#4a4a6a} QLineEdit{background:#1e1e32;color:#e0e0e0;border:1px solid #2a2a4a;padding:5px;border-radius:3px}
QTableWidget{background:#1e1e32;color:#ccc;gridline-color:#2a2a3e;border:none} QHeaderView::section{background:#2a2a4a;color:#eee;padding:5px;border:1px solid #2a2a3e}
QScrollBar:vertical{background:#1a1a2e;width:10px} QScrollBar::handle:vertical{background:#2a2a4a;border-radius:4px;min-height:20px}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0} QGroupBox{border:1px solid #2a2a3e;border-radius:6px;margin-top:10px;padding-top:15px;color:#e0e0e0}
QTabWidget::pane{border:1px solid #2a2a3e;background:#1a1a2e} QTabBar::tab{background:#1e1e32;color:#aaa;padding:8px 16px;border:1px solid #2a2a3e} QTabBar::tab:selected{background:#2a2a4a;color:#fff}
QProgressBar{background:#1e1e32;border:1px solid #2a2a3e;border-radius:4px;text-align:center;color:white} QProgressBar::chunk{border-radius:3px}
QComboBox{background:#1e1e32;color:#e0e0e0;border:1px solid #2a2a4a;padding:5px;border-radius:3px} QComboBox QAbstractItemView{background:#1e1e32;color:#e0e0e0;selection-background-color:#2a2a4a}
QSpinBox,QDateEdit{background:#1e1e32;color:#e0e0e0;border:1px solid #2a2a4a;padding:5px} QCheckBox{color:#ccc;spacing:6px} QLabel{color:#e0e0e0} QScrollArea{border:none;background:#1a1a2e}"""
LIGHT_STYLE = """QMainWindow{background:#f5f5f5} QWidget{background:#f5f5f5;color:#333;font-family:'Segoe UI',Arial;font-size:12px}
QPushButton{background:#e0e0e0;color:#333;border:1px solid #ccc;padding:6px 14px;border-radius:4px} QPushButton:hover{background:#d0d0d0}
QLineEdit,QComboBox,QSpinBox,QDateEdit{background:#fff;color:#333;border:1px solid #ccc;padding:5px;border-radius:3px} QTableWidget{background:#fff;color:#333;gridline-color:#ddd;border:none}
QHeaderView::section{background:#e8e8e8;color:#333;padding:5px;border:1px solid #ddd} QScrollBar:vertical{background:#f0f0f0;width:10px} QScrollBar::handle:vertical{background:#ccc;border-radius:4px;min-height:20px}
QGroupBox{border:1px solid #ddd;border-radius:6px;margin-top:10px;padding-top:15px;color:#333} QTabWidget::pane{border:1px solid #ddd;background:#f5f5f5}
QTabBar::tab{background:#e8e8e8;color:#666;padding:8px 16px;border:1px solid #ddd} QTabBar::tab:selected{background:#fff;color:#333}
QProgressBar{background:#e8e8e8;border:1px solid #ddd;border-radius:4px;text-align:center;color:#333} QProgressBar::chunk{background:#4CAF50;border-radius:3px} QCheckBox,QLabel{color:#333}"""


class NavButton(QPushButton):
    def __init__(self, text, icon="", page_index=0, parent=None):
        super().__init__(text, parent); self.page_index = page_index; self.icon = icon; self.source_text = text; self._selected = False
        self.setMinimumHeight(44); self.setCursor(Qt.PointingHandCursor); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self._update_text(); self._update_style()
    def _update_text(self): self.setText(f"{self.icon}  {tr(self.source_text, getattr(self.window(), '_language', LANGUAGE_AR))}" if self.icon else tr(self.source_text, getattr(self.window(), '_language', LANGUAGE_AR)))
    def set_selected(self, selected): self._selected = selected; self.setChecked(selected); self._update_style()
    def _update_style(self):
        direction = getattr(self.window(), '_language', LANGUAGE_AR)
        align = "right" if direction == LANGUAGE_AR else "left"
        border = "right" if direction == LANGUAGE_AR else "left"
        if self._selected:
            self.setStyleSheet(f"QPushButton{{background:#2a2a4a;color:#fff;border:none;border-{border}:3px solid #4CAF50;text-align:{align};padding:10px 16px;font-size:13px;font-weight:bold;border-radius:0}}")
        else:
            self.setStyleSheet(f"QPushButton{{background:transparent;color:#aaa;border:none;border-{border}:3px solid transparent;text-align:{align};padding:10px 16px;font-size:13px;border-radius:0}} QPushButton:hover{{background:#1e1e32;color:#ddd}}")


class SidebarWidget(QFrame):
    navigation_requested = pyqtSignal(int)
    PAGES = [("لوحة التحكم","📊",0),("مراقبة الموارد","📈",1),("إدارة العمليات","⚙",2),("إدارة التخزين","💾",3),("إدارة الخدمات","🔧",4),("الأمان والصحة","🛡",5),("السجلات والتقارير","📋",6),("الأوامر","💻",7),("الإعدادات","⚙",8)]
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedWidth(230); self.setSizePolicy(QSizePolicy.Fixed,QSizePolicy.Expanding)
        self.setStyleSheet("SidebarWidget{background:#12122a;border-left:1px solid #2a2a3e}")
        layout=QVBoxLayout(self); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        self.logo=QLabel("🖥 WinAdmin"); self.logo.setStyleSheet("color:#4CAF50;font-size:20px;font-weight:bold;padding:20px 16px 10px"); layout.addWidget(self.logo)
        self.subtitle=QLabel("أداة إدارة النظام"); self.subtitle.setStyleSheet("color:#666;font-size:10px;padding:0 16px 20px"); layout.addWidget(self.subtitle)
        line=QFrame(); line.setFrameShape(QFrame.HLine); line.setStyleSheet("background:#2a2a3e;max-height:1px"); layout.addWidget(line)
        self.nav_buttons=[]
        for name,icon,idx in self.PAGES:
            btn=NavButton(name,icon,idx); btn.clicked.connect(lambda checked=False,i=idx:self.navigation_requested.emit(i)); layout.addWidget(btn); self.nav_buttons.append(btn)
        layout.addStretch(); self.version=QLabel("v1.0.0 | Python"); self.version.setStyleSheet("color:#555;font-size:9px;padding:10px 16px"); layout.addWidget(self.version); self.set_language(LANGUAGE_AR); self.set_selected(0)
    def set_language(self, language):
        self.setLayoutDirection(Qt.RightToLeft if language==LANGUAGE_AR else Qt.LeftToRight)
        self.logo.setAlignment(Qt.AlignRight|Qt.AlignVCenter if language==LANGUAGE_AR else Qt.AlignLeft|Qt.AlignVCenter)
        self.subtitle.setAlignment(self.logo.alignment()); self.version.setLayoutDirection(Qt.LeftToRight)
        self.version.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        for btn in self.nav_buttons: btn._update_text(); btn._update_style()
        self.setStyleSheet(f"SidebarWidget{{background:#12122a;border-{('left' if language==LANGUAGE_AR else 'right')}:1px solid #2a2a3e}}")
        self.subtitle.setText(tr("أداة إدارة النظام",language))
    def set_selected(self,index):
        for btn in self.nav_buttons: btn.set_selected(btn.page_index==index)


class MainWindow(QMainWindow):
    PAGE_TITLES=("لوحة التحكم","مراقبة الموارد","إدارة العمليات","إدارة التخزين","إدارة الخدمات","الأمان والصحة","السجلات والتقارير","الأوامر","الإعدادات")
    def __init__(self):
        super().__init__(); self._language=normalize_language("ar"); self.setMinimumSize(1100,700); self.resize(1300,800)
        self.setWindowTitle("WinAdmin — أداة إدارة النظام")
        appdata=os.getenv('LOCALAPPDATA') or os.getenv('APPDATA') or os.path.expanduser('~'); db_dir=os.path.join(appdata,'WinAdmin'); os.makedirs(db_dir,exist_ok=True)
        self.db=OptimizedDatabaseManager(os.path.join(db_dir,'winadmin.db')); self.alert_manager=AlertManager(self.db)
        self._language=normalize_language(self.db.get_setting("language","ar")); self._apply_theme(self.db.get_setting("theme","dark")); self._setup_ui(); self._apply_language(self._language)
    def _setup_ui(self):
        central=QWidget(); central.setLayoutDirection(Qt.LeftToRight); self.setCentralWidget(central)
        self.main_layout=QHBoxLayout(central); self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)
        self.content_frame=QFrame(); self.content_frame.setStyleSheet("QFrame{background:#1a1a2e}"); content_layout=QVBoxLayout(self.content_frame); content_layout.setContentsMargins(0,0,0,0); content_layout.setSpacing(0)
        self.top_bar=QFrame(); self.top_bar.setFixedHeight(50); self.top_bar.setStyleSheet("background:#12122a;border-bottom:1px solid #2a2a3e"); self.top_layout=QHBoxLayout(self.top_bar); self.top_layout.setContentsMargins(12,0,12,0); self.top_layout.setSpacing(8)
        self.lbl_top_title=QLabel(); self.lbl_top_title.setStyleSheet("color:#e0e0e0;font-size:14px;font-weight:bold"); self.top_layout.addWidget(self.lbl_top_title); self.top_layout.addStretch()
        self.btn_hardware=QPushButton(); self.btn_hardware.setMinimumHeight(34); self.btn_hardware.setStyleSheet("QPushButton{background:#234b35;color:#dfffe9;border:1px solid #35734e;padding:6px 12px;border-radius:5px;font-weight:bold} QPushButton:hover{background:#2d6245}"); self.btn_hardware.clicked.connect(self._open_hardware_advisor); self.top_layout.addWidget(self.btn_hardware)
        self.language_combo=QComboBox(); self.language_combo.setMinimumWidth(115); self.language_combo.addItem("العربية",LANGUAGE_AR); self.language_combo.addItem("English",LANGUAGE_EN); self.language_combo.currentIndexChanged.connect(self._language_changed); self.top_layout.addWidget(self.language_combo)
        self.lbl_time=QLabel(); self.lbl_time.setLayoutDirection(Qt.LeftToRight); self.lbl_time.setMinimumWidth(145); self.lbl_time.setStyleSheet("color:#888;font-size:11px"); self.top_layout.addWidget(self.lbl_time)
        content_layout.addWidget(self.top_bar)
        self.stack=QStackedWidget(); self.stack.setStyleSheet("QStackedWidget{background:#1a1a2e}")
        self.page_factories=(lambda:DashboardWidget(self.db,self.alert_manager),lambda:ResourceMonitorWidget(),lambda:ProcessManagerWidget(),lambda:StorageManagerWidget(),lambda:ServiceManagerWidget(),lambda:SecurityWidget(self.db),lambda:ReportsWidget(self.db),lambda:CommandsWidget(),lambda:SettingsWidget(self.db,self.alert_manager))
        self.pages=[None]*len(self.page_factories); content_layout.addWidget(self.stack,1)
        self.sidebar=SidebarWidget(); self.sidebar.navigation_requested.connect(self._switch_page); self.main_layout.addWidget(self.content_frame,1); self.main_layout.addWidget(self.sidebar,0); self._ensure_page(0)
        self._time_timer=QTimer(self); self._time_timer.setTimerType(Qt.CoarseTimer); self._time_timer.timeout.connect(self._update_time); self._time_timer.start(1000); self._update_time()
    def _language_changed(self,index):
        if getattr(self,'_setting_language',False): return
        self._apply_language(self.language_combo.itemData(index))
    def _apply_language(self,language):
        self._language=normalize_language(language); rtl=self._language==LANGUAGE_AR; direction=Qt.RightToLeft if rtl else Qt.LeftToRight
        QApplication.instance().setLayoutDirection(direction); self.setLayoutDirection(direction); self.content_frame.setLayoutDirection(direction); self.top_bar.setLayoutDirection(direction); self.stack.setLayoutDirection(direction)
        self.main_layout.setDirection(QHBoxLayout.LeftToRight)
        while self.main_layout.count(): self.main_layout.takeAt(0)
        if rtl: self.main_layout.addWidget(self.content_frame,1); self.main_layout.addWidget(self.sidebar,0)
        else: self.main_layout.addWidget(self.sidebar,0); self.main_layout.addWidget(self.content_frame,1)
        self.top_layout.setDirection(QHBoxLayout.RightToLeft if rtl else QHBoxLayout.LeftToRight)
        self.lbl_top_title.setText(tr(self.PAGE_TITLES[self.stack.currentIndex() if self.stack.currentIndex()>=0 else 0],self._language))
        self.lbl_top_title.setAlignment(Qt.AlignRight|Qt.AlignVCenter if rtl else Qt.AlignLeft|Qt.AlignVCenter)
        self.btn_hardware.setText(tr("فحص الجهاز والمساعد الذكي",self._language)); self.btn_hardware.setToolTip(tr("تحليل مواصفات الجهاز وتحديد أفضل الاستخدامات والتوصيات",self._language))
        self.language_combo.blockSignals(True); self.language_combo.setCurrentIndex(0 if rtl else 1); self.language_combo.blockSignals(False)
        self.sidebar.set_language(self._language)
        for page in self.pages:
            if page is not None:
                try:
                    apply_language(page,self._language)
                    if hasattr(page,'set_language'): page.set_language(self._language)
                except Exception: logger.exception("Language update failed for %s",type(page).__name__)
        try: self.db.set_setting("language",self._language)
        except Exception: pass
    def _ensure_page(self,index):
        if not 0<=index<len(self.page_factories): return None
        if self.pages[index] is not None: return self.pages[index]
        try:
            page=self.page_factories[index](); page.setLayoutDirection(Qt.RightToLeft if self._language==LANGUAGE_AR else Qt.LeftToRight); self.pages[index]=page; self.stack.addWidget(page); apply_language(page,self._language)
            if hasattr(page,'set_language'): page.set_language(self._language)
            return page
        except Exception as exc:
            self.pages[index]=None; logger.exception("Failed to create page %s",index); QMessageBox.critical(self,tr("خطأ في فتح الصفحة",self._language),f"{tr('تعذر فتح صفحة',self._language)} «{tr(self.PAGE_TITLES[index],self._language)}».\n\n{exc}"); return None
    @staticmethod
    def _stop_page_timers(page):
        for name in ('timer','timer_slow'):
            try:
                timer=getattr(page,name,None)
                if timer is not None and timer.isActive(): timer.stop()
            except RuntimeError: pass
    @staticmethod
    def _resume_page_timers(page):
        for name in ('timer','timer_slow'):
            try:
                timer=getattr(page,name,None)
                if timer is not None and not timer.isActive(): timer.start()
            except RuntimeError: pass
    def _switch_page(self,index):
        page=self._ensure_page(index)
        if page is None:return
        for other in self.pages:
            if other is not None and other is not page:self._stop_page_timers(other)
        try:self.stack.setCurrentWidget(page)
        except RuntimeError:return
        self._resume_page_timers(page); self.lbl_top_title.setText(tr(self.PAGE_TITLES[index],self._language)); self.sidebar.set_selected(index)
    def _open_hardware_advisor(self):
        try: HardwareAdvisorDialog(self).exec_()
        except Exception as exc: logger.exception("Failed to open hardware advisor"); QMessageBox.critical(self,tr("خطأ",self._language),f"{tr('تعذر فتح فحص الجهاز',self._language)}.\n\n{exc}")
    def _update_time(self):
        try:self.lbl_time.setText(datetime.now().strftime("%Y-%m-%d  %H:%M:%S"))
        except RuntimeError:pass
    def _apply_theme(self,theme): QApplication.instance().setStyleSheet(LIGHT_STYLE if theme=="light" else DARK_STYLE)
    def closeEvent(self,event):
        try:self._time_timer.stop(); self._time_timer.timeout.disconnect(self._update_time)
        except Exception:pass
        for page in self.pages:
            if page is not None:
                try:
                    if hasattr(page,'stop'):page.stop()
                except Exception:logger.exception("Error stopping page")
        try:self.db.close()
        except Exception:logger.exception("Error closing database")
        event.accept()


def main():
    app=QApplication(sys.argv); app.setApplicationDisplayName("WinAdmin"); app.setApplicationName("WinAdmin"); app.setApplicationVersion("1.0.0"); app.setLayoutDirection(Qt.RightToLeft)
    if os.name=="nt" and not is_admin():
        reply=QMessageBox.question(None,tr("تحتاج صلاحيات المدير","ar"),"هذا التطبيق يفضل التشغيل بصلاحيات Administrator لعمل بعض الأدوات.\nهل تريد إعادة التشغيل بصلاحيات الإدارة؟",QMessageBox.Yes|QMessageBox.No,QMessageBox.No)
        if reply==QMessageBox.Yes and relaunch_as_admin():return
    window=MainWindow(); window.show(); sys.exit(app.exec_())
if __name__=="__main__":main()
