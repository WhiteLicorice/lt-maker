from app.constants import TILEWIDTH, TILEHEIGHT
from app.data.database.database import DB
from app.events.regions import RegionType

from app.engine.sprites import SPRITES
from app.engine import engine, line_of_sight, aura_funcs, skill_system
from app.engine.movement.move_selection import MoveSelection
from app.engine.game_state import game

import logging

class HighlightController():
    # As on the GBA (gOpenLimitViewImgLut), squares newly shown grow out of their
    # bottom left corner, a frame at a time, before they are drawn whole
    opening_sizes = (5, 7, 9, 11, 13, 15)
    starting_cutoff = 0  # Frames into opening

    def __init__(self):
        self.images = {'spell': SPRITES.get('highlight_green'),
                       'attack': SPRITES.get('highlight_red'),
                       'splash': SPRITES.get('highlight_lightred'),
                       'possible_move': SPRITES.get('highlight_lightblue'),
                       'move': SPRITES.get('highlight_blue'),
                       'possible_xcom_move': SPRITES.get('highlight_lightyellow'),
                       'xcom_move': SPRITES.get('highlight_yellow'),
                       'aura': SPRITES.get('highlight_lightpurple'),
                       'spell_splash': SPRITES.get('highlight_lightgreen')}

        self.highlights = {k: set() for k in self.images}
        self.transitions = {k: self.starting_cutoff for k in self.images}

        self.last_update = 0
        self.update_idx = 0

        self.current_hover = None

        self.formation_highlights = []
        self.escape_highlights = []

    def add_highlight(self, position, name, allow_overlap=False):
        if not allow_overlap:
            for k in self.images:
                self.highlights[k].discard(position)
        self.highlights[name].add(position)
        self.transitions[name] = self.starting_cutoff

    def add_highlights(self, positions: set, name: str, allow_overlap: bool = False):
        if not allow_overlap:
            for k in self.images:
                self.highlights[k] -= positions
        self.highlights[name] |= positions
        self.transitions[name] = self.starting_cutoff

    def remove_highlights(self, name=None):
        if name:
            self.highlights[name].clear()
            self.transitions[name] = self.starting_cutoff
        else:
            for k in self.images:
                self.highlights[k].clear()
                self.transitions[k] = self.starting_cutoff
        self.current_hover = None

    def remove_aura_highlights(self):
        self.highlights['aura'].clear()

    def handle_hover(self):
        hover_unit = game.cursor.get_hover()
        if self.current_hover and hover_unit != self.current_hover:
            self.remove_highlights()
        if hover_unit and hover_unit != self.current_hover:
            selection = game.path_system.get_move_selection(
                hover_unit, zero_move=hover_unit.team != 'player')
            self.display_highlights(hover_unit, selection, light=True)
            self.display_aura_highlights(hover_unit)
        self.current_hover = hover_unit

    def display_moves(self, valid_moves, light=False):
        name = 'possible_move' if light else 'move'
        self.add_highlights(valid_moves, name)

    def display_xcom_moves(self, valid_xcom_moves, light=False):
        name = 'possible_xcom_move' if light else 'xcom_move'
        self.add_highlights(valid_xcom_moves, name, allow_overlap=True)

    def display_possible_attacks(self, valid_attacks, light=False):
        name = 'splash' if light else 'attack'
        self.add_highlights(valid_attacks, name)

    def display_possible_spell_attacks(self, valid_attacks, light=False):
        name = 'spell_splash' if light else 'spell'
        self.add_highlights(valid_attacks, name)

    def display_highlights(self, unit, selection: MoveSelection, light=False):
        """Draws where the unit may move and what it could hit from there.

        The selection is handed in rather than worked out here -- it is the same object
        the cursor and the move state act on, so the highlights cannot promise a move
        the engine will refuse.
        """
        valid_moves = selection.normal
        valid_attacks = game.target_system.get_all_attackable_positions_spells(unit, valid_moves)
        self.display_possible_spell_attacks(valid_attacks, light=light)
        valid_attacks = game.target_system.get_all_attackable_positions_weapons(unit, valid_moves)
        self.display_possible_attacks(valid_attacks, light=light)
        self.display_moves(valid_moves, light=light)
        self.display_xcom_moves(selection.xcom, light=light)

    def display_aura_highlights(self, unit):
        for skill in unit.skills:
            if skill.aura and not skill.hide_aura:
                positions = game.board.get_aura_positions(skill.subskill)
                if DB.constants.value('aura_los'):
                    aura_range = skill_system.get_max_shape_range(skill)
                    if aura_range is None: #Use default behavior
                        aura_range = skill.aura_range.value
                    positions = line_of_sight.line_of_sight({unit.position}, positions, aura_range)
                self.add_highlights(set(positions), 'aura', allow_overlap=True)

    def show_formation(self, positions: list):
        self.formation_highlights += positions

    def hide_formation(self):
        self.formation_highlights.clear()

    def update(self):
        self.update_idx = (self.update_idx + 1) % 64

    def draw(self, surf, cull_rect):
        # Handle Formation Highlight
        formation_image = SPRITES.get('highlight_blue')
        rect = (self.update_idx//4 * TILEWIDTH, 0, TILEWIDTH, TILEHEIGHT)
        formation_image = engine.subsurface(formation_image, rect)
        for position in self.formation_highlights:
            surf.blit(formation_image, (position[0] * TILEWIDTH - cull_rect[0], position[1] * TILEHEIGHT - cull_rect[1]))

        # Handle Region Highlights
        escape_image = SPRITES.get('highlight_yellow') #Not needed since it can now be achieved through the region highlight, but kept for backward compatability
        rect = (self.update_idx//4 * TILEWIDTH, 0, TILEWIDTH, TILEHEIGHT)
        escape_image = engine.subsurface(escape_image, rect)
        for region in game.level.regions:
            if region.highlight is not None and region.region_type in (RegionType.NORMAL, RegionType.STATUS, RegionType.TERRAIN, RegionType.EVENT):
                highlight_image = SPRITES.get('highlight_' + region.highlight)
                highlight_image = engine.subsurface(highlight_image, rect)
                for position in region.get_all_positions():
                    surf.blit(highlight_image, (position[0] * TILEWIDTH - cull_rect[0], position[1] * TILEHEIGHT - cull_rect[1]))
            elif (region.region_type == RegionType.EVENT and region.sub_nid in ('Escape', 'Arrive')):
                for position in region.get_all_positions():
                    surf.blit(escape_image, (position[0] * TILEWIDTH - cull_rect[0], position[1] * TILEHEIGHT - cull_rect[1]))

        # Regular highlights
        for name, highlight_set in self.highlights.items():
            if not highlight_set:
                continue
            frame = self.transitions[name]
            if frame < len(self.opening_sizes):
                size = self.opening_sizes[frame]
                self.transitions[name] += 1
            else:
                size = TILEWIDTH
            # The bottom left corner of the square, that size
            rect = (self.update_idx//4 * TILEWIDTH, TILEHEIGHT - size, size, size)
            image = engine.subsurface(self.images[name], rect)
            for position in highlight_set:
                surf.blit(image, (position[0] * TILEWIDTH - cull_rect[0], position[1] * TILEHEIGHT - cull_rect[1] + TILEHEIGHT - size))
        return surf
