import platform
import psutil
import socket
import locale
from datetime import datetime

class InfoGetter:
    SUPPORTED_LANGS = {'zh', 'en', 'fr', 'ru', 'es', 'ar'}

    # 多语言字段字典
    TRANSLATIONS = {
        "Operating System": {
            'zh': "操作系统", 'en': "Operating System", 'fr': "Système d’exploitation",
            'ru': "Операционная система", 'es': "Sistema operativo", 'ar': "نظام التشغيل"
        },
        "OS Version": {
            'zh': "系统版本", 'en': "OS Version", 'fr': "Version de l’OS",
            'ru': "Версия ОС", 'es': "Versión del SO", 'ar': "إصدار النظام"
        },
        "Release": {
            'zh': "发行版本", 'en': "Release", 'fr': "Édition",
            'ru': "Релиз", 'es': "Edición", 'ar': "الإصدار"
        },
        "Architecture": {
            'zh': "系统架构", 'en': "Architecture", 'fr': "Architecture",
            'ru': "Архитектура", 'es': "Arquitectura", 'ar': "البنية"
        },
        "Hostname": {
            'zh': "主机名", 'en': "Hostname", 'fr': "Nom d’hôte",
            'ru': "Имя хоста", 'es': "Nombre de host", 'ar': "اسم المضيف"
        },
        "IP Address": {
            'zh': "IP地址", 'en': "IP Address", 'fr': "Adresse IP",
            'ru': "IP-адрес", 'es': "Dirección IP", 'ar': "عنوان IP"
        },
        "Processor": {
            'zh': "处理器", 'en': "Processor", 'fr': "Processeur",
            'ru': "Процессор", 'es': "Procesador", 'ar': "المعالج"
        },
        "CPU Cores (Logical)": {
            'zh': "CPU核心数（逻辑）", 'en': "CPU Cores (Logical)", 'fr': "Cœurs CPU (logiques)",
            'ru': "Логических ядер", 'es': "Núcleos CPU (lógicos)", 'ar': "أنوية المعالج (منطقية)"
        },
        "CPU Cores (Physical)": {
            'zh': "CPU核心数（物理）", 'en': "CPU Cores (Physical)", 'fr': "Cœurs CPU (physiques)",
            'ru': "Физических ядер", 'es': "Núcleos CPU (físicos)", 'ar': "أنوية المعالج (مادية)"
        },
        "Total Memory (GB)": {
            'zh': "总内存（GB）", 'en': "Total Memory (GB)", 'fr': "Mémoire totale (Go)",
            'ru': "Всего памяти (ГБ)", 'es': "Memoria total (GB)", 'ar': "إجمالي الذاكرة (جيجابايت)"
        },
        "Available Memory (GB)": {
            'zh': "可用内存（GB）", 'en': "Available Memory (GB)", 'fr': "Mémoire disponible (Go)",
            'ru': "Доступно памяти (ГБ)", 'es': "Memoria disponible (GB)", 'ar': "الذاكرة المتاحة (جيجابايت)"
        },
        "Total Disk (GB)": {
            'zh': "总磁盘（GB）", 'en': "Total Disk (GB)", 'fr': "Disque total (Go)",
            'ru': "Всего диска (ГБ)", 'es': "Disco total (GB)", 'ar': "إجمالي القرص (جيجابايت)"
        },
        "Used Disk (GB)": {
            'zh': "已用磁盘（GB）", 'en': "Used Disk (GB)", 'fr': "Disque utilisé (Go)",
            'ru': "Использовано (ГБ)", 'es': "Disco usado (GB)", 'ar': "المستخدم من القرص (جيجابايت)"
        },
        "Free Disk (GB)": {
            'zh': "可用磁盘（GB）", 'en': "Free Disk (GB)", 'fr': "Disque libre (Go)",
            'ru': "Свободно (ГБ)", 'es': "Disco libre (GB)", 'ar': "القرص المتاح (جيجابايت)"
        },
        "Python Version": {
            'zh': "Python版本", 'en': "Python Version", 'fr': "Version de Python",
            'ru': "Версия Python", 'es': "Versión de Python", 'ar': "إصدار بايثون"
        },
        "CPU Usage (%)": {
            'zh': "CPU占用率（%）", 'en': "CPU Usage (%)", 'fr': "Utilisation CPU (%)",
            'ru': "Загрузка CPU (%)", 'es': "Uso de CPU (%)", 'ar': "استخدام المعالج (%)"
        },
        "Memory Usage (%)": {
            'zh': "内存占用率（%）", 'en': "Memory Usage (%)", 'fr': "Utilisation mémoire (%)",
            'ru': "Загрузка памяти (%)", 'es': "Uso de memoria (%)", 'ar': "استخدام الذاكرة (%)"
        },
        "Disk Usage (%)": {
            'zh': "磁盘占用率（%）", 'en': "Disk Usage (%)", 'fr': "Utilisation du disque (%)",
            'ru': "Загрузка диска (%)", 'es': "Uso del disco (%)", 'ar': "استخدام القرص (%)"
        },
        "Boot Time": {
            'zh': "开机时间", 'en': "Boot Time", 'fr': "Heure de démarrage",
            'ru': "Время загрузки", 'es': "Hora de arranque", 'ar': "وقت الإقلاع"
        },
        "System Time": {
            'zh': "当前系统时间", 'en': "System Time", 'fr': "Heure système",
            'ru': "Системное время", 'es': "Hora del sistema", 'ar': "وقت النظام"
        },
        "Uptime": {
            'zh': "系统已运行时间", 'en': "Uptime", 'fr': "Temps de fonctionnement",
            'ru': "Время работы", 'es': "Tiempo en funcionamiento", 'ar': "مدة تشغيل النظام"
        },
        "Unavailable": {
            'zh': "获取失败", 'en': "Unavailable", 'fr': "Indisponible",
            'ru': "Недоступно", 'es': "No disponible", 'ar': "غير متوفر"
        }
    }

    @staticmethod
    def _detect_lang(lang):
        if lang is None:
            system_locale = locale.getlocale()[0] or ''
            lang = system_locale.split('_')[0].lower()
        lang = lang.lower()
        return lang if lang in InfoGetter.SUPPORTED_LANGS else 'zh'

    @staticmethod
    def _tr(key, lang):
        return InfoGetter.TRANSLATIONS.get(key, {}).get(lang, key)

    @staticmethod
    def get_status_info(lang: str = ""):
        lang = InfoGetter._detect_lang(lang)
        tr = lambda key: InfoGetter._tr(key, lang)

        info = {}
        info[tr("CPU Usage (%)")] = psutil.cpu_percent(interval=0.5)
        info[tr("Memory Usage (%)")] = psutil.virtual_memory().percent
        info[tr("Disk Usage (%)")] = psutil.disk_usage('/').percent
        
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        info[tr("Boot Time")] = boot_time.strftime('%Y-%m-%d %H:%M:%S')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info[tr("System Time")] = now
        uptime = datetime.now() - boot_time
        info[tr("Uptime")] = str(uptime).split('.')[0]

        return info

    @staticmethod
    def get_system_info(lang: str = "", include_ip: bool = False):
        lang = InfoGetter._detect_lang(lang)
        tr = lambda key: InfoGetter._tr(key, lang)

        info = {}
        info[tr("Operating System")] = platform.system()
        info[tr("OS Version")] = platform.version()
        info[tr("Release")] = platform.release()
        info[tr("Architecture")] = platform.machine()
        info[tr("Hostname")] = socket.gethostname()

        if include_ip:
            try:
                info[tr("IP Address")] = socket.gethostbyname(socket.gethostname())
            except:
                info[tr("IP Address")] = tr("Unavailable")

        info[tr("Processor")] = platform.processor()
        info[tr("CPU Cores (Logical)")] = psutil.cpu_count()
        info[tr("CPU Cores (Physical)")] = psutil.cpu_count(logical=False)

        mem = psutil.virtual_memory()
        info[tr("Total Memory (GB)")] = round(mem.total / (1024 ** 3), 2)
        info[tr("Available Memory (GB)")] = round(mem.available / (1024 ** 3), 2)

        disk = psutil.disk_usage('/')
        info[tr("Total Disk (GB)")] = round(disk.total / (1024 ** 3), 2)
        info[tr("Used Disk (GB)")] = round(disk.used / (1024 ** 3), 2)
        info[tr("Free Disk (GB)")] = round(disk.free / (1024 ** 3), 2)

        info[tr("Python Version")] = platform.python_version()

        return info

if __name__ == '__main__':
    print("【Auto Language Detection】")
    info_auto = InfoGetter.get_status_info()
    for k, v in info_auto.items():
        print(f"{k}: {v}")
