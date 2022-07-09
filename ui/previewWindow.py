import sys
import os

from PySide6 import QtCore, QtWidgets, QtGui


class PrevieWindow(QtWidgets.QWidget):
    """
    This "window" is a QWidget. If it has no parent, it
    will appear as a free-floating window as we want.
    """
    def __init__(self, file_name: str):
        super().__init__()
        self.file_name = file_name
        self.initUi()

    def initUi(self):
        self.setMinimumSize(640, 480)
        self.setWindowTitle(self.file_name)

        layout = QtWidgets.QVBoxLayout()
        self.memo = QtWidgets.QTextBrowser()
        layout.addWidget(self.memo)
        self.setLayout(layout)

        self.messegeErr = QtWidgets.QErrorMessage()