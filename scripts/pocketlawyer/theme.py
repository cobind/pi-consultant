
PALETTES = {
    "dark": dict(BG="#12151c", PANEL="#181c25", CARD="#1f2430", BORDER="#2b3140",
                 TEXT="#e6e9ef", MUTED="#8b93a7", ACCENT="#4f8cff", ACCENT_HI="#6ba0ff",
                 OK="#3ecf8e", WARN="#f5a524", ERR="#f56565", SEL="#2b3140"),
    "light": dict(BG="#f4f6fb", PANEL="#ffffff", CARD="#ffffff", BORDER="#dde2ee",
                  TEXT="#1b2030", MUTED="#667089", ACCENT="#2f6df6", ACCENT_HI="#1f56d6",
                  OK="#1a9d63", WARN="#c77c02", ERR="#d64545", SEL="#e8eefc"),
}
THEMES = list(PALETTES)
CURRENT = {"name": "dark"}


def colors(name):
    return PALETTES.get(name, PALETTES["dark"])


def current():
    return colors(CURRENT["name"])


def style(name="dark"):
    CURRENT["name"] = name
    c = colors(name)
    BG, PANEL, CARD, BORDER = c["BG"], c["PANEL"], c["CARD"], c["BORDER"]
    TEXT, MUTED, ACCENT, ACCENT_HI, ERR, SEL = c["TEXT"], c["MUTED"], c["ACCENT"], c["ACCENT_HI"], c["ERR"], c["SEL"]
    on_accent = "#ffffff"
    return f"""
* {{ font-size: 14px; color: {TEXT}; }}
QMainWindow, QDialog, QMessageBox, QWidget#root, QStackedWidget, QScrollArea, QWidget#chatHost, QWidget#page {{ background: {BG}; }}
QScrollArea {{ border: none; }}
QWidget#sidebar {{ background: {PANEL}; border-right: 1px solid {BORDER}; }}
QLabel#brand {{ font-size: 17px; font-weight: 700; }}
QLabel#brandSub, QLabel#muted {{ color: {MUTED}; font-size: 12px; }}
QLabel#h1 {{ font-size: 20px; font-weight: 700; }}
QLabel#welcomeTitle {{ font-size: 26px; font-weight: 700; }}
QLabel#welcomeSub {{ color: {MUTED}; font-size: 15px; }}
QLabel#statNum {{ font-size: 22px; font-weight: 700; color: {ACCENT_HI}; }}
QLabel#statLbl {{ color: {MUTED}; font-size: 12px; }}
QPushButton#nav {{ background: transparent; border: none; text-align: left; padding: 10px 14px;
    border-radius: 8px; color: {MUTED}; font-weight: 600; }}
QPushButton#nav:hover {{ background: {SEL}; color: {TEXT}; }}
QPushButton#nav:checked {{ background: {SEL}; color: {ACCENT_HI}; }}
QPushButton {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 14px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QPushButton#primary {{ background: {ACCENT}; border: none; color: {on_accent}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {ACCENT_HI}; }}
QPushButton#primary:disabled {{ background: {BORDER}; color: {MUTED}; }}
QPushButton#danger {{ background: transparent; border: 1px solid {ERR}; color: {ERR}; }}
QPushButton#link {{ background: transparent; border: none; color: {ACCENT_HI}; padding: 2px 0; text-align: left; }}
QLineEdit, QComboBox, QSpinBox {{ background: {CARD}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 9px 12px; selection-background-color: {ACCENT}; }}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {ACCENT}; }}
QComboBox QAbstractItemView {{ background: {CARD}; border: 1px solid {BORDER}; selection-background-color: {ACCENT}; selection-color: {on_accent}; }}
QFrame#userBubble {{ background: {ACCENT}; border-radius: 14px; }}
QFrame#userBubble QLabel {{ color: {on_accent}; }}
QFrame#aiBubble {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
QFrame#errBubble {{ background: transparent; border: 1px solid {ERR}; border-radius: 14px; }}
QFrame#card {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; }}
QFrame#stat {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#emptyBox {{ background: transparent; border: 2px dashed {BORDER}; border-radius: 14px; }}
QLabel#badge {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 9px; padding: 1px 8px;
    color: {MUTED}; font-size: 12px; }}
QLabel#badgeOk {{ background: transparent; border: 1px solid {c['OK']}; border-radius: 9px; padding: 1px 8px;
    color: {c['OK']}; font-size: 12px; }}
QLabel#badgeWarn {{ background: transparent; border: 1px solid {c['WARN']}; border-radius: 9px; padding: 1px 8px;
    color: {c['WARN']}; font-size: 12px; }}
QPlainTextEdit {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 10px; padding: 8px; }}
QProgressBar {{ background: {CARD}; border: none; border-radius: 4px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 4px; }}
QStatusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}
QStatusBar QLabel {{ color: {MUTED}; font-size: 12px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QToolTip {{ background: {CARD}; color: {TEXT}; border: 1px solid {BORDER}; }}
"""
