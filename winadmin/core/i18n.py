"""Central Arabic/English localization for WinAdmin."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QAbstractButton, QLabel, QComboBox, QLineEdit, QTableWidget

LANGUAGE_AR = "ar"
LANGUAGE_EN = "en"

AR_TO_EN = {
    "لوحة التحكم": "Dashboard", "مراقبة الموارد": "Resource Monitor", "إدارة العمليات": "Process Manager",
    "إدارة التخزين": "Storage Manager", "إدارة الخدمات": "Service Manager", "الأمان والصحة": "Security & Health",
    "السجلات والتقارير": "Logs & Reports", "الأوامر": "Commands", "الإعدادات": "Settings",
    "أداة إدارة النظام": "System Administration Tool", "المعالج": "CPU", "الذاكرة": "RAM", "التخزين": "Disk",
    "الشبكة": "Network", "اسم الجهاز": "Computer Name", "نظام التشغيل": "Operating System", "وقت التشغيل": "Uptime",
    "الذاكرة الكلية": "Total Memory", "التخزين الكلي": "Total Storage", "رفع": "Upload", "تنزيل": "Download",
    "آخر الأخطاء": "Recent Errors", "آخر التنبيهات": "Recent Alerts", "لا توجد تنبيهات": "No alerts",
    "لا توجد أخطاء حديثة ✓": "No recent errors ✓", "مظلم (Dark)": "Dark", "فاتح (Light)": "Light",
    "تطبيق المظهر": "Apply Theme", "فحص الجهاز والمساعد الذكي": "Hardware Scan & Smart Assistant",
    "تحليل مواصفات الجهاز وتحديد أفضل الاستخدامات والتوصيات": "Analyze hardware, best use cases and recommendations",
    "خطأ": "Error", "خطأ في فتح الصفحة": "Page Error", "تحتاج صلاحيات المدير": "Administrator Privileges Required",
    "نعم": "Yes", "لا": "No", "حفظ": "Save", "حذف": "Delete", "إغلاق": "Close", "إضافة جهاز": "Add Device",
    "حذف جهاز": "Remove Device", "اختبار": "Test", "تفعيل تنبيهات البريد": "Enable Email Alerts",
    "خادم SMTP:": "SMTP Server:", "المنفذ:": "Port:", "البريد المرسل:": "Sender Email:", "كلمة المرور:": "Password:",
    "المستلمون (مفصولين بفاصلة):": "Recipients (comma separated):", "حفظ العتبات": "Save Thresholds",
    "📊 عتبات التنبيهات": "📊 Alert Thresholds", "📧 البريد الإلكتروني": "📧 Email",
    "🌐 الأجهزة البعيدة": "🌐 Remote Devices", "🎨 المظهر": "🎨 Appearance", "📁 مسار حفظ السجلات:": "📁 Log Path:",
    "تطبيق اللغة": "Apply Language", "اللغة / Language": "Language / اللغة", "العربية": "Arabic",
    "مساعد النظام": "System Assistant", "فحص الجهاز": "Hardware Scan", "إعادة الفحص": "Rescan",
    "لا توجد بيانات": "No data", "الحالة": "Status", "الاسم": "Name", "المستخدم": "User",
    "إصدار التطبيق": "Application Version", "الثيم": "Theme", "المظهر": "Appearance",
}
EN_TO_AR = {v: k for k, v in AR_TO_EN.items()}


def normalize_language(value):
    return LANGUAGE_EN if str(value).lower().startswith("en") else LANGUAGE_AR


def tr(text, language="ar"):
    text = str(text)
    language = normalize_language(language)
    if language == LANGUAGE_EN:
        return AR_TO_EN.get(text, text)
    return EN_TO_AR.get(text, text)


def remember_and_translate(widget, language):
    if isinstance(widget, QComboBox):
        return
    if not isinstance(widget, (QAbstractButton, QLabel, QLineEdit)):
        return
    try:
        if widget.property("i18n_source") is None:
            widget.setProperty("i18n_source", widget.text())
        source = widget.property("i18n_source")
        if source:
            widget.setText(tr(source, language))
    except (RuntimeError, AttributeError):
        pass


def apply_language(root: QWidget, language: str):
    language = normalize_language(language)
    direction = Qt.RightToLeft if language == LANGUAGE_AR else Qt.LeftToRight
    root.setLayoutDirection(direction)
    remember_and_translate(root, language)
    for widget in root.findChildren(QWidget):
        remember_and_translate(widget, language)
        if isinstance(widget, QTableWidget):
            widget.horizontalHeader().setLayoutDirection(direction)


def language_name(language):
    return "العربية" if normalize_language(language) == LANGUAGE_AR else "English"
