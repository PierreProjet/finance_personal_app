from __future__ import annotations


def stylesheet(accent: str, theme: str = "dark", compact: bool = False) -> str:
    """Build the application stylesheet from explicit user preferences."""
    dark = theme != "light"
    background = "#0F1117" if dark else "#F5F7FB"
    surface = "#171B26" if dark else "#FFFFFF"
    sidebar = "#151822" if dark else "#E9EDF5"
    input_bg = "#121620" if dark else "#FFFFFF"
    text = "#F2F4F8" if dark else "#18202E"
    muted = "#9BA4B5" if dark else "#667085"
    border = "#262B3A" if dark else "#D8DEE9"
    button = "#202534" if dark else "#FFFFFF"
    font_size = "13px" if compact else "14px"
    return f"""
    QWidget {{ background: {background}; color: {text}; font-family: 'Segoe UI'; font-size: {font_size}; }}
    QFrame#Sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}
    QFrame#Card {{ background: {surface}; border: 1px solid {border}; border-radius: 14px; }}
    QFrame#Drawer {{ background: {surface}; border-left: 1px solid {border}; }}
    QLabel#Title {{ font-size: 27px; font-weight: 700; }}
    QLabel#CardValue {{ font-size: 25px; font-weight: 700; color: {accent}; }}
    QLabel#Muted {{ color: {muted}; }}
    QPushButton {{ background: {button}; border: 1px solid {border}; border-radius: 9px; padding: 9px 13px; text-align: left; }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton#Primary {{ background: {accent}; color: white; border: none; font-weight: 600; text-align: center; }}
    QPushButton#Nav {{ padding: 11px 14px; border: none; }}
    QPushButton#Nav:checked {{ background: {accent}; color: white; }}
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {{ background: {input_bg}; border: 1px solid {border}; border-radius: 8px; padding: 8px; }}
    QTableWidget {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; gridline-color: {border}; }}
    QHeaderView::section {{ background: {sidebar}; padding: 8px; border: none; color: {muted}; }}
    QProgressBar {{ background: {button}; border: none; border-radius: 6px; text-align: center; }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}
    QCheckBox {{ spacing: 8px; }}
    """
