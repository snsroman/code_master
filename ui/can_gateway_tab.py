"""Вкладка «CAN Шлюз» для ретрансляции, игнорирования и подмены пакетов."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.can_protocol import pack_can_frame
from core.serial_manager import SerialManager
from models.config import Config
from models.logger import get_logger
from models.utils import hex_to_int, parse_data_bytes

logger = get_logger(__name__)

RULE_COUNT = 10
IGNORE_COUNT = 10


class CanGatewayTab(QWidget):
    """Вкладка настройки CAN-шлюза."""

    def __init__(self, serial_manager: SerialManager, parent: Optional[QWidget] = None) -> None:
        """Создаёт вкладку CAN Шлюз.

        Args:
            serial_manager: Менеджер COM-порта.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._config = Config()
        self._active = False
        self._ignore_enabled = False
        self._ignore_ids: set[int] = set()
        self._rules: List[Dict[str, object]] = []
        self._ignore_edits: List[QLineEdit] = []
        self._rule_widgets: List[Dict[str, object]] = []

        self._create_widgets()
        self._layout_widgets()
        self._load_config()

    def _create_widgets(self) -> None:
        """Создаёт элементы управления шлюзом."""
        # Секция игнорирования
        self._ignore_group = QGroupBox("Игнорировать")
        self._ignore_group.setFont(QFont("Segoe UI", 10))
        ignore_layout = QVBoxLayout(self._ignore_group)
        ignore_layout.setSpacing(6)

        ignore_row1 = QHBoxLayout()
        ignore_row2 = QHBoxLayout()
        for i in range(IGNORE_COUNT):
            edit = QLineEdit()
            edit.setFixedWidth(110)
            edit.setMaxLength(8)
            edit.setFont(QFont("Segoe UI", 10))
            edit.setPlaceholderText("ID HEX")
            self._ignore_edits.append(edit)
            if i < 5:
                ignore_row1.addWidget(edit)
            else:
                ignore_row2.addWidget(edit)
        ignore_row1.addStretch()
        ignore_row2.addStretch()
        ignore_layout.addLayout(ignore_row1)
        ignore_layout.addLayout(ignore_row2)

        self._ignore_check = QCheckBox("Включить игнорирование")
        self._ignore_check.setFont(QFont("Segoe UI", 10))
        ignore_layout.addWidget(self._ignore_check)

        # Секция правил подмены
        self._rules_scroll = QScrollArea()
        self._rules_scroll.setWidgetResizable(True)
        self._rules_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._rules_content = QWidget()
        self._rules_layout = QVBoxLayout(self._rules_content)
        self._rules_layout.setSpacing(8)
        self._rules_layout.setContentsMargins(6, 6, 6, 6)

        for i in range(RULE_COUNT):
            rule = self._create_rule_block(i)
            self._rule_widgets.append(rule)
            self._rules_layout.addWidget(rule["widget"])

        self._rules_layout.addStretch()
        self._rules_scroll.setWidget(self._rules_content)

        # Кнопки управления
        self._start_button = QPushButton("Запустить шлюз")
        self._start_button.setFixedSize(140, 34)
        self._start_button.setFont(QFont("Segoe UI", 10))
        self._start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._start_button.clicked.connect(self._start_gateway)

        self._stop_button = QPushButton("Остановить")
        self._stop_button.setFixedSize(120, 34)
        self._stop_button.setFont(QFont("Segoe UI", 10))
        self._stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_button.clicked.connect(self._stop_gateway)

        self._save_button = QPushButton("Сохранить правила")
        self._save_button.setFixedSize(130, 28)
        self._save_button.setFont(QFont("Segoe UI", 9))
        self._save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_button.clicked.connect(self._save_gateway_to_file)

        self._load_button = QPushButton("Загрузить правила")
        self._load_button.setFixedSize(130, 28)
        self._load_button.setFont(QFont("Segoe UI", 9))
        self._load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_button.clicked.connect(self._load_gateway_from_file)

    def _create_rule_block(self, index: int) -> Dict[str, object]:
        """Создаёт один блок правила подмены."""
        group = QGroupBox(f"Правило {index + 1}")
        group.setFont(QFont("Segoe UI", 10))
        group.setStyleSheet("QGroupBox { border: 1px solid #444444; }")

        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        # Приём
        receive_layout = QHBoxLayout()
        receive_layout.addWidget(QLabel("Прием ID:"))
        recv_id = QLineEdit()
        recv_id.setFixedWidth(110)
        recv_id.setMaxLength(8)
        receive_layout.addWidget(recv_id)
        recv_data: List[QLineEdit] = []
        for i in range(8):
            edit = QLineEdit()
            edit.setFixedWidth(40)
            edit.setPlaceholderText(f"D{i}")
            receive_layout.addWidget(edit)
            recv_data.append(edit)
        receive_layout.addStretch()

        # Подмена
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Подмена ID:"))
        rep_id = QLineEdit()
        rep_id.setFixedWidth(110)
        rep_id.setMaxLength(8)
        replace_layout.addWidget(rep_id)
        rep_data: List[QLineEdit] = []
        for i in range(8):
            edit = QLineEdit()
            edit.setFixedWidth(40)
            edit.setPlaceholderText(f"D{i}")
            replace_layout.addWidget(edit)
            rep_data.append(edit)
        replace_layout.addStretch()

        # Направление и активность
        options_layout = QHBoxLayout()
        direction = QComboBox()
        direction.addItems(["Из CAN1 в CAN2", "Из CAN2 в CAN1"])
        direction.setFixedWidth(150)
        options_layout.addWidget(QLabel("Направление:"))
        options_layout.addWidget(direction)
        active = QCheckBox("Активен")
        options_layout.addWidget(active)
        options_layout.addStretch()

        layout.addLayout(receive_layout)
        layout.addLayout(replace_layout)
        layout.addLayout(options_layout)

        return {
            "widget": group,
            "recv_id": recv_id,
            "recv_data": recv_data,
            "rep_id": rep_id,
            "rep_data": rep_data,
            "direction": direction,
            "active": active,
        }

    def _layout_widgets(self) -> None:
        """Располагает элементы на вкладке."""
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self._ignore_group)
        layout.addWidget(self._rules_scroll)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._start_button)
        button_layout.addWidget(self._stop_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        file_layout = QHBoxLayout()
        file_layout.addStretch()
        file_layout.addWidget(self._save_button)
        file_layout.addWidget(self._load_button)
        file_layout.addStretch()
        layout.addLayout(file_layout)

    def _load_config(self) -> None:
        """Загружает настройки шлюза из конфигурации."""
        ignore_list = self._config.get("ignore_list", [])
        for i, value in enumerate(ignore_list[:IGNORE_COUNT]):
            self._ignore_edits[i].setText(str(value))
        self._ignore_check.setChecked(self._config.get("ignore_enabled", False))

        rules = self._config.get("gateway_rules", [])
        for i, rule in enumerate(rules[:RULE_COUNT]):
            widgets = self._rule_widgets[i]
            widgets["recv_id"].setText(rule.get("recv_id", ""))
            for j, edit in enumerate(widgets["recv_data"]):
                edit.setText(rule.get(f"recv_data_{j}", ""))
            widgets["rep_id"].setText(rule.get("rep_id", ""))
            for j, edit in enumerate(widgets["rep_data"]):
                edit.setText(rule.get(f"rep_data_{j}", ""))
            index = widgets["direction"].findText(rule.get("direction", "Из CAN1 в CAN2"))
            if index >= 0:
                widgets["direction"].setCurrentIndex(index)
            widgets["active"].setChecked(rule.get("active", False))

    def _save_config(self) -> None:
        """Сохраняет настройки шлюза в конфигурацию."""
        ignore_list = [edit.text().strip() for edit in self._ignore_edits if edit.text().strip()]
        self._config.set_bulk(
            {
                "ignore_list": ignore_list,
                "ignore_enabled": self._ignore_check.isChecked(),
            }
        )

        rules = []
        for widgets in self._rule_widgets:
            rule = {
                "recv_id": widgets["recv_id"].text().strip(),
                "rep_id": widgets["rep_id"].text().strip(),
                "direction": widgets["direction"].currentText(),
                "active": widgets["active"].isChecked(),
            }
            for j, edit in enumerate(widgets["recv_data"]):
                rule[f"recv_data_{j}"] = edit.text().strip()
            for j, edit in enumerate(widgets["rep_data"]):
                rule[f"rep_data_{j}"] = edit.text().strip()
            rules.append(rule)
        self._config.set("gateway_rules", rules)

    def _start_gateway(self) -> None:
        """Активирует шлюз."""
        self._save_config()
        self._build_rules()
        self._ignore_enabled = self._ignore_check.isChecked()
        self._ignore_ids = set()
        for edit in self._ignore_edits:
            value = hex_to_int(edit.text())
            if value is not None:
                self._ignore_ids.add(value)
        self._active = True
        logger.info("CAN-шлюз запущен. Игнорируемых ID: %d, активных правил: %d", len(self._ignore_ids), len(self._rules))
        QMessageBox.information(self, "Шлюз", "CAN-шлюз запущен")

    def _stop_gateway(self) -> None:
        """Останавливает шлюз."""
        self._active = False
        logger.info("CAN-шлюз остановлен")
        QMessageBox.information(self, "Шлюз", "CAN-шлюз остановлен")

    def _build_rules(self) -> None:
        """Собирает активные правила подмены."""
        self._rules = []
        for widgets in self._rule_widgets:
            if not widgets["active"].isChecked():
                continue
            recv_id = hex_to_int(widgets["recv_id"].text())
            rep_id = hex_to_int(widgets["rep_id"].text())
            if recv_id is None or rep_id is None:
                continue
            recv_data = parse_data_bytes([edit.text() for edit in widgets["recv_data"]])
            rep_data = parse_data_bytes([edit.text() for edit in widgets["rep_data"]])
            direction_text = widgets["direction"].currentText()
            source = 1 if "CAN1" in direction_text else 2
            target = 2 if source == 1 else 1
            self._rules.append(
                {
                    "recv_id": recv_id,
                    "recv_data": recv_data,
                    "rep_id": rep_id,
                    "rep_data": rep_data,
                    "source": source,
                    "target": target,
                }
            )

    def process_frame(self, frame: Dict[str, object]) -> None:
        """Обрабатывает входящий CAN-кадр: ретранслирует, игнорирует или подменяет.

        Args:
            frame: Распакованный CAN-кадр.
        """
        if not self._active:
            return

        channel = int(frame["channel"])
        frame_id = int(frame["id"])
        frame_data = bytes(frame["data"])

        # Игнорирование
        if self._ignore_enabled and frame_id in self._ignore_ids:
            logger.info("CAN-шлюз: пакет ID=0x%03X игнорирован", frame_id)
            return

        # Подмена
        for rule in self._rules:
            if rule["source"] != channel:
                continue
            if rule["recv_id"] != frame_id:
                continue
            if rule["recv_data"]:
                if len(frame_data) < len(rule["recv_data"]):
                    continue
                if not all(frame_data[i] == rule["recv_data"][i] for i in range(len(rule["recv_data"]))):
                    continue
            new_frame = pack_can_frame(rule["target"], rule["rep_id"], bytes(rule["rep_data"]))
            if self._serial_manager.send_data(new_frame):
                logger.info(
                    "CAN-шлюз: подмена ID=0x%03X -> 0x%03X, направление %d->%d",
                    frame_id,
                    rule["rep_id"],
                    rule["source"],
                    rule["target"],
                )
            return

        # Ретрансляция в противоположный канал
        target_channel = 2 if channel == 1 else 1
        new_frame = pack_can_frame(target_channel, frame_id, frame_data)
        if self._serial_manager.send_data(new_frame):
            logger.debug("CAN-шлюз: ретрансляция ID=0x%03X из %d в %d", frame_id, channel, target_channel)

    def get_config(self) -> Dict[str, object]:
        """Возвращает настройки шлюза для экспорта."""
        self._save_config()
        return {
            "ignore_list": self._config.get("ignore_list", []),
            "ignore_enabled": self._config.get("ignore_enabled", False),
            "gateway_rules": self._config.get("gateway_rules", []),
        }

    def set_config(self, config: Dict[str, object]) -> None:
        """Загружает настройки шлюза из импортированного профиля."""
        self._config.set_bulk(
            {
                "ignore_list": config.get("ignore_list", []),
                "ignore_enabled": config.get("ignore_enabled", False),
                "gateway_rules": config.get("gateway_rules", []),
            }
        )
        self._load_config()

    def _save_gateway_to_file(self) -> None:
        """Сохраняет только набор правил шлюза в JSON-файл."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить правила шлюза",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.get_config(), ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Правила шлюза сохранены в %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка сохранения правил шлюза: %s", exc)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить правила шлюза: {exc}")

    def _load_gateway_from_file(self) -> None:
        """Загружает набор правил шлюза из JSON-файла."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить правила шлюза",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            config = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                raise ValueError("Файл должен содержать объект правил шлюза")
            self.set_config(config)
            logger.info("Правила шлюза загружены из %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка загрузки правил шлюза: %s", exc)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить правила шлюза: {exc}")
