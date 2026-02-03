import sys
import os
import logging
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import QUrl
from modbus_manager import ModbusManager

# Настройка логирования для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    os.environ["QT_QUICK_CONTROLS_STYLE"] = "Fusion"
    # Отключаем логирование Qt (включая qt.graphs2d.critical и qt.qpa.fonts)
    # Используем правильный формат для QT_LOGGING_RULES - отключаем все логи qt.graphs2d и qt.qpa.fonts
    # Также отключаем предупреждения о шрифтах
    os.environ["QT_LOGGING_RULES"] = "qt.graphs2d.*=false;qt.qpa.fonts.*=false;*.warning=false"
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    # Регистрируем ModbusManager для использования в QML
    qmlRegisterType(ModbusManager, "XeusGUI", 1, 0, "ModbusManager")
    
    # Создаем глобальный экземпляр ModbusManager
    modbus_manager = ModbusManager()
    engine.rootContext().setContextProperty("modbusManager", modbus_manager)
    # Гарантированно останавливаем I/O thread при выходе (даже если QML не загрузился)
    app.aboutToQuit.connect(lambda: modbus_manager._shutdownIoThread())

    # Определяем базовый путь (директория исполняемого файла)
    if getattr(sys, 'frozen', False):
        # Если приложение собрано (PyInstaller)
        base_path = os.path.dirname(sys.executable)
        # Для macOS: ресурсы в .app/Contents/Resources
        # Для Windows: ресурсы в той же папке или в _internal
        if sys.platform == 'darwin':
            resources_path = os.path.join(base_path, "../Resources")
        else:
            # Windows: проверяем _internal (onedir) или текущую папку (onefile)
            resources_path = base_path
            _internal_path = os.path.join(base_path, "_internal")
            if os.path.exists(_internal_path):
                resources_path = _internal_path
    else:
        # Режим разработки
        base_path = os.path.abspath(os.path.dirname(__file__))
        resources_path = base_path

    # Добавляем пути для поиска QML-модулей
    engine.addImportPath(resources_path)
    engine.addImportPath(base_path)

    # Путь к app.qml
    qml_file = os.path.join(resources_path, "app.qml")
    # Если app.qml не найден, пробуем в корне проекта (режим разработки)
    if not os.path.exists(qml_file):
        qml_file = os.path.join(base_path, "app.qml")

    # Загружаем app.qml
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        print(f"Не удалось загрузить QML-файл: {qml_file}")
        sys.exit(-1)
    sys.exit(app.exec())