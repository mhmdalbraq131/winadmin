"""
ui/monitors.py — شاشة مراقبة الموارد
عرض تفصيلي لاستهلاك CPU, RAM, Disk, Network مع رسوم بيانية مباشرة.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QTabWidget, QGroupBox, QGridLayout,
                              QProgressBar, QTableWidget, QTableWidgetItem,
                              QHeaderView)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor
from core.system_info import SystemInfo
from collections import deque


class MiniChart(QWidget):
    """رسم بياني خطي مبسط يُحدّث مباشرة."""

    def __init__(self, title: str, color: str = "#4CAF50", max_points: int = 60, parent=None):
        super().__init__(parent)
        self.title = title
        self.color = color
        self.max_points = max_points
        self.data = deque(maxlen=max_points)
        self.setMinimumHeight(120)
        self.setMinimumWidth(250)

    def add_point(self, value: float):
        self.data.append(value)
        self.update()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPen, QLinearGradient, QBrush, QPainterPath

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 5
        chart_h = h - 30
        chart_w = w - 2 * margin

        # خلفية
        painter.fillRect(self.rect(), QColor("#1e1e32"))

        # العنوان
        painter.setPen(QColor("#aaaaaa"))
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(margin, 15, self.title)

        # خطوط أفقية
        pen_grid = QPen(QColor("#2a2a4a"), 1, Qt.DotLine)
        painter.setPen(pen_grid)
        for i in range(0, 101, 25):
            y = margin + chart_h - int(chart_h * i / 100)
            painter.drawLine(margin, y, margin + chart_w, y)
            painter.setPen(QColor("#555"))
            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(0, y + 4, f"{i}")
            painter.setPen(pen_grid)

        if len(self.data) < 2:
            painter.end()
            return

        # الرسم البياني
        path = QPainterPath()
        step = chart_w / max(1, (self.max_points - 1))

        points = list(self.data)
        first_x = margin + (self.max_points - len(points)) * step
        first_y = margin + chart_h - int(chart_h * points[0] / 100)
        path.moveTo(first_x, first_y)

        for i, val in enumerate(points[1:], 1):
            x = first_x + i * step
            y = margin + chart_h - int(chart_h * val / 100)
            path.lineTo(x, y)

        # تعبئة التدرج
        fill_path = QPainterPath(path)
        fill_path.lineTo(margin + chart_w, margin + chart_h)
        fill_path.lineTo(first_x, margin + chart_h)
        fill_path.closeSubpath()

        gradient = QLinearGradient(0, margin, 0, margin + chart_h)
        color = QColor(self.color)
        gradient.setColorAt(0, color.lighter(150))
        gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 30))
        painter.fillPath(fill_path, QBrush(gradient))

        # الخط
        pen_line = QPen(color, 2)
        painter.setPen(pen_line)
        painter.drawPath(path)

        # القيمة الحالية
        if points:
            painter.setPen(QColor("#ffffff"))
            painter.setFont(QFont("Segoe UI", 12, QFont.Bold))
            painter.drawText(margin + chart_w - 80, 15, f"{points[-1]:.1f}%")

        painter.end()


class ResourceMonitorWidget(QWidget):
    """شاشة مراقبة الموارد مع تبويبات تفصيلية."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._prev_net = {"sent": 0, "recv": 0}
        self._setup_ui()
        self._start_timers()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # ─ عنوان ─
        title = QLabel("📊 مراقبة الموارد")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e0e0e0;")
        layout.addWidget(title)

        # ─ تبويبات ─
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #2a2a3e; background: #1a1a2e; }
            QTabBar::tab { background: #1e1e32; color: #aaa; padding: 8px 20px; border: 1px solid #2a2a3e; }
            QTabBar::tab:selected { background: #2a2a4a; color: #fff; }
        """)

        # تبويب CPU
        cpu_tab = QWidget()
        cpu_layout = QVBoxLayout(cpu_tab)
        self.chart_cpu = MiniChart("استهلاك المعالج (CPU)", "#4CAF50")
        cpu_layout.addWidget(self.chart_cpu)

        self.cpu_detail_layout = QGridLayout()
        self.lbl_cpu_freq = QLabel("التردد: —")
        self.lbl_cpu_cores = QLabel("الأنوية: —")
        self.lbl_cpu_temp = QLabel("الحرارة: —")
        for lbl in [self.lbl_cpu_freq, self.lbl_cpu_cores, self.lbl_cpu_temp]:
            lbl.setStyleSheet("color: #ccc; font-size: 13px; padding: 5px;")
        self.cpu_detail_layout.addWidget(self.lbl_cpu_freq, 0, 0)
        self.cpu_detail_layout.addWidget(self.lbl_cpu_cores, 0, 1)
        self.cpu_detail_layout.addWidget(self.lbl_cpu_temp, 0, 2)
        cpu_layout.addLayout(self.cpu_detail_layout)

        # أشرطة تقدم لكل نواة
        self.cpu_per_core_layout = QVBoxLayout()
        cpu_layout.addLayout(self.cpu_per_core_layout)
        cpu_layout.addStretch()
        self.tabs.addTab(cpu_tab, "⚡ المعالج")

        # تبويب RAM
        ram_tab = QWidget()
        ram_layout = QVBoxLayout(ram_tab)
        self.chart_ram = MiniChart("استهلاك الذاكرة (RAM)", "#2196F3")
        ram_layout.addWidget(self.chart_ram)

        ram_info = QGridLayout()
        self.lbl_ram_used = QLabel("المستخدم: —")
        self.lbl_ram_total = QLabel("الكلي: —")
        self.lbl_ram_avail = QLabel("المتاح: —")
        self.lbl_ram_swap = QLabel("Swap: —")
        for lbl in [self.lbl_ram_used, self.lbl_ram_total, self.lbl_ram_avail, self.lbl_ram_swap]:
            lbl.setStyleSheet("color: #ccc; font-size: 13px; padding: 5px;")
        ram_info.addWidget(self.lbl_ram_used, 0, 0)
        ram_info.addWidget(self.lbl_ram_total, 0, 1)
        ram_info.addWidget(self.lbl_ram_avail, 0, 2)
        ram_info.addWidget(self.lbl_ram_swap, 1, 0)
        ram_layout.addLayout(ram_info)

        self.ram_bar = QProgressBar()
        self.ram_bar.setStyleSheet("""
            QProgressBar { background: #1e1e32; border: 1px solid #2a2a3e; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background: #2196F3; border-radius: 3px; }
        """)
        ram_layout.addWidget(self.ram_bar)
        ram_layout.addStretch()
        self.tabs.addTab(ram_tab, "🧠 الذاكرة")

        # تبويب Disk
        disk_tab = QWidget()
        disk_layout = QVBoxLayout(disk_tab)
        self.chart_disk = MiniChart("استهلاك التخزين", "#FF9800")
        disk_layout.addWidget(self.chart_disk)

        self.disk_table = QTableWidget()
        self.disk_table.setStyleSheet("""
            QTableWidget { background: #1e1e32; color: #ccc; gridline-color: #2a2a3e; border: none; }
            QHeaderView::section { background: #2a2a4a; color: #eee; padding: 5px; border: 1px solid #2a2a3e; }
        """)
        self.disk_table.setColumnCount(5)
        self.disk_table.setHorizontalHeaderLabels(["القرص", "الإجمالي", "المستخدم", "المتاح", "النسبة"])
        self.disk_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.disk_table.setEditTriggers(QTableWidget.NoEditTriggers)
        disk_layout.addWidget(self.disk_table)
        self.tabs.addTab(disk_tab, "💾 التخزين")

        # تبويب Network
        net_tab = QWidget()
        net_layout = QVBoxLayout(net_tab)

        net_charts = QHBoxLayout()
        self.chart_net_send = MiniChart("رفع (Upload)", "#4CAF50")
        self.chart_net_recv = MiniChart("تنزيل (Download)", "#9C27B0")
        net_charts.addWidget(self.chart_net_send)
        net_charts.addWidget(self.chart_net_recv)
        net_layout.addLayout(net_charts)

        net_info = QHBoxLayout()
        self.lbl_net_send = QLabel("📤 رفع: —")
        self.lbl_net_recv = QLabel("📥 تنزيل: —")
        self.lbl_net_send_rate = QLabel("↑ — /s")
        self.lbl_net_recv_rate = QLabel("↓ — /s")
        for lbl in [self.lbl_net_send, self.lbl_net_recv, self.lbl_net_send_rate, self.lbl_net_recv_rate]:
            lbl.setStyleSheet("color: #ccc; font-size: 13px; padding: 5px;")
        net_info.addWidget(self.lbl_net_send)
        net_info.addWidget(self.lbl_net_recv)
        net_info.addWidget(self.lbl_net_send_rate)
        net_info.addWidget(self.lbl_net_recv_rate)
        net_layout.addLayout(net_info)

        # جدول واجهات الشبكة
        self.iface_table = QTableWidget()
        self.iface_table.setStyleSheet(self.disk_table.styleSheet())
        self.iface_table.setColumnCount(3)
        self.iface_table.setHorizontalHeaderLabels(["الواجهة", "العنوان", "السرعة"])
        self.iface_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.iface_table.setEditTriggers(QTableWidget.NoEditTriggers)
        net_layout.addWidget(self.iface_table)

        net_layout.addStretch()
        self.tabs.addTab(net_tab, "🌐 الشبكة")

        layout.addWidget(self.tabs)

    def _start_timers(self):
        self._update_data()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_data)
        self.timer.start(1500)

    def _update_data(self):
        """تحديث جميع بيانات المراقبة."""
        try:
            # CPU
            cpu = SystemInfo.get_cpu_info()
            self.chart_cpu.add_point(cpu.get("percent", 0))
            freq = cpu.get("freq_current", 0)
            self.lbl_cpu_freq.setText(f"التردد: {freq:.0f} MHz")
            self.lbl_cpu_cores.setText(f"الأنوية: {cpu.get('count_physical', '?')}F / {cpu.get('count_logical', '?')}L")
            self.lbl_cpu_temp.setText("الحرارة: —")

            # أنوية فردية — أشرطة تقدم
            per_cpu = cpu.get("per_cpu", [])
            # نحدث الأشرطة فقط إذا تغير عددها
            while self.cpu_per_core_layout.count():
                item = self.cpu_per_core_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for i, pct in enumerate(per_cpu):
                bar = QProgressBar()
                bar.setMaximum(100)
                bar.setValue(int(pct))
                bar.setFormat(f"Core {i}: {pct:.0f}%")
                bar.setStyleSheet("""
                    QProgressBar { background: #1e1e32; border: none; border-radius: 3px; text-align: center; color: white; max-height: 16px; }
                    QProgressBar::chunk { background: #4CAF50; border-radius: 3px; }
                """)
                self.cpu_per_core_layout.addWidget(bar)

            # RAM
            mem = SystemInfo.get_memory_info()
            self.chart_ram.add_point(mem.get("percent", 0))
            self.lbl_ram_used.setText(f"المستخدم: {SystemInfo.bytes_to_human(mem.get('used', 0))}")
            self.lbl_ram_total.setText(f"الكلي: {SystemInfo.bytes_to_human(mem.get('total', 0))}")
            self.lbl_ram_avail.setText(f"المتاح: {SystemInfo.bytes_to_human(mem.get('available', 0))}")
            self.lbl_ram_swap.setText(f"Swap: {SystemInfo.bytes_to_human(mem.get('swap_used', 0))} / {SystemInfo.bytes_to_human(mem.get('swap_total', 0))}")
            self.ram_bar.setValue(int(mem.get("percent", 0)))

            # Disk
            disks = SystemInfo.get_disk_info()
            if disks:
                self.chart_disk.add_point(disks[0].get("percent", 0))
            self.disk_table.setRowCount(len(disks))
            for i, d in enumerate(disks):
                self.disk_table.setItem(i, 0, QTableWidgetItem(d.get("device", "")))
                self.disk_table.setItem(i, 1, QTableWidgetItem(SystemInfo.bytes_to_human(d.get("total", 0))))
                self.disk_table.setItem(i, 2, QTableWidgetItem(SystemInfo.bytes_to_human(d.get("used", 0))))
                self.disk_table.setItem(i, 3, QTableWidgetItem(SystemInfo.bytes_to_human(d.get("free", 0))))
                self.disk_table.setItem(i, 4, QTableWidgetItem(f"{d.get('percent', 0):.1f}%"))

            # Network
            net = SystemInfo.get_network_info()
            cur_sent = net.get("bytes_sent", 0)
            cur_recv = net.get("bytes_recv", 0)
            send_rate = (cur_sent - self._prev_net["sent"]) / 1.5 if self._prev_net["sent"] > 0 else 0
            recv_rate = (cur_recv - self._prev_net["recv"]) / 1.5 if self._prev_net["recv"] > 0 else 0
            self._prev_net = {"sent": cur_sent, "recv": cur_recv}

            # نسب رمزية للرسم البياني
            self.chart_net_send.add_point(min(100, max(0, (send_rate / 1_000_000) * 5)))
            self.chart_net_recv.add_point(min(100, max(0, (recv_rate / 1_000_000) * 5)))

            self.lbl_net_send.setText(f"📤 رفع: {SystemInfo.bytes_to_human(cur_sent)}")
            self.lbl_net_recv.setText(f"📥 تنزيل: {SystemInfo.bytes_to_human(cur_recv)}")
            self.lbl_net_send_rate.setText(f"↑ {SystemInfo.bytes_to_human(max(0, send_rate))}/s")
            self.lbl_net_recv_rate.setText(f"↓ {SystemInfo.bytes_to_human(max(0, recv_rate))}/s")

            # واجهات الشبكة
            ifaces = net.get("interfaces", [])
            self.iface_table.setRowCount(len(ifaces))
            for i, iface in enumerate(ifaces):
                self.iface_table.setItem(i, 0, QTableWidgetItem(iface.get("name", "")))
                addr = iface.get("addresses", [])
                addr_str = ", ".join(a.get("address", "") for a in addr[:2])
                self.iface_table.setItem(i, 1, QTableWidgetItem(addr_str))
                self.iface_table.setItem(i, 2, QTableWidgetItem(f"{iface.get('speed', 0)} Mbps"))

        except Exception:
            pass

    def stop(self):
        self.timer.stop()
