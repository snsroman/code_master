"""Окно «Настройка» с вкладками CAN Тригер, Мониторинг CAN и CAN Шлюз."""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.serial_manager import SerialManager
from models.config import Config
from models.logger import get_logger
from ui.can_gateway_tab import CanGatewayTab
from ui.can_monitor_tab import CanMonitorTab
from ui.can_trigger_tab import CanTriggerTab

logger = get_logger(__name__)


class SettingsWindow(QWidget):
    """Немодальное окно настроек с вкладками."""

    def __init__(self, serial_manager: SerialManager, parent: Optional[QWidget] = None) -> None:
        """Создаёт окно настроек.

        Args:
            serial_manager: Менеджер COM-порта.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._config = Config()
        self.setWindowTitle("Настройка")
        self.setMinimumSize(900, 650)
        self.setWindowFlags(Qt.WindowType.Window)

        self._create_widgets()
        self._layout_widgets()
        self._connect_signals()
        self._setup_shortcuts()

    def _create_widgets(self) -> None:
        """Создаёт вкладки и кнопки окна."""
        self._title_label = QLabel("Настройка")
        self._title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._tab_widget = QTabWidget()
        self._trigger_tab = CanTriggerTab(self._serial_manager, self)
        self._monitor_tab = CanMonitorTab(self._serial_manager, self)
        self._gateway_tab = CanGatewayTab(self._serial_manager, self)

        self._tab_widget.addTab(self._trigger_tab, "CAN Тригер")
        self._tab_widget.addTab(self._monitor_tab, "Мониторинг CAN")
        self._tab_widget.addTab(self._gateway_tab, "CAN Шлюз")

        self._save_config_button = QPushButton("Сохранить конфигурацию в файл")
        self._save_config_button.setFixedHeight(34)
        self._save_config_button.setFont(QFont("Segoe UI", 10))
        self._save_config_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._load_config_button = QPushButton("Загрузить конфигурацию из файла")
        self._load_config_button.setFixedHeight(34)
        self._load_config_button.setFont(QFont("Segoe UI", 10))
        self._load_config_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self._close_button = QPushButton("Закрыть")
        self._close_button.setFixedSize(120, 34)
        self._close_button.setFont(QFont("Segoe UI", 10))
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _layout_widgets(self) -> None:
        """Располагает элементы окна."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        layout.addWidget(self._title_label)
        layout.addWidget(self._tab_widget)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self._save_config_button)
        buttons_layout.addWidget(self._load_config_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self._close_button)
        layout.addLayout(buttons_layout)

    def _connect_signals(self) -> None:
        """Подключает сигналы кнопок."""
        self._close_button.clicked.connect(self.close)
        self._save_config_button.clicked.connect(self._save_config_to_file)
        self._load_config_button.clicked.connect(self._load_config_from_file)
        self._serial_manager.new_can_frame.connect(self._on_can_frame)
        self._monitor_tab.create_trigger_requested.connect(self._on_create_trigger_from_packet)

    def _setup_shortcuts(self) -> None:
        """Настраивает горячие клавиши окна настроек."""
        QShortcut(QKeySequence("Esc"), self, activated=self.close)

    def set_current_tab(self, index: int) -> None:
        """Делает активной указанную вкладку.

        Args:
            index: Индекс вкладки (0 - CAN Тригер, 1 - Мониторинг CAN, 2 - CAN Шлюз).
        """
        if 0 <= index < self._tab_widget.count():
            self._tab_widget.setCurrentIndex(index)
            self.raise_()
            self.activateWindow()

    def _on_create_trigger_from_packet(self, packet: dict) -> None:
        """Переключается на вкладку CAN Тригер и создаёт триггер из пакета."""
        self.show()
        self.raise_()
        self.activateWindow()
        self.set_current_tab(0)
        self._trigger_tab.create_trigger_from_packet(packet)
        logger.info("Создание триггера из пакета мониторинга: %s", packet)

    def _on_can_frame(self, frame: dict) -> None:
        """Распределяет входящий CAN-кадр между вкладками.

        Args:
            frame: Распакованный CAN-кадр.
        """
        self._trigger_tab.process_frame(frame)
        self._monitor_tab.process_frame(frame)
        self._gateway_tab.process_frame(frame)

    def _save_config_to_file(self) -> None:
        """Сохраняет полный профиль настроек в JSON-файл."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить конфигурацию",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        profile = {
            "triggers": self._trigger_tab.get_config(),
            "gateway": self._gateway_tab.get_config(),
        }
        try:
            Path(path).write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Конфигурация сохранена в %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка сохранения конфигурации: %s", exc)

    def _load_config_from_file(self) -> None:
        """Загружает полный профиль настроек из JSON-файла."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить конфигурацию",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            profile = json.loads(Path(path).read_text(encoding="utf-8"))
            self._trigger_tab.set_config(profile.get("triggers", []))
            self._gateway_tab.set_config(profile.get("gateway", {}))
            logger.info("Конфигурация загружена из %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка загрузки конфигурации: %s", exc)

    def closeEvent(self, event) -> None:  # noqa: N802
        """Корректно закрывает окно настроек."""
        logger.info("Окно настроек закрыто")
        self._serial_manager.new_can_frame.disconnect(self._on_can_frame)
        event.accept()
