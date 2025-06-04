import os
import sys
import psutil
import time
import configparser
import threading
from tkinter import Tk, ttk, Checkbutton, IntVar, StringVar, messagebox
from PIL import Image, ImageDraw, ImageTk
import pystray
import winreg

# Константы
CONFIG_FILE = "config.ini"
DEFAULT_CONFIG = {
    'settings': {
        'check_interval': '3',
        'memory_threshold': '95',
        'autostart': '0',
        'processes_to_kill': 'chrome.exe,msedge.exe,firefox.exe'
    }
}

class MemoryMonitorApp:
    def __init__(self):
        self.running = False
        self.config = configparser.ConfigParser()
        self.load_config()
        self.setup_autostart()
        self.create_tray_icon()
        self.settings_window = None

    def load_config(self):
        """Загрузка конфигурации из файла"""
        self.config.read_dict(DEFAULT_CONFIG)
        if os.path.exists(CONFIG_FILE):
            self.config.read(CONFIG_FILE)
        
        # Преобразование значений
        self.check_interval = int(self.config['settings']['check_interval'])
        self.memory_threshold = int(self.config['settings']['memory_threshold'])
        self.autostart = self.config['settings'].getboolean('autostart')
        self.processes_to_kill = [
            p.strip() for p in self.config['settings']['processes_to_kill'].split(',') 
            if p.strip()
        ]

    def save_config(self):
        """Сохранение конфигурации в файл"""
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def setup_autostart(self):
        """Настройка автозапуска через реестр"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "MemoryMonitor"
        app_path = f'"{sys.executable}" "{os.path.abspath(__file__)}"'
        
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                if self.autostart:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except WindowsError:
                        pass
        except Exception as e:
            print(f"Ошибка настройки автозапуска: {e}")

    def create_tray_icon(self):
        """Создание иконки в трее с меню"""
        # Генерация иконки
        image = Image.new('RGB', (64, 64), (70, 70, 70))
        dc = ImageDraw.Draw(image)
        dc.text((10, 10), "RAM", fill="white")
        
        # Меню
        menu_items = [
            pystray.MenuItem(
                "Настройки",
                self.show_settings
            ),
            pystray.MenuItem(
                "Освободить память сейчас",
                self.force_free_memory
            ),
            pystray.MenuItem(
                "Выход",
                self.exit_app
            )
        ]
        
        self.icon = pystray.Icon(
            "memory_monitor", 
            image, 
            "Монитор памяти", 
            pystray.Menu(*menu_items)
        )

    def update_memory_info(self):
        """Основной цикл мониторинга памяти"""
        while self.running:
            mem = psutil.virtual_memory()
            used_percent = mem.percent
            free_gb = mem.available / (1024**3)
            total_gb = mem.total / (1024**3)
            
            # Обновляем подсказку
            tooltip = (
                f"Использовано RAM: {used_percent:.1f}%\n"
                f"Свободно: {free_gb:.1f} ГБ из {total_gb:.1f} ГБ\n"
                f"Порог: {self.memory_threshold}%\n"
                f"Проверка каждые {self.check_interval} сек"
            )
            self.icon.title = tooltip
            
            # Меняем цвет иконки при превышении порога
            if used_percent > self.memory_threshold:
                self.set_icon_color("red")
                self.kill_processes()
            else:
                self.set_icon_color("green")
            
            time.sleep(self.check_interval)

    def set_icon_color(self, color):
        """Изменение цвета иконки"""
        colors = {
            "green": (50, 200, 50),
            "red": (200, 50, 50),
            "blue": (50, 50, 200)
        }
        image = Image.new('RGB', (64, 64), colors.get(color, (70, 70, 70)))
        dc = ImageDraw.Draw(image)
        dc.text((10, 10), "RAM", fill="white")
        self.icon.icon = image

    def kill_processes(self):
        """Закрытие указанных процессов"""
        killed = []
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() in [p.lower() for p in self.processes_to_kill]:
                try:
                    psutil.Process(proc.info['pid']).terminate()
                    killed.append(proc.info['name'])
                except:
                    continue
        
        if killed:
            self.icon.notify(
                f"Закрыто процессов: {len(killed)}\n"
                f"({', '.join(set(killed))})",
                "Автоочистка памяти"
            )

    def force_free_memory(self):
        """Принудительное освобождение памяти"""
        self.kill_processes()
        self.icon.notify("Память успешно освобождена", "Ручная очистка")

    def show_settings(self):
        """Отображение окна настроек"""
        # Если окно уже существует - поднимаем его
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.deiconify()
            self.settings_window.lift()
            return
        
        # Создаем новое окно
        self.settings_window = Tk()
        self.settings_window.title("Настройки Memory Monitor")
        self.settings_window.resizable(False, False)
        
        # Обработка закрытия окна
        self.settings_window.protocol("WM_DELETE_WINDOW", self.on_settings_close)
        
        # Иконка окна
        try:
            img = Image.new('RGB', (32, 32), (70, 70, 70))
            dc = ImageDraw.Draw(img)
            dc.text((5, 5), "RAM", fill="white")
            self.settings_window.iconphoto(False, ImageTk.PhotoImage(img))
        except:
            pass

        # Переменные для виджетов
        check_interval_var = StringVar(value=str(self.check_interval))
        threshold_var = StringVar(value=str(self.memory_threshold))
        autostart_var = IntVar(value=int(self.autostart))
        processes_var = StringVar(value=", ".join(self.processes_to_kill))

        # Фрейм настроек
        frame = ttk.Frame(self.settings_window, padding="10")
        frame.grid(row=0, column=0, sticky="nsew")

        # Виджеты
        ttk.Label(frame, text="Интервал проверки (сек):").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=check_interval_var, width=5).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Label(frame, text="Порог памяти (%):").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=threshold_var, width=5).grid(row=1, column=1, sticky="w", padx=5)

        Checkbutton(
            frame, 
            text="Запускать при старте системы",
            variable=autostart_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(frame, text="Процессы для закрытия (через запятую):").grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Entry(frame, textvariable=processes_var, width=40).grid(row=4, column=0, columnspan=2, sticky="we")

        # Кнопки
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(
            btn_frame, 
            text="Сохранить", 
            command=lambda: self.save_settings(
                check_interval_var.get(),
                threshold_var.get(),
                autostart_var.get(),
                processes_var.get()
            )
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame, 
            text="Отмена", 
            command=self.on_settings_close
        ).pack(side="left", padx=5)

        # Центрирование окна
        self.settings_window.eval('tk::PlaceWindow . center')
        self.settings_window.mainloop()

    def on_settings_close(self):
        """Обработчик закрытия окна настроек"""
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.destroy()
        self.settings_window = None

    def save_settings(self, interval, threshold, autostart, processes):
        """Сохранение новых настроек"""
        try:
            # Валидация
            interval = max(1, min(60, int(interval)))
            threshold = max(50, min(100, int(threshold)))
            processes = [p.strip() for p in processes.split(',') if p.strip()]
            
            # Обновление конфига
            self.config['settings']['check_interval'] = str(interval)
            self.config['settings']['memory_threshold'] = str(threshold)
            self.config['settings']['autostart'] = str(autostart)
            self.config['settings']['processes_to_kill'] = ",".join(processes)
            
            self.save_config()
            self.load_config()  # Перезагружаем настройки
            self.setup_autostart()
            
            self.on_settings_close()
            self.icon.notify("Настройки успешно сохранены", "Memory Monitor")
            
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректные значения параметров")

    def exit_app(self):
        """Корректное завершение работы"""
        self.running = False
        if hasattr(self, 'icon'):
            self.icon.stop()
        self.on_settings_close()
        sys.exit(0)

    def run(self):
        """Запуск приложения"""
        self.running = True
        threading.Thread(target=self.update_memory_info, daemon=True).start()
        self.icon.run()

if __name__ == "__main__":
    # Скрываем консоль при запуске
    if sys.platform == "win32" and not sys.argv[0].endswith(".py"):
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    app = MemoryMonitorApp()
    app.run()