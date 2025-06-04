@echo off
:: Скрипт установки окружения для Memory Monitor
title Установка Memory Monitor

echo Установка Python 3.10+...
winget install Python.Python.3.10 --silent --accept-package-agreements

echo Обновление pip...
python -m pip install --upgrade pip

echo Установка зависимостей...
pip install -r requirements.txt

echo Создание ярлыка в автозагрузке...
set SCRIPT_PATH=%~dp0memory_monitor.py
set SHORTCUT_PATH=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\MemoryMonitor.lnk

echo Создание ярлыка...
powershell -command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); $s.TargetPath = 'pythonw'; $s.Arguments = '%SCRIPT_PATH%'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

echo Готово! Приложение будет запускаться автоматически.
pause