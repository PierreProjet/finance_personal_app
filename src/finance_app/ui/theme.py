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

    return "\n".join(
        [
            (
                f"QWidget {{ background: {background}; color: {text}; "
                f"font-family: 'Segoe UI'; font-size: {font_size}; }}"
            ),
            f"QFrame#Sidebar {{ background: {sidebar}; border-right: 1px solid {border}; }}",
            (
                f"QFrame#Card {{ background: {surface}; border: 1px solid {border}; "
                "border-radius: 14px; }}"
            ),
            f"QFrame#Drawer {{ background: {surface}; border-left: 1px solid {border}; }}",
            "QLabel#Title { font-size: 27px; font-weight: 700; }",
            f"QLabel#CardValue {{ font-size: 25px; font-weight: 700; color: {accent}; }}",
            f"QLabel#Muted {{ color: {muted}; }}",
            (
                f"QPushButton {{ background: {button}; border: 1px solid {border}; "
                "border-radius: 9px; padding: 9px 13px; text-align: left; }}"
            ),
            f"QPushButton:hover {{ border-color: {accent}; }}",
            (
                f"QPushButton#Primary {{ background: {accent}; color: white; border: none; "
                "font-weight: 600; text-align: center; }}"
            ),
            "QPushButton#Nav { padding: 11px 14px; border: none; }",
            f"QPushButton#Nav:checked {{ background: {accent}; color: white; }}",
            (
                "QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit { "
                f"background: {input_bg}; border: 1px solid {border}; "
                "border-radius: 8px; padding: 8px; }"
            ),
            (
                f"QTableWidget {{ background: {surface}; border: 1px solid {border}; "
                f"border-radius: 10px; gridline-color: {border}; }}"
            ),
            (
                f"QHeaderView::section {{ background: {sidebar}; padding: 8px; "
                f"border: none; color: {muted}; }}"
            ),
            (
                f"QProgressBar {{ background: {button}; border: none; "
                "border-radius: 6px; text-align: center; }}"
            ),
            f"QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}",
            "QCheckBox { spacing: 8px; }",
        ]
    )
