"""Главное окно приложения «Код Мастер»."""

import sys
import traceback
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QWidget,
)

from core.bootloader import Bootloader, BootloaderError
from core.serial_manager import SerialManager
from core.update_checker import check_for_updates
from models.config import Config
from models.logger import get_logger, open_log_folder
from models.translations import _ as tr, set_language
from ui.com_settings_dialog import ComSettingsDialog
from ui.dark_theme import apply_dark_theme, apply_light_theme
from ui.settings_window import SettingsWindow

logger = get_logger(__name__)


class FirmwareWorker(QThread):
    """Фоновый поток для прошивки STM32 через bootloader."""

    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, serial_manager: SerialManager, file_path: str, parent: Optional[QWidget] = None) -> None:
        """Создаёт рабочий поток прошивки.

        Args:
            serial_manager: Менеджер COM-порта с открытым портом.
            file_path: Путь к файлу .bin прошивки.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._file_path = file_path

    def run(self) -> None:
        """Выполняет прошивку STM32 в фоне."""
        try:
            port = self._serial_manager._port
            if port is None:
                raise BootloaderError("COM-порт не открыт")
            import serial
            if not isinstance(port, serial.Serial):
                raise BootloaderError("Прошивка требует реальный COM-порт")
            bootloader = Bootloader(port, progress_callback=self.progress.emit)
            bootloader.flash_firmware(self._file_path)
            self.finished.emit(True, "Прошивка завершена успешно")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка прошивки")
            self.finished.emit(False, f"Ошибка прошивки: {exc}")


class DiagnosticsWorker(QThread):
    """Фоновый поток для диагностики bootloader STM32."""

    finished = Signal(bool, str)

    def __init__(self, serial_manager: SerialManager, parent: Optional[QWidget] = None) -> None:
        """Создаёт рабочий поток диагностики.

        Args:
            serial_manager: Менеджер COM-порта с открытым портом.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager

    def run(self) -> None:
        """Выполняет диагностику bootloader в фоне."""
        try:
            port = self._serial_manager._port
            if port is None:
                raise BootloaderError("COM-порт не открыт")
            import serial
            if not isinstance(port, serial.Serial):
                raise BootloaderError("Диагностика требует реальный COM-порт")
            bootloader = Bootloader(port)
            info = bootloader.diagnostics()
            message = (
                f"{tr('Версия бутлоадера')}: 0x{info['version']:02X}\n"
                f"{tr('ID устройства')}: 0x{info['device_id']:03X}"
            )
            self.finished.emit(True, message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Ошибка диагностики bootloader")
            self.finished.emit(False, f"{tr('Ошибка диагностики')}: {exc}")


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self, serial_manager: SerialManager, parent: Optional[QWidget] = None) -> None:
        """Создаёт главное окно.

        Args:
            serial_manager: Общий менеджер COM-порта.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._config = Config()
        set_language(self._config.get("language", "ru"))
        self._settings_window: Optional[SettingsWindow] = None
        self._firmware_worker: Optional[FirmwareWorker] = None
        self._diagnostics_worker: Optional[DiagnosticsWorker] = None

        self.setWindowTitle(tr("Код Мастер"))
        self.setFixedSize(480, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        central = QWidget(self)
        self.setCentralWidget(central)

        self._create_widgets()
        self._layout_widgets()
        self._connect_signals()
        self._setup_shortcuts()
        self._update_port_indicator()
        self._theme_button.setText("☾" if self._config.get("light_theme", False) else "☀")
        self._lang_button.setText("RU" if self._config.get("language", "ru") == "en" else "EN")

        # Восстанавливаем подключение, если порт сохранён
        saved_port = self._config.get("port", "")
        if saved_port:
            self._serial_manager.open_port(
                saved_port,
                self._config.get("baudrate", 115200),
                self._config.get("emulation", False),
                self._config.get("auto_reconnect", False),
                self._config.get("error_probability", 0),
            )

    def _create_widgets(self) -> None:
        """Создаёт все виджеты главного окна."""
        self._update_button = QPushButton(tr("Обновить"), self)
        self._settings_button = QPushButton(tr("Настроить"), self)
        for button in (self._update_button, self._settings_button):
            button.setFixedSize(130, 34)
            button.setFont(QFont("Segoe UI", 10))
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._logs_button = QPushButton("📄 Логи", self)
        self._logs_button.setFixedSize(80, 24)
        self._logs_button.setFont(QFont("Segoe UI", 9))

        self._diagnostics_button = QPushButton(tr("Диагностика"), self)
        self._diagnostics_button.setFixedSize(100, 24)
        self._diagnostics_button.setFont(QFont("Segoe UI", 9))
        self._diagnostics_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._diagnostics_button.clicked.connect(self._on_diagnostics_clicked)

        self._theme_button = QPushButton("☀", self)
        self._theme_button.setFixedSize(30, 24)
        self._theme_button.setFont(QFont("Segoe UI", 9))
        self._theme_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_button.setToolTip(tr("Переключить светлую/тёмную тему"))
        self._theme_button.clicked.connect(self._on_theme_clicked)

        self._lang_button = QPushButton("EN", self)
        self._lang_button.setFixedSize(40, 24)
        self._lang_button.setFont(QFont("Segoe UI", 9))
        self._lang_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._lang_button.setToolTip(tr("Переключить язык"))
        self._lang_button.clicked.connect(self._on_language_clicked)

        self._update_check_button = QPushButton("🔄", self)
        self._update_check_button.setFixedSize(30, 24)
        self._update_check_button.setFont(QFont("Segoe UI", 9))
        self._update_check_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_check_button.setToolTip(tr("Проверка обновлений"))
        self._update_check_button.clicked.connect(self._on_check_updates_clicked)

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedHeight(20)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)

        self._status_label = QLabel(tr("Готов к работе"), self)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setFont(QFont("Segoe UI", 10))

        self._port_indicator = QLabel("●", self)
        self._port_indicator.setFixedSize(20, 20)
        self._port_indicator.setStyleSheet("color: #888888; font-size: 14px;")
        self._port_indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._port_label = QLabel(tr("Нет подключения"), self)
        self._port_label.setFont(QFont("Segoe UI", 9))

        self._heartbeat_label = QLabel("●", self)
        self._heartbeat_label.setFixedSize(20, 20)
        self._heartbeat_label.setStyleSheet("color: #888888; font-size: 14px;")
        self._heartbeat_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._heartbeat_label.setToolTip("Индикатор жизни потока чтения COM-порта")

    def _layout_widgets(self) -> None:
        """Располагает виджеты по координатам."""
        self._logs_button.move(10, 10)
        self._diagnostics_button.move(100, 10)
        self._theme_button.move(355, 10)
        self._lang_button.move(400, 10)
        self._update_check_button.move(445, 10)

        self._update_button.move(480 - 130 - 50, 10)
        self._settings_button.move(480 - 130 - 50 - 130 - 12, 10)

        self._progress_bar.setGeometry(50, 70, 380, 20)

        self._port_indicator.move(10, 320 - 28)
        self._port_label.move(32, 320 - 30)
        self._heartbeat_label.move(450, 320 - 28)

        self._status_label.setGeometry(0, 320 - 60, 480, 20)

    def _connect_signals(self) -> None:
        """Подключает сигналы кнопок и менеджера."""
        self._update_button.clicked.connect(self._on_update_clicked)
        self._settings_button.clicked.connect(self._on_settings_clicked)
        self._logs_button.clicked.connect(self._open_logs)
        self._serial_manager.connection_changed.connect(self._update_port_indicator)
        self._serial_manager.error_occurred.connect(self._on_serial_error)
        self._serial_manager.heartbeat.connect(self._on_heartbeat)

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.timeout.connect(self._reset_heartbeat_color)
        self._heartbeat_timer.start(1500)

    def _setup_shortcuts(self) -> None:
        """Настраивает горячие клавиши главного окна."""
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._open_firmware_shortcut)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self._open_settings_monitor)
        QShortcut(QKeySequence("Ctrl+T"), self, activated=self._open_settings_trigger)
        QShortcut(QKeySequence("Esc"), self, activated=self._handle_esc)

    def _open_firmware_shortcut(self) -> None:
        """Обработчик Ctrl+O: открыть файл прошивки."""
        self._on_update_clicked()

    def _open_settings_monitor(self) -> None:
        """Обработчик Ctrl+M: открыть окно настроек на вкладке мониторинга."""
        self._on_settings_clicked()
        if self._settings_window is not None:
            self._settings_window.set_current_tab(1)

    def _open_settings_trigger(self) -> None:
        """Обработчик Ctrl+T: открыть окно настроек на вкладке CAN Тригер."""
        self._on_settings_clicked()
        if self._settings_window is not None:
            self._settings_window.set_current_tab(0)

    def _handle_esc(self) -> None:
        """Обработчик Esc: сбрасывает фокус."""
        self.setFocus()

    def _on_heartbeat(self) -> None:
        """Обработчик heartbeat: делает индикатор зелёным."""
        self._heartbeat_label.setStyleSheet("color: #00CC00; font-size: 14px;")

    def _reset_heartbeat_color(self) -> None:
        """Сбрасывает индикатор в серый, если heartbeat давно не приходил."""
        self._heartbeat_label.setStyleSheet("color: #888888; font-size: 14px;")

    def _ensure_port(self) -> bool:
        """Проверяет подключение COM-порта, иначе открывает диалог выбора.

        Returns:
            True, если порт выбран и открыт.
        """
        if self._serial_manager.is_open():
            return True
        dialog = ComSettingsDialog(self._serial_manager, self)
        if dialog.exec() == ComSettingsDialog.DialogCode.Accepted:
            return self._serial_manager.is_open()
        return False

    def _on_update_clicked(self) -> None:
        """Обработчик нажатия кнопки «Обновить» для прошивки STM32."""
        if not self._ensure_port():
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл прошивки",
            "",
            "Firmware (*.bin *.hex);;All files (*)",
        )
        if not file_path:
            return

        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(True)
        self._status_label.setText("Идёт прошивка...")
        self._update_button.setEnabled(False)

        self._firmware_worker = FirmwareWorker(self._serial_manager, file_path, self)
        self._firmware_worker.progress.connect(self._progress_bar.setValue)
        self._firmware_worker.finished.connect(self._on_firmware_finished)
        self._firmware_worker.start()

    def _on_firmware_finished(self, success: bool, message: str) -> None:
        """Выводит результат прошивки и восстанавливает интерфейс."""
        self._update_button.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._status_label.setText(tr("Готов к работе") if success else tr("Ошибка прошивки"))
        if success:
            QMessageBox.information(self, tr("Обновить"), message)
        else:
            QMessageBox.critical(self, tr("Ошибка"), message)
        self._firmware_worker = None

    def _on_check_updates_clicked(self) -> None:
        """Проверяет наличие обновлений приложения."""
        self._status_label.setText(tr("Проверка обновлений"))
        available, message = check_for_updates()
        self._status_label.setText(tr("Готов к работе"))
        if available:
            QMessageBox.information(self, tr("Доступно обновление"), message)
        else:
            QMessageBox.information(self, tr("Последняя версия"), message)

    def _on_language_clicked(self) -> None:
        """Переключает язык интерфейса между русским и английским."""
        lang = "en" if self._config.get("language", "ru") == "ru" else "ru"
        self._config.set("language", lang)
        set_language(lang)
        self._lang_button.setText("RU" if lang == "en" else "EN")
        QMessageBox.information(self, tr("Переключить язык"), "Restart the application to apply the new language." if lang == "en" else "Перезапустите приложение, чтобы применить новый язык.")
        logger.info("Переключён язык: %s", lang)

    def _on_theme_clicked(self) -> None:
        """Переключает между светлой и тёмной темой."""
        from PySide6.QtWidgets import QApplication
        light = not self._config.get("light_theme", False)
        self._config.set("light_theme", light)
        app = QApplication.instance()
        if app is not None:
            if light:
                apply_light_theme(app)
                self._theme_button.setText("☾")
            else:
                apply_dark_theme(app)
                self._theme_button.setText("☀")
        logger.info("Переключена тема: %s", "светлая" if light else "тёмная")

    def _on_diagnostics_clicked(self) -> None:
        """Запускает диагностику bootloader STM32."""
        if not self._ensure_port():
            return
        self._status_label.setText("Диагностика bootloader...")
        self._diagnostics_button.setEnabled(False)

        self._diagnostics_worker = DiagnosticsWorker(self._serial_manager, self)
        self._diagnostics_worker.finished.connect(self._on_diagnostics_finished)
        self._diagnostics_worker.start()

    def _on_diagnostics_finished(self, success: bool, message: str) -> None:
        """Выводит результат диагностики bootloader."""
        self._diagnostics_button.setEnabled(True)
        self._status_label.setText(tr("Готов к работе") if success else tr("Ошибка диагностики"))
        if success:
            QMessageBox.information(self, tr("Диагностика bootloader"), message)
        else:
            QMessageBox.critical(self, tr("Ошибка"), message)
        self._diagnostics_worker = None

    def _on_settings_clicked(self) -> None:
        """Открывает немодальное окно настроек."""
        if self._settings_window is None or not self._settings_window.isVisible():
            self._settings_window = SettingsWindow(self._serial_manager, self)
            self._settings_window.show()
        else:
            self._settings_window.raise_()
            self._settings_window.activateWindow()

    def _open_logs(self) -> None:
        """Открывает папку с лог-файлом."""
        try:
            open_log_folder()
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось открыть папку с логами: %s", exc)
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть папку с логами: {exc}")

    def _update_port_indicator(self, connected: bool = False) -> None:
        """Обновляет цвет индикатора и текст порта."""
        if self._serial_manager.is_open():
            self._port_indicator.setStyleSheet("color: #00AA00; font-size: 14px;")
            self._port_label.setText(self._serial_manager.current_port_name())
        else:
            self._reset_heartbeat_color()
        if self._config.get("port"):
            self._port_indicator.setStyleSheet("color: #AA0000; font-size: 14px;")
            self._port_label.setText(tr("Порт не открыт"))
        else:
            self._port_indicator.setStyleSheet("color: #888888; font-size: 14px;")
            self._port_label.setText(tr("Нет подключения"))

    def _on_serial_error(self, message: str) -> None:
        """Показывает сообщение об ошибке COM-порта."""
        logger.error("Ошибка COM-порта: %s", message)
        self._status_label.setText(tr("Ошибка порта"))

    def closeEvent(self, event) -> None:  # noqa: N802
        """Корректно закрывает приложение и освобождает ресурсы."""
        logger.info("Закрытие главного окна")
        if self._settings_window is not None:
            self._settings_window.close()
        self._serial_manager.close_port()
        event.accept()


def show_exception_box(exc_type, exc_value, exc_tb) -> None:
    """Показывает QMessageBox при необработанном исключении."""
    message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logger.critical("Необработанное исключение: %s", message)
    try:
        QMessageBox.critical(None, "Критическая ошибка", f"Произошла непредвиденная ошибка:\n{exc_value}")
    except Exception:  # noqa: BLE001
        pass


sys.excepthook = show_exception_box
