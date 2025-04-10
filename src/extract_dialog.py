from PySide6 import QtWidgets
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import *

class ExtractDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.romInput = QLineEdit(self)
        romButton = QPushButton(self)
        romButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.DocumentOpen))
        romButton.clicked.connect(self.romButtonClicked)
        romRow = QHBoxLayout()
        romRow.addWidget(self.romInput)
        romRow.addWidget(romButton)

        self.enemyIDInput = QLineEdit('0xCEBF', self)
        self.enemySpritemapStartInput = QLineEdit('0xA288DA', self)
        self.enemySpritemapEndInput = QLineEdit(self)
        self.enemyNameInput = QLineEdit('Boyon', self)

        self.genericGFXAddrInput = QLineEdit(self)
        self.genericGFXSizeInput = QSpinBox(self)
        self.genericGFXSizeInput.setRange(1, 0x200)
        self.genericGFXSizeInput.setDisplayIntegerBase(16)
        self.genericGFXOffsetInput = QSpinBox(self)
        self.genericGFXOffsetInput.setRange(0, 0x1FF)
        self.genericGFXOffsetInput.setDisplayIntegerBase(16)
        self.genericCompressedGFXCheckBox = QCheckBox(self)
        self.genericPalAddrInput = QLineEdit(self)
        self.genericPalCountInput = QSpinBox(self)
        self.genericPalCountInput.setRange(1, 8)
        self.genericPalOffsetInput = QSpinBox(self)
        self.genericPalOffsetInput.setRange(0, 7)
        self.genericSpritemapStartInput = QLineEdit(self)
        self.genericSpritemapEndInput = QLineEdit(self)
        self.genericNameInput = QLineEdit(self)

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        enemyForm = QFormLayout(self)
        enemyForm.addRow('Enemy ID', self.enemyIDInput)
        enemyForm.addRow('Spritemaps start', self.enemySpritemapStartInput)
        enemyForm.addRow('Spritemaps end (leave it blank to autodetect)', self.enemySpritemapEndInput)
        enemyForm.addRow('Name', self.enemyNameInput)

        enemyFormWidget = QWidget(self)
        enemyFormWidget.setLayout(enemyForm)

        genericForm = QFormLayout(self)
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

        genericFormWidget = QWidget(self)
        genericFormWidget.setLayout(genericForm)

        self.tabWidget = QTabWidget()
        self.tabWidget.addTab(enemyFormWidget, 'Enemy')
        self.tabWidget.addTab(genericFormWidget, 'Generic')

        formLayout = QFormLayout(self)
        formLayout.addRow('ROM', romRow)
        formLayout.addRow(self.tabWidget)
        formLayout.addRow(buttonBox)

    def romButtonClicked(self):
        fileName = QFileDialog.getOpenFileName(self, filter='SNES ROM files (*.sfc *.smc)')[0]
        self.romInput.setText(fileName)
