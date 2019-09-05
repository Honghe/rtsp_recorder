# -*- coding: utf-8 -*-
import sys

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QCompleter
from fbs_runtime.application_context.PyQt5 import ApplicationContext


def get_data(model):
    model.setStringList(["completion", "data", "goes", "here"])


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        uic.loadUi('main.ui', self)
        self.button = self.findChild(QtWidgets.QPushButton, 'pushButton')
        self.button.clicked.connect(self.playButtonPressed)

        self.input = self.findChild(QtWidgets.QLineEdit, 'lineEdit')

        completer = QCompleter()
        self.input.setCompleter(completer)

        model = QStringListModel()
        completer.setModel(model)
        get_data(model)

        self.show()

    def playButtonPressed(self):
        print('play text: {}'.format(self.input.text()))


if __name__ == '__main__':
    appctxt = ApplicationContext()  # 1. Instantiate ApplicationContext
    window = Ui()
    exit_code = appctxt.app.exec_()  # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)
