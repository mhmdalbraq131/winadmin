"""Central Arabic/English localization for WinAdmin."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QAbstractButton, QLabel, QComboBox, QLineEdit, QTableWidget

LANGUAGE_AR = "ar"
LANGUAGE_EN = "en"

TRANSLATIONS = {
    "ar": {
        "لوحة التحكم": "Dashboard", "مراقبة الموارد": "Resource Monitor", "إدارة العمليات": "Process Manager",
        "إدارة التخزين": "Storage Manager", "إدارة الخدمات": "Service Manager", "الأمان والصحة": "Security & Health",
        "السجلات والتقارير": "Logs & Reports", "الأوامر": "Commands", "الإعدادات": "Settings",
        "أداة إدارة النظام": "System Administration Tool", "لوحة تحكم": "Dashboard", "المعالج": "CPU",
        "الذاكرة": "RAM", "التخزين": "Disk", "الشبكة": "Network", "اسم الجهاز": "Computer Name",
        "نظام التشغيل": "Operating System", "وقت التشغيل": "Uptime", "الذاكرة الكلية": "Total Memory",
        "التخزين الكلي": "Total Storage", "رفع": "Upload", "تنزيل": "Download", "آخر الأخطاء": "Recent Errors",
        "آخر التنبيهات": "Recent Alerts", "لا توجد تنبيهات": "No alerts", "لا توجد أخطاء حديثة ✓": "No recent errors ✓",
        "مظلم (Dark)": "Dark", "فاتح (Light)": "Light", "تطبيق المظهر": "Apply Theme",
        "فحص الجهاز والمساعد الذكي": "Hardware Scan & Smart Assistant",
        "تحليل مواصفات الجهاز وتحديد أفضل الاستخدامات والتوصيات": "Analyze hardware, best use cases and recommendations",
        "خطأ": "Error", "خطأ في فتح الصفحة": "Page Error", "تحتاج صلاحيات المدير": "Administrator Privileges Required",
        "نعم": "Yes", "لا": "No", "حفظ": "Save", "حذف": "Delete", "إغلاق": "Close", "إضافة جهاز": "Add Device",
        "حذف جهاز": "Remove Device", "اختبار": "Test", "تفعيل تنبيهات البريد": "Enable Email Alerts",
        "خادم SMTP:": "SMTP Server:", "المنفذ:": "Port:", "البريد المرسل:": "Sender Email:",
        "كلمة المرور:": "Password:", "المستلمون (مفصولين بفاصلة):": "Recipients (comma separated):",
        "📊 عتبات التنبيهات": "📊 Alert Thresholds", "📧 البريد الإلكتروني": "📧 Email",
        "🌐 الأجهزة البعيدة": "🌐 Remote Devices", "🎨 المظهر": "🎨 Appearance",
        "حفظ العتبات": "Save Thresholds", "📁 مسار حفظ السجلات:": "📁 Log Path:",
        "تطبيق اللغة": "Apply Language", "اللغة / Language": "Language / اللغة", "العربية": "Arabic", "English": "English",
        "مساعد النظام": "System Assistant", "فحص الجهاز": "Hardware Scan", "إعادة الفحص": "Rescan",
        "لا توجد بيانات": "No data", "الحالة": "Status", "الاسم": "Name", "المستخدم": "User",
    },
    "en": {
        "Dashboard": "لوحة التحكم", "Resource Monitor": "مراقبة الموارد", "Process Manager": "إدارة العمليات",
        "Storage Manager": "إدارة التخزين", "Service Manager": "إدارة الخدمات", "Security & Health": "الأمان والصحة",
        "Logs & Reports": "السجلات والتقارير", "Commands": "الأوامر", "Settings": "الإعدادات",
        "System Administration Tool": "أداة إدارة النظام", "Dashboard": "لوحة التحكم", "CPU": "المعالج",
        "RAM": "الذاكرة", "Disk": "التخزين", "Network": "الشبكة", "Computer Name": "اسم الجهاز",
        "Operating System": "نظام التشغيل", "Uptime": "وقت التشغيل", "Total Memory": "الذاكرة الكلية",
        "Total Storage": "التخزين الكلي", "Upload": "رفع", "Download": "تنزيل", "Recent Errors": "آخر الأخطاء",
        "Recent Alerts": "آخر التنبيهات", "No alerts": "لا توجد تنبيهات", "No recent errors ✓": "لا توجد أخطاء حديثة ✓",
        "Dark": "مظلم (Dark)", "Light": "فاتح (Light)", "Apply Theme": "تطبيق المظهر",
        "Hardware Scan & Smart Assistant": "فحص الجهاز والمساعد الذكي",
        "Analyze hardware, best use cases and recommendations": "تحليل مواصفات الجهاز وتحديد أفضل الاستخدامات والتوصيات",
        "Error": "خطأ", "Page Error": "خطأ في فتح الصفحة", "Administrator Privileges Required": "تحتاج صلاحيات المدير",
        "Yes": "نعم", "No": "لا", "Save": "حفظ", "Delete": "حذف", "Close": "إغلاق", "Add Device": "إضافة جهاز",
        "Remove Device": "حذف جهاز", "Test": "اختبار", "Enable Email Alerts": "تفعيل تنبيهات البريد",
        "SMTP Server:": "خادم SMTP:", "Port:": "المنفذ:", "Sender Email:": "البريد المرسل:",
        "Password:": "كلمة المرور:", "Recipients (comma separated):": "المستلمون (مفصولين بفاصلة):",
        "📊 Alert Thresholds": "📊 عتبات التنبيهات", "📧 Email": "📧 البريد الإلكتروني",
        "🌐 Remote Devices": "🌐 الأجهزة البعيدة", "🎨 Appearance": "🎨 المظهر",
        "Save Thresholds": "حفظ العتبات", "📁 Log Path:": "📁 مسار حفظ السجلات:",
        "Apply Language": "تطبيق اللغة", "Language / اللغة": "اللغة / Language", "Arabic": "العربية", "English": "English",
        "System Assistant": "مساعد النظام", "Hardware Scan": "فحص الجهاز", "Rescan": "إعادة الفحص",
        "No data": "لا توجد بيانات", "Status": "الحالة", "Name": "الاسم", "User": "المستخدم",
    }
}


def normalize_language(value):
    return LANGUAGE_EN if str(value).lower().startswith("en") else LANGUAGE_AR


def tr(text, language="ar"):
    language = normalize_language(language)
    return TRANSLATIONS.get(language, {}).get(str(text), str(text))


def remember_and_translate(widget, language):
    """Translate known UI strings while preserving the original key."""
    if not isinstance(widget, (QAbstractButton, QLabel, QComboBox, QLineEdit)):
        return
    if isinstance(widget, QComboBox):
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
    root.setLayoutDirection(Qt.RightToLeft if language == LANGUAGE_AR else Qt.LeftToRight)
    for widget in root.findChildren(QWidget):
        remember_and_translate(widget, language)
        if isinstance(widget, QTableWidget):
            header = widget.horizontalHeader()
            if header:
                header.setLayoutDirection(Qt.RightToLeft if language == LANGUAGE_AR else Qt.LeftToRight)


def language_name(language):
    return "العربية" if normalize_language(language) == LANGUAGE_AR else "English"
