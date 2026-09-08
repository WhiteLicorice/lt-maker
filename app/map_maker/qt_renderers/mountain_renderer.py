from app.map_maker.painter_utils import Painter
from app.map_maker.palette_collection import Palette
from app.map_maker.qt_renderers.qt_palette import get_qt_palette
from app.map_maker.qt_renderers import SimpleRenderer

class MountainRenderer(SimpleRenderer):
    def __init__(self, painter: Painter, palette: Palette):
        self.painter = painter
        self.palette = get_qt_palette(palette)
        # Mountains are solved on background Qt threads in the editor
        self.painter.gui_processing = True
        # Assign the painter the
        self.painter.mountain_process_finished = self.mountain_process_finished
        self.painter.mountain_processing = self.mountain_processing

    def mountain_process_finished(self, thread, tilemap):
        if thread not in self.painter.current_threads:
            # Cancelled (quit_all_threads/_quit_thread already dropped it).
            # Its group is pre-resize/pre-repaint, so filling organization from
            # it would put sprites at positions that no longer hold mountains.
            return
        print("Finished", id(thread), thread.did_complete)
        if thread.did_complete:
            self.painter.organization.update(thread.organization)
        else:
            self.painter._generic_fill(tilemap, thread.group)
        # Update the image since the user may not have requested a change -- this does it manually
        for pos in self.painter.organization.keys():
            sprite = self.determine_sprite(tilemap, pos, 0)
            tilemap.tile_grid[pos] = sprite
        if thread in self.painter.current_threads:
            self.painter.current_threads.remove(thread)

    def mountain_processing(self, thread, tilemap):
        print("Processing... %s" % id(thread))
        for pos, coord in thread.organization.items():
            sprite = self.palette.get_pixmap16(self.painter, coord, 0)
            tilemap.tile_grid[pos] = sprite
