from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import *

from src.extract_dialog import ExtractDialog
from src.spritemap_editor import SpritemapEditorWidget
from src.extract_export import extract_generic, extract_enemy, export_to_asm, export_to_png
from src.romhandler import RomHandlerParent
import base64, bz2, json, math, sys

class DataLeaf(QTreeWidgetItem):
    def __init__(self, parent, data):
        super().__init__(parent, [data['name']])

        self.datas = data

class DataTree(QTreeWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        QTreeWidget.keyPressEvent(self, event)

        # Copy
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_C:
            if self.currentItem() != None:
                item = self.currentItem()
                if item.parent() is self.parent.spritemaps or item.parent() is self.parent.ext_hitboxes or item.parent() is self.parent.ext_spritemaps:
                    QApplication.clipboard().setText(json.dumps(item.datas))
        
        # Paste
        if event.modifiers() == Qt.ControlModifier and event.key() == Qt.Key_V:
            if self.currentItem() != None:
                item = self.currentItem()
                pastedData = json.loads(QApplication.clipboard().text())
                if item is self.parent.spritemaps or item.parent() is self.parent.spritemaps:
                    item = DataLeaf(self.parent.spritemaps, pastedData)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    self.setCurrentItem(item)
                elif item is self.parent.ext_hitboxes or item.parent() is self.parent.ext_hitboxes:
                    item = DataLeaf(self.parent.ext_hitboxes, pastedData)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    self.setCurrentItem(item)
                elif item is self.parent.ext_spritemaps or item.parent() is self.parent.ext_spritemaps:
                    item = DataLeaf(self.parent.ext_spritemaps, pastedData)
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    self.setCurrentItem(item)
        
        # Delete
        if event.key() == Qt.Key_Delete:
            self.parent.deleteClicked()

class MainWindow(QMainWindow):
    def __init__(self, fp=None, parent=None):
        super().__init__(parent)

        if fp != None:
            self.data = json.load(open(fp, 'r'))
            self.updateOldData()
        else:
            self.data = data = {
                'game': 'sm',
                'name': 'NewProject',
                'gfx': '',
                'palette': [0]*16,
                'gfx_offset': 0,
                'palette_offset': 0,
                'spritemaps': [],
                'ext_hitboxes': [],
                'ext_spritemaps': []
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

        self.dataTree.currentItemChanged.connect(self.selectItem)
        self.dataTree.itemChanged.connect(self.renameItem)

    @Slot()
    def openExtractDialog(self):
        self.extractDialog.exec()

    @Slot()
    def extractDialogAccepted(self):
        rom = RomHandlerParent(self.extractDialog.romInput.text())

        def int_or_none(text):
            return None if text == '' else int(text, 16)

        match self.extractDialog.tabWidget.currentIndex():
            case 0:
                enemy_id = int(self.extractDialog.enemyIDInput.text(), 16)
                spritemap_start = int(self.extractDialog.enemySpritemapStartInput.text(), 16)
                spritemap_end = int_or_none(self.extractDialog.enemySpritemapEndInput.text())
                ext_hitbox_start = int_or_none(self.extractDialog.enemyExtHitboxStartInput.text())
                ext_hitbox_end = int_or_none(self.extractDialog.enemyExtHitboxEndInput.text())
                ext_spritemap_start = int_or_none(self.extractDialog.enemyExtSpritemapStartInput.text())
                ext_spritemap_end = int_or_none(self.extractDialog.enemyExtSpritemapEndInput.text())
                name = self.extractDialog.enemyNameInput.text()

                self.data = extract_enemy(rom, enemy_id, (spritemap_start, spritemap_end), (ext_hitbox_start, ext_hitbox_end), (ext_spritemap_start, ext_spritemap_end), name)
            case 1:
                gfx_addr = int(self.extractDialog.genericGFXAddrInput.text(), 16)
                gfx_size = self.extractDialog.genericGFXSizeInput.value()
                gfx_offset = self.extractDialog.genericGFXOffsetInput.value()
                compressed_gfx = self.extractDialog.genericCompressedGFXCheckBox.checkState() == Qt.Checked
                pal_addr = int(self.extractDialog.genericPalAddrInput.text(), 16)
                pal_count = self.extractDialog.genericPalCountInput.value()
                pal_offset = self.extractDialog.genericPalOffsetInput.value()
                spritemap_start = int(self.extractDialog.genericSpritemapStartInput.text(), 16)
                spritemap_end = int_or_none(self.extractDialog.genericSpritemapEndInput.text())
                ext_hitbox_start = int_or_none(self.extractDialog.genericExtHitboxStartInput.text())
                ext_hitbox_end = int_or_none(self.extractDialog.genericExtHitboxEndInput.text())
                ext_spritemap_start = int_or_none(self.extractDialog.genericExtSpritemapStartInput.text())
                ext_spritemap_end = int_or_none(self.extractDialog.genericExtSpritemapEndInput.text())
                name = self.extractDialog.genericNameInput.text()

                self.data = extract_generic(rom, gfx_addr, gfx_size, gfx_offset, pal_addr, pal_count, pal_offset, (spritemap_start, spritemap_end), (ext_hitbox_start, ext_hitbox_end), (ext_spritemap_start, ext_spritemap_end), name, compressed_gfx)

        self.updateDataTree()
        self.stackedWidget.setCurrentIndex(0)
        self.spritemapEditor.loadData(self.data)

    @Slot()
    def openFile(self):
        fileName = QFileDialog.getOpenFileName(self, filter='JSON files (*.json)')[0]
        if fileName != '':
            self.data = json.load(open(fileName, 'r'))
            self.updateOldData()
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

    def updateOldData(self):
        ''' Update data from previous versions'''

        if 'extended_hitboxes' in self.data:
            del self.data['extended_hitboxes']
            self.data['ext_hitboxes'] = []
        if 'extended_spritemaps' in self.data:
            del self.data['extended_spritemaps']
            self.data['ext_spritemaps'] = []

    def updateData(self):
        self.data['spritemaps'] = []
        for i in range(self.spritemaps.childCount()):
            self.data['spritemaps'].append(self.spritemaps.child(i).datas)

    def updateDataTree(self):
        self.initialized = False

        self.dataTree.clear()
        self.dataGroup = QTreeWidgetItem(self.dataTree, [self.data['name']])
        self.dataGroup.setExpanded(True)
        self.dataGroup.setFlags(self.dataGroup.flags() | Qt.ItemIsEditable) # make it renamable

        self.spritemaps = QTreeWidgetItem(self.dataGroup, ['Spritemaps'])
        self.spritemaps.setExpanded(True)
        for spritemap in self.data['spritemaps']:
            item = DataLeaf(self.spritemaps, spritemap)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

        self.ext_hitboxes = QTreeWidgetItem(self.dataGroup, ['Extended hitboxes'])
        self.ext_hitboxes.setExpanded(True)
        for hitbox in self.data['ext_hitboxes']:
            item = DataLeaf(self.ext_hitboxes, hitbox)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

        self.ext_spritemaps = QTreeWidgetItem(self.dataGroup, ['Extended spritemaps'])
        self.ext_spritemaps.setExpanded(True)
        for spritemap in self.data['ext_spritemaps']:
            item = DataLeaf(self.ext_spritemaps, spritemap)
            item.setFlags(item.flags() | Qt.ItemIsEditable)

        self.initialized = True

    @Slot()
    def selectItem(self):
        if self.dataTree.currentItem() != None:
            if self.dataTree.currentItem().parent() is self.spritemaps:
                self.stackedWidget.setCurrentIndex(1)
                self.spritemapEditor.updateSpritemapChanged(self.dataTree.currentItem().datas)
            else:
                self.stackedWidget.setCurrentIndex(0)

    @Slot(QTreeWidgetItem, int)
    def renameItem(self, item, column):
        if self.initialized and column == 0:
            if item is self.dataGroup:
                self.data['name'] = item.text(0)
            elif item.parent() is self.spritemaps:
                for h in self.data['ext_hitboxes']:
                    if h['spritemap'] == item.datas['name']:
                        h['spritemap'] = item.text(0)
                for e in self.data['ext_spritemaps']:
                    for s in e['ext_spritemap']:
                        if s['spritemap'] == item.datas['name']:
                            s['spritemap'] = item.text(0)
                item.datas['name'] = item.text(0)

    @Slot()
    def newClicked(self):
        if self.dataTree.currentItem() != None:
            if self.dataTree.currentItem() is self.spritemaps or self.dataTree.currentItem().parent() is self.spritemaps:
                data = {
                    'name': 'NewSpritemap',
                    'spritemap': []
                }
                item = DataLeaf(self.spritemaps, data)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.dataTree.setCurrentItem(item)
            elif self.dataTree.currentItem() is self.ext_hitboxes or self.dataTree.currentItem().parent() is self.ext_hitboxes:
                data = {
                    'name': 'NewHitbox',
                    'spritemap': None,
                    'hitbox': []
                }
                item = DataLeaf(self.ext_hitboxes, data)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.dataTree.setCurrentItem(item)
            elif self.dataTree.currentItem() is self.ext_spritemaps or self.dataTree.currentItem().parent() is self.ext_spritemaps:
                data = {
                    'name': 'NewExtSpritemap',
                    'ext_spritemap': []
                }
                item = DataLeaf(self.ext_spritemaps, data)
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.dataTree.setCurrentItem(item)

    @Slot()
    def deleteClicked(self):
        if self.dataTree.currentItem() != None:
            item = self.dataTree.currentItem()
            if item.parent() is self.spritemaps:
                for h in self.data['ext_hitboxes']:
                    if h['spritemap'] == item.datas['name']:
                        h['spritemap'] = None
                for e in self.data['ext_spritemaps']:
                    for s in e['ext_spritemap']:
                        if s['spritemap'] == item.datas['name']:
                            s['spritemap'] = None
                item.parent().removeChild(item)
            elif item.parent() is self.ext_hitboxes or item.parent() is self.ext_spritemaps:
                item.parent().removeChild(item)

    @Slot()
    def moveUpClicked(self):
        if self.dataTree.currentItem() != None:
            item = self.dataTree.currentItem()
            parent = item.parent()
            if parent is self.spritemaps or parent is self.ext_hitboxes or parent is self.ext_spritemaps:
                index = parent.indexOfChild(item)
                if index > 0:
                    parent.removeChild(item)
                    parent.insertChild(index-1, item)
                    self.dataTree.setCurrentItem(item)

    @Slot()
    def moveDownClicked(self):
        if self.dataTree.currentItem() != None:
            item = self.dataTree.currentItem()
            parent = item.parent()
            if parent is self.spritemaps or parent is self.ext_hitboxes or parent is self.ext_spritemaps:
                index = parent.indexOfChild(item)
                if index < parent.childCount()-1:
                    parent.removeChild(item)
                    parent.insertChild(index+1, item)
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
