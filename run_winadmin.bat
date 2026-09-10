@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "REQ_FILE=%~dp0winadmin\requirements.txt"
set "APP_FILE=%~dp0winadmin\main.py"

whoami /groups | findstr /b /c:"Mandatory Label\: High Mandatory Level" >nul 2>&1
if errorlevel 1 (
    echo [WinAdmin] التطبيق يحتاج صلاحيات المدير (Run as Administrator).
    echo [WinAdmin] جارٍ فتح التطبيق بصلاحيات الإدارة...
    powershell -NoProfile -Command "Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '""%APP_FILE%""' -Verb RunAs"
    exit /b 0
)

if not exist "%PYTHON_EXE%" (
    echo [WinAdmin] ما لقينا البيئة الافتراضية (.venv).
    echo [WinAdmin] تأكد إن المشروع موجود في نفس المجلد.
    pause
    exit /b 1
)

echo [WinAdmin] فحص المكتبات المطلوبة...
"%PYTHON_EXE%" -c "import PyQt5, psutil, requests, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [WinAdmin] جاري تثبيت المكتبات...
    "%PYTHON_EXE%" -m pip install --disable-pip-version-check -r "%REQ_FILE%"
    if errorlevel 1 (
        echo [WinAdmin] فشل تثبيت المكتبات.
        pause
        exit /b 1
    )
)

echo [WinAdmin] جاري تشغيل التطبيق...
echo [WinAdmin] هذا الملف سيبقى مفتوحاً ليرى الخطأ إن وجد.
"%PYTHON_EXE%" "%APP_FILE%"

echo.
echo [WinAdmin] تم إنهاء التطبيق برمز الخروج: %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%
