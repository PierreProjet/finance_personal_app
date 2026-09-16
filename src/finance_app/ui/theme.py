from __future__ import annotations


def stylesheet(accent: str) -> str:
    return f"""
    QWidget {{
        background: #0F1117;
        color: #F2F4F8;
        font-family: 'Segoe UI';
        font-size: 14px;
    }}
    QFrame#Sidebar {{ background: #151822; border-right: 1px solid #242838; }}
    QFrame#Card {{ background: #171B26; border: 1px solid #262B3A; border-radius: 14px; }}
    QLabel#Title {{ font-size: 27px; font-weight: 700; }}
    QLabel#CardValue {{ font-size: 25px; font-weight: 700; color: {accent}; }}
    QLabel#Muted {{ color: #9BA4B5; }}
    QPushButton {{
        background: #202534;
        border: 1px solid #30364A;
        border-radius: 9px;
        padding: 9px 13px;
        text-align: left;
    }}
    QPushButton:hover {{ border-color: {accent}; }}
    QPushButton#Primary {{
        background: {accent};
        color: white;
        border: none;
        font-weight: 600;
        text-align: center;
    }}
    QLineEdit, QComboBox, QDoubleSpinBox, QDateEdit {{
        background: #121620;
        border: 1px solid #30364A;
        border-radius: 8px;
        padding: 8px;
    }}
    QTableWidget {{
        background: #151923;
        border: 1px solid #262B3A;
        border-radius: 10px;
        gridline-color: #242A39;
    }}
    QHeaderView::section {{
        background: #1D2230;
        padding: 8px;
        border: none;
        color: #AEB6C5;
    }}
    QProgressBar {{
        background: #202534;
        border: none;
        border-radius: 6px;
        text-align: center;
    }}
    QProgressBar::chunk {{ background: {accent}; border-radius: 6px; }}
    """
