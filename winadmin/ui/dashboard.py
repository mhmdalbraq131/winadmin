"""
ui/dashboard.py — لوحة التحكم الرئيسية
عرض ملخص لحالة النظام مع رسوم بيانية مباشرة وتنبيهات فورية.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QFrame, QScrollArea, QPushButton, QGridLayout,
                              QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
from core.system_info import SystemInfo


class GaugeWidget(QWidget):
    """مقياس دائري لعرض نسبة الاستهلاك."""

    def __init__(self, title: str, color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.value = 0.0
        self.setMinimumSize(170, 170)
        self.setMaximumSize(220, 220)

    def set_value(self, val: float):
        self.value = max(0, min(100, val))
        # تغيير اللون حسب القيمة
        if self.value >= 90:
            self.color = "#f44336"
        elif self.value >= 75:
            self.color = "#ff9800"
        else:
            self.color = "#4CAF50"
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QConicalGradient, QBrush
        from PyQt5.QtCore import QRectF

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height()) - 10
        rect = QRectF(5, 5, side, side)

        # خلفية المقياس
        pen_bg = QPen(QColor("#2a2a3e"), 10)
        painter.setPen(pen_bg)
        painter.drawArc(rect, 0, 360 * 16)

        # القيمة
        pen_val = QPen(QColor(self.color), 10)
        pen_val.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_val)
        span = int(self.value * 3.6 * 16)
        start = 90 * 16
        painter.drawArc(rect, start, -span)

        # النص
        painter.setPen(QColor("#e0e0e0"))
        font = QFont("Segoe UI", 18, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{self.value:.0f}%")

        # العنوان
        painter.setPen(QColor("#aaaaaa"))
        font_small = QFont("Segoe UI", 9)
        painter.setFont(font_small)
        title_rect = QRectF(0, self.height() - 22, self.width(), 20)
        painter.drawText(title_rect, Qt.AlignCenter, self.title)

        painter.end()


class InfoCard(QFrame):
    """بطاقة معلومات مع عنوان وقيمة."""

    def __init__(self, title: str, value: str = "—", color: str = "#4CAF50", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            InfoCard {{
                background-color: #1e1e32;
                border: 1px solid {color};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        layout.addWidget(lbl_title)

        self.lbl_value = QLabel(value)
        self.lbl_value.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: bold;")
        self.lbl_value.setWordWrap(True)
        layout.addWidget(self.lbl_value)

    def set_value(self, value: str):
        self.lbl_value.setText(value)


class AlertBanner(QFrame):
    """شريط تنبيه يظهر عند تجاوز العتبات."""

    clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            AlertBanner {
                background-color: #3e1c1c;
                border: 1px solid #f44336;
                border-radius: 6px;
                padding: 6px;
            }
        """)
        layout = QHBoxLayout(self)

        self.icon_lbl = QLabel("⚠")
        self.icon_lbl.setStyleSheet("color: #f44336; font-size: 16px;")
        layout.addWidget(self.icon_lbl)

        self.msg_lbl = QLabel("")
        self.msg_lbl.setStyleSheet("color: #ff8a80; font-size: 12px;")
        self.msg_lbl.setWordWrap(True)
        layout.addWidget(self.msg_lbl, 1)

        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.setStyleSheet("color: #ff8a80; border: none; font-size: 14px;")
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

        self.hide()

    def show_alert(self, message: str, severity: str = "warning"):
        self.msg_lbl.setText(message)
        if severity == "critical":
            self.setStyleSheet("AlertBanner { background-color: #4e0e0e; border: 1px solid #ff1744; border-radius: 6px; padding: 6px; }")
        else:
            self.setStyleSheet("AlertBanner { background-color: #3e2c1c; border: 1px solid #ff9800; border-radius: 6px; padding: 6px; }")
        self.show()
        # إخفاء تلقائي بعد 15 ثانية
        QTimer.singleShot(15000, self.hide)


class DashboardWidget(QWidget):
    """لوحة التحكم الرئيسية — عرض شامل لحالة النظام."""

    def __init__(self, db_manager, alert_manager, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.alert_manager = alert_manager
        self._setup_ui()
        self._start_timers()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # ─ شريط التنبيهات ─
        self.alert_banner = AlertBanner()
        main_layout.addWidget(self.alert_banner)

        # ─ عنوان ─
        title = QLabel("🖥 لوحة التحكم")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        main_layout.addWidget(title)

        # ─ مقاييس الموارد ─
        gauges_layout = QHBoxLayout()
        gauges_layout.setSpacing(20)

        self.gauge_cpu = GaugeWidget("المعالج (CPU)", "#4CAF50")
        self.gauge_ram = GaugeWidget("الذاكرة (RAM)", "#2196F3")
        self.gauge_disk = GaugeWidget("التخزين (Disk)", "#FF9800")
        self.gauge_net = GaugeWidget("الشبكة (Net)", "#9C27B0")

        gauges_layout.addWidget(self.gauge_cpu)
        gauges_layout.addWidget(self.gauge_ram)
        gauges_layout.addWidget(self.gauge_disk)
        gauges_layout.addWidget(self.gauge_net)
        gauges_layout.addStretch()

        main_layout.addLayout(gauges_layout)

        # ─ بطاقات المعلومات ─
        cards_layout = QGridLayout()
        cards_layout.setSpacing(10)

        self.card_hostname = InfoCard("🖥 اسم الجهاز", "—", "#4CAF50")
        self.card_os = InfoCard("💾 نظام التشغيل", "—", "#2196F3")
        self.card_uptime = InfoCard("⏱ وقت التشغيل", "—", "#FF9800")
        self.card_cpu_model = InfoCard("⚡ المعالج", "—", "#9C27B0")
        self.card_ram_total = InfoCard("🧠 الذاكرة الكلية", "—", "#00BCD4")
        self.card_disk_total = InfoCard("💾 التخزين الكلي", "—", "#E91E63")

        cards_layout.addWidget(self.card_hostname, 0, 0)
        cards_layout.addWidget(self.card_os, 0, 1)
        cards_layout.addWidget(self.card_uptime, 0, 2)
        cards_layout.addWidget(self.card_cpu_model, 1, 0)
        cards_layout.addWidget(self.card_ram_total, 1, 1)
        cards_layout.addWidget(self.card_disk_total, 1, 2)

        main_layout.addLayout(cards_layout)

        # ─ تفاصيل إضافية ─
        detail_row = QHBoxLayout()
        detail_row.setSpacing(10)

        # معلومات الشبكة
        self.card_net_up = InfoCard("📤 رفع", "—", "#4CAF50")
        self.card_net_down = InfoCard("📥 تنزيل", "—", "#2196F3")
        detail_row.addWidget(self.card_net_up)
        detail_row.addWidget(self.card_net_down)

        # آخر الأخطاء
        self.card_errors = InfoCard("🔴 آخر الأخطاء", "—", "#f44336")
        self.card_errors.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        detail_row.addWidget(self.card_errors)

        detail_row.addStretch()
        main_layout.addLayout(detail_row)

        # ─ التنبيهات الأخيرة ─
        alerts_label = QLabel("🔔 آخر التنبيهات")
        alerts_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0; margin-top: 10px;")
        main_layout.addWidget(alerts_label)

        self.alerts_list_label = QLabel("لا توجد تنبيهات")
        self.alerts_list_label.setStyleSheet("color: #888; font-size: 12px; padding: 8px;")
        self.alerts_list_label.setWordWrap(True)
        main_layout.addWidget(self.alerts_list_label)

        main_layout.addStretch()

        # تسجيل استدعاء التنبيه
        self.alert_manager.register_callback(self._on_alert)

    def _start_timers(self):
        """بدء مؤقتات التحديث."""
        self._update_static_info()
        self._update_dynamic_info()

        # تحديث ديناميكي كل 2 ثانية
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_dynamic_info)
        self.timer.start(2000)

        # تحديث ثابت كل 30 ثانية
        self.timer_slow = QTimer(self)
        self.timer_slow.timeout.connect(self._update_static_info)
        self.timer_slow.start(30000)

    def _update_static_info(self):
        """تحديث المعلومات الثابتة."""
        try:
            overview = SystemInfo.get_system_overview()
            self.card_hostname.set_value(overview.get("hostname", "—"))
            self.card_os.set_value(overview.get("os", "—"))
            self.card_uptime.set_value(overview.get("uptime", "—"))
            self.card_cpu_model.set_value(overview.get("processor", "—"))

            mem = SystemInfo.get_memory_info()
            self.card_ram_total.set_value(SystemInfo.bytes_to_human(mem.get("total", 0)))

            disks = SystemInfo.get_disk_info()
            if disks:
                self.card_disk_total.set_value(SystemInfo.bytes_to_human(disks[0].get("total", 0)))
        except Exception as e:
            pass

    def _update_dynamic_info(self):
        """تحديث البيانات المتغيرة."""
        try:
            cpu = SystemInfo.get_cpu_info()
            mem = SystemInfo.get_memory_info()
            disks = SystemInfo.get_disk_info()
            net = SystemInfo.get_network_info()

            cpu_pct = cpu.get("percent", 0)
            ram_pct = mem.get("percent", 0)
            disk_pct = disks[0].get("percent", 0) if disks else 0

            self.gauge_cpu.set_value(cpu_pct)
            self.gauge_ram.set_value(ram_pct)
            self.gauge_disk.set_value(disk_pct)

            # مقياس الشبكة (استخدام رمزي بنسبة من سرعة الارتباط)
            net_speed = sum(iface.get("speed", 0) for iface in net.get("interfaces", []))
            net_pct = min(100, (net.get("bytes_recv", 0) / max(1, net_speed * 1_000_000)) * 100) if net_speed > 0 else 0
            self.gauge_net.set_value(min(net_pct, 50))  # تقدير رمزي

            # بطاقات الشبكة
            self.card_net_up.set_value(SystemInfo.bytes_to_human(net.get("bytes_sent", 0)))
            self.card_net_down.set_value(SystemInfo.bytes_to_human(net.get("bytes_recv", 0)))

            # آخر الأخطاء
            errors = self.db.get_recent_errors(3)
            if errors:
                err_text = "\n".join(f"• [{e.get('level','')}] {e.get('source','')}: {(e.get('message','')[:60])}" for e in errors)
                self.card_errors.set_value(err_text)
            else:
                self.card_errors.set_value("لا توجد أخطاء حديثة ✓")

            # فحص العتبات
            self.alert_manager.check_thresholds(cpu_pct, ram_pct, disk_pct)

            # تسجيل الأداء في قاعدة البيانات (كل 2 ثانية)
            self.db.log_performance(
                cpu_pct, ram_pct, mem.get("used", 0), mem.get("total", 0),
                disk_pct, disks[0].get("used", 0) if disks else 0,
                disks[0].get("total", 0) if disks else 0,
                net.get("bytes_sent", 0), net.get("bytes_recv", 0)
            )

            # آخر التنبيهات
            alerts = self.db.get_recent_alerts(5)
            if alerts:
                alert_text = "\n".join(
                    f"• [{a.get('severity','')}] {a.get('message','')}"
                    for a in alerts
                )
                self.alerts_list_label.setText(alert_text)
                self.alerts_list_label.setStyleSheet("color: #ff8a80; font-size: 12px; padding: 8px;")
            else:
                self.alerts_list_label.setText("لا توجد تنبيهات ✓")
                self.alerts_list_label.setStyleSheet("color: #888; font-size: 12px; padding: 8px;")

        except Exception as e:
            pass

    def _on_alert(self, key, severity, message):
        """استدعاء عند تلقي تنبيه — عرض في الشريط."""
        self.alert_banner.show_alert(message, severity)

    def stop(self):
        """إيقاف المؤقتات."""
        self.timer.stop()
        self.timer_slow.stop()
