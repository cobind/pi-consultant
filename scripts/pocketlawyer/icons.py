from PyQt6.QtCore import QByteArray, Qt
from PyQt6.QtGui import QIcon, QImage, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer

_LINE = {
    "ask": '<path d="M4 5h16v11H9l-5 4z"/>',
    "search": '<circle cx="11" cy="11" r="6"/><path d="M16 16l5 5"/>',
    "library": '<path d="M5 4v16M10 4v16M15 5l4 15"/><path d="M3 20h13"/>',
    "settings": '<path d="M4 7h10M18 7h2M4 17h2M10 17h10"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="17" r="2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "refresh": '<path d="M20 11a8 8 0 1 0-2 6"/><path d="M20 4v7h-7"/>',
    "trash": '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>',
}

LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <rect width="128" height="128" rx="26" fill="#12151c"/>
  <rect x="6" y="6" width="116" height="116" rx="22" fill="none" stroke="#4f8cff" stroke-width="4"/>
  <path d="M64 24v72M40 96h48M64 36L34 44M64 36l30 8" stroke="#e6e9ef" stroke-width="6" stroke-linecap="round" fill="none"/>
  <path d="M34 44L20 74h28zM94 44L80 74h28z" fill="#4f8cff"/>
  <path d="M20 74a14 8 0 0 0 28 0M80 74a14 8 0 0 0 28 0" fill="none" stroke="#e6e9ef" stroke-width="5" stroke-linecap="round"/>
</svg>"""


def _render(svg, size):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(0)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(p)
    p.end()
    return QPixmap.fromImage(img)


def line_pixmap(name, color, size=20):
    scale = 2
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{_LINE[name]}</svg>')
    pm = _render(svg, size * scale)
    pm.setDevicePixelRatio(scale)
    return pm


def nav_icon(name, muted, active, size=20):
    icon = QIcon()
    icon.addPixmap(line_pixmap(name, muted, size), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(line_pixmap(name, active, size), QIcon.Mode.Normal, QIcon.State.On)
    return icon


def button_icon(name, color, size=18):
    return QIcon(line_pixmap(name, color, size))


def logo_pixmap(size=96):
    pm = _render(LOGO_SVG, size * 2)
    pm.setDevicePixelRatio(2)
    return pm


def app_icon():
    icon = QIcon()
    for s in (16, 32, 48, 64, 128, 256):
        icon.addPixmap(_render(LOGO_SVG, s))
    return icon
