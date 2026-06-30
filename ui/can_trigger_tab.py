"""Вкладка «CAN Тригер» для настройки автоматических ответов на CAN-пакеты."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
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
from models.utils import format_data_bytes, hex_to_int, int_to_hex, parse_data_bytes

logger = get_logger(__name__)

TRIGGER_COUNT = 10


class CanTriggerTab(QWidget):
    """Вкладка настройки триггеров CAN."""

    def __init__(self, serial_manager: SerialManager, parent: Optional[QWidget] = None) -> None:
        """Создаёт вкладку CAN Тригер.

        Args:
            serial_manager: Менеджер COM-порта для отправки ответов.
            parent: Родительский виджет.
        """
        super().__init__(parent)
        self._serial_manager = serial_manager
        self._config = Config()
        self._active = False
        self._triggers: List[Dict[str, object]] = []
        self._trigger_widgets: List[Dict[str, object]] = []
        self._trigger_counters: List[int] = [0] * TRIGGER_COUNT

        self._create_widgets()
        self._layout_widgets()
        self._load_config()

    def _create_widgets(self) -> None:
        """Создаёт элементы управления триггерами."""
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._scroll_content = QWidget()
        self._scroll_layout = QVBoxLayout(self._scroll_content)
        self._scroll_layout.setSpacing(10)
        self._scroll_layout.setContentsMargins(10, 10, 10, 10)

        for i in range(TRIGGER_COUNT):
            group = self._create_trigger_block(i)
            self._trigger_widgets.append(group)
            self._scroll_layout.addWidget(group["widget"])

        self._scroll_layout.addStretch()
        self._scroll_area.setWidget(self._scroll_content)

        self._apply_button = QPushButton("Применить триггеры")
        self._apply_button.setFixedSize(140, 34)
        self._apply_button.setFont(QFont("Segoe UI", 10))
        self._apply_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_button.clicked.connect(self._apply_triggers)

        self._stop_button = QPushButton("Остановить")
        self._stop_button.setFixedSize(120, 34)
        self._stop_button.setFont(QFont("Segoe UI", 10))
        self._stop_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_button.clicked.connect(self._stop_triggers)

        self._save_button = QPushButton("Сохранить триггеры")
        self._save_button.setFixedSize(130, 28)
        self._save_button.setFont(QFont("Segoe UI", 9))
        self._save_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_button.clicked.connect(self._save_triggers_to_file)

        self._load_button = QPushButton("Загрузить триггеры")
        self._load_button.setFixedSize(130, 28)
        self._load_button.setFont(QFont("Segoe UI", 9))
        self._load_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._load_button.clicked.connect(self._load_triggers_from_file)

    def _create_trigger_block(self, index: int) -> Dict[str, object]:
        """Создаёт один блок триггера с полями приёма и ответа."""
        group = QGroupBox(f"Тригер {index + 1}")
        group.setFont(QFont("Segoe UI", 10))

        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        # Приём
        receive_layout = QHBoxLayout()
        receive_layout.setSpacing(6)
        receive_layout.addWidget(QLabel("ID:"))
        id_edit = QLineEdit()
        id_edit.setFixedWidth(110)
        id_edit.setMaxLength(8)
        id_edit.setFont(QFont("Segoe UI", 10))
        receive_layout.addWidget(id_edit)

        data_edits: List[QLineEdit] = []
        for i in range(8):
            edit = QLineEdit()
            edit.setFixedWidth(40)
            edit.setFont(QFont("Segoe UI", 10))
            edit.setPlaceholderText(f"D{i}")
            receive_layout.addWidget(edit)
            data_edits.append(edit)

        active_check = QCheckBox("Активен")
        active_check.setFont(QFont("Segoe UI", 10))
        receive_layout.addWidget(active_check)

        counter_label = QLabel("Сраб.: 0")
        counter_label.setFont(QFont("Segoe UI", 9))
        counter_label.setStyleSheet("color: #AAAAAA;")
        receive_layout.addWidget(counter_label)
        receive_layout.addStretch()

        # Ответ
        response_layout = QHBoxLayout()
        response_layout.setSpacing(6)
        response_layout.addWidget(QLabel("ID отв.:"))
        resp_id_edit = QLineEdit()
        resp_id_edit.setFixedWidth(110)
        resp_id_edit.setMaxLength(8)
        resp_id_edit.setFont(QFont("Segoe UI", 10))
        response_layout.addWidget(resp_id_edit)

        resp_data_edits: List[QLineEdit] = []
        for i in range(8):
            edit = QLineEdit()
            edit.setFixedWidth(40)
            edit.setFont(QFont("Segoe UI", 10))
            edit.setPlaceholderText(f"D{i}")
            response_layout.addWidget(edit)
            resp_data_edits.append(edit)

        response_layout.addWidget(QLabel("Задержка мс:"))
        delay_edit = QLineEdit()
        delay_edit.setFixedWidth(60)
        delay_edit.setMaxLength(5)
        delay_edit.setFont(QFont("Segoe UI", 10))
        delay_edit.setPlaceholderText("0")
        response_layout.addWidget(delay_edit)

        test_button = QPushButton("Тест")
        test_button.setFixedSize(60, 26)
        test_button.setFont(QFont("Segoe UI", 9))
        test_button.setCursor(Qt.CursorShape.PointingHandCursor)
        test_button.clicked.connect(lambda _checked, idx=index: self._test_trigger(idx))
        response_layout.addWidget(test_button)
        response_layout.addStretch()

        layout.addLayout(receive_layout)
        layout.addLayout(response_layout)

        return {
            "widget": group,
            "id": id_edit,
            "data": data_edits,
            "active": active_check,
            "counter": counter_label,
            "resp_id": resp_id_edit,
            "resp_data": resp_data_edits,
            "delay": delay_edit,
        }

    def _layout_widgets(self) -> None:
        """Располагает элементы на вкладке."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        main_layout.addWidget(self._scroll_area)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self._apply_button)
        button_layout.addWidget(self._stop_button)
        button_layout.addStretch()
        main_layout.addLayout(button_layout)

        file_layout = QHBoxLayout()
        file_layout.addStretch()
        file_layout.addWidget(self._save_button)
        file_layout.addWidget(self._load_button)
        file_layout.addStretch()
        main_layout.addLayout(file_layout)

    def _load_config(self) -> None:
        """Загружает сохранённые триггеры из конфигурации."""
        triggers = self._config.get("triggers", [])
        for i, trigger in enumerate(triggers[:TRIGGER_COUNT]):
            widgets = self._trigger_widgets[i]
            widgets["id"].setText(trigger.get("id", ""))
            for j, edit in enumerate(widgets["data"]):
                edit.setText(trigger.get(f"data_{j}", ""))
            widgets["active"].setChecked(trigger.get("active", False))
            widgets["resp_id"].setText(trigger.get("resp_id", ""))
            for j, edit in enumerate(widgets["resp_data"]):
                edit.setText(trigger.get(f"resp_data_{j}", ""))
            widgets["delay"].setText(str(trigger.get("delay", "0")))

    def _save_config(self) -> None:
        """Сохраняет текущие триггеры в конфигурацию."""
        triggers = []
        for widgets in self._trigger_widgets:
            trigger = {
                "id": widgets["id"].text().strip(),
                "active": widgets["active"].isChecked(),
                "resp_id": widgets["resp_id"].text().strip(),
                "delay": widgets["delay"].text().strip(),
            }
            for j, edit in enumerate(widgets["data"]):
                trigger[f"data_{j}"] = edit.text().strip()
            for j, edit in enumerate(widgets["resp_data"]):
                trigger[f"resp_data_{j}"] = edit.text().strip()
            triggers.append(trigger)
        self._config.set("triggers", triggers)

    def _apply_triggers(self) -> None:
        """Активирует обработку триггеров."""
        self._save_config()
        self._build_triggers()
        self._reset_counters()
        self._active = True
        logger.info("Триггеры CAN применены: %d активных", sum(1 for t in self._triggers if t["active"]))
        QMessageBox.information(self, "Триггеры", "Триггеры применены и активны")

    def _stop_triggers(self) -> None:
        """Останавливает обработку триггеров."""
        self._active = False
        self._reset_counters()
        logger.info("Обработка триггеров CAN остановлена")
        QMessageBox.information(self, "Триггеры", "Обработка триггеров остановлена")

    def _reset_counters(self) -> None:
        """Сбрасывает счётчики срабатываний всех триггеров."""
        self._trigger_counters = [0] * TRIGGER_COUNT
        for widgets in self._trigger_widgets:
            widgets["counter"].setText("Сраб.: 0")

    def _build_triggers(self) -> None:
        """Собирает внутренний список активных триггеров."""
        self._triggers = []
        for widgets in self._trigger_widgets:
            if not widgets["active"].isChecked():
                continue
            can_id = hex_to_int(widgets["id"].text())
            if can_id is None:
                continue
            data = parse_data_bytes([edit.text() for edit in widgets["data"]])
            resp_id = hex_to_int(widgets["resp_id"].text())
            if resp_id is None:
                resp_id = can_id
            resp_data = parse_data_bytes([edit.text() for edit in widgets["resp_data"]])
            try:
                delay_ms = int(widgets["delay"].text().strip() or "0")
            except ValueError:
                delay_ms = 0
            self._triggers.append(
                {
                    "index": i,
                    "id": can_id,
                    "data": data,
                    "resp_id": resp_id,
                    "resp_data": resp_data,
                    "delay": max(0, delay_ms),
                }
            )

    def _test_trigger(self, index: int) -> None:
        """Отправляет тестовый ответный пакет для указанного триггера."""
        widgets = self._trigger_widgets[index]
        resp_id = hex_to_int(widgets["resp_id"].text())
        if resp_id is None:
            resp_id = 0x123
        resp_data = parse_data_bytes([edit.text() for edit in widgets["resp_data"]])
        try:
            delay_ms = int(widgets["delay"].text().strip() or "0")
        except ValueError:
            delay_ms = 0
        frame = pack_can_frame(0x01, resp_id, bytes(resp_data))
        if delay_ms > 0:
            QTimer.singleShot(delay_ms, lambda rf=frame: self._send_trigger_response(rf))
        else:
            self._send_trigger_response(frame)
        logger.info("Тестовый триггер %d отправлен: ID=0x%s (задержка %d мс)", index + 1, int_to_hex(resp_id, 8), delay_ms)

    def process_frame(self, frame: Dict[str, object]) -> None:
        """Проверяет входящий кадр на совпадение с активными триггерами.

        Args:
            frame: Распакованный CAN-кадр {'channel', 'id', 'data'}.
        """
        if not self._active:
            return
        if not self._triggers:
            return

        frame_id = int(frame["id"])
        frame_data = bytes(frame["data"])

        for trigger in self._triggers:
            if trigger["id"] != frame_id:
                continue
            if trigger["data"]:
                if len(frame_data) < len(trigger["data"]):
                    continue
                if not all(frame_data[i] == trigger["data"][i] for i in range(len(trigger["data"]))):
                    continue
            idx = trigger["index"]
            self._trigger_counters[idx] += 1
            self._trigger_widgets[idx]["counter"].setText(f"Сраб.: {self._trigger_counters[idx]}")
            resp_frame = pack_can_frame(
                int(frame["channel"]),
                trigger["resp_id"],
                bytes(trigger["resp_data"]),
            )
            delay_ms = trigger.get("delay", 0)
            if delay_ms > 0:
                QTimer.singleShot(delay_ms, lambda rf=resp_frame: self._send_trigger_response(rf))
            else:
                self._send_trigger_response(resp_frame)
            logger.info(
                "Сработал триггер: ID=0x%s -> ответ ID=0x%s в канал %s (задержка %d мс)",
                int_to_hex(frame_id, 8),
                int_to_hex(trigger["resp_id"], 8),
                frame["channel"],
                delay_ms,
            )

    def _send_trigger_response(self, resp_frame: bytes) -> None:
        """Отправляет подготовленный ответный кадр."""
        self._serial_manager.send_data(resp_frame)

    def get_config(self) -> List[Dict[str, object]]:
        """Возвращает текущие настройки триггеров для экспорта."""
        self._save_config()
        return self._config.get("triggers", [])

    def set_config(self, triggers: List[Dict[str, object]]) -> None:
        """Загружает настройки триггеров из импортированного профиля."""
        self._config.set("triggers", triggers)
        self._load_config()

    def create_trigger_from_packet(self, packet: Dict[str, object]) -> None:
        """Заполняет первый свободный триггер данными из пакета и активирует его.

        Args:
            packet: Словарь с ключами 'id' (строка HEX) и 'data' (список строк HEX).
        """
        for i, widgets in enumerate(self._trigger_widgets):
            if widgets["active"].isChecked():
                continue
            widgets["id"].setText(packet.get("id", ""))
            for j, edit in enumerate(widgets["data"]):
                values = packet.get("data", [])
                edit.setText(values[j] if j < len(values) else "")
            widgets["active"].setChecked(True)
            logger.info("Создан триггер %d из пакета мониторинга", i + 1)
            break
        self._save_config()

    def _save_triggers_to_file(self) -> None:
        """Сохраняет только набор триггеров в JSON-файл."""
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить триггеры",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(self.get_config(), ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info("Триггеры сохранены в %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка сохранения триггеров: %s", exc)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить триггеры: {exc}")

    def _load_triggers_from_file(self) -> None:
        """Загружает набор триггеров из JSON-файла."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить триггеры",
            "",
            "JSON files (*.json)",
        )
        if not path:
            return
        try:
            triggers = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(triggers, list):
                raise ValueError("Файл должен содержать список триггеров")
            self.set_config(triggers)
            logger.info("Триггеры загружены из %s", path)
        except Exception as exc:  # noqa: BLE001
            logger.error("Ошибка загрузки триггеров: %s", exc)
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить триггеры: {exc}")
