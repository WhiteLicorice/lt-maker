from PyQt5.QtCore import Qt, QPoint, QLineF, QRectF, pyqtSignal
from PyQt5.QtWidgets import QWidget, QAction, QPushButton, QLabel, QDialog, QScrollArea, QDialogButtonBox, QSpinBox, QToolBar, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QIcon, QPainter, QColor, QPen, QPixmap
from app import dark_theme
from enum import IntEnum
import math

def rotate(coords:list[list], theta:int):
    #Rotate by theta = k*pi/2 radians counterclockwise for k an integer.
    cos = int(math.cos(theta)) 
    sin = int(math.sin(theta))
    new_coords = [[coord[0] * cos + coord[1] * sin, coord[1] * cos-coord[0] * sin] for coord in coords]
    return new_coords

class ShapeIcon(QPushButton):
    shapeChanged = pyqtSignal()

    def __init__(self,parent,shape: list[list], size:int):
        super().__init__(parent)
        self._shape = shape
        self.set_size(size)
        self.pressed.connect(self.initiate_shape_dialog)

    def set_size(self, size):
        self.size = size
        self.setMinimumHeight(self.size)
        self.setMaximumHeight(self.size)
        self.setMinimumWidth(self.size)
        self.setMaximumWidth(self.size)
        self.resize(self.size, self.size)
        
    def change_shape(self, shape:list[list]):
        if shape != self._shape:
            self._shape = shape
            self.shapeChanged.emit()
        
    def shape(self):
        return self._shape.copy()

    def initiate_shape_dialog(self):
        dlg = ShapeDialog(self, self._shape.copy())
        if dlg.exec_():
            self.change_shape(dlg.get_shape())
            
class DrawState(IntEnum):
    Inactive = -1
    Paint = 0
    Erase = 1
    Fill = 2
    Rotate = 3
    ResizeDown = 4
    ResizeUp = 5
            
class PaintGrid(QLabel):
    mousePress = pyqtSignal(QPoint, bool) #Point: mouse position, bool: True if left clicked, false if right clicked
    mouseMoved = pyqtSignal(QPoint)
    def __init__(self, parent):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.mouse_held = DrawState.Inactive
        self.container = parent.grid_container
        
    def mousePressEvent(self, mouse):
        if mouse.button() == Qt.LeftButton:
            left_clicked = True
        if mouse.button() == Qt.RightButton:
            left_clicked = False
        p = QPoint(-self.container.horizontalScrollBar().value() + mouse.pos().x(), -self.container.verticalScrollBar().value() + mouse.pos().y())
        if self.container.viewport().rect().contains(p): #Make sure mouse is inside grid viewport
            self.mousePress.emit(mouse.pos(), left_clicked)
        if left_clicked:
            self.mouse_held = DrawState.Paint
        else:
            self.mouse_held = DrawState.Erase
        
    def mouseMoveEvent(self, mouse):
        p = QPoint(-self.container.horizontalScrollBar().value() + mouse.pos().x(), -self.container.verticalScrollBar().value() + mouse.pos().y())
        if self.container.viewport().rect().contains(p):
            if self.mouse_held >= 0:
                if self.mouse_held == DrawState.Paint:
                    self.mousePress.emit(mouse.pos(), True)
                else:
                    self.mousePress.emit(mouse.pos(), False)
            self.mouseMoved.emit(mouse.pos())
            
    def mouseReleaseEvent(self, mouse):
        self.mouse_held = DrawState.Inactive

class SizeSpinBox(QSpinBox):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        
    def keyPressEvent(self, e):
        #Let parent handle input used for shortcut keys
        key = e.key()
        self.parent.keyPressEvent(e)
        super().keyPressEvent(e)
                       
class ShapeDialog(QDialog):
    mode = DrawState.Paint
    size = 1 #Current grid size
    disp_size = 10 #Max display size of grid
    coords = [] #Locations currently included in the shape
    wx_size = 480 #Default width of window
    wy_size = 600 #Default height of window
    x_size = 452 #Default width of grid
    y_size = 447 #Default height of grid
    cell_width = 0
    cell_height = 0 
    prev_action = DrawState.Inactive
    prev_data = []
    primary_col = QColor(185, 185, 185) #For grid background
    secondary_col = QColor(80, 80, 80) #For grid lines/center tile
    shade_col = QColor(41, 121, 201) #For selected tiles
    center_selectable = False

    def __init__(self,parent, init_shape:list[list], center_selectable = False):
        super().__init__(parent)
        self.setWindowTitle("Draw Shape")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.resize(self.wx_size, self.wy_size)
        main_layout = QVBoxLayout()
        size_layout = QHBoxLayout()
        
        #Toolbar for paint/erase
        tools = QToolBar()
        theme = dark_theme.get_theme()
        icon_folder = theme.icon_dir()

        self.paint = QAction(QIcon(f"{icon_folder}/brush.png"), "Paint", self, triggered = self.set_paint_mode)
        self.paint.setCheckable(True)
        self.paint.setChecked(True)
        self.paint.setToolTip("Paint (P)")
        self.mode = DrawState.Paint
        tools.addAction(self.paint)
        self.erase = QAction(QIcon(f"{icon_folder}/eraser.png"), "Erase", self, triggered = self.set_erase_mode)
        self.erase.setCheckable(True)
        self.erase.setToolTip("Erase (E)")
        tools.addAction(self.erase)
        self.fill = QAction(QIcon(f"{icon_folder}/fill.png"), "Fill", self, triggered = self.set_fill_mode)
        self.fill.setCheckable(True)
        self.fill.setToolTip("Fill (F)")
        tools.addAction(self.fill)
        self.rotate = QAction(QIcon(f"{icon_folder}/command_loop.png"), "Rotate", self, triggered = self.rotate_grid)
        self.rotate.setToolTip("Rotate (R)")
        tools.addAction(self.rotate)
        self.undo = QAction(QIcon(f"{icon_folder}/back.png"), "Undo", self, triggered = self.undo_action)
        self.undo.setToolTip("Undo (Ctrl+Z)")
        tools.addAction(self.undo)

        #Grid
        self.center_selectable = center_selectable
        self.grid_container = QScrollArea()
        self.grid_container.setAlignment(Qt.AlignLeft|Qt.AlignTop)
        self.grid = PaintGrid(self)
        self.grid.resize(self.x_size, self.y_size)
        self.grid.setAlignment(Qt.AlignLeft|Qt.AlignTop)
        self.set_shape(init_shape)
        surface = QPixmap(self.x_size, self.y_size)
        self.grid.setPixmap(surface)
        self.populate_grid()
        self.grid.mousePress.connect(self.handle_mouse_input)
        self.grid.mouseMoved.connect(self.update_mouse_pos)
        self.grid_container.setWidget(self.grid)
        
        #Size toggle
        self.mouse_pos = QLabel("  ")
        self.mouse_pos.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        label = QLabel("Size:")
        label.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.size_value = SizeSpinBox(self)
        self.size_value.setValue(self.size)
        self.size_value.setMinimum(1)
        self.size_value.editingFinished.connect(self.resize_grid)
        
        #Confirm/cancel buttons
        confirm = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        confirm.accepted.connect(self.accept)
        confirm.rejected.connect(self.reject)
        
        #Set-up layout
        main_layout.addWidget(tools)
        main_layout.addWidget(self.grid_container)
        size_layout.addWidget(self.mouse_pos)
        size_layout.addWidget(label)
        size_layout.addWidget(self.size_value)
        size_layout.setSpacing(10)
        main_layout.addLayout(size_layout)
        main_layout.addWidget(confirm)
  
        self.setLayout(main_layout)
            
    def populate_grid(self):
        #Redraws the grid and shades in selected coordinates
        s=self.size * 2 + 1
        self.draw_grid(s, s)
        if not self.center_selectable: #Block out center tile
            self.shade_rect(self.size,self.size, self.secondary_col)
        else:
            self.shade_rect(self.size, self.size, self.primary_col)
        for coord in self.coords:
            if coord != [0, 0] or self.center_selectable:
                self.shade_rect(coord[0] + self.size, coord[1] + self.size, self.shade_col)
                    
    def draw_grid(self, x_cells:int, y_cells:int):
        #Erases existing grid contents and draws gridlines
        self.cell_width = self.x_size / (min(x_cells, self.disp_size * 2 + 1))
        self.cell_height = self.y_size / (min(y_cells, self.disp_size * 2 + 1))
        surface = self.grid.pixmap()
        if self.size > self.disp_size: #Grid is too big, resize it and use scrollbars
            self.grid.resize(int(self.cell_width * x_cells), int(self.cell_height * y_cells))
            surface = QPixmap(int(self.cell_width * x_cells), int(self.cell_height * y_cells))
        else:
            self.grid.resize(self.x_size, self.y_size)
            surface = QPixmap(self.x_size, self.y_size)
            
        painter = QPainter(surface)
        painter.setPen(QPen(self.secondary_col))
        painter.fillRect(surface.rect(), self.primary_col)
        for i in range(0, x_cells + 1):
            y = i * self.cell_height
            line = QLineF(0, y, self.grid.width(), y)
            painter.drawLine(line)
        for j in range(0, y_cells + 1):
            x = j * self.cell_width
            line = QLineF(x, 0, x, self.grid.height())
            painter.drawLine(line)
        painter.end()
        self.grid.setPixmap(surface) #Needed to update display
        
    def shade_rect(self, i:int, j:int, col:QColor):
        #Fills in a rectangle with the specified color at the given [i,j] coordinate
        x = i * self.cell_width
        y = j * self.cell_height
        surface = self.grid.pixmap()
        painter = QPainter(surface)
        if i == self.size and j == self.size and self.center_selectable: #Handle central tile fill
            painter.fillRect(QRectF(x, y, self.cell_width, self.cell_height), self.secondary_col)
            painter.fillRect(QRectF(x + self.cell_width / 5, y + self.cell_height / 5, self.cell_width - 2 * self.cell_width / 5,self.cell_height - 2 * self.cell_height / 5), col)
        else:
            painter.fillRect(QRectF(x, y, self.cell_width, self.cell_height), col)
            painter.setPen(QPen(self.secondary_col))
            painter.drawRect(QRectF(x, y, self.cell_width, self.cell_height)) #Otherwise previous step colors over grid lines 
        painter.end()
        self.grid.setPixmap(surface)
               
    def resize_grid(self):
        #Redraw grid with new size.
        new_size = self.size_value.value()
        if self.size > new_size: #Delete coordinates at the edge of the grid if size decreases.
            new_coords = []
            removed_coords = []
            for coord in self.coords:
                if max(abs(coord[0]), abs(coord[1])) <= new_size:
                    new_coords.append(coord)
                else:
                    removed_coords.append(coord)
            self.coords = new_coords
            self.prev_action = DrawState.ResizeDown
            self.prev_data = [self.size, removed_coords]
        else:
            self.prev_action = DrawState.ResizeUp
            self.prev_data = [self.size, []]
        
        self.size = new_size
        self.populate_grid()
                  
    def set_paint_mode(self):
        self.paint.setChecked(True)
        self.mode = DrawState.Paint
        self.erase.setChecked(False)
        self.fill.setChecked(False)
        
    def set_erase_mode(self):
        self.erase.setChecked(True)
        self.mode = DrawState.Erase
        self.paint.setChecked(False)
        self.fill.setChecked(False)
        
    def set_fill_mode(self):
        self.fill.setChecked(True)
        self.mode = DrawState.Fill
        self.paint.setChecked(False)
        self.erase.setChecked(False)
        
    def handle_mouse_input(self, pos:QPoint, left_clicked:bool):
        #Triggers when mouse clicked or mouse held and moved
        if self.mode == DrawState.Erase:
            if left_clicked:
                mode = DrawState.Erase
            else:
                mode = DrawState.Paint
        else: #Paint or fill
            if left_clicked:
                mode = DrawState.Paint
            else:
                mode = DrawState.Erase
        if mode == DrawState.Paint:
            col = self.shade_col
        else:
            col = self.primary_col
        grid_coord = self.get_grid_coord(pos)
        if grid_coord != (self.size, self.size) or self.center_selectable: #Handles central tile
            shifted_coord = [grid_coord[0] - self.size, grid_coord[1] - self.size]
            #Paint
            if mode == DrawState.Paint and self.mode in [DrawState.Paint, DrawState.Erase]:
                if self.grid.mouse_held == DrawState.Inactive: #Mouse was just pressed
                    self.prev_action = DrawState.Paint
                    self.prev_data = []
                if shifted_coord not in self.coords:
                    self.coords.append(shifted_coord)
                    self.prev_data.append(shifted_coord)
                self.shade_rect(grid_coord[0], grid_coord[1], col)
            #Erase
            elif mode == DrawState.Erase and self.mode in [DrawState.Paint, DrawState.Erase]:
                if self.grid.mouse_held == DrawState.Inactive:
                    self.prev_action = DrawState.Erase
                    self.prev_data = []
                if shifted_coord in self.coords:
                    self.coords.remove(shifted_coord)
                    self.prev_data.append(shifted_coord)
                self.shade_rect(grid_coord[0], grid_coord[1], col)
            #Fill
            elif self.mode == DrawState.Fill and self.grid.mouse_held == DrawState.Inactive:
                filled = shifted_coord in self.coords
                shifted_coord = tuple(shifted_coord)
                if mode == DrawState.Paint and not filled: #Fill connected block of empty tiles
                    self.fill_block(shifted_coord, filled, col)
                elif mode == DrawState.Erase and filled: #Erase connected block of shaded tiles
                    self.fill_block(shifted_coord, filled, col)
    
    def update_mouse_pos(self, pos:QPoint):
        #Handles mouse coordinate display
        grid_coord = self.get_grid_coord(pos)
        self.mouse_pos.setText("(" + str(grid_coord[0]-self.size) + " , " + str(grid_coord[1]-self.size) + ")")
    
    def keyPressEvent(self, e):
        #Handles shortcut keys
        if e.key() == Qt.Key_P:
            self.set_paint_mode()
        elif e.key() == Qt.Key_E:
            self.set_erase_mode()
        elif e.key() == Qt.Key_F:
            self.set_fill_mode()
        elif e.key() == Qt.Key_R:
            self.rotate_grid()
        elif e.key() == Qt.Key_Z and e.modifiers() == Qt.ControlModifier:
            self.undo_action()
        elif e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter: #Prevent enter key press from closing the QDialog (reserved for resize spinbox)
            pass
        else:
            super().keyPressEvent(e)
    
    def fill_block(self, start_pos:tuple[int], filled:bool, col:QColor):
        #Shade or erase a block of similar tiles
        to_alter = self.flood_fill(start_pos, filled) 
        self.prev_data = []
        for coord in to_alter:
            self.shade_rect(coord[0] + self.size, coord[1] + self.size,col)
            coord = list(coord)
            self.prev_data.append(coord)
            if filled: #We're erasing
                self.coords.remove(coord)
            else: #We're filling
                self.coords.append(coord)
        self.prev_action = filled
                             
    def flood_fill(self, starting_pos: tuple[int], filled: bool):
        #Finds locations to alter for the fill operation
        blob_positions = set()
        grid_lookup = [[0] * (self.size * 2 + 1) for i in range(0, self.size * 2 + 1)] #So we only have to loop through coords once rather than at every location.
        for coord in self.coords:
            grid_lookup[coord[0] + self.size][coord[1] + self.size] = 1
        unexplored_stack = []

        def find_similar(starting_pos):
            unexplored_stack.append(starting_pos)
            while unexplored_stack:
                current_pos = unexplored_stack.pop()

                if current_pos in blob_positions: #Already covered this location
                    continue
                if current_pos == (0, 0) and not self.center_selectable: #Don't affect origin
                    continue
                if (abs(current_pos[0]) > self.size) or (abs(current_pos[1]) > self.size): #Reached edge of grid
                    continue
                current_filled = grid_lookup[current_pos[0] + self.size][current_pos[1] + self.size]
                if (filled and not current_filled) or (not filled and current_filled): #Check if current pos is different from start pos
                    continue
                blob_positions.add(current_pos)
                unexplored_stack.append((current_pos[0] + 1, current_pos[1]))
                unexplored_stack.append((current_pos[0] - 1, current_pos[1]))
                unexplored_stack.append((current_pos[0], current_pos[1] + 1))
                unexplored_stack.append((current_pos[0], current_pos[1] - 1))

        #Determine which coords should be flood-filled
        find_similar(starting_pos)
        return blob_positions
    
    def rotate_grid(self):
        self.coords = rotate(self.coords, math.pi / 2)
        self.populate_grid()
        self.prev_action = DrawState.Rotate
        self.prev_data = math.pi / 2
    
    def undo_action(self):
        if self.prev_action == DrawState.Paint:
            for coord in self.prev_data:
                self.coords.remove(coord)
                self.shade_rect(coord[0] + self.size, coord[1] + self.size, self.primary_col)
                self.prev_action = DrawState.Erase      
        elif self.prev_action == DrawState.Erase:
            for coord in self.prev_data:
                self.coords.append(coord)
                self.shade_rect(coord[0] + self.size, coord[1] + self.size, self.shade_col)
                self.prev_action = DrawState.Paint       
        elif self.prev_action == DrawState.Rotate:
            self.prev_data *= -1
            self.coords = rotate(self.coords, self.prev_data)
            self.populate_grid()
        elif self.prev_action == DrawState.ResizeDown:
            for coord in self.prev_data[1]:
                self.coords.append(coord)
            self.size_value.setValue(self.prev_data[0])
        elif self.prev_action == DrawState.ResizeUp:
            self.size_value.setValue(self.prev_data[0])
                   
    def get_grid_coord(self, pos:QPoint):
        #Used for converting the mouse's position to a coordinate in the grid.
        return (int(pos.x() // self.cell_width),int(pos.y() // self.cell_height))
        
    def set_shape(self, shape:list[list]):
        #Initializes data
        self.coords = shape
        if self.coords:
            self.size = max([max(abs(coord[0]), abs(coord[1])) for coord in self.coords])
        else:
            self.size = 1
        
    def get_shape(self):
        return self.coords.copy()       