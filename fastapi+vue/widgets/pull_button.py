from PyQt5.QtWidgets import QPushButton
from PyQt5.QtCore import Qt, pyqtSignal


class PullButton(QPushButton):
    pulling = pyqtSignal(float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_pos = None

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:
            self.pulling.emit((e.x() - self.start_pos) / 500)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.x()

    def mouseReleaseEvent(self, event):
        if (self.start_pos is not None and
                event.button() == Qt.LeftButton and
                event.pos() in self.rect()):
            self.clicked.emit()
        self.start_pos = None
