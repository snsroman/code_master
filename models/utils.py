"""Вспомогательные функции для приложения «Код Мастер»."""

import re
from typing import List, Optional


def hex_to_int(text: str) -> Optional[int]:
    """Преобразует строку с HEX-значением в целое число.

    Args:
        text: Строка, например «1A», «0x1A» или «1a».

    Returns:
        Целое число или None, если строка пустая или некорректная.
    """
    if not text:
        return None
    cleaned = text.strip().replace("0x", "").replace("0X", "")
    if not cleaned:
        return None
    try:
        return int(cleaned, 16)
    except ValueError:
        return None


def int_to_hex(value: int, width: int = 2) -> str:
    """Форматирует целое число в HEX-строку заданной длины.

    Args:
        value: Целое число.
        width: Минимальное количество символов (по умолчанию 2).

    Returns:
        HEX-строка в верхнем регистре, например «1A».
    """
    return f"{value:0{width}X}"


def parse_data_bytes(fields: List[str]) -> List[int]:
    """Преобразует список строковых HEX-полей в список байт.

    Пустые строки игнорируются.

    Args:
        fields: Список строк с HEX-значениями байт.

    Returns:
        Список целых чисел от 0 до 255.
    """
    result: List[int] = []
    for field in fields:
        value = hex_to_int(field)
        if value is not None:
            result.append(value & 0xFF)
    return result


def format_data_bytes(data: bytes) -> List[str]:
    """Преобразует байты в список HEX-строк.

    Args:
        data: Байтовая строка длиной до 8 байт.

    Returns:
        Список строк, например ['1A', '2B', '00'].
    """
    return [int_to_hex(b) for b in data]


def hex_string_to_bytes(text: str) -> bytes:
    """Преобразует строку из HEX-символов в байты.

    Пробелы и префикс 0x игнорируются.

    Args:
        text: Строка, например «DE AD BE EF».

    Returns:
        Байтовая строка.
    """
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", text)
    if len(cleaned) % 2 != 0:
        cleaned = "0" + cleaned
    return bytes.fromhex(cleaned)


def bytes_to_hex_string(data: bytes) -> str:
    """Преобразует байты в строку HEX с пробелами.

    Args:
        data: Байтовая строка.

    Returns:
        Строка, например «DE AD BE EF».
    """
    return " ".join(f"{b:02X}" for b in data)
