"""
ui/settings.py — الإعدادات
عتبات التنبيهات، البريد الإلكتروني، جدولة الفحوصات، الأجهزة البعيدة، المظهر.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QLineEdit, QSpinBox, QGroupBox,
                              QGridLayout, QCheckBox, QComboBox, QTableWidget,
                              QTableWidgetItem, QHeaderView, QMessageBox,
                              QTabWidget, QFileDialog, QDialog,
                              QDialogButtonBox, QFormLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class AddHostDialog(QDialog):
    """نافذة إضافة جهاز بعيد."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("إضافة جهاز بعيد")
        self.setMinimumWidth(350)
        self.setStyleSheet("background: #1a1a2e; color: #e0e0e0;")

        layout = QFormLayout(self)

        self.input_hostname = QLineEdit()
        self.input_hostname.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; border-radius: 3px;")
        layout.addRow("اسم الجهاز:", self.input_hostname)

        self.input_ip = QLineEdit()
        self.input_ip.setStyleSheet(self.input_hostname.styleSheet())
        layout.addRow("عنوان IP:", self.input_ip)

        self.input_port = QSpinBox()
        self.input_port.setRange(1, 65535)
        self.input_port.setValue(5555)
        self.input_port.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px;")
        layout.addRow("المنفذ:", self.input_port)

        self.input_user = QLineEdit()
        self.input_user.setStyleSheet(self.input_hostname.styleSheet())
        layout.addRow("اسم المستخدم:", self.input_user)

        self.input_token = QLineEdit()
        self.input_token.setEchoMode(QLineEdit.Password)
        self.input_token.setStyleSheet(self.input_hostname.styleSheet())
        layout.addRow("رمز المصادقة:", self.input_token)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 15px; border-radius: 3px;")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_data(self):
        return {
            "hostname": self.input_hostname.text(),
            "ip": self.input_ip.text(),
            "port": self.input_port.value(),
            "username": self.input_user.text(),
            "auth_token": self.input_token.text(),
        }


class SettingsWidget(QWidget):
    """الإعدادات — عتبات، بريد، أجهزة بعيدة، مظهر."""

    def __init__(self, db_manager, alert_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.alert_manager = alert_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("⚙ الإعدادات")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ تبويبات ─
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a3e; background: #1a1a2e; }
            QTabBar::tab { background: #1e1e32; color: #aaa; padding: 8px 20px; border: 1px solid #2a2a3e; }
            QTabBar::tab:selected { background: #2a2a4a; color: #fff; }
        """)

        # ── تبويب عتبات التنبيهات ──
        threshold_tab = QWidget()
        threshold_layout = QGridLayout(threshold_tab)

        # CPU
        lbl_cpu = QLabel("⚡ عتبة المعالج (CPU):")
        lbl_cpu.setStyleSheet("color: #ccc; font-size: 13px;")
        threshold_layout.addWidget(lbl_cpu, 0, 0)
        self.spin_cpu = QSpinBox()
        self.spin_cpu.setRange(50, 100)
        self.spin_cpu.setValue(int(self.alert_manager.thresholds.get("cpu_percent", 90)))
        self.spin_cpu.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px;")
        self.spin_cpu.setSuffix(" %")
        threshold_layout.addWidget(self.spin_cpu, 0, 1)

        # RAM
        lbl_ram = QLabel("🧠 عتبة الذاكرة (RAM):")
        lbl_ram.setStyleSheet("color: #ccc; font-size: 13px;")
        threshold_layout.addWidget(lbl_ram, 1, 0)
        self.spin_ram = QSpinBox()
        self.spin_ram.setRange(50, 100)
        self.spin_ram.setValue(int(self.alert_manager.thresholds.get("ram_percent", 90)))
        self.spin_ram.setStyleSheet(self.spin_cpu.styleSheet())
        self.spin_ram.setSuffix(" %")
        threshold_layout.addWidget(self.spin_ram, 1, 1)

        # Disk
        lbl_disk = QLabel("💾 عتبة التخزين (Disk):")
        lbl_disk.setStyleSheet("color: #ccc; font-size: 13px;")
        threshold_layout.addWidget(lbl_disk, 2, 0)
        self.spin_disk = QSpinBox()
        self.spin_disk.setRange(50, 100)
        self.spin_disk.setValue(int(self.alert_manager.thresholds.get("disk_percent", 90)))
        self.spin_disk.setStyleSheet(self.spin_cpu.styleSheet())
        self.spin_disk.setSuffix(" %")
        threshold_layout.addWidget(self.spin_disk, 2, 1)

        self.btn_save_thresholds = QPushButton("💾 حفظ العتبات")
        self.btn_save_thresholds.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 20px; border-radius: 4px;")
        self.btn_save_thresholds.clicked.connect(self._save_thresholds)
        threshold_layout.addWidget(self.btn_save_thresholds, 3, 0, 1, 2)

        self.tabs.addTab(threshold_tab, "📊 عتبات التنبيهات")

        # ── تبويب البريد الإلكتروني ──
        email_tab = QWidget()
        email_layout = QGridLayout(email_tab)

        self.chk_email = QCheckBox("تفعيل تنبيهات البريد")
        self.chk_email.setChecked(self.alert_manager.email_settings.get("enabled", False))
        self.chk_email.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(self.chk_email, 0, 0, 1, 2)

        lbl_smtp = QLabel("خادم SMTP:")
        lbl_smtp.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(lbl_smtp, 1, 0)
        self.input_smtp = QLineEdit(self.alert_manager.email_settings.get("smtp_server", ""))
        self.input_smtp.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; border-radius: 3px;")
        email_layout.addWidget(self.input_smtp, 1, 1)

        lbl_port = QLabel("المنفذ:")
        lbl_port.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(lbl_port, 2, 0)
        self.spin_smtp_port = QSpinBox()
        self.spin_smtp_port.setRange(1, 65535)
        self.spin_smtp_port.setValue(self.alert_manager.email_settings.get("smtp_port", 587))
        self.spin_smtp_port.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px;")
        email_layout.addWidget(self.spin_smtp_port, 2, 1)

        lbl_sender = QLabel("البريد المرسل:")
        lbl_sender.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(lbl_sender, 3, 0)
        self.input_sender = QLineEdit(self.alert_manager.email_settings.get("sender", ""))
        self.input_sender.setStyleSheet(self.input_smtp.styleSheet())
        email_layout.addWidget(self.input_sender, 3, 1)

        lbl_pass = QLabel("كلمة المرور:")
        lbl_pass.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(lbl_pass, 4, 0)
        self.input_pass = QLineEdit(self.alert_manager.email_settings.get("password", ""))
        self.input_pass.setEchoMode(QLineEdit.Password)
        self.input_pass.setStyleSheet(self.input_smtp.styleSheet())
        email_layout.addWidget(self.input_pass, 4, 1)

        lbl_recipients = QLabel("المستلمون (مفصولين بفاصلة):")
        lbl_recipients.setStyleSheet("color: #ccc; font-size: 13px;")
        email_layout.addWidget(lbl_recipients, 5, 0)
        self.input_recipients = QLineEdit(",".join(self.alert_manager.email_settings.get("recipients", [])))
        self.input_recipients.setStyleSheet(self.input_smtp.styleSheet())
        email_layout.addWidget(self.input_recipients, 5, 1)

        btn_row = QHBoxLayout()
        self.btn_save_email = QPushButton("💾 حفظ")
        self.btn_save_email.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 20px; border-radius: 4px;")
        self.btn_save_email.clicked.connect(self._save_email)
        btn_row.addWidget(self.btn_save_email)

        self.btn_test_email = QPushButton("📧 اختبار")
        self.btn_test_email.setStyleSheet("background: #1c3e2c; color: #80ffcc; border: none; padding: 8px 20px; border-radius: 4px;")
        self.btn_test_email.clicked.connect(self._test_email)
        btn_row.addWidget(self.btn_test_email)

        email_layout.addLayout(btn_row, 6, 0, 1, 2)

        self.tabs.addTab(email_tab, "📧 البريد الإلكتروني")

        # ── تبويب الأجهزة البعيدة ──
        remote_tab = QWidget()
        remote_layout = QVBoxLayout(remote_tab)

        btn_row_remote = QHBoxLayout()
        btn_add_host = QPushButton("➕ إضافة جهاز")
        btn_add_host.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 6px 14px; border-radius: 4px;")
        btn_add_host.clicked.connect(self._add_remote_host)
        btn_row_remote.addWidget(btn_add_host)

        btn_remove_host = QPushButton("🗑 حذف جهاز")
        btn_remove_host.setStyleSheet("background: #4e1c1c; color: #ff8a80; border: none; padding: 6px 14px; border-radius: 4px;")
        btn_remove_host.clicked.connect(self._remove_remote_host)
        btn_row_remote.addWidget(btn_remove_host)
        btn_row_remote.addStretch()
        remote_layout.addLayout(btn_row_remote)

        self.host_table = QTableWidget()
        self.host_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
        """)
        self.host_table.setColumnCount(5)
        self.host_table.setHorizontalHeaderLabels(["الاسم", "IP", "المنفذ", "المستخدم", "الحالة"])
        self.host_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.host_table.setEditTriggers(QTableWidget.NoEditTriggers)
        remote_layout.addWidget(self.host_table)

        self.tabs.addTab(remote_tab, "🌐 الأجهزة البعيدة")

        # ── تبويب المظهر ──
        theme_tab = QWidget()
        theme_layout = QVBoxLayout(theme_tab)

        lbl_theme = QLabel("🎨 المظهر")
        lbl_theme.setStyleSheet("color: #ccc; font-size: 14px; font-weight: bold;")
        theme_layout.addWidget(lbl_theme)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["مظلم (Dark)", "فاتح (Light)"])
        current_theme = self.db.get_setting("theme", "dark")
        self.theme_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        self.theme_combo.setStyleSheet("""
            QComboBox { background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; border-radius: 4px; padding: 6px; }
            QComboBox QAbstractItemView { background: #1e1e32; color: #e0e0e0; }
        """)
        theme_layout.addWidget(self.theme_combo)

        self.btn_apply_theme = QPushButton("تطبيق المظهر")
        self.btn_apply_theme.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 8px 20px; border-radius: 4px;")
        self.btn_apply_theme.clicked.connect(self._apply_theme)
        theme_layout.addWidget(self.btn_apply_theme)

        # ── مسار السجلات ──
        lbl_log_path = QLabel("📁 مسار حفظ السجلات:")
        lbl_log_path.setStyleSheet("color: #ccc; font-size: 13px; margin-top: 15px;")
        theme_layout.addWidget(lbl_log_path)

        path_row = QHBoxLayout()
        self.input_log_path = QLineEdit(self.db.get_setting("log_path", "./logs"))
        self.input_log_path.setStyleSheet("background: #1e1e32; color: #e0e0e0; border: 1px solid #2a2a4a; padding: 5px; border-radius: 3px;")
        path_row.addWidget(self.input_log_path)

        btn_browse = QPushButton("📂")
        btn_browse.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 5px 10px; border-radius: 3px;")
        btn_browse.clicked.connect(self._browse_log_path)
        path_row.addWidget(btn_browse)

        btn_save_path = QPushButton("💾 حفظ")
        btn_save_path.setStyleSheet("background: #2a2a4a; color: #e0e0e0; border: none; padding: 5px 12px; border-radius: 3px;")
        btn_save_path.clicked.connect(self._save_log_path)
        path_row.addWidget(btn_save_path)

        theme_layout.addLayout(path_row)

        # ── تنظيف البيانات ──
        lbl_cleanup = QLabel("🧹 تنظيف البيانات القديمة:")
        lbl_cleanup.setStyleSheet("color: #ccc; font-size: 13px; margin-top: 15px;")
        theme_layout.addWidget(lbl_cleanup)

        btn_cleanup = QPushButton("حذف بيانات أقدم من 30 يوم")
        btn_cleanup.setStyleSheet("background: #4e1c1c; color: #ff8a80; border: none; padding: 8px 16px; border-radius: 4px;")
        btn_cleanup.clicked.connect(self._cleanup_data)
        theme_layout.addWidget(btn_cleanup)

        theme_layout.addStretch()

        self.tabs.addTab(theme_tab, "🎨 المظهر والسجلات")

        layout.addWidget(self.tabs)

        # تحميل الأجهزة البعيدة
        self._load_remote_hosts()

    # ── حفظ العتبات ──────────────────────────────────────
    def _save_thresholds(self):
        self.alert_manager.update_threshold("cpu_percent", self.spin_cpu.value())
        self.alert_manager.update_threshold("ram_percent", self.spin_ram.value())
        self.alert_manager.update_threshold("disk_percent", self.spin_disk.value())
        QMessageBox.information(self, "تم", "تم حفظ عتبات التنبيهات")

    # ── حفظ إعدادات البريد ──────────────────────────────
    def _save_email(self):
        self.alert_manager.update_email_settings({
            "enabled": self.chk_email.isChecked(),
            "smtp_server": self.input_smtp.text(),
            "smtp_port": self.spin_smtp_port.value(),
            "sender": self.input_sender.text(),
            "password": self.input_pass.text(),
            "recipients": [r.strip() for r in self.input_recipients.text().split(",") if r.strip()],
        })
        QMessageBox.information(self, "تم", "تم حفظ إعدادات البريد")

    def _test_email(self):
        success, msg = self.alert_manager.test_email()
        if success:
            QMessageBox.information(self, "نجاح", msg)
        else:
            QMessageBox.critical(self, "فشل", msg)

    # ── الأجهزة البعيدة ──────────────────────────────────
    def _add_remote_host(self):
        dialog = AddHostDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if data["hostname"] and data["ip"]:
                self.db.add_remote_host(data["hostname"], data["ip"],
                                        data["port"], data["username"], data["auth_token"])
                self._load_remote_hosts()
            else:
                QMessageBox.warning(self, "تنبيه", "يجب ملء اسم الجهاز وعنوان IP")

    def _remove_remote_host(self):
        row = self.host_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "تنبيه", "اختر جهازاً للحذف")
            return

        host_id = self.host_table.item(row, 0).data(Qt.UserRole)
        reply = QMessageBox.question(self, "تأكيد", "هل تريد حذف هذا الجهاز؟",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.remove_remote_host(host_id)
            self._load_remote_hosts()

    def _load_remote_hosts(self):
        hosts = self.db.get_remote_hosts()
        self.host_table.setRowCount(len(hosts))
        for i, h in enumerate(hosts):
            item = QTableWidgetItem(h.get("hostname", ""))
            item.setData(Qt.UserRole, h.get("id"))
            self.host_table.setItem(i, 0, item)
            self.host_table.setItem(i, 1, QTableWidgetItem(h.get("ip_address", "")))
            self.host_table.setItem(i, 2, QTableWidgetItem(str(h.get("port", 5555))))
            self.host_table.setItem(i, 3, QTableWidgetItem(h.get("username", "")))
            self.host_table.setItem(i, 4, QTableWidgetItem(h.get("status", "unknown")))

    # ── المظهر ────────────────────────────────────────────
    def _apply_theme(self):
        theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        self.db.set_setting("theme", theme)
        QMessageBox.information(self, "المظهر", f"سيتم تطبيق المظهر {theme} عند إعادة تشغيل التطبيق")

    # ── مسار السجلات ──────────────────────────────────────
    def _browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "اختر مجلد السجلات")
        if path:
            self.input_log_path.setText(path)

    def _save_log_path(self):
        self.db.set_setting("log_path", self.input_log_path.text())
        QMessageBox.information(self, "تم", "تم حفظ مسار السجلات")

    # ── تنظيف البيانات ────────────────────────────────────
    def _cleanup_data(self):
        reply = QMessageBox.question(self, "تأكيد", "سيتم حذف البيانات الأقدم من 30 يوم. هل تريد المتابعة؟",
                                      QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.cleanup_old_data(30)
            QMessageBox.information(self, "تم", "تم تنظيف البيانات القديمة")

    def stop(self):
        pass
