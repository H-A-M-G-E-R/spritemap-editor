from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import *

from src.extract_dialog import ExtractDialog
from src.spritemap_editor import SpritemapEditorWidget
from src.extract_export import extract_generic, extract_enemy, export_to_asm, export_to_png
from src.romhandler import RomHandlerParent
import base64, bz2, json, math, sys

class SpritemapTreeItem(QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent, [data['name']])

        self.spritemapData = data

class DataTree(QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        QTreeWidget.keyPressEvent(self, event)

        # Copy
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            if self.currentItem() != None:
                if isinstance(self.currentItem(), SpritemapTreeItem):
                    QApplication.clipboard().setText(json.dumps(self.currentItem().spritemapData))
        
        # Paste
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            pastedData = json.loads(QApplication.clipboard().text())
            if self.currentItem() is self.parent.spritemaps or isinstance(self.currentItem(), SpritemapTreeItem):
                item = SpritemapTreeItem(self.parent.spritemaps, pastedData)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.setCurrentItem(item)
        
        # Delete
        if event.key() == Qt.Key_Delete:
            if self.currentItem() != None:
                if isinstance(self.currentItem(), SpritemapTreeItem):
                    self.parent.spritemaps.removeChild(self.currentItem())

class MainWindow(QMainWindow):
    def __init__(self, fp=None, parent=None):
        super().__init__(parent)

        if fp != None:
            self.data = json.load(open(fp, 'r'))
        else:
            self.data = data = {
                'game': 'sm',
                'name': 'NewProject',
                'gfx': '',
                'palette': [0]*16,
                'gfx_offset': 0,
                'palette_offset': 0,
                'spritemaps': [],
                'extended_hitboxes': None,
                'extended_spritemaps': None
            }

        newButton = QPushButton('New')
        newButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.ListAdd))
        newButton.clicked.connect(self.newClicked)

        deleteButton = QPushButton('Delete')
        deleteButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.ListRemove))
        deleteButton.clicked.connect(self.deleteClicked)

        moveUpButton = QPushButton('Move up')
        moveUpButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoUp))
        moveUpButton.clicked.connect(self.moveUpClicked)

        moveDownButton = QPushButton('Move down')
        moveDownButton.setIcon(QIcon.fromTheme(QIcon.ThemeIcon.GoDown))
        moveDownButton.clicked.connect(self.moveDownClicked)

        editDataRow = QHBoxLayout()
        editDataRow.addWidget(newButton)
        editDataRow.addWidget(deleteButton)
        editDataRow.addWidget(moveUpButton)
        editDataRow.addWidget(moveDownButton)

        self.dataTree = DataTree(self)
        self.dataTree.setHeaderLabel('Data')
        self.updateDataTree()

        fileMenu = QMenu('File')
        extractAction = fileMenu.addAction('Import from ROM...')
        extractAction.triggered.connect(self.openExtractDialog)
        self.extractDialog = ExtractDialog(self)
        self.extractDialog.accepted.connect(self.extractDialogAccepted)

        openFileAction = fileMenu.addAction('Open...')
        openFileAction.setShortcut('Ctrl+O')
        openFileAction.triggered.connect(self.openFile)
        fileMenu.addSeparator()
        saveFileAction = fileMenu.addAction('Save...')
        saveFileAction.setShortcut('Ctrl+S')
        saveFileAction.triggered.connect(self.saveFile)
        saveAsFileAction = fileMenu.addAction('Save as...')
        saveAsFileAction.setShortcut('Ctrl+Shift+S')
        saveAsFileAction.triggered.connect(self.saveFileAs)
        fileMenu.addSeparator()
        exportASMAction = fileMenu.addAction('Export ASM...')
        exportASMAction.triggered.connect(self.exportASM)
        exportPNGAction = fileMenu.addAction('Export PNG...')
        exportPNGAction.triggered.connect(self.exportPNG)
        fileMenu.addSeparator()
        exitAction = fileMenu.addAction('Exit')
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)

        self.fileNameToSave = fp

        editMenu = QMenu('Edit')
        hFlipAction = editMenu.addAction('Flip horizontal')
        hFlipAction.setShortcut('Shift+H')
        hFlipAction.triggered.connect(self.hFlipTriggered)
        vFlipAction = editMenu.addAction('Flip vertical')
        vFlipAction.setShortcut('Shift+V')
        vFlipAction.triggered.connect(self.vFlipTriggered)

        self.menuBar = self.menuBar()
        self.menuBar.addMenu(fileMenu)
        self.menuBar.addMenu(editMenu)

        left = QVBoxLayout()
        left.addLayout(editDataRow)
        left.addWidget(self.dataTree)

        leftWidget = QWidget()
        leftWidget.setLayout(left)

        dataTreeDock = QDockWidget()
        dataTreeDock.setWidget(leftWidget)
        dataTreeDock.setAllowedAreas(Qt.LeftDockWidgetArea)
        dataTreeDock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.LeftDockWidgetArea, dataTreeDock)

        self.spritemapEditor = SpritemapEditorWidget(self, self.data)

        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(QWidget()) # dummy
        self.stackedWidget.addWidget(self.spritemapEditor)

        stackedWidgetDock = QDockWidget()
        stackedWidgetDock.setWidget(self.stackedWidget)
        stackedWidgetDock.setAllowedAreas(Qt.RightDockWidgetArea)
        stackedWidgetDock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, stackedWidgetDock)

        self.dataTree.itemSelectionChanged.connect(self.selectItem)
        self.dataTree.itemChanged.connect(self.renameItem)

    @Slot()
    def openExtractDialog(self):
        self.extractDialog.exec()

    @Slot()
    def extractDialogAccepted(self):
        rom = RomHandlerParent(self.extractDialog.romInput.text())
        match self.extractDialog.tabWidget.currentIndex():
            case 0:
                enemy_id = int(self.extractDialog.enemyIDInput.text(), 16)
                spritemap_start = int(self.extractDialog.enemySpritemapStartInput.text(), 16)
                if self.extractDialog.enemySpritemapEndInput.text() == '':
                    spritemap_end = None
                else:
                    spritemap_end = int(self.extractDialog.enemySpritemapEndInput.text(), 16)
                name = self.extractDialog.enemyNameInput.text()

                self.data = extract_enemy(rom, enemy_id, spritemap_start, name, spritemap_end)
            case 1:
                gfx_addr = int(self.extractDialog.genericGFXAddrInput.text(), 16)
                gfx_size = self.extractDialog.genericGFXSizeInput.value()
                gfx_offset = self.extractDialog.genericGFXOffsetInput.value()
                compressed_gfx = self.extractDialog.genericCompressedGFXCheckBox.checkState() == Qt.Checked
                pal_addr = int(self.extractDialog.genericPalAddrInput.text(), 16)
                pal_count = self.extractDialog.genericPalCountInput.value()
                pal_offset = self.extractDialog.genericPalOffsetInput.value()
                spritemap_start = int(self.extractDialog.genericSpritemapStartInput.text(), 16)
                if self.extractDialog.genericSpritemapEndInput.text() == '':
                    spritemap_end = None
                else:
                    spritemap_end = int(self.extractDialog.genericSpritemapEndInput.text(), 16)
                name = self.extractDialog.genericNameInput.text()

                self.data = extract_generic(rom, gfx_addr, gfx_size, gfx_offset, pal_addr, pal_count, pal_offset, spritemap_start, name, spritemap_end, compressed_gfx)

        self.updateDataTree()
        self.stackedWidget.setCurrentIndex(0)
        self.spritemapEditor.loadData(self.data)

    @Slot()
    def openFile(self):
        fileName = QFileDialog.getOpenFileName(self, filter='JSON files (*.json)')[0]
        if fileName != '':
            self.data = json.load(open(fileName, 'r'))
            self.updateDataTree()
            self.stackedWidget.setCurrentIndex(0)
            self.spritemapEditor.loadData(self.data)
            self.fileNameToSave = fileName

    @Slot()
    def saveFile(self):
        if self.fileNameToSave == None:
            self.saveFileAs()
        else:
            self.updateData()
            json.dump(self.data, open(self.fileNameToSave, 'w'), indent=1)

    @Slot()
    def saveFileAs(self):
        fp = self.fileNameToSave if self.fileNameToSave != None else self.data['name']+'.json'
        fileName = QFileDialog.getSaveFileName(self, dir=fp, filter='JSON files (*.json)')[0]
        if fileName != '':
            self.updateData()
            json.dump(self.data, open(fileName, 'w'), indent=1)
            self.fileNameToSave = fileName

    @Slot()
    def exportASM(self):
        directory = QFileDialog.getExistingDirectory(self, 'Select folder to put GFX, PAL and ASM files in')
        if directory != '':
            self.updateData()
            export_to_asm(self.data, directory)

    @Slot()
    def exportPNG(self):
        directory = QFileDialog.getExistingDirectory(self, 'Select folder to put PNG files in')
        if directory != '':
            self.updateData()
            export_to_png(self.data, directory)

    def updateData(self):
        self.data['spritemaps'] = []
        for i in range(self.spritemaps.childCount()):
            self.data['spritemaps'].append(self.spritemaps.child(i).spritemapData)

    def updateDataTree(self):
        self.dataTree.clear()
        self.dataGroup = QTreeWidgetItem(self.dataTree, [self.data['name']])
        self.dataGroup.setExpanded(True)
        self.dataGroup.setFlags(self.dataGroup.flags() | Qt.ItemIsEditable) # make it renamable

        self.spritemaps = QTreeWidgetItem(self.dataGroup, ['Spritemaps'])
        self.spritemaps.setExpanded(True)
        for spritemap in self.data['spritemaps']:
            item = SpritemapTreeItem(self.spritemaps, spritemap)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

    @Slot()
    def selectItem(self):
        if isinstance(self.dataTree.currentItem(), SpritemapTreeItem):
            self.stackedWidget.setCurrentIndex(1)
            self.spritemapEditor.updateSpritemapChanged(self.dataTree.currentItem().spritemapData)
        else:
            self.stackedWidget.setCurrentIndex(0)

    @Slot(QTreeWidgetItem, int)
    def renameItem(self, item, column):
        if column == 0:
            if item is self.dataGroup:
                self.data['name'] = item.text(0)
            elif isinstance(item, SpritemapTreeItem):
                item.spritemapData['name'] = item.text(0)

    @Slot()
    def newClicked(self):
        if self.dataTree.currentItem() is self.spritemaps or isinstance(self.dataTree.currentItem(), SpritemapTreeItem):
            data = {
                'name': 'New spritemap',
                'spritemap': []
            }
            item = SpritemapTreeItem(self.spritemaps, data)
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.dataTree.setCurrentItem(item)

    @Slot()
    def deleteClicked(self):
        if isinstance(self.dataTree.currentItem(), SpritemapTreeItem):
            self.spritemaps.removeChild(self.dataTree.currentItem())

    @Slot()
    def moveUpClicked(self):
        if isinstance(self.dataTree.currentItem(), SpritemapTreeItem):
            item = self.dataTree.currentItem()
            index = self.spritemaps.indexOfChild(item)
            if index > 0:
                self.spritemaps.removeChild(item)
                self.spritemaps.insertChild(index-1, item)
                self.dataTree.setCurrentItem(item)

    @Slot()
    def moveDownClicked(self):
        if isinstance(self.dataTree.currentItem(), SpritemapTreeItem):
            item = self.dataTree.currentItem()
            index = self.spritemaps.indexOfChild(item)
            if index < self.spritemaps.childCount()-1:
                self.spritemaps.removeChild(item)
                self.spritemaps.insertChild(index+1, item)
                self.dataTree.setCurrentItem(item)

    @Slot()
    def hFlipTriggered(self):
        match self.stackedWidget.currentIndex():
            case 1:
                self.spritemapEditor.hFlip()

    @Slot()
    def vFlipTriggered(self):
        match self.stackedWidget.currentIndex():
            case 1:
                self.spritemapEditor.vFlip()
