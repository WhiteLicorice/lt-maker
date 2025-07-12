from app.map_maker.painter_utils import Painter
from app.map_maker.qt_renderers.qt_palette import QtPalette
from app.map_maker.qt_renderers import SimpleRenderer

class MountainRenderer(SimpleRenderer):
    def __init__(self, painter: Painter, palette: QtPalette):
        self.painter = painter
        self.palette = palette
        # Assign the painter the 
        self.painter.mountain_process_finished = self.mountain_process_finished
        self.painter.mountain_processing = self.mountain_processing

    def mountain_process_finished(self, thread, tilemap):
        print("Finished", id(thread), thread.did_complete)
        if thread.did_complete:
            self.painter.organization.update(thread.organization)
        else:
            self.painter._generic_fill(thread.group)
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
