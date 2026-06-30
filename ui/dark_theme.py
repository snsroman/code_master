"""Применение единой тёмной темы ко всем виджетам PySide6.

Функция apply_dark_theme() устанавливает палитру и глобальную таблицу стилей,
чтобы все окна приложения выглядели одинаково на macOS и Windows.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


def apply_light_theme(app: QApplication) -> None:
    """Применяет светлую тему к приложению.

    Args:
        app: Экземпляр QApplication.
    """
    font = QFont("Segoe UI", 10)
    if not QFont(font).exactMatch():
        font = QFont("sans-serif", 10)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F0F0F0"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#E0E0E0"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0078D7"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow, QDialog, QWidget {
            background-color: #FFFFFF;
            color: #000000;
        }
        QLineEdit, QComboBox, QSpinBox, QTableWidget, QTableView {
            background-color: #FFFFFF;
            color: #000000;
            border: 1px solid #AAAAAA;
            border-radius: 6px;
            padding: 4px;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #0078D7;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox QAbstractItemView {
            background-color: #FFFFFF;
            color: #000000;
            selection-background-color: #0078D7;
        }
        QPushButton {
            background-color: #E0E0E0;
            color: #000000;
            border: none;
            border-radius: 17px;
            padding: 6px 14px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #D0D0D0;
        }
        QPushButton:pressed {
            background-color: #BBBBBB;
        }
        QPushButton:disabled {
            background-color: #F0F0F0;
            color: #888888;
        }
        QTableWidget {
            gridline-color: #CCCCCC;
        }
        QTableWidget::item {
            background-color: #FFFFFF;
        }
        QHeaderView::section {
            background-color: #E0E0E0;
            color: #000000;
            border: 1px solid #CCCCCC;
            padding: 4px;
        }
        QScrollBar:vertical {
            background: #F0F0F0;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #AAAAAA;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #0078D7;
        }
        QScrollBar:horizontal {
            background: #F0F0F0;
            height: 12px;
        }
        QScrollBar::handle:horizontal {
            background: #AAAAAA;
            border-radius: 6px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #0078D7;
        }
        QTabWidget::pane {
            border: 1px solid #AAAAAA;
            background-color: #FFFFFF;
        }
        QTabBar::tab {
            background: #E0E0E0;
            color: #000000;
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:selected {
            background: #0078D7;
            color: #FFFFFF;
        }
        QTabBar::tab:hover {
            background: #D0D0D0;
        }
        QGroupBox {
            border: 1px solid #AAAAAA;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QProgressBar {
            background-color: #FFFFFF;
            border: 1px solid #AAAAAA;
            border-radius: 6px;
            text-align: center;
            color: #000000;
        }
        QProgressBar::chunk {
            background-color: #0078D7;
            border-radius: 6px;
        }
        QLabel {
            color: #000000;
        }
        QCheckBox {
            color: #000000;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        """
    )


def apply_dark_theme(app: QApplication) -> None:
    """Применяет тёмную тему к приложению.

    Args:
        app: Экземпляр QApplication.
    """
    # Шрифт: Segoe UI на Windows, системный sans-serif на Mac и Linux
    font = QFont("Segoe UI", 10)
    if not QFont(font).exactMatch():
        font = QFont("sans-serif", 10)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#2B2B2B"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2B2B2B"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#1E1E1E"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#1A1A1A"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#FFFFFF"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#4A6A8A"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    app.setStyleSheet(
        """
        QMainWindow, QDialog, QWidget {
            background-color: #2B2B2B;
            color: #FFFFFF;
        }
        QLineEdit, QComboBox, QSpinBox, QTableWidget, QTableView {
            background-color: #1E1E1E;
            color: #FFFFFF;
            border: 1px solid #444444;
            border-radius: 6px;
            padding: 4px;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #4A6A8A;
        }
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        QComboBox QAbstractItemView {
            background-color: #1E1E1E;
            color: #FFFFFF;
            selection-background-color: #4A6A8A;
        }
        QPushButton {
            background-color: #1A1A1A;
            color: #FFFFFF;
            border: none;
            border-radius: 17px;
            padding: 6px 14px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #333333;
        }
        QPushButton:pressed {
            background-color: #4D4D4D;
        }
        QPushButton:disabled {
            background-color: #333333;
            color: #888888;
        }
        QTableWidget {
            gridline-color: #333333;
        }
        QTableWidget::item {
            background-color: #1E1E1E;
        }
        QHeaderView::section {
            background-color: #1A1A1A;
            color: #FFFFFF;
            border: 1px solid #333333;
            padding: 4px;
        }
        QScrollBar:vertical {
            background: #1E1E1E;
            width: 12px;
        }
        QScrollBar::handle:vertical {
            background: #444444;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4A6A8A;
        }
        QScrollBar:horizontal {
            background: #1E1E1E;
            height: 12px;
        }
        QScrollBar::handle:horizontal {
            background: #444444;
            border-radius: 6px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: #4A6A8A;
        }
        QTabWidget::pane {
            border: 1px solid #444444;
            background-color: #2B2B2B;
        }
        QTabBar::tab {
            background: #1A1A1A;
            color: #FFFFFF;
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }
        QTabBar::tab:selected {
            background: #4A6A8A;
        }
        QTabBar::tab:hover {
            background: #333333;
        }
        QGroupBox {
            border: 1px solid #444444;
            border-radius: 8px;
            margin-top: 10px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }
        QProgressBar {
            background-color: #1E1E1E;
            border: 1px solid #444444;
            border-radius: 6px;
            text-align: center;
            color: #FFFFFF;
        }
        QProgressBar::chunk {
            background-color: #4A6A8A;
            border-radius: 6px;
        }
        QLabel {
            color: #FFFFFF;
        }
        QCheckBox {
            color: #FFFFFF;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
        }
        """
    )
