from PySide6 import QtCore, QtGui, QtWidgets
from src.main_window import MainWindow
import json, sys

if __name__ == '__main__':
    fp = None if len(sys.argv) == 1 else sys.argv[1]
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = MainWindow(fp)
    mainWindow.show()
    sys.exit(app.exec())
