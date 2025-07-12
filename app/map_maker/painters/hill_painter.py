from app.utilities.typing import Pos

from app.map_maker.painter_utils import Painter
from app.map_maker.utilities import random_choice
from app.map_maker.terrain import Terrain

class HillPainter(Painter): 
    base_coord = (1, 1)
    data = {
        'main': (0, 1), 
        'pair1': (1, 0), 
        'pair2': (2, 0), 
        'alter1': (1, 1),
    }
    
    @property
    def check_flood_fill(self):
        return True

    def get_coord(self, tilemap, pos: Pos) -> Pos:
        _, east, _, west = tilemap.get_cardinal_terrain(pos)
        _, far_east, _, _ = tilemap.get_cardinal_terrain((pos[0] + 1, pos[1]))
        _, _, _, far_west = tilemap.get_cardinal_terrain((pos[0] - 1, pos[1]))
        if east != Terrain.HILL and west != Terrain.HILL:
            choice = random_choice([1, 2, 3, 4, 5, 6], pos)
            if choice <= 3:
                coord = self.data['main']
            elif choice in (4, 5):
                coord = self.data['alter1']
            else:
                coord = self.data['pair2']
        elif west != Terrain.HILL:
            coord = self.data['main']
        elif east != Terrain.HILL:
            if far_west == Terrain.HILL:
                coord = self.data['pair2']
            else:
                coord = self.data['pair1']
        else:
            coord = self.data['pair1']

        return coord
