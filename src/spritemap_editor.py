from PySide6 import QtCore, QtGui, QtWidgets
from src.gfx import add_to_canvas_from_spritemap, to_qimage, convert_to_4bpp
import base64, json, math

class SpritePixmapItem(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, listItem, editor):
        super().__init__()
        self.editor = editor

        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)

        self.listItem = listItem
        listItem.pixmapItem = self
        self.spriteData = self.listItem.spriteData

        self.setPos(self.spriteData['x'], self.spriteData['y'])
        self.updateImage()

    def updateImage(self):
        canvas = {}
        add_to_canvas_from_spritemap(canvas, [{
            'x': 0,
            'y': 0,
            'big': self.spriteData['big'],
            'tile': self.spriteData['tile']-self.editor.data['gfx_offset'],
            'palette': 0,
            'bg_priority': self.spriteData['bg_priority'],
            'h_flip': self.spriteData['h_flip'],
            'v_flip': self.spriteData['v_flip']
        }], self.editor.tiles)
        image = to_qimage(canvas, self.editor.displayedPalettes[self.spriteData['palette']],
            0, 0, 16 if self.spriteData['big'] else 8, 16 if self.spriteData['big'] else 8)

        self.setPixmap(QtGui.QPixmap.fromImage(image))

class SpriteListItem(QtWidgets.QListWidgetItem):
    def __init__(self, text, parent, data, editor):
        super().__init__(text, parent)

        self.spriteData = data
        self.editor = editor
        self.pixmapItem = SpritePixmapItem(self, editor)
        editor.spritemapScene.addItem(self.pixmapItem)

class SpritemapScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def drawBackground(self, painter, rect):
        painter.drawLine(rect.x()-2, 0, rect.x()+rect.width()+2, 0)
        painter.drawLine(0, rect.y()-2, 0, rect.y()+rect.height()+2)

    def	mousePressEvent(self, event):
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
        if self.mouseGrabberItem() != None:
            self.parent.spriteList.setCurrentItem(self.mouseGrabberItem().listItem)

    def mouseMoveEvent(self, event):
        # Snap tiles to nearest pixel
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)
        if self.mouseGrabberItem() != None:
            for item in self.selectedItems():
                item.setPos(math.floor(item.x()+0.5), math.floor(item.y()+0.5))
                item.spriteData['x'] = int(item.x())
                item.spriteData['y'] = int(item.y())

            self.parent.updateCurrentSpriteChanged()

    def keyPressEvent(self, event):
        # Move items with arrow keys
        x = 0
        y = 0
        if event.key() == QtCore.Qt.Key_Left:
            x = -1
        if event.key() == QtCore.Qt.Key_Right:
            x = 1
        if event.key() == QtCore.Qt.Key_Up:
            y = -1
        if event.key() == QtCore.Qt.Key_Down:
            y = 1
        if event.modifiers() == QtCore.Qt.ShiftModifier:
            x *= 8
            y *= 8
        if x != 0 or y != 0:
            for item in self.selectedItems():
                item.setPos(item.x()+x, item.y()+y)
                item.spriteData['x'] = int(item.x())
                item.spriteData['y'] = int(item.y())

            self.parent.updateCurrentSpriteChanged()

        # Copy
        if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_C:
            copiedData = []
            for item in self.items(): # the copied data needs to be sorted
                if item.isSelected():
                    copiedData.append(item.spriteData)
            QtWidgets.QApplication.clipboard().setText(json.dumps(copiedData))

        # Paste
        if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_V:
            pastedData = json.loads(QtWidgets.QApplication.clipboard().text())
            if len(pastedData) > 0:
                for item in self.items():
                    item.setSelected(False)

                listSet = False
                for tile in pastedData:
                    item = SpriteListItem(str(self.parent.spriteList.count()), self.parent.spriteList, tile, self.parent)
                    item.pixmapItem.setSelected(True)
                    if not listSet:
                        self.parent.spriteList.setCurrentItem(item)
                        listSet = True

                self.parent.updateSpritePixmapItemsZValues()
                self.parent.updateData()

        # Select all
        if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_A:
            for item in self.items():
                item.setSelected(True)

        # Delete selected
        if event.key() == QtCore.Qt.Key_Delete:
            for item in self.selectedItems():
                self.removeItem(item)
                self.parent.spriteList.takeItem(self.parent.spriteList.indexFromItem(item.listItem).row())

            self.parent.updateSpritePixmapItemsZValues()
            self.parent.fixSpriteListLabels()
            self.parent.updateData()

class SpritemapView(QtWidgets.QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)

        self.zoom = 4
        self.scale(self.zoom, self.zoom)
        self.ctrlPressed = False

    def keyPressEvent(self, event):
        QtWidgets.QGraphicsView.keyPressEvent(self, event)
        self.ctrlPressed = event.modifiers() == QtCore.Qt.ControlModifier
        if self.ctrlPressed and event.key() == QtCore.Qt.Key_Equal:
            self.zoom += 1
            self.setTransform(QtGui.QTransform(self.zoom, 0, 0, self.zoom, 0, 0))
        if self.ctrlPressed and event.key() == QtCore.Qt.Key_Minus:
            if self.zoom > 1:
                self.zoom -= 1
                self.setTransform(QtGui.QTransform(self.zoom, 0, 0, self.zoom, 0, 0))

    def keyReleaseEvent(self, event):
        QtWidgets.QGraphicsView.keyReleaseEvent(self, event)
        self.ctrlPressed = event.modifiers() == QtCore.Qt.ControlModifier

    def wheelEvent(self, event):
        if self.ctrlPressed:
            self.zoom += event.angleDelta().y()//abs(event.angleDelta().y())
            if self.zoom < 1:
                self.zoom = 1
            self.setTransform(QtGui.QTransform(self.zoom, 0, 0, self.zoom, 0, 0))
        else:
            QtWidgets.QGraphicsView.wheelEvent(self, event)

class SpriteList(QtWidgets.QListWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def keyPressEvent(self, event):
        QtWidgets.QListWidget.keyPressEvent(self, event)

        # Copy
        if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_C:
            if self.currentItem() != None:
                QtWidgets.QApplication.clipboard().setText(json.dumps([self.currentItem().spriteData]))

        # Paste
        if event.modifiers() == QtCore.Qt.ControlModifier and event.key() == QtCore.Qt.Key_V:
            pastedData = json.loads(QtWidgets.QApplication.clipboard().text())
            if len(pastedData) > 0:
                for item in self.parent.spritemapScene.items():
                    item.setSelected(False)

                listSet = False
                for tile in pastedData:
                    item = SpriteListItem(str(self.count()), self, tile, self.parent)
                    item.pixmapItem.setSelected(True)
                    if not listSet:
                        self.setCurrentItem(item)
                        listSet = True

                self.parent.updateSpritePixmapItemsZValues()
                self.parent.updateData()

        # Delete
        if event.key() == QtCore.Qt.Key_Delete:
            if self.currentItem() != None:
                self.parent.spritemapScene.removeItem(self.currentItem().pixmapItem)
                self.takeItem(self.indexFromItem(self.currentItem()).row())

                self.parent.updateSpritePixmapItemsZValues()
                self.parent.fixSpriteListLabels()
                self.parent.updateData()

class TileSelectorScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.selection = QtWidgets.QGraphicsRectItem(0, 0, 8, 8)
        self.selection.setPen(QtGui.QPen(0xFFFFFF))
        self.selection.setZValue(1)
        self.selection.hide()
        self.addItem(self.selection)

    def updateCurrentSpriteChanged(self):
        if self.parent.spriteList.currentItem() != None:
            data = self.parent.spriteList.currentItem().spriteData
            tileIndex = data['tile']-self.parent.data['gfx_offset']
            tileSize = 8+8*data['big']

            self.selection.setRect(QtCore.QRectF(tileIndex%16*8, tileIndex//16*8, tileSize, tileSize))
            self.selection.show()
            self.selectionOriginX = 0
            self.selectionOriginY = 0
        else:
            self.selection.hide()

    def	mousePressEvent(self, event):
        QtWidgets.QGraphicsScene.mousePressEvent(self, event)
        if self.parent.spriteList.currentItem() != None:
            self.selectionOriginX = event.scenePos().x()
            self.selectionOriginY = event.scenePos().y()
            self.selection.setRect(QtCore.QRectF(self.selectionOriginX//8*8, self.selectionOriginY//8*8, 8, 8))
            self.selection.show()
    
    def mouseMoveEvent(self, event):
        QtWidgets.QGraphicsScene.mouseMoveEvent(self, event)
        if self.parent.spriteList.currentItem() != None:
            if event.scenePos().x() > self.selectionOriginX:
                x1 = math.floor(self.selectionOriginX/8)*8
            else:
                x1 = math.ceil(self.selectionOriginX/8)*8
            if event.scenePos().y() > self.selectionOriginY:
                y1 = math.floor(self.selectionOriginY/8)*8
            else:
                y1 = math.ceil(self.selectionOriginY/8)*8

            if event.scenePos().x() > self.selectionOriginX:
                x2 = math.ceil(event.scenePos().x()/8)*8
            else:
                x2 = math.floor(event.scenePos().x()/8)*8
            if event.scenePos().y() > self.selectionOriginY:
                y2 = math.ceil(event.scenePos().y()/8)*8
            else:
                y2 = math.floor(event.scenePos().y()/8)*8

            if abs(x1-x2) == 0:
                x2 = x1+math.copysign(8, x2-x1)
            elif abs(x1-x2) > 16:
                x2 = x1+math.copysign(16, x2-x1)

            if abs(y1-y2) == 0:
                y2 = y1+math.copysign(8, y2-y1)
            elif abs(y1-y2) > 16:
                y2 = y1+math.copysign(16, y2-y1)

            if abs(x1-x2) == 16 and abs(y1-y2) == 8:
                x2 = x1+math.copysign(8, x2-x1)
            elif abs(x1-x2) == 8 and abs(y1-y2) == 16:
                y2 = y1+math.copysign(8, y2-y1)

            self.selection.setRect(QtCore.QRectF(QtCore.QPointF(min(x1, x2), min(y1, y2)), QtCore.QPointF(max(x1, x2), max(y1, y2))))

    def mouseReleaseEvent(self, event):
        QtWidgets.QGraphicsScene.mouseReleaseEvent(self, event)
        if self.parent.spriteList.currentItem() != None:
            data = self.parent.spriteList.currentItem().spriteData
            data['tile'] = int(self.selection.rect().x()//8+self.selection.rect().y()//8*16)+self.parent.data['gfx_offset']
            data['big'] = self.selection.rect().width() == 16

            self.parent.spriteList.currentItem().pixmapItem.updateImage()

class SpritemapEditorWidget(QtWidgets.QWidget):
    def __init__(self, parent, data: dict):
        super().__init__(parent)
        self.parent = parent

        self.spritemapScene = SpritemapScene(self)
        self.spritemapScene.selectionChanged.connect(self.spritemapSceneSelectionChanged)
        self.spritemapView = SpritemapView(self.spritemapScene)
        self.spritemapView.setSceneRect(-256, -128, 512, 256)
        self.spritemapView.setDragMode(QtWidgets.QGraphicsView.RubberBandDrag)

        newSpriteButton = QtWidgets.QPushButton('New')
        newSpriteButton.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListAdd))
        newSpriteButton.clicked.connect(self.newSpriteClicked)
        deleteSpriteButton = QtWidgets.QPushButton('Delete')
        deleteSpriteButton.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.ListRemove))
        deleteSpriteButton.clicked.connect(self.deleteSpriteClicked)
        moveSpriteUpButton = QtWidgets.QPushButton('Move up')
        moveSpriteUpButton.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.GoUp))
        moveSpriteUpButton.clicked.connect(self.moveSpriteUpClicked)
        moveSpriteDownButton = QtWidgets.QPushButton('Move down')
        moveSpriteDownButton.setIcon(QtGui.QIcon.fromTheme(QtGui.QIcon.ThemeIcon.GoDown))
        moveSpriteDownButton.clicked.connect(self.moveSpriteDownClicked)

        editSpriteListRow = QtWidgets.QHBoxLayout()
        editSpriteListRow.addWidget(newSpriteButton)
        editSpriteListRow.addWidget(deleteSpriteButton)
        editSpriteListRow.addWidget(moveSpriteUpButton)
        editSpriteListRow.addWidget(moveSpriteDownButton)

        self.spriteList = SpriteList(self)
        self.spriteList.itemPressed.connect(self.spriteListSelectItem)
        self.spriteList.currentItemChanged.connect(self.updateCurrentSpriteChanged)

        self.tileSelectorScene = TileSelectorScene(self)
        self.tileSelectorView = QtWidgets.QGraphicsView(self.tileSelectorScene)
        self.tileSelectorView.setSceneRect(0, 0, 16*8, 1*8)
        self.tileSelectorView.setFixedSize(16*8*4+6, 1*8*4+6)
        self.tileSelectorView.scale(4, 4)
        self.tileSelectorImage = None
        self.tileSelectorPixmap = QtWidgets.QGraphicsPixmapItem()
        self.tileSelectorScene.addItem(self.tileSelectorPixmap)

        loadTilesButton = QtWidgets.QPushButton('Load GFX')
        loadTilesButton.clicked.connect(self.loadTilesClicked)
        saveTilesButton = QtWidgets.QPushButton('Save GFX')
        saveTilesButton.clicked.connect(self.saveTilesClicked)

        loadSaveTiles = QtWidgets.QHBoxLayout()
        loadSaveTiles.addWidget(loadTilesButton)
        loadSaveTiles.addWidget(saveTilesButton)

        self.gfxOffsetSpinBox = QtWidgets.QSpinBox(self)
        self.gfxOffsetSpinBox.setRange(0, 0x1FF)
        self.gfxOffsetSpinBox.setDisplayIntegerBase(16)
        self.gfxOffsetSpinBox.valueChanged.connect(self.gfxOffsetSpinBoxChanged)
        self.paletteOffsetSpinBox = QtWidgets.QSpinBox(self)
        self.paletteOffsetSpinBox.setRange(0, 7)
        self.paletteOffsetSpinBox.valueChanged.connect(self.paletteOffsetSpinBoxChanged)

        gfxPropertiesForm = QtWidgets.QFormLayout()
        gfxPropertiesForm.addRow('GFX offset', self.gfxOffsetSpinBox)
        gfxPropertiesForm.addRow('Palettes offset', self.paletteOffsetSpinBox)

        self.xSpinBox = QtWidgets.QSpinBox(self)
        self.xSpinBox.setRange(-0x100, 0xFF)
        self.xSpinBox.valueChanged.connect(self.xSpinBoxChanged)
        self.ySpinBox = QtWidgets.QSpinBox(self)
        self.ySpinBox.setRange(-0x80, 0x7F)
        self.ySpinBox.valueChanged.connect(self.ySpinBoxChanged)
        self.paletteSpinBox = QtWidgets.QSpinBox(self)
        self.paletteSpinBox.setRange(0, 7)
        self.paletteSpinBox.valueChanged.connect(self.paletteSpinBoxChanged)
        self.prioritySpinBox = QtWidgets.QSpinBox(self)
        self.prioritySpinBox.setRange(0, 3)
        self.prioritySpinBox.valueChanged.connect(self.prioritySpinBoxChanged)
        self.hFlipCheckBox = QtWidgets.QCheckBox(self)
        self.hFlipCheckBox.checkStateChanged.connect(self.hFlipCheckBoxChanged)
        self.vFlipCheckBox = QtWidgets.QCheckBox(self)
        self.vFlipCheckBox.checkStateChanged.connect(self.vFlipCheckBoxChanged)

        spritePropertiesForm = QtWidgets.QFormLayout()
        spritePropertiesForm.addRow('X position', self.xSpinBox)
        spritePropertiesForm.addRow('Y position', self.ySpinBox)
        spritePropertiesForm.addRow('Palette', self.paletteSpinBox)
        spritePropertiesForm.addRow('BG priority', self.prioritySpinBox)
        spritePropertiesForm.addRow('H-flip', self.hFlipCheckBox)
        spritePropertiesForm.addRow('V-flip', self.vFlipCheckBox)

        self.spritePropertiesFormBox = QtWidgets.QGroupBox('Properties')
        self.spritePropertiesFormBox.setLayout(spritePropertiesForm)
        self.spritePropertiesFormBox.setEnabled(False)

        rightSide = QtWidgets.QVBoxLayout()
        rightSide.addLayout(editSpriteListRow)
        rightSide.addWidget(self.spriteList)
        rightSide.addLayout(loadSaveTiles)
        rightSide.addLayout(gfxPropertiesForm)
        rightSide.addWidget(self.tileSelectorView)
        rightSide.addWidget(self.spritePropertiesFormBox)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.spritemapView)
        layout.addLayout(rightSide)

        self.loadData(data)

    def loadData(self, data):
        self.initialized = False
        self.data = data
        self.frames = data['spritemaps']
        self.loadPalettesFromData()
        self.gfxOffsetSpinBox.setValue(data['gfx_offset'])
        self.paletteOffsetSpinBox.setValue(data['palette_offset'])

    def loadPalettesFromData(self):
        self.displayedPalettes = []
        for i in range(self.data['palette_offset']):
            self.displayedPalettes.append([0]+[0xFF000000]*16)
        for i in range(0, len(self.data['palette']), 16):
            self.displayedPalettes.append([0]+self.data['palette'][i+1:i+16])
        for i in range(8-len(self.displayedPalettes)):
            self.displayedPalettes.append([0]+[0xFF000000]*16)

    def updateData(self):
        self.currentSpritemapData['spritemap'] = []
        for i in range(self.spriteList.count()):
            self.currentSpritemapData['spritemap'].append(self.spriteList.item(i).spriteData)

    def updateSpritemapChanged(self, spritemapData):
        self.initialized = False

        self.spritemapScene.clear()
        self.currentSpritemapData = spritemapData
        self.spriteList.clear()
        self.spritePropertiesFormBox.setEnabled(False)

        self.tiles = bytearray(base64.b64decode(bytes(self.data['gfx'], 'utf8')))

        # Add tiles to the sprite tile list and the spritemap scene
        for i in range(len(self.currentSpritemapData['spritemap'])):
            SpriteListItem(str(i), self.spriteList, self.currentSpritemapData['spritemap'][i], self)

        self.updateSpritePixmapItemsZValues()

        self.updateTileSelector()
        self.tileSelectorScene.selection.hide()

        self.initialized = True

    def spritemapSceneSelectionChanged(self):
        if self.initialized: # needed to not throw an error when switching to a different spritemap with items selected
            for i in range(self.spriteList.count()):
                item = self.spriteList.item(i)
                if item.pixmapItem.isSelected():
                    self.spriteList.setCurrentItem(item)
                    break

    def newSpriteClicked(self):
        item = SpriteListItem(str(self.spriteList.count()), self.spriteList, {
            'x': 0,
            'y': 0,
            'big': False,
            'tile': self.data['gfx_offset'],
            'palette': 0,
            'bg_priority': 2,
            'h_flip': False,
            'v_flip': False
        }, self)
        self.spriteListSelectItem(item)

    def deleteSpriteClicked(self):
        for item in self.spriteList.selectedItems():
            if item is self.spriteList.currentItem():
                self.spriteList.setCurrentItem(None)
            self.spriteList.takeItem(self.spriteList.indexFromItem(item).row())
            self.spritemapScene.removeItem(item.pixmapItem)

        self.updateSpritePixmapItemsZValues()
        self.fixSpriteListLabels()
        self.updateData()

    def moveSpriteUpClicked(self):
        item = self.spriteList.currentItem()
        if item != None:
            index = self.spriteList.indexFromItem(item).row()
            if index > 0:
                self.spriteList.takeItem(index)
                self.spriteList.insertItem(index-1, item)
                self.spriteList.setCurrentItem(item)
               
                self.updateSpritePixmapItemsZValues()
                self.fixSpriteListLabels()
                self.updateData()

    def moveSpriteDownClicked(self):
        item = self.spriteList.currentItem()
        if item != None:
            index = self.spriteList.indexFromItem(item).row()
            if index < self.spriteList.count()-1:
                self.spriteList.takeItem(index)
                self.spriteList.insertItem(index+1, item)
                self.spriteList.setCurrentItem(item)
               
                self.updateSpritePixmapItemsZValues()
                self.fixSpriteListLabels()
                self.updateData()

    def spriteListSelectItem(self, item):
        for pixmapItem in self.spritemapScene.items():
            pixmapItem.setSelected(False)

        self.spriteList.setCurrentItem(item)
        item.pixmapItem.setSelected(True)

    def fixSpriteListLabels(self):
        for i in range(self.spriteList.count()):
            self.spriteList.item(i).setText(str(i))

    def updateSpritePixmapItemsZValues(self):
        z = 0
        for i in range(self.spriteList.count()):
            self.spriteList.item(i).pixmapItem.setZValue(z)
            z -= 1

    def updateTileSelector(self):
        canvas = {}
        tileCount = len(self.tiles)//32
        for i in range(tileCount):
            add_to_canvas_from_spritemap(canvas, [{
                'x': i%16*8,
                'y': i//16*8,
                'big': False,
                'tile': i,
                'palette': 0,
                'bg_priority': 2,
                'h_flip': False,
                'v_flip': False
            }], self.tiles)
        self.tileSelectorImage = to_qimage(canvas, self.data['palette'], 0, 0, 16*8, (tileCount-1)//16*8+8)
        self.tileSelectorPixmap.setPixmap(QtGui.QPixmap.fromImage(self.tileSelectorImage))
        self.tileSelectorView.setSceneRect(0, 0, 16*8, (tileCount-1)//16*8+8)
        #self.tileSelectorView.setFixedSize(16*8*4+6, ((tileCount-1)//16*8+8)*4+6)
        self.tileSelectorView.setMaximumHeight(((tileCount-1)//16*8+8)*4+6)

    def loadTilesClicked(self):
        if self.tileSelectorImage != None:
            fileName = QtWidgets.QFileDialog.getOpenFileName(self, filter='PNG files (*.png)')[0]
            if fileName != '':
                image = QtGui.QImage(fileName)
                self.tiles = convert_to_4bpp(image)
                self.data['gfx'] = str(base64.b64encode(self.tiles), 'utf8')
                self.data['palette'] = image.colorTable()

                self.loadPalettesFromData()
                self.updateTileSelector()

                # update all sprites in the spritemap scene
                for item in self.spritemapScene.items():
                    item.updateImage()

    def saveTilesClicked(self):
        if self.tileSelectorImage != None:
            fileName = QtWidgets.QFileDialog.getSaveFileName(self, filter='PNG files (*.png)')[0]
            if fileName != '':
                self.tileSelectorImage.save(fileName)

    def updateCurrentSpriteChanged(self):
        self.tileSelectorScene.updateCurrentSpriteChanged()
        if self.spriteList.currentItem() != None:
            self.spritePropertiesFormBox.setEnabled(True)
            data = self.spriteList.currentItem().spriteData
            self.xSpinBox.setValue(data['x']) # xSpinBoxChanged gets activated, but this isn't a problem
            self.ySpinBox.setValue(data['y'])
            self.paletteSpinBox.setValue(data['palette'])
            self.prioritySpinBox.setValue(data['bg_priority'])
            self.hFlipCheckBox.setCheckState(QtCore.Qt.Checked if data['h_flip'] else QtCore.Qt.Unchecked)
            self.vFlipCheckBox.setCheckState(QtCore.Qt.Checked if data['v_flip'] else QtCore.Qt.Unchecked)
        else:
            self.spritePropertiesFormBox.setEnabled(False)

    def gfxOffsetSpinBoxChanged(self, offset):
        self.data['gfx_offset'] = offset
        for item in self.spritemapScene.items():
            item.updateImage()

    def paletteOffsetSpinBoxChanged(self, offset):
        self.data['palette_offset'] = offset
        self.loadPalettesFromData()
        for item in self.spritemapScene.items():
            item.updateImage()

    def xSpinBoxChanged(self, x):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            if data['x'] != x: # check if the value actually changed
                data['x'] = x
                self.spriteList.currentItem().pixmapItem.setX(x)

    def ySpinBoxChanged(self, y):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            if data['y'] != y:
                data['y'] = y
                self.spriteList.currentItem().pixmapItem.setY(y)

    def paletteSpinBoxChanged(self, palette):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            if data['palette'] != palette:
                data['palette'] = palette
                self.spriteList.currentItem().pixmapItem.updateImage()

    def prioritySpinBoxChanged(self, priority):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            data['bg_priority'] = priority

    def hFlipCheckBoxChanged(self, state):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            checked = state == QtCore.Qt.Checked
            if data['h_flip'] != checked:
                data['h_flip'] = checked
                self.spriteList.currentItem().pixmapItem.updateImage()

    def vFlipCheckBoxChanged(self, state):
        if self.spriteList.currentItem() != None:
            data = self.spriteList.currentItem().spriteData
            checked = state == QtCore.Qt.Checked
            if data['v_flip'] != checked:
                data['v_flip'] = checked
                self.spriteList.currentItem().pixmapItem.updateImage()

    def hFlip(self):
        toflip = self.spritemapScene.selectedItems()
        if len(toflip) == 0:
            toflip = self.spritemapScene.items()
        for item in toflip:
            data = item.spriteData
            data['h_flip'] = not data['h_flip']
            data['x'] = -data['x']-(16 if data['big'] else 8)
            item.setX(data['x'])
            item.updateImage()

    def vFlip(self):
        toflip = self.spritemapScene.selectedItems()
        if len(toflip) == 0:
            toflip = self.spritemapScene.items()
        for item in toflip:
            data = item.spriteData
            data['v_flip'] = not data['v_flip']
            data['y'] = -data['y']-(16 if data['big'] else 8)
            item.setY(data['y'])
            item.updateImage()
