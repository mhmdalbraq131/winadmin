"""Responsive dashboard with clean RTL/LTR behavior."""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor, QFont
from core.system_info import SystemInfo
from core.i18n import LANGUAGE_AR, tr


class GaugeWidget(QWidget):
    def __init__(self, title, color="#4CAF50", parent=None):
        super().__init__(parent); self.source_title = title; self.title = title; self.color = color; self.value = 0.0
        self.setMinimumSize(135, 135); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    def set_language(self, language): self.title = tr(self.source_title, language); self.update()
    def set_value(self, value):
        self.value=max(0.0,min(100.0,float(value))); self.color="#f44336" if self.value>=90 else "#ff9800" if self.value>=75 else "#4CAF50"; self.update()
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.Antialiasing); side=min(self.width(),self.height())-14; rect=QRectF((self.width()-side)/2,5,side,side)
        painter.setPen(QPen(QColor("#2a2a3e"),9)); painter.drawArc(rect,0,360*16); pen=QPen(QColor(self.color),9); pen.setCapStyle(Qt.RoundCap); painter.setPen(pen); painter.drawArc(rect,90*16,-int(self.value*3.6*16))
        painter.setPen(QColor("#e0e0e0")); painter.setFont(QFont("Segoe UI",17,QFont.Bold)); painter.drawText(rect,Qt.AlignCenter,f"{self.value:.0f}%")
        painter.setPen(QColor("#aaa")); painter.setFont(QFont("Segoe UI",9)); painter.drawText(QRectF(0,self.height()-22,self.width(),20),Qt.AlignCenter,self.title); painter.end()


class InfoCard(QFrame):
    def __init__(self,title,value="—",accent="#4CAF50",parent=None):
        super().__init__(parent); self.setObjectName("InfoCard"); self.setStyleSheet(f"InfoCard{{background:#1e1e32;border:1px solid {accent};border-radius:8px}}")
        layout=QVBoxLayout(self); layout.setContentsMargins(12,9,12,9); layout.setSpacing(4); self.lbl_title=QLabel(title); self.lbl_title.setStyleSheet(f"color:{accent};font-size:11px;font-weight:bold"); self.lbl_value=QLabel(value); self.lbl_value.setStyleSheet("color:#e0e0e0;font-size:13px;font-weight:bold"); self.lbl_value.setWordWrap(True); self.lbl_value.setTextInteractionFlags(Qt.TextSelectableByMouse); layout.addWidget(self.lbl_title); layout.addWidget(self.lbl_value,1); self.setMinimumHeight(76)
    def set_value(self,value): self.lbl_value.setText(str(value))


class AlertBanner(QFrame):
    clicked=pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent); self.setObjectName("AlertBanner"); layout=QHBoxLayout(self); layout.setContentsMargins(10,6,10,6); self.icon_lbl=QLabel("⚠"); self.msg_lbl=QLabel(""); self.msg_lbl.setWordWrap(True); self.close_btn=QLabel("✕"); self.close_btn.setCursor(Qt.PointingHandCursor); layout.addWidget(self.icon_lbl); layout.addWidget(self.msg_lbl,1); layout.addWidget(self.close_btn); self.close_btn.mousePressEvent=lambda e:self.hide(); self.hide()
    def show_alert(self,message,severity="warning"):
        bg,border=("#4e0e0e","#ff1744") if severity=="critical" else ("#3e2c1c","#ff9800"); self.setStyleSheet(f"AlertBanner{{background:{bg};border:1px solid {border};border-radius:6px}} QLabel{{color:#ffccbc}}"); self.msg_lbl.setText(message); self.show(); QTimer.singleShot(15000,self.hide)


class DashboardWidget(QWidget):
    def __init__(self,db_manager,alert_manager,parent=None):
        super().__init__(parent); self.db=db_manager; self.alert_manager=alert_manager; self.setLayoutDirection(Qt.RightToLeft); self._setup_ui(); self._start_timers()
    def _setup_ui(self):
        main=QVBoxLayout(self); main.setContentsMargins(15,12,15,15); main.setSpacing(10); self.alert_banner=AlertBanner(); main.addWidget(self.alert_banner)
        gauges=QHBoxLayout(); gauges.setSpacing(8); self.gauge_cpu=GaugeWidget("المعالج (CPU)"); self.gauge_ram=GaugeWidget("الذاكرة (RAM)"); self.gauge_disk=GaugeWidget("التخزين (Disk)"); self.gauge_net=GaugeWidget("الشبكة (Net)")
        for g in (self.gauge_cpu,self.gauge_ram,self.gauge_disk,self.gauge_net): gauges.addWidget(g,1)
        main.addLayout(gauges)
        cards=QGridLayout(); cards.setSpacing(8); self.card_hostname=InfoCard("🖥 اسم الجهاز",accent="#4CAF50"); self.card_os=InfoCard("💾 نظام التشغيل",accent="#2196F3"); self.card_uptime=InfoCard("⏱ وقت التشغيل",accent="#FF9800"); self.card_cpu_model=InfoCard("⚡ المعالج",accent="#9C27B0"); self.card_ram_total=InfoCard("🧠 الذاكرة الكلية",accent="#00BCD4"); self.card_disk_total=InfoCard("💾 التخزين الكلي",accent="#E91E63")
        for i,card in enumerate((self.card_hostname,self.card_os,self.card_uptime,self.card_cpu_model,self.card_ram_total,self.card_disk_total)): cards.addWidget(card,i//3,i%3)
        main.addLayout(cards)
        details=QGridLayout(); details.setSpacing(8); self.card_errors=InfoCard("🔴 آخر الأخطاء","لا توجد أخطاء حديثة ✓","#f44336"); self.card_net_up=InfoCard("📤 رفع",accent="#4CAF50"); self.card_net_down=InfoCard("📥 تنزيل",accent="#2196F3"); details.addWidget(self.card_errors,0,0,2,2); details.addWidget(self.card_net_up,0,2); details.addWidget(self.card_net_down,1,2); main.addLayout(details)
        self.alerts_title=QLabel("🔔 آخر التنبيهات"); self.alerts_title.setStyleSheet("font-size:14px;font-weight:bold;color:#e0e0e0;padding-top:3px"); main.addWidget(self.alerts_title); self.alerts_list_label=QLabel("لا توجد تنبيهات ✓"); self.alerts_list_label.setWordWrap(True); self.alerts_list_label.setMinimumHeight(42); self.alerts_list_label.setStyleSheet("color:#888;padding:8px;background:#1e1e32;border:1px solid #2a2a3e;border-radius:6px"); main.addWidget(self.alerts_list_label); main.addStretch(); self.alert_manager.register_callback(self._on_alert)
    def set_language(self,language):
        for gauge in (self.gauge_cpu,self.gauge_ram,self.gauge_disk,self.gauge_net): gauge.set_language(language)
    def _start_timers(self):
        self._update_static_info(); self._update_dynamic_info(); self.timer=QTimer(self); self.timer.timeout.connect(self._update_dynamic_info); self.timer.start(2000); self.timer_slow=QTimer(self); self.timer_slow.timeout.connect(self._update_static_info); self.timer_slow.start(30000)
    def _update_static_info(self):
        try:
            overview=SystemInfo.get_system_overview(); self.card_hostname.set_value(overview.get("hostname","—")); self.card_os.set_value(overview.get("os","—")); self.card_uptime.set_value(overview.get("uptime","—")); self.card_cpu_model.set_value(overview.get("processor","—")); mem=SystemInfo.get_memory_info(); self.card_ram_total.set_value(SystemInfo.bytes_to_human(mem.get("total",0))); disks=SystemInfo.get_disk_info();
            if disks:self.card_disk_total.set_value(SystemInfo.bytes_to_human(disks[0].get("total",0)))
        except Exception: pass
    def _update_dynamic_info(self):
        try:
            cpu=SystemInfo.get_cpu_info(); mem=SystemInfo.get_memory_info(); disks=SystemInfo.get_disk_info(); net=SystemInfo.get_network_info(); cpu_pct,ram_pct=cpu.get("percent",0),mem.get("percent",0); disk_pct=disks[0].get("percent",0) if disks else 0; self.gauge_cpu.set_value(cpu_pct); self.gauge_ram.set_value(ram_pct); self.gauge_disk.set_value(disk_pct); net_speed=sum(i.get("speed",0) for i in net.get("interfaces",[])); net_pct=min(50,(net.get("bytes_recv",0)/max(1,net_speed*1_000_000))*100) if net_speed else 0; self.gauge_net.set_value(net_pct); self.card_net_up.set_value(SystemInfo.bytes_to_human(net.get("bytes_sent",0))); self.card_net_down.set_value(SystemInfo.bytes_to_human(net.get("bytes_recv",0))); errors=self.db.get_recent_errors(3); self.card_errors.set_value("\n".join(f"• [{e.get('level','')}] {e.get('source','')}: {str(e.get('message',''))[:70]}" for e in errors) if errors else "لا توجد أخطاء حديثة ✓"); self.alert_manager.check_thresholds(cpu_pct,ram_pct,disk_pct); self.db.log_performance(cpu_pct,ram_pct,mem.get("used",0),mem.get("total",0),disk_pct,disks[0].get("used",0) if disks else 0,disks[0].get("total",0) if disks else 0,net.get("bytes_sent",0),net.get("bytes_recv",0)); alerts=self.db.get_recent_alerts(5); self.alerts_list_label.setText("\n".join(f"• [{a.get('severity','')}] {a.get('message','')}" for a in alerts) if alerts else "لا توجد تنبيهات ✓"); self.alerts_list_label.setStyleSheet("color:#ff8a80;padding:8px;background:#1e1e32;border:1px solid #2a2a3e;border-radius:6px" if alerts else "color:#888;padding:8px;background:#1e1e32;border:1px solid #2a2a3e;border-radius:6px")
        except Exception: pass
    def _on_alert(self,key,severity,message): self.alert_banner.show_alert(message,severity)
    def stop(self):
        try:self.timer.stop(); self.timer_slow.stop()
        except Exception:pass
