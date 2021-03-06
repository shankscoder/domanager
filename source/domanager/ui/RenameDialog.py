from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtCore import Qt

from domanager.resources import rPath

class RenameDialog(QtWidgets.QDialog):
    def __init__(self, oldName, parent=None):
        super(RenameDialog, self).__init__(parent)
        self.setWindowIcon(self._icon("rename.png"))
        self.setWindowTitle("Rename %s" % oldName)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)

        self._okButton = QtWidgets.QPushButton("OK")
        self._cancelButton = QtWidgets.QPushButton("Cancel")

        self._buttonsLayout = QtWidgets.QHBoxLayout()
        self._buttonsLayout.setContentsMargins(0, 0, 0, 0)
        self._buttonsLayout.addWidget(QtWidgets.QWidget(self), 1)
        self._buttonsLayout.addWidget(self._okButton)
        self._buttonsLayout.addWidget(self._cancelButton)

        self._nameBox = QtWidgets.QLineEdit(self)
        self._nameBox.setText(oldName)
        validator = QtGui.QRegExpValidator(QtCore.QRegExp("[ -~]*"), self._nameBox)
        self._nameBox.setValidator(validator)

        self._layout.addWidget(self._nameBox)
        self._layout.addLayout(self._buttonsLayout)

        self._cancelButton.clicked.connect(self.close)
        self._okButton.clicked.connect(self._onOK)

        self._nameBox.setFocus()
        self._nameBox.selectAll()

        self.result = None

        self.resize(250, 10)

    def _onOK(self):
        name = self._nameBox.text()
        if len(name.replace(' ', '')) > 0:
            self.result = name
            self.close()
        else:
            self._nameBox.setFocus()

    def _icon(self, filename):
        return QtGui.QIcon(rPath(filename))