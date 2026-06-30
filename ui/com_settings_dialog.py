"""Модальное окно выбора COM-порта."""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from core.serial_manager import SerialManager
from models.config import Config
from models.logger import get_logger

logger = get_logger(__name__)


try:
    from serial.tools.list_ports import comports
except Exception:  # noqa: BLE001
    comports = lambda: []  # type: ignore[assignment]


class ComSettingsDialog(QDialog):
    """Диалог для выбора COM-порта, скорости и режима эмуляции."""

    def __init__(self, serial_manager: SerialManager, parent: Optional[QDialog] = None) -> None:
        """Создаёт диалог настройки COM-порта.

        Args:
            serial_manager: Менеджер COM-порта.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._config = Config()

        self.setWindowTitle("Выбор COM-порта")
        self.setFixedSize(360, 240)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        self._create_widgets()
        self._layout_widgets()
        self._load_defaults()

    def _create_widgets(self) -> None:
        """Создаёт элементы диалога."""
        self._port_label = QLabel("COM-порт:")
        self._port_label.setFont(QFont("Segoe UI", 10))

        self._port_combo = QComboBox()
        self._port_combo.setFont(QFont("Segoe UI", 10))
        self._port_combo.setEditable(False)

        self._baud_label = QLabel("Скорость:")
        self._baud_label.setFont(QFont("Segoe UI", 10))

        self._baud_combo = QComboBox()
        self._baud_combo.setFont(QFont("Segoe UI", 10))
        self._baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400", "460800"])

        self._emulation_check = QCheckBox("Режим эмуляции")
        self._emulation_check.setFont(QFont("Segoe UI", 9))
        self._emulation_check.setStyleSheet("color: #888888;")
        self._emulation_check.setToolTip("Использовать виртуальный COM-порт для тестирования без STM32")
        self._emulation_check.stateChanged.connect(self._on_emulation_changed)

        self._auto_reconnect_check = QCheckBox("Автопереподключение")
        self._auto_reconnect_check.setFont(QFont("Segoe UI", 9))
        self._auto_reconnect_check.setStyleSheet("color: #888888;")
        self._auto_reconnect_check.setToolTip("Автоматически пытаться переподключиться к COM-порту при разрыве")

        self._error_label = QLabel("Вероятность ошибки CAN: 0%")
        self._error_label.setFont(QFont("Segoe UI", 9))
        self._error_label.setStyleSheet("color: #888888;")
        self._error_label.setEnabled(False)

        self._error_slider = QSlider(Qt.Orientation.Horizontal)
        self._error_slider.setRange(0, 100)
        self._error_slider.setValue(0)
        self._error_slider.setEnabled(False)
        self._error_slider.valueChanged.connect(self._on_error_slider_changed)

        self._connect_button = QPushButton("Подключить")
        self._connect_button.setFixedSize(130, 34)
        self._connect_button.setFont(QFont("Segoe UI", 10))
        self._connect_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._connect_button.clicked.connect(self._on_connect)

    def _layout_widgets(self) -> None:
        """Располагает элементы диалога."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(self._port_label)
        layout.addWidget(self._port_combo)
        layout.addWidget(self._baud_label)
        layout.addWidget(self._baud_combo)
        layout.addWidget(self._emulation_check)
        layout.addWidget(self._auto_reconnect_check)
        layout.addWidget(self._error_label)
        layout.addWidget(self._error_slider)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._connect_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        layout.addStretch()

    def _load_defaults(self) -> None:
        """Загружает список портов и сохранённые настройки."""
        self._port_combo.addItem("FAKE (эмулятор)")
        for port_info in comports():
            self._port_combo.addItem(port_info.device)

        saved_port = self._config.get("port", "")
        if saved_port:
            index = self._port_combo.findText(saved_port)
            if index < 0:
                self._port_combo.addItem(saved_port)
                index = self._port_combo.count() - 1
            self._port_combo.setCurrentIndex(index)

        saved_baud = str(self._config.get("baudrate", 115200))
        index = self._baud_combo.findText(saved_baud)
        if index >= 0:
            self._baud_combo.setCurrentIndex(index)

        self._emulation_check.setChecked(self._config.get("emulation", False))
        self._auto_reconnect_check.setChecked(self._config.get("auto_reconnect", False))
        error_prob = self._config.get("error_probability", 0)
        self._error_slider.setValue(error_prob)
        self._error_label.setText(f"Вероятность ошибки CAN: {error_prob}%")
        self._on_emulation_changed()

    def _on_emulation_changed(self) -> None:
        """Включает/отключает настройку ошибок в зависимости от режима эмуляции."""
        enabled = self._emulation_check.isChecked()
        self._error_label.setEnabled(enabled)
        self._error_slider.setEnabled(enabled)

    def _on_error_slider_changed(self, value: int) -> None:
        """Обновляет текст метки вероятности ошибки."""
        self._error_label.setText(f"Вероятность ошибки CAN: {value}%")

    def _on_connect(self) -> None:
        """Пробует открыть выбранный порт и сохранить настройки."""
        port_text = self._port_combo.currentText()
        if port_text.startswith("FAKE"):
            port_name = "FAKE"
            emulation = True
        else:
            port_name = port_text
            emulation = self._emulation_check.isChecked()

        auto_reconnect = self._auto_reconnect_check.isChecked()
        error_probability = self._error_slider.value() if emulation else 0
        baudrate = int(self._baud_combo.currentText())
        logger.info("Попытка подключения к %s", port_name)

        if self._serial_manager.open_port(port_name, baudrate, emulation, auto_reconnect, error_probability):
            self._config.set("auto_reconnect", auto_reconnect)
            self._config.set("error_probability", error_probability)
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                f"Не удалось открыть порт {port_name}.\nПроверьте, что порт доступен.",
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        """Закрытие по крестику считается отменой."""
        if self.result() != QDialog.DialogCode.Accepted:
            self.reject()
        event.accept()
