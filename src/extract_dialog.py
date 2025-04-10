from PySide6 import QtCore, QtGui, QtWidgets

class ExtractDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.romInput = QtWidgets.QLineEdit(self)
        romButton = QtWidgets.QPushButton(self)
        romButton.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.DocumentOpen))
        romButton.clicked.connect(self.romButtonClicked)
        romRow = QtWidgets.QHBoxLayout()
        romRow.addWidget(self.romInput)
        romRow.addWidget(romButton)

        self.enemyIDInput = QtWidgets.QLineEdit('0xCEBF', self)
        self.enemySpritemapStartInput = QtWidgets.QLineEdit('0xA288DA', self)
        self.enemySpritemapEndInput = QtWidgets.QLineEdit(self)
        self.enemyNameInput = QtWidgets.QLineEdit('Boyon', self)

        self.genericGFXAddrInput = QtWidgets.QLineEdit(self)
        self.genericGFXSizeInput = QtWidgets.QSpinBox(self)
        self.genericGFXSizeInput.setRange(1, 0x200)
        self.genericGFXSizeInput.setDisplayIntegerBase(16)
        self.genericGFXOffsetInput = QtWidgets.QSpinBox(self)
        self.genericGFXOffsetInput.setRange(0, 0x1FF)
        self.genericGFXOffsetInput.setDisplayIntegerBase(16)
        self.genericCompressedGFXCheckBox = QtWidgets.QCheckBox(self)
        self.genericPalAddrInput = QtWidgets.QLineEdit(self)
        self.genericPalCountInput = QtWidgets.QSpinBox(self)
        self.genericPalCountInput.setRange(1, 8)
        self.genericPalOffsetInput = QtWidgets.QSpinBox(self)
        self.genericPalOffsetInput.setRange(0, 7)
        self.genericSpritemapStartInput = QtWidgets.QLineEdit(self)
        self.genericSpritemapEndInput = QtWidgets.QLineEdit(self)
        self.genericNameInput = QtWidgets.QLineEdit(self)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        enemyForm = QtWidgets.QFormLayout(self)
        enemyForm.addRow('Enemy ID', self.enemyIDInput)
        enemyForm.addRow('Spritemaps start', self.enemySpritemapStartInput)
        enemyForm.addRow('Spritemaps end (leave it blank to autodetect)', self.enemySpritemapEndInput)
        enemyForm.addRow('Name', self.enemyNameInput)

        enemyFormWidget = QtWidgets.QWidget(self)
        enemyFormWidget.setLayout(enemyForm)

        genericForm = QtWidgets.QFormLayout(self)
        genericForm.addRow('GFX address', self.genericGFXAddrInput)
        genericForm.addRow('GFX size in tiles', self.genericGFXSizeInput)
        genericForm.addRow('GFX offset in tiles', self.genericGFXOffsetInput)
        genericForm.addRow('Compressed GFX (ignore size)', self.genericCompressedGFXCheckBox)
        genericForm.addRow('Palettes address', self.genericPalAddrInput)
        genericForm.addRow('Palette count', self.genericPalCountInput)
        genericForm.addRow('Palettes offset', self.genericPalOffsetInput)
        genericForm.addRow('Spritemaps start', self.genericSpritemapStartInput)
        genericForm.addRow('Spritemaps end (leave it blank to autodetect)', self.genericSpritemapEndInput)
        genericForm.addRow('Name', self.genericNameInput)

        genericFormWidget = QtWidgets.QWidget(self)
        genericFormWidget.setLayout(genericForm)

        self.tabWidget = QtWidgets.QTabWidget()
        self.tabWidget.addTab(enemyFormWidget, 'Enemy')
        self.tabWidget.addTab(genericFormWidget, 'Generic')

        formLayout = QtWidgets.QFormLayout(self)
        formLayout.addRow('ROM', romRow)
        formLayout.addRow(self.tabWidget)
        formLayout.addRow(buttonBox)

    def romButtonClicked(self):
        fileName = QtWidgets.QFileDialog.getOpenFileName(self, filter='SNES ROM files (*.sfc *.smc)')[0]
        self.romInput.setText(fileName)
