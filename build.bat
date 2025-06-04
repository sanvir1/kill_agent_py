@echo off
:: Скрипт сборки Memory Monitor
title Сборка Memory Monitor

echo Очистка предыдущих сборок...
rd /s /q build 2>nul
rd /s /q dist 2>nul
del memory_monitor.spec 2>nul

echo Создание иконки (если отсутствует)...
if not exist icon.ico (
  echo Создание временной иконки...
  python -c "from PIL import Image; Image.new('RGB', (64, 64), (70, 70, 70)).save('icon.ico')"
)

echo Сборка EXE...
pyinstaller --onefile --windowed --icon=icon.ico --name MemoryMonitor --clean --noconfirm memory_monitor.py

echo Копирование в папку dist...
xcopy /Y /E "dist\*" ".\" 2>nul

echo Создание portable-версии...
mkdir Portable 2>nul
copy MemoryMonitor.exe Portable\MemoryMonitor.exe 2>nul
copy config.ini Portable\config.ini 2>nul

echo Готово! EXE-файлы созданы:
echo - Основной: MemoryMonitor.exe
echo - Portable: Portable\MemoryMonitor.exe
pause