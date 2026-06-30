"""Эмулятор COM-порта для отладки интерфейса без реального STM32.

FakeSerial имитирует интерфейс pyserial.Serial: генерация случайных CAN-кадров,
ответы на команды бутлоадера и стандартные методы read/write/close.
"""

import random
import threading
import time
from typing import Optional

from core.can_protocol import MARKER_RX, MARKER_RX_EXT, MARKER_TX, MARKER_TX_EXT, pack_can_frame, xor_checksum
from models.logger import get_logger

logger = get_logger(__name__)


class FakeSerial:
    """Фиктивный COM-порт для тестирования приложения на macOS и Windows."""

    def __init__(self, port: str = "FAKE", baudrate: int = 115200, error_probability: int = 0) -> None:
        """Создаёт эмулятор порта.

        Args:
            port: Имя порта (только для отображения).
            baudrate: Скорость обмена (только для отображения).
            error_probability: Вероятность симуляции ошибки CAN (0-100).
        """
        self.port = port
        self.baudrate = baudrate
        self._error_probability = max(0, min(100, error_probability))
        self._is_open = False
        self._rx_buffer = bytearray()
        self._buffer_lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._bootloader_mode = False
        self._last_address = 0

    def _schedule_frame(self) -> None:
        """Добавляет в буфер случайный CAN-кадр и планирует следующий."""
        if not self._is_open:
            return

        channel = random.choice([0x01, 0x02])
        # 25% пакетов с Extended CAN-ID
        if random.random() < 0.25:
            can_id = random.randint(0x800, 0x1FFFFFFF)
        else:
            can_id = random.randint(0x000, 0x7FF)
        length = random.randint(1, 8)
        data = bytes(random.randint(0, 255) for _ in range(length))
        # В эмуляторе используем маркер приёма
        frame = self._swap_marker(pack_can_frame(channel, can_id, data))

        # Симуляция ошибки CAN: портится контрольная сумма
        if random.randint(1, 100) <= self._error_probability:
            frame = self._corrupt_frame(frame)
            logger.info("Симулирована ошибка CAN в канале %d", channel)

        with self._buffer_lock:
            self._rx_buffer.extend(frame)

        self._timer = threading.Timer(random.uniform(0.05, 0.3), self._schedule_frame)
        self._timer.daemon = True
        self._timer.start()

    @staticmethod
    def _swap_marker(frame: bytes) -> bytes:
        """Меняет маркер отправки на маркер приёма."""
        return bytes([MARKER_RX_EXT if b == MARKER_TX_EXT else (MARKER_RX if b == MARKER_TX else b) for b in frame])

    @staticmethod
    def _corrupt_frame(frame: bytes) -> bytes:
        """Портит контрольную сумму кадра для имитации ошибки шины."""
        if len(frame) < 2:
            return frame
        frame = bytearray(frame)
        frame[-1] ^= 0xFF
        return bytes(frame)

    def open(self) -> None:
        """Открывает эмулятор порта и запускает генерацию кадров."""
        self._is_open = True
        self._schedule_frame()

    def close(self) -> None:
        """Закрывает эмулятор и останавливает таймер."""
        self._is_open = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def is_open(self) -> bool:
        """Возвращает True, если эмулятор активен."""
        return self._is_open

    def read(self, size: int = 1) -> bytes:
        """Читает указанное количество байт из буфера.

        Args:
            size: Сколько байт нужно прочитать.

        Returns:
            Байтовая строка, возможно меньше запрошенного размера.
        """
        with self._buffer_lock:
            chunk = self._rx_buffer[:size]
            self._rx_buffer = self._rx_buffer[size:]
        return bytes(chunk)

    def in_waiting(self) -> int:
        """Возвращает количество байт, готовых к чтению."""
        with self._buffer_lock:
            return len(self._rx_buffer)

    def write(self, data: bytes) -> int:
        """Записывает данные в эмулятор и формирует ответ.

        Для бутлоадера эмулирует ACK (0x79) и ответы на команды.
        Для CAN-кадров ничего не возвращает.

        Args:
            data: Байты, отправленные в порт.

        Returns:
            Количество записанных байт.
        """
        if not data:
            return 0

        # Базовая эмуляция бутлоадера STM32
        if data[0] == 0x7F:
            self._bootloader_mode = True
            self._append_response(bytes([0x79]))
            return len(data)

        if not self._bootloader_mode:
            return len(data)

        command = data[0]
        if command == 0x00:  # Get
            self._append_response(bytes([0x79, 0x01, 0x00, 0x79]))
        elif command == 0x11:  # Read Memory
            self._append_response(bytes([0x79]))
        elif command == 0x21:  # Go
            self._append_response(bytes([0x79]))
        elif command == 0x31:  # Write Memory
            self._append_response(bytes([0x79]))
        elif command == 0x43:  # Erase
            self._append_response(bytes([0x79]))
        elif command == 0x44:  # Extended Erase
            self._append_response(bytes([0x79]))
        elif command == 0xFF:  # Mass erase
            self._append_response(bytes([0x79]))

        return len(data)

    def _append_response(self, response: bytes) -> None:
        """Добавляет ответ в приёмный буфер."""
        with self._buffer_lock:
            self._rx_buffer.extend(response)

    def flush(self) -> None:
        """Пустая заглушка для совместимости с pyserial."""

    def reset_input_buffer(self) -> None:
        """Очищает приёмный буфер."""
        with self._buffer_lock:
            self._rx_buffer.clear()
