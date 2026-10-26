from enum import IntEnum

from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
from PyQt5.QtCore import Qt, QRect, QRectF
from PyQt5.QtGui import QPainter, QImage, QColor, QPen

from app.constants import TILEWIDTH, TILEHEIGHT, WINWIDTH, WINHEIGHT

from app.utilities.typing import Pos

from app.map_maker.editor.draw_tilemap import update_tile_grid, simple_draw_tilemap
import app.map_maker.utilities as map_utils
from app.map_maker.qt_renderers.renderer_database import RENDERERS
from app.editor import timer

class PaintTool(IntEnum):
    NoTool = 0
    Brush = 1
    Fill = 2
    Erase = 3
    CliffMarker = 4

class MapEditorView(QGraphicsView):
    min_scale = 1
    max_scale = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self.window = parent

        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setMouseTracking(True)

        self.setMinimumSize(WINWIDTH, WINHEIGHT)
        self.setStyleSheet("background-color:rgb(128, 128, 128);")

        self.screen_scale = 1

        self.tilemap = None
        # Every tile of the tilemap, drawn behind the scene. Only the
        # tiles whose sprites change are drawn on it again
        self.map_image: QImage = None
        # The grid lines, drawn over the map. Only drawn again when the map changes size
        self.grid_image: QImage = None

        self.current_mouse_position = (0, 0)
        self.old_middle_pos = None

        self.left_selecting = False
        self.right_selecting = False
        self.right_selection = {}  # Dictionary of tile_sprites

        self.draw_autotiles = True
        self.draw_gridlines = True

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        if self.tilemap and self.update_map_image():
            self.viewport().update()

    def set_current(self, current):
        self.tilemap = current
        self.map_image = None
        self.update_view()

    def update_view(self):
        """Brings the map image up to date and repaints everything,
        for when what is drawn over the map may have changed too"""
        if self.tilemap:
            self.update_map_image()
        self.viewport().update()

    def update_map_image(self) -> bool:
        """Redraws the tiles of map_image whose sprites changed since
        it was last drawn. Returns whether anything was redrawn"""
        if self.draw_autotiles:
            update_tile_grid(self.tilemap, autotile_fps=self.tilemap.autotile_fps)
        else:
            update_tile_grid(self.tilemap, autotile_fps=0)

        width, height = self.tilemap.width * TILEWIDTH, self.tilemap.height * TILEHEIGHT
        if self.map_image is None or (self.map_image.width(), self.map_image.height()) != (width, height):
            self.map_image = simple_draw_tilemap(self.tilemap)
            self.grid_image = self.draw_grid_image()
            self.scene.setSceneRect(0, 0, width, height)
            self.tilemap.tile_grid_changed.clear()
            return True
        if not self.tilemap.tile_grid_changed:
            return False

        painter = QPainter()
        painter.begin(self.map_image)
        # Each tile replaces whatever was drawn there before, transparency included
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        for pos in self.tilemap.tile_grid_changed:
            if pos in self.tilemap.tile_grid:
                painter.drawPixmap(pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT, self.tilemap.tile_grid[pos])
            else:
                painter.fillRect(pos[0] * TILEWIDTH, pos[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT, Qt.transparent)
        painter.end()
        self.tilemap.tile_grid_changed.clear()
        return True

    def draw_grid_image(self) -> QImage:
        image = QImage(self.tilemap.width * TILEWIDTH, self.tilemap.height * TILEHEIGHT, QImage.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))
        painter = QPainter()
        painter.begin(image)
        painter.setPen(QPen(QColor(0, 0, 0, 128), 1, Qt.DotLine))
        for x in range(self.tilemap.width):
            painter.drawLine(x * TILEWIDTH, 0, x * TILEWIDTH, self.tilemap.height * TILEHEIGHT)
        for y in range(self.tilemap.height):
            painter.drawLine(0, y * TILEHEIGHT, self.tilemap.width * TILEWIDTH, y * TILEHEIGHT)
        painter.end()
        return image

    def drawBackground(self, painter: QPainter, rect: QRectF):
        super().drawBackground(painter, rect)
        if self.map_image:
            exposed = rect.intersected(QRectF(self.map_image.rect()))
            painter.drawImage(exposed, self.map_image, exposed)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        if not self.tilemap:
            return
        # Nothing drawn over the map reaches past its edges
        painter.setClipRect(QRectF(0, 0, self.tilemap.width * TILEWIDTH, self.tilemap.height * TILEHEIGHT))

        # Draw grid lines
        if self.draw_gridlines:
            exposed = rect.intersected(QRectF(self.grid_image.rect()))
            painter.drawImage(exposed, self.grid_image, exposed)

            # Draw cliff markers
            painter.setPen(QPen(QColor(255, 0, 0, 128), 2))
            for cliff_marker in self.tilemap.cliff_markers:
                painter.drawPoint(cliff_marker[0] * TILEWIDTH, cliff_marker[1] * TILEHEIGHT)

        # Draw cursor...
        if self.window.current_tool == PaintTool.CliffMarker:
            painter.setPen(QPen(QColor(128, 0, 128, 255), 3))
            mouse_pos = self.current_mouse_position
            painter.drawPoint(mouse_pos[0] * TILEWIDTH, mouse_pos[1] * TILEHEIGHT)
        elif self.right_selecting:
            # Currently holding down right click and selecting area
            self.draw_selection(painter)
        elif self.right_selection:
            # Currently drawing with a right click held down area
            self.draw_right_cursor(painter)
        elif self.window.current_tool in (PaintTool.Erase, PaintTool.NoTool):
            self.draw_simple_cursor(painter)
        else:
            # Currently drawing with a terrain
            self.draw_normal_cursor(painter)

    def draw_simple_cursor(self, qpainter):
        mouse_pos = self.current_mouse_position
        # Fill with blue
        rect = QRect(mouse_pos[0] * TILEWIDTH, mouse_pos[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
        qpainter.fillRect(rect, QColor(0, 255, 255, 96))

    def draw_normal_cursor(self, qpainter):
        mouse_pos = self.current_mouse_position
        terrain = self.window.terrain_painter_menu().get_current_terrain()
        if not terrain:
            return

        renderer = RENDERERS.get(terrain)
        im = renderer.get_display_pixmap().toImage()
        qpainter.drawImage(mouse_pos[0] * TILEWIDTH,
                           mouse_pos[1] * TILEHEIGHT,
                           im)
        # Fill with blue
        rect = QRect(mouse_pos[0] * TILEWIDTH, mouse_pos[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
        qpainter.fillRect(rect, QColor(0, 255, 255, 96))

    def draw_right_cursor(self, qpainter):
        mouse_pos = self.current_mouse_position
        for coord, (true_coord, terrain) in self.right_selection.items():
            if not terrain:
                continue  # Empty tiles in the selection leave the map as it is

            renderer = RENDERERS.get(terrain)
            true_coord = mouse_pos[0] + coord[0], mouse_pos[1] + coord[1]
            qpainter.drawImage(true_coord[0] * TILEWIDTH,
                               true_coord[1] * TILEHEIGHT,
                               renderer.get_display_pixmap().toImage())
            # Fill with blue
            rect = QRect(true_coord[0] * TILEWIDTH, true_coord[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
            qpainter.fillRect(rect, QColor(0, 255, 255, 96))

    def draw_selection(self, qpainter):
        starting_pos = self.right_selecting
        if not starting_pos:
            return
        for coord, (true_coord, terrain) in self.right_selection.items():
            color = QColor(0, 255, 255, 128)
            rect = QRect(true_coord[0] * TILEWIDTH, true_coord[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
            qpainter.fillRect(rect, color)

    def create_right_selection(self):
        self.right_selection.clear()
        left = min(self.right_selecting[0], self.current_mouse_position[0])
        width = max(self.right_selecting[0], self.current_mouse_position[0]) - left + 1
        top = min(self.right_selecting[1], self.current_mouse_position[1])
        height = max(self.right_selecting[1], self.current_mouse_position[1]) - top + 1
        for x in range(width):
            for y in range(height):
                i, j = x + left, y + top
                self.right_selection[(x, y)] = ((i, j), self.tilemap.get_terrain((i, j)))

    def paint_terrain(self, tile_pos: Pos):
        if self.right_selection:
            new_terrains = {}
            for coord, (true_coord, terrain) in self.right_selection.items():
                true_pos = tile_pos[0] + coord[0], tile_pos[1] + coord[1]
                # Empty tiles in the selection leave the map as it is
                if terrain and self.tilemap.check_bounds(true_pos):
                    new_terrains[true_pos] = terrain
            self.tilemap.set_many(new_terrains)

        elif self.tilemap.check_bounds(tile_pos):
            terrain = self.window.terrain_painter_menu().get_current_terrain()
            old_terrain = self.tilemap.get_terrain(tile_pos)
            self.tilemap.set(tile_pos, old_terrain, terrain)

    def erase_terrain(self, tile_pos: Pos):
        if self.tilemap.check_bounds(tile_pos):
            terrain = self.tilemap.get_terrain(tile_pos)
            self.tilemap.erase_terrain(tile_pos, terrain)

    def flood_fill_terrain(self, tile_pos: Pos):
        if not self.tilemap.check_bounds(tile_pos):
            return

        coords_to_replace = map_utils.flood_fill(self.tilemap, tile_pos)

        if self.right_selection:
            # Only handles the topleft tile
            coords = list(self.right_selection.keys())
            topleft = min(coords)
            w = max(coord[0] for coord in coords) - topleft[0] + 1
            h = max(coord[1] for coord in coords) - topleft[1] + 1

            # Do the deed
            new_terrains = {}
            for x in range(self.tilemap.width):
                for y in range(self.tilemap.height):
                    if (x, y) in coords_to_replace:
                        new_coord_x = (x % w) + topleft[0]
                        new_coord_y = (y % h) + topleft[1]
                        if (new_coord_x, new_coord_y) in coords:
                            new_terrain = self.right_selection[(new_coord_x, new_coord_y)][1]
                            # Empty tiles in the selection leave the map as it is
                            if new_terrain:
                                new_terrains[(x, y)] = new_terrain
            self.tilemap.set_many(new_terrains)
        else:
            new_terrain = self.window.terrain_painter_menu().get_current_terrain()
            self.tilemap.set_many({pos: new_terrain for pos in coords_to_replace})

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        tile_pos = int(scene_pos.x() // TILEWIDTH), \
            int(scene_pos.y() // TILEHEIGHT)

        # Determined by Paint Tool selected
        if event.button() == Qt.LeftButton:
            # Put a single terrain on location
            if self.window.current_tool == PaintTool.Brush:
                self.paint_terrain(tile_pos)
                self.left_selecting = True
            # Erase the terrain on location
            elif self.window.current_tool == PaintTool.Erase:
                self.erase_terrain(tile_pos)
                self.left_selecting = True
            # Flood-fill terrain on location
            elif self.window.current_tool == PaintTool.Fill:
                self.flood_fill_terrain(tile_pos)
            # Add new cliff marker on location
            elif self.window.current_tool == PaintTool.CliffMarker:
                self.window.cliff_marker_widget.add_new_marker(tile_pos)

        # Select the current terrain under cursor
        elif event.button() == Qt.RightButton and self.tilemap.check_bounds(tile_pos):
            current_terrain = self.tilemap.get_terrain(tile_pos)
            if current_terrain:
                if current_terrain.outdoor:
                    self.window.outdoor_terrain_painter_menu.set_current_terrain(current_terrain)
                    self.window.terrain_tab.setCurrentIndex(0)
                else:
                    self.window.indoor_terrain_painter_menu.set_current_terrain(current_terrain)
                    self.window.terrain_tab.setCurrentIndex(1)
            
        # Move about the map
        elif event.button() == Qt.MiddleButton:
            self.old_middle_pos = event.pos()

        self.update_view()

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        tile_pos = int(scene_pos.x() // TILEWIDTH), \
            int(scene_pos.y() // TILEHEIGHT)

        # Within one tile, the cursor, painting and selection all stay the same
        moved_tile = tile_pos != self.current_mouse_position
        self.current_mouse_position = tile_pos

        self.window.set_position_bar(tile_pos)
        terrain = self.tilemap.get_terrain(tile_pos)
        if terrain:
            self.window.set_message("%s" % terrain.value)
        else:
            self.window.set_message(None)

        # If holding down mouse, paint or erase
        if self.left_selecting and self.tilemap.check_bounds(tile_pos):
            if self.window.current_tool == PaintTool.Brush:
                self.paint_terrain(tile_pos)
            elif self.window.current_tool == PaintTool.Erase:
                self.erase_terrain(tile_pos)
        # Calculate what coordinates have been selected under me
        elif self.right_selecting:
            self.create_right_selection()
        # Move about the map
        elif event.buttons() & Qt.MiddleButton:
            offset = self.old_middle_pos - event.pos()
            self.old_middle_pos = event.pos()

            self.verticalScrollBar().setValue(self.verticalScrollBar().value() + offset.y())
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() + offset.x())

        if moved_tile:
            self.update_view()

    def mouseReleaseEvent(self, event):
        if self.window.current_tool == PaintTool.Brush:
            if event.button() == Qt.LeftButton:
                self.left_selecting = False
            elif event.button() == Qt.RightButton:
                if self.right_selecting:
                    self.create_right_selection()
                    self.right_selecting = False
        elif self.window.current_tool == PaintTool.Erase:
            if event.button() == Qt.LeftButton:
                self.left_selecting = False

        self.update_view()

    def zoom_in(self):
        if self.screen_scale < self.max_scale:
            self.screen_scale += 1
            self.scale(2, 2)

    def zoom_out(self):
        if self.screen_scale > self.min_scale:
            self.screen_scale -= 1
            self.scale(0.5, 0.5)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.zoom_in()
        elif event.angleDelta().y() < 0:
            self.zoom_out()
