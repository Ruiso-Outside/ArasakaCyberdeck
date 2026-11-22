"""
ARASAKA CYBERDECK // janela: barra de busca flutuante (abre e fecha pelo atalho de teclado).

Cada vez que o atalho e apertado, um processo novo abre. Se ja houver um aberto, ele recebe "toggle" pelo
socket local e fecha; o novo sai na hora. Assim a janela sempre ganha o foco (inclusive no Wayland).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QFileInfo, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygonF, QShortcut
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QFileIconProvider, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QVBoxLayout, QWidget)

from . import core
from .core import APP_NAME, VERSION, Item
from .kit import FONTS, FG, MUTED, RED, load_fonts, logo_pixmap, stylesheet

SOCK = f"arasaka-cyberdeck-{os.getuid() if hasattr(os, 'getuid') else 'u'}"
KIND_TXT = {"APP": "APP", "JOGO": "JOGO", "VM": "VM", "MODULO": "MÓDULO", "PASTA": "PASTA", "ACAO": "AÇÃO", "CALC": "CÁLCULO"}

QSS = """
QWidget#deck { background: transparent; }
QLineEdit#q { background: transparent; border: none; color: #ececf0; font-size: 24px; padding: 6px 4px; selection-background-color: #e3121f; }
QListWidget#res { background: transparent; border: none; outline: none; }
QListWidget#res::item { border: none; padding: 0; margin: 0; }
QListWidget#res::item:selected { background: transparent; }
"""


class Row(QWidget):
    def __init__(self, it: Item, n: int):
        super().__init__()
        self.it, self.n, self.sel = it, n, False
        self.setFixedHeight(54)
        self.pm = icon_pixmap(it, 30)

    def set_sel(self, on: bool):
        self.sel = on
        self.update()

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        if self.sel:
            p.fillRect(0, 2, w, h - 4, QColor(227, 18, 31, 46))
            p.fillRect(0, 2, 3, h - 4, RED)
        if self.pm:
            p.drawPixmap(16, (h - 30) // 2, self.pm)
        else:
            p.setPen(QPen(RED, 1))
            p.drawRect(16, (h - 30) // 2, 30, 30)
        f = QFont(FONTS["ui"])
        f.setPixelSize(16)
        f.setBold(self.sel)
        p.setFont(f)
        p.setPen(FG)
        p.drawText(QRectF(60, 7, w - 220, 22), Qt.AlignLeft | Qt.AlignVCenter, self.it.title)
        f.setPixelSize(12)
        f.setBold(False)
        p.setFont(f)
        p.setPen(MUTED)
        p.drawText(QRectF(60, 28, w - 220, 18), Qt.AlignLeft | Qt.AlignVCenter, self.it.subtitle)
        fm = QFont(FONTS["mono"])
        fm.setPixelSize(11)
        fm.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(fm)
        p.setPen(RED if self.sel else QColor(110, 110, 120))
        p.drawText(QRectF(w - 150, 0, 92, h), Qt.AlignRight | Qt.AlignVCenter, KIND_TXT.get(self.it.kind, self.it.kind))
        if self.n <= 9:
            p.setPen(QColor(80, 80, 90))
            p.drawText(QRectF(w - 50, 0, 36, h), Qt.AlignRight | Qt.AlignVCenter, f"^{self.n}")


def icon_pixmap(it: Item, size: int) -> QPixmap | None:
    if not it.icon:
        return None
    if core.WIN and os.path.isabs(it.icon) and it.icon.lower().endswith((".lnk", ".url", ".exe")):
        # Windows: o icone que o Explorer mostra para o atalho (o .lnk em si nao e uma imagem)
        ic = QFileIconProvider().icon(QFileInfo(it.icon))
        return None if ic.isNull() else ic.pixmap(QSize(size, size))
    ic = QIcon(it.icon) if os.path.isabs(it.icon) else QIcon.fromTheme(it.icon)
    if ic.isNull() and not os.path.isabs(it.icon):
        for base in (core.HOME / ".local/share/icons/hicolor", Path("/usr/share/icons/hicolor"), Path("/usr/share/pixmaps")):
            for cand in list(base.glob(f"*/apps/{it.icon}.png"))[:1] + list(base.glob(f"{it.icon}.png"))[:1] + list(base.glob(f"*/apps/{it.icon}.svg"))[:1]:
                ic = QIcon(str(cand))
                break
            if not ic.isNull():
                break
    if ic.isNull():
        return None
    return ic.pixmap(QSize(size, size))


class Deck(QWidget):
    W = 760

    def __init__(self, index: core.Index):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.index = index
        self.setObjectName("deck")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(APP_NAME)
        self.setFixedWidth(self.W)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 18, 22, 16)
        lay.setSpacing(8)
        top = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(logo_pixmap(30))
        top.addWidget(logo)
        self.q = QLineEdit()
        self.q.setObjectName("q")
        self.q.setPlaceholderText("Abrir app, jogo, VM, módulo, pasta... ou fazer uma conta")
        self.q.textChanged.connect(self.update_results)
        self.q.installEventFilter(self)
        top.addWidget(self.q, 1)
        lay.addLayout(top)
        self.list = QListWidget()
        self.list.setObjectName("res")
        self.list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(lambda it: self.activate(self.list.row(it)))
        lay.addWidget(self.list)
        self.hint = QLabel()
        self.hint.setStyleSheet("color:#55555e; font-size:11px; letter-spacing:2px;")
        lay.addWidget(self.hint)
        self.results: list[Item] = []
        self.sel = 0
        for i in range(1, 10):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, activated=lambda n=i: self.activate(n - 1))
        QShortcut(QKeySequence("Esc"), self, activated=self.close)
        self.update_results("")

    # -------------------------------------------------------- desenho (painel HUD com cantos cortados)
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h, c = self.width() - 1, self.height() - 1, 18
        poly = QPolygonF([QPointF(c, 0.5), QPointF(w, 0.5), QPointF(w, h - c), QPointF(w - c, h), QPointF(0.5, h), QPointF(0.5, c)])
        p.setBrush(QColor(7, 7, 9, 246))
        p.setPen(QPen(QColor(90, 10, 16), 1))
        p.drawPolygon(poly)
        p.setPen(QPen(RED, 2))
        p.drawLine(QPointF(c, 1), QPointF(c + 60, 1))
        p.drawLine(QPointF(w - c, h - 1), QPointF(w - c - 60, h - 1))
        p.setPen(QPen(QColor(42, 10, 13), 1))
        p.drawLine(22, 66, w - 22, 66)

    def eventFilter(self, obj, ev):
        if obj is self.q and ev.type() == QEvent.KeyPress:
            k = ev.key()
            if k in (Qt.Key_Down, Qt.Key_Tab):
                self.move_sel(1)
                return True
            if k in (Qt.Key_Up, Qt.Key_Backtab):
                self.move_sel(-1)
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.activate(self.sel)
                return True
        return super().eventFilter(obj, ev)

    def changeEvent(self, ev):
        # clicou fora: fecha (como um menu)
        if ev.type() == QEvent.ActivationChange and not self.isActiveWindow() and self.isVisible() and not getattr(self, "_asking", False):
            QTimer.singleShot(120, lambda: (not self.isActiveWindow() and not getattr(self, "_asking", False)) and self.close())
        super().changeEvent(ev)

    def update_results(self, text: str):
        self.results = self.index.search(text, 8)
        self.list.clear()
        for i, it in enumerate(self.results):
            li = QListWidgetItem()
            li.setSizeHint(QSize(self.W - 44, 54))
            self.list.addItem(li)
            self.list.setItemWidget(li, Row(it, i + 1))
        self.sel = 0
        self.paint_sel()
        n = len(self.results)
        self.list.setFixedHeight(max(n, 1) * 54 if n else 0)
        if not text.strip():
            self.hint.setText("MAIS USADOS" if n else f"CYBERDECK v{VERSION}  ·  DIGITE PARA BUSCAR  ·  ESC FECHA")
        elif not n:
            self.hint.setText("NADA ENCONTRADO")
        else:
            self.hint.setText("ENTER ABRE  ·  ↑↓ ESCOLHE  ·  CTRL+1..9 ATALHO  ·  ESC FECHA")
        self.adjustSize()

    def move_sel(self, d: int):
        if self.results:
            self.sel = (self.sel + d) % len(self.results)
            self.paint_sel()

    def paint_sel(self):
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if w:
                w.set_sel(i == self.sel)

    def activate(self, i: int):
        if not (0 <= i < len(self.results)):
            return
        it = self.results[i]
        if it.kind == "CALC":
            QGuiApplication.clipboard().setText(it.title)
            self.hint.setText(f"COPIADO: {it.title}")
            QTimer.singleShot(700, self.close)
            return
        if it.confirm:
            self._asking = True
            ok = QMessageBox.question(self, APP_NAME, it.confirm) == QMessageBox.Yes
            self._asking = False
            if not ok:
                return
        err = core.launch(it)
        if err:
            self.hint.setText("ERRO: " + err.upper())
            return
        self.index.used(it.key)
        self.close()

    def show_centered(self):
        scr = QGuiApplication.screenAt(QGuiApplication.primaryScreen().geometry().center()) or QGuiApplication.primaryScreen()
        g = scr.availableGeometry()
        self.adjustSize()
        self.move(g.x() + (g.width() - self.W) // 2, g.y() + int(g.height() * 0.22))
        self.show()
        self.raise_()
        self.activateWindow()
        self.q.setFocus()


def main(argv: list[str] | None = None):
    argv = list(sys.argv if argv is None else argv)
    QApplication.setApplicationName(core.APP_ID)
    QApplication.setDesktopFileName(core.APP_ID)
    app = QApplication(argv)
    shot = next((a.split("=", 1)[1] for a in argv if a.startswith("--screenshot=")), None)
    if not shot:
        # ja tem um aberto? pede para ele fechar (toggle) e sai
        s = QLocalSocket()
        s.connectToServer(SOCK)
        if s.waitForConnected(150):
            s.write(b"toggle")
            s.flush()
            s.waitForBytesWritten(200)
            return 0
    load_fonts()
    app.setStyleSheet(stylesheet() + QSS)
    app.setWindowIcon(QIcon(str(core.ASSETS / "arasaka-cyberdeck.svg")))
    deck = Deck(core.Index())
    server = QLocalServer()
    if not shot:
        QLocalServer.removeServer(SOCK)
        server.listen(SOCK)
        server.newConnection.connect(lambda: (server.nextPendingConnection(), deck.close()))
    app.setQuitOnLastWindowClosed(True)
    if shot:
        path, _, q = shot.partition(",")
        deck.q.setText(q)
        deck.show_centered()
        QTimer.singleShot(900, lambda: (deck.grab().save(path), app.quit()))
    else:
        deck.show_centered()
    return app.exec()
