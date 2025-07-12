from typing import Dict, List, Set, Optional

from collections import Counter

from PyQt5.QtGui import QImage, qRgb

from app.editor.tile_editor.autotiles import PaletteData, check_hashes

from app.constants import TILEWIDTH, TILEHEIGHT
from app.utilities.typing import Pos

DIRECTIONS = ('left', 'right', 'up', 'down')

class QuadPaletteData():
    def __init__(self, im: QImage):
        topleft_rect = (0, 0, TILEWIDTH//2, TILEHEIGHT//2)
        self.topleft = PaletteData(im.copy(*topleft_rect))
        topright_rect = (TILEWIDTH//2, 0, TILEWIDTH//2, TILEHEIGHT//2)
        self.topright = PaletteData(im.copy(*topright_rect))
        bottomleft_rect = (0, TILEHEIGHT//2, TILEWIDTH//2, TILEHEIGHT//2)
        self.bottomleft = PaletteData(im.copy(*bottomleft_rect))
        bottomright_rect = (TILEWIDTH//2, TILEHEIGHT//2, TILEWIDTH//2, TILEHEIGHT//2)
        self.bottomright = PaletteData(im.copy(*bottomright_rect))

class MountainPaletteData(QuadPaletteData):
    def __init__(self, im: QImage, coord: tuple):
        super().__init__(im)
        self.coord = coord
        self.rules = {}
        for direction in DIRECTIONS:
            self.rules[direction] = Counter()

def similar(p1: QuadPaletteData, p2: MountainPaletteData) -> bool:
    topleft_good = check_hashes(p1.topleft, p2.topleft)
    topright_good = check_hashes(p1.topright, p2.topright)
    bottomleft_good = check_hashes(p1.bottomleft, p2.bottomleft)
    bottomright_good = check_hashes(p1.bottomright, p2.bottomright)
    return topleft_good and topright_good and bottomleft_good and bottomright_good

# def get_mountain_coords(fn: str) -> Set[Pos]:
#     if fn.endswith('mountain.png'):
#         topleft = {(0, 11), (0, 12), (1, 11), (1, 12), (2, 12), (3, 11), (3, 12)}
#         main = {(x, y) for x in range(17) for y in range(13, 20)}
#         # (18, 18) is a duplicate of (15, 17)
#         right = {(17, 14), (17, 15), (17, 16), (17, 17), (17, 18), (17, 19), (18, 16), (18, 17), (18, 19)}
#         bottomleft = {(4, 22), (5, 22), (0, 26), (0, 27), (0, 28), (1, 26), (1, 27), (2, 27), (3, 27)}
#         bottom = {(x, y) for x in range(6, 12) for y in range(20, 25)}
#         bottomright = {(12, 22), (13, 22), (14, 22), (15, 22), (12, 23), (13, 23), (14, 23), (15, 23), (16, 23), (12, 24), (13, 24), (13, 25), (15, 20), (16, 20), (17, 20), (18, 20), (17, 21), (18, 21)}
#         # extra = {(0, 6), (1, 6), (2, 6)}
#         extra = {(0, 5), (14, 21)}
#         return topleft | main | right | bottomleft | bottom | bottomright | extra
#     return set()

def get_mountain_coords(fn: str) -> Set[Pos]:
    image = QImage(fn)
    valid_coords = set()
    background_color = qRgb(0, 0, 0)
    for x in range(image.width() // TILEWIDTH):
        for y in range(image.height() // TILEHEIGHT):
            color = image.pixel(x * TILEWIDTH, y * TILEHEIGHT)
            if color != background_color:
                valid_coords.add((x, y))
    print(sorted(valid_coords))
    return valid_coords

def load_mountain_palettes(fn: str, coords: List[Pos]) -> Dict[Pos, MountainPaletteData]:
    palettes: Dict[Pos, MountainPaletteData] = {}
    image = QImage(fn)
    for coord in coords:
        rect = (coord[0] * TILEWIDTH, coord[1] * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
        palette = image.copy(*rect)
        d = MountainPaletteData(palette, coord)
        palettes[coord] = d
    return palettes

def assign_rules(palette_templates: Dict[Pos, MountainPaletteData], fns: List[str]):
    print("Assign Rules")
    # Fns is a list of all example mountain pictures
    for fn in fns:
        print("Processing %s..." % fn)
        image = QImage(fn)
        num_tiles_x = image.width() // TILEWIDTH
        num_tiles_y = image.height() // TILEHEIGHT
        image_palette_data: Dict[Pos, PaletteData] = {}
        for x in range(num_tiles_x):
            for y in range(num_tiles_y):
                rect = (x * TILEWIDTH, y * TILEHEIGHT, TILEWIDTH, TILEHEIGHT)
                palette = image.copy(*rect)
                d = QuadPaletteData(palette)
                image_palette_data[(x, y)] = d
        
        best_matches: Dict[Pos, MountainPaletteData] = {}  # Position: Mountain Template match
        for position, palette in image_palette_data.items():
            mountain_match: MountainPaletteData = is_present(palette, palette_templates)
            if mountain_match:
                best_matches[position] = mountain_match
        # print({k: v.coord for k, v in best_matches.items()})

        for position, mountain_match in best_matches.items():
            # Find adjacent positions
            left = position[0] - 1, position[1]
            right = position[0] + 1, position[1]
            up = position[0], position[1] - 1
            down = position[0], position[1] + 1
            left_palette = best_matches.get(left)
            right_palette = best_matches.get(right)
            up_palette = best_matches.get(up)
            down_palette = best_matches.get(down)
            # determine if those positions are in palette_templates
            # If they are, mark those coordinates in the list of valid coords
            # If not, mark as end validity\
            should_never_be_none = ((5, 8), (13, 3), (13, 4), (12, 4), (12, 5), (11, 6), (12, 6), (11, 7), (12, 7), (11, 8), (12, 8), (11, 9), (12, 9), (12, 10))
            if left[0] >= 0:
                if left_palette:
                    mountain_match.rules['left'][left_palette.coord] += 1
                else:
                    mountain_match.rules['left'][None] += 1
                    if mountain_match.coord in should_never_be_none:
                        print("Left None", position)
            if right[0] < num_tiles_x:
                if right_palette:
                    mountain_match.rules['right'][right_palette.coord] += 1
                else:
                    mountain_match.rules['right'][None] += 1
                    if mountain_match.coord in should_never_be_none:
                        print("Right None", position)
            if up[1] >= 0:
                if up_palette:
                    mountain_match.rules['up'][up_palette.coord] += 1
                else:
                    mountain_match.rules['up'][None] += 1
                    if mountain_match.coord in should_never_be_none:
                        print("Up None", position)
            if down[1] < num_tiles_y:
                if down_palette:
                    mountain_match.rules['down'][down_palette.coord] += 1
                else:
                    mountain_match.rules['down'][None] += 1
                    if mountain_match.coord in should_never_be_none + ((6, 13), (6, 14), (7, 13)):
                        print("Down None", position)

def is_present(palette: QuadPaletteData, palette_templates: Dict[Pos, MountainPaletteData]) -> Optional[MountainPaletteData]:
    for coord, mountain in palette_templates.items():
        if similar(palette, mountain):
            return mountain
    return None

def remove_connections_that_only_appear_once(mountain_palettes: Dict[Pos, MountainPaletteData]) -> Dict[Pos, MountainPaletteData]:
    for palette in mountain_palettes.values():
        for direction in DIRECTIONS:
            palette.rules[direction] = {k: v for k, v in palette.rules[direction].items() if v > 1}
    return mountain_palettes

def remove_infrequent_palettes(mountain_palettes: Dict[Pos, MountainPaletteData]) -> Dict[Pos, MountainPaletteData]:
    # Remove palettes that don't appear very often
    infrequent_limit = 15
    for coord in list(mountain_palettes.keys()):
        palette = mountain_palettes[coord]
        # Only bother with the ones that actually have rules
        if sum(palette.rules['left'].values()) >= infrequent_limit or \
                sum(palette.rules['right'].values()) >= infrequent_limit or \
                sum(palette.rules['up'].values()) >= infrequent_limit or \
                sum(palette.rules['down'].values()) >= infrequent_limit:
            pass
        else:
            del mountain_palettes[coord]
    # Now delete connections
    remaining_coords = mountain_palettes.keys()
    for palette in mountain_palettes.values():
        for direction in DIRECTIONS:
            palette.rules[direction] = {k: v for k, v in palette.rules[direction].items() if k in remaining_coords or k is None}
    return mountain_palettes

def remove_adjacent_palettes(mountain_palettes: Dict[Pos, MountainPaletteData]) -> Dict[Pos, MountainPaletteData]:
    # Make it so that no coord can connect to itself
    for coord, palette in mountain_palettes.items():
        for direction in DIRECTIONS:
            palette.rules[direction] = {k: v for k, v in palette.rules[direction].items() if k != coord}
    return mountain_palettes

def fuse(mountain_palettes: Dict[Pos, MountainPaletteData], parent: Pos, child: Pos) -> Dict[Pos, MountainPaletteData]:
    """Fuses the rules of the child coordinate into the rules of the parent coordinate
    """
    assert parent != child
    if parent in mountain_palettes and child in mountain_palettes:
        parent_palette = mountain_palettes[parent]
        child_palette = mountain_palettes[child]
        for direction in DIRECTIONS:
            parent_palette.rules[direction].update(child_palette.rules[direction])
        # Replace connections to child with connections to parent
        for coord, palette in mountain_palettes.items():
            for direction in DIRECTIONS:
                if child in palette.rules[direction]:
                    if parent in palette.rules[direction]:
                        palette.rules[direction][parent] += palette.rules[direction][child]
                    else:
                        palette.rules[direction][parent] = palette.rules[direction][child]
                    del palette.rules[direction][child]
        del mountain_palettes[child]
    else:
        print(f"Could not find both {parent} and {child} in mountain_palettes")
    return mountain_palettes

def fuse_palettes(mountain_palettes: Dict[Pos, MountainPaletteData]) -> Dict[Pos, MountainPaletteData]:
    """
    Mountains actually have two kinds of shading on their left side (towards the "sun")
    The Mountain solver does not like dealing with this level of discrimination
    so we just fuse the palettes that are completely bright into the 
    palettes that are a little shaded
    Other fusions are done as needed
    """
    # Bright into shaded
    fuse(mountain_palettes, (1, 3), (0, 3))  # Fuse (0, 13) into (1, 13)
    fuse(mountain_palettes, (3, 3), (2, 3))
    fuse(mountain_palettes, (5, 3), (4, 3))
    fuse(mountain_palettes, (1, 4), (0, 4))
    fuse(mountain_palettes, (3, 4), (2, 4))
    fuse(mountain_palettes, (5, 4), (4, 4))
    fuse(mountain_palettes, (1, 6), (0, 6))
    fuse(mountain_palettes, (1, 7), (0, 7))
    fuse(mountain_palettes, (1, 8), (0, 8))
    fuse(mountain_palettes, (1, 9), (0, 9))

    # Fuse similar Bright left side Dark right side tiles
    fuse(mountain_palettes, (8, 3), (7, 3))
    fuse(mountain_palettes, (8, 3), (6, 3))
    fuse(mountain_palettes, (8, 3), (9, 3))
    fuse(mountain_palettes, (8, 3), (11, 4))
    fuse(mountain_palettes, (8, 3), (3, 2))

    # Fuse similar Bright left side, Dark right side with a curve to the right
    fuse(mountain_palettes, (8, 4), (7, 4))
    fuse(mountain_palettes, (8, 4), (6, 4))
    fuse(mountain_palettes, (8, 4), (10, 5))
    fuse(mountain_palettes, (8, 4), (11, 5))

    # Fuse dark crack
    fuse(mountain_palettes, (5, 5), (2, 5))
    fuse(mountain_palettes, (5, 5), (3, 5))
    fuse(mountain_palettes, (5, 5), (4, 5))

    # Fuse dark left corner
    fuse(mountain_palettes, (5, 6), (2, 6))
    fuse(mountain_palettes, (5, 6), (3, 6))
    fuse(mountain_palettes, (5, 6), (4, 6))

    # Fuse dark right corner
    fuse(mountain_palettes, (8, 7), (6, 6))
    fuse(mountain_palettes, (8, 7), (7, 6))
    fuse(mountain_palettes, (8, 7), (8, 6))

    # Fuse topleft corner mountains
    fuse(mountain_palettes, (0, 1), (15, 10))
    fuse(mountain_palettes, (15, 8), (16, 13))

    # Fuse topright corner mountains
    fuse(mountain_palettes, (17, 5), (17, 6))
    fuse(mountain_palettes, (17, 5), (17, 7))

    # Fuse slightly different dark right corner
    fuse(mountain_palettes, (5, 7), (2, 7))
    fuse(mountain_palettes, (5, 7), (3, 7))

    # Fuse Dark top
    fuse(mountain_palettes, (4, 8), (2, 8))
    fuse(mountain_palettes, (4, 8), (3, 8))

    # More bright pairs
    fuse(mountain_palettes, (3, 9), (2, 9))
    fuse(mountain_palettes, (10, 6), (9, 6))
    fuse(mountain_palettes, (6, 12), (4, 12))
    fuse(mountain_palettes, (6, 12), (5, 12))
    fuse(mountain_palettes, (6, 11), (5, 11))
    
    # Bright sheet mountain
    fuse(mountain_palettes, (12, 6), (11, 6))
    fuse(mountain_palettes, (12, 6), (10, 7))
    fuse(mountain_palettes, (12, 6), (11, 7))
    fuse(mountain_palettes, (12, 6), (12, 7))
    fuse(mountain_palettes, (12, 6), (11, 8))
    fuse(mountain_palettes, (12, 6), (12, 8))
    fuse(mountain_palettes, (12, 6), (11, 9))
    fuse(mountain_palettes, (12, 6), (12, 9))
    fuse(mountain_palettes, (12, 6), (12, 10))

    # Dark sheet mountain
    fuse(mountain_palettes, (13, 3), (12, 3))
    fuse(mountain_palettes, (13, 3), (12, 4))
    fuse(mountain_palettes, (13, 3), (12, 5))
    fuse(mountain_palettes, (13, 3), (13, 4))

    return mountain_palettes

def print_rules(mountain_palettes: Dict[Pos, MountainPaletteData]):
    # Do some printing
    print("--- Final Rules ---")
    final_rules = {coord: mountain_palette.rules for coord, mountain_palette in mountain_palettes.items()}
    for coord, rules in sorted(final_rules.items()):
        print("---", coord, "---")
        if rules['left']:
            print('left', rules['left'])
        if rules['right']:
            print('right', rules['right'])
        if rules['up']:
            print('up', rules['up'])
        if rules['down']:
            print('down', rules['down'])

    print("Number of Coordinates:", len(final_rules))
    print("Number of Rules: ", sum(sum(len(mountain_palette[direction]) for direction in DIRECTIONS) for mountain_palette in final_rules.values()))
    return final_rules

# python -m app.map_maker.mountain_data_generation.mountain_maker
if __name__ == '__main__':
    import sys, glob
    try:
        import cPickle as pickle
    except ImportError:
        import pickle

    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)

    tileset = 'app/map_maker/palettes/journey/mountain.png'
    # Which tiles are mountains?
    mountain_coords: Set[Pos] = get_mountain_coords(tileset)
    print(f"Total Mountains: {len(mountain_coords)}")

    mountain_palettes: Dict[Pos, MountainPaletteData] = load_mountain_palettes(tileset, mountain_coords)
    mountain_data_dir = glob.glob('app/map_maker/mountain_data_generation/maps_with_mountains/*.png')
    # Stores rules in the palette data itself
    assign_rules(mountain_palettes, mountain_data_dir)
    # input()
    # print_rules(mountain_palettes)
    # We don't do this because it's sometimes useful to have palettes be adjacent to themselves
    # mountain_palettes = remove_adjacent_palettes(mountain_palettes)
    mountain_palettes = fuse_palettes(mountain_palettes)
    # input()
    # print_rules(mountain_palettes)
    mountain_palettes = remove_connections_that_only_appear_once(mountain_palettes)
    # input()
    # print_rules(mountain_palettes)
    mountain_palettes = remove_infrequent_palettes(mountain_palettes)
    # input()
    final_rules = print_rules(mountain_palettes)

    data_loc = 'app/map_maker/mountain_data_generation/mountain_data.p'
    with open(data_loc, 'wb') as fp:
        pickle.dump(final_rules, fp)

    # input()
    # backup_data_loc = 'app/map_maker/mountain_data_generation/mountain_data_bak.p'
    # with open(backup_data_loc, 'rb') as fp:
    #     backup_rules = pickle.load(fp)
    #     for coord, rules in sorted(backup_rules.items()):
    #         print("---", coord, "---")
    #         if rules['left']:
    #             print('left', rules['left'])
    #         if rules['right']:
    #             print('right', rules['right'])
    #         if rules['up']:
    #             print('up', rules['up'])
    #         if rules['down']:
    #             print('down', rules['down'])
    #     print("Number of Coordinates:", len(backup_rules))
    #     print("Number of Rules: ", sum(sum(len(mountain_palette[direction]) for direction in DIRECTIONS) for mountain_palette in backup_rules.values()))
