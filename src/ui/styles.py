"""Centralized QSS style constants and stylesheet for CNAB PIX application.

Colors follow 60/30/10 rule per UI-SPEC Color section.
Spacing follows multiples-of-4 scale per UI-SPEC Spacing Scale section.
"""
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPen, QColor, QPainterPath
from PySide6.QtCore import Qt, QRectF, QPointF

# Colors per UI-SPEC Color section
COLOR_BG = "#F5F5F5"           # Dominant 60% — dialog/window background
COLOR_PANEL = "#FFFFFF"        # Secondary 30% — form panels, inputs, table bg
COLOR_ACCENT = "#1565C0"       # Accent 10% — primary action buttons only
COLOR_DESTRUCTIVE = "#C62828"  # Destructive — deactivate button, error text
COLOR_ACTIVE = "#2E7D32"       # Active user badge
COLOR_INACTIVE = "#616161"     # Inactive user badge
COLOR_BORDER = "#BDBDBD"       # Input/table borders

# Spacing per UI-SPEC Spacing Scale section (multiples of 4)
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 16
SPACING_LG = 24
SPACING_XL = 32
SPACING_2XL = 48


def get_app_stylesheet() -> str:
    """Return the application-wide QSS stylesheet.

    Styles:
    - QDialog, QMainWindow: COLOR_BG background
    - QGroupBox: COLOR_PANEL interior, COLOR_BORDER border
    - QLineEdit: COLOR_BORDER border, COLOR_PANEL background
    - QPushButton#primary: COLOR_ACCENT background, white text, 32px min-height
    - QPushButton#destructive: COLOR_DESTRUCTIVE text, transparent background
    - QTableWidget: COLOR_PANEL background
    """
    return f"""
    QDialog, QMainWindow {{
        background-color: {COLOR_BG};
    }}
    QWidget {{
        background-color: {COLOR_BG};
        color: #212121;
        font-size: 13px;
    }}
    QGroupBox {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 8px;
        font-size: 13px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 4px;
        left: 8px;
    }}
    QLineEdit {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 24px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLOR_ACCENT};
    }}
    QComboBox {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 4px 8px;
        min-height: 24px;
        font-size: 13px;
    }}
    QComboBox:focus {{
        border: 1px solid {COLOR_ACCENT};
    }}
    QPushButton {{
        border: 1px solid {COLOR_BORDER};
        border-radius: 3px;
        padding: 4px 12px;
        min-height: 32px;
        font-size: 13px;
        background-color: {COLOR_PANEL};
    }}
    QPushButton:hover {{
        background-color: #E8E8E8;
    }}
    QPushButton#primary {{
        background-color: {COLOR_ACCENT};
        color: white;
        border: none;
        min-height: 32px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton#primary:hover {{
        background-color: #1976D2;
    }}
    QPushButton#primary:disabled {{
        background-color: #90CAF9;
        color: #E3F2FD;
    }}
    QPushButton#destructive {{
        color: {COLOR_DESTRUCTIVE};
        background-color: transparent;
        border: none;
        font-size: 13px;
    }}
    QPushButton#destructive:hover {{
        color: #B71C1C;
        text-decoration: underline;
    }}
    QPushButton#destructive:disabled {{
        color: {COLOR_INACTIVE};
    }}
    QWidget#toolbar {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        border-radius: 4px;
    }}
    QTableWidget {{
        background-color: {COLOR_PANEL};
        border: 1px solid {COLOR_BORDER};
        gridline-color: {COLOR_BORDER};
        font-size: 13px;
    }}
    QTableWidget::item {{
        padding: 4px 8px;
        min-height: 28px;
    }}
    QTableWidget::item:selected {{
        background-color: #E3F2FD;
        color: #1A237E;
    }}
    QHeaderView::section {{
        background-color: {COLOR_BG};
        border: none;
        border-bottom: 1px solid {COLOR_BORDER};
        border-right: 1px solid {COLOR_BORDER};
        padding: 4px 8px;
        font-size: 13px;
        font-weight: bold;
    }}
    QTabWidget::pane {{
        border: 1px solid {COLOR_BORDER};
        background-color: {COLOR_PANEL};
    }}
    QTabBar::tab {{
        background-color: {COLOR_BG};
        border: 1px solid {COLOR_BORDER};
        border-bottom: none;
        padding: 6px 16px;
        margin-right: 2px;
        font-size: 13px;
    }}
    QTabBar::tab:selected {{
        background-color: {COLOR_PANEL};
        border-bottom: 1px solid {COLOR_PANEL};
    }}
    QScrollArea {{
        border: none;
        background-color: {COLOR_PANEL};
    }}
    QLabel {{
        background-color: transparent;
        color: #212121;
        font-size: 13px;
    }}
    QMessageBox {{
        background-color: {COLOR_BG};
    }}
    QPushButton#icon_action {{
        border: none;
        background-color: transparent;
        padding: 2px;
        border-radius: 3px;
    }}
    QPushButton#icon_action:hover {{
        background-color: #E0E0E0;
    }}
    QPushButton#icon_action:disabled {{
        background-color: transparent;
    }}
    """


def make_icon(draw_func, size: int = 20, color: str = "#616161") -> QIcon:
    """Create a QIcon by drawing on a QPixmap with the given function and color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    draw_func(painter, size)
    painter.end()
    return QIcon(pixmap)


def icon_edit(size: int = 20) -> QIcon:
    """Pencil icon for edit actions."""
    def draw(p: QPainter, s: int):
        m = s * 0.2  # margin
        # Pencil body (diagonal line with nib)
        p.drawLine(QPointF(s - m, m), QPointF(m + 2, s - m - 2))
        # Pencil tip
        p.drawLine(QPointF(m + 2, s - m - 2), QPointF(m, s - m))
        p.drawLine(QPointF(m, s - m), QPointF(m + 4, s - m - 1))
        # Small editing line at base
        p.drawLine(QPointF(m + 1, s - m), QPointF(s * 0.55, s - m))
    return make_icon(draw, size, COLOR_ACCENT)


def icon_deactivate(size: int = 20) -> QIcon:
    """X icon for deactivate actions."""
    def draw(p: QPainter, s: int):
        m = s * 0.25
        p.drawLine(QPointF(m, m), QPointF(s - m, s - m))
        p.drawLine(QPointF(s - m, m), QPointF(m, s - m))
    return make_icon(draw, size, COLOR_DESTRUCTIVE)


def icon_reactivate(size: int = 20) -> QIcon:
    """Checkmark icon for reactivate actions."""
    def draw(p: QPainter, s: int):
        m = s * 0.2
        p.drawLine(QPointF(m, s * 0.5), QPointF(s * 0.4, s - m))
        p.drawLine(QPointF(s * 0.4, s - m), QPointF(s - m, m))
    return make_icon(draw, size, COLOR_ACTIVE)
