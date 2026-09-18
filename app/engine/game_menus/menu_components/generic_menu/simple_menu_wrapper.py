from __future__ import annotations

from typing import Callable, List, Tuple

from app.constants import COLORKEY
from app.data.database.database import DB
from app.data.database.items import ItemPrefab
from app.data.database.klass import Klass
from app.data.database.skills import SkillPrefab
from app.data.resources.portraits import INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT, CHIBI_HEIGHT
from app.data.resources.resources import RESOURCES
from app.engine import engine
from app.engine.game_menus.menu_components.generic_menu.simple_menu import \
    SimpleIconTable
from app.engine.game_state import game
from app.engine.graphics.ui_framework.ui_framework import UIComponent
from app.engine.graphics.ui_framework.ui_framework_layout import convert_align
from app.engine.icons import draw_chibi, get_icon, get_icon_by_nid, get_portrait_from_nid
from app.engine.objects.item import ItemObject
from app.engine.objects.unit import UnitObject
from app.engine.unit_sprite import load_klass_sprite
from app.sprites import SPRITES
from app.utilities.enums import Alignments, HAlignment, Orientation
from app.utilities.typing import NID

ICON_HEIGHT = 16

# Rows of these types show animated map sprites, so they are rebuilt on every update
MAP_SPRITE_DATA_TYPES = ('type_unit', 'type_class')

HEIGHT_DATA_TYPE_MAP = {
    'type_base_item': ICON_HEIGHT,
    'type_game_item': ICON_HEIGHT,
    'type_skill': ICON_HEIGHT,
    'type_unit': ICON_HEIGHT,
    'type_class': ICON_HEIGHT,
    'type_portrait': INFO_PORTRAIT_HEIGHT,
    'type_chibi': CHIBI_HEIGHT,
    'type_icon': ICON_HEIGHT,
    'str': ICON_HEIGHT,
}

class SimpleMenuUI():
    def __init__(self, data: List[str] | Callable[[], List] = None, data_type: str = 'str',
                 title: str = None, rows: int = 0, cols: int = 1, row_width: int = -1,
                 alignment: Alignments = Alignments.TOP_LEFT, bg: str = 'menu_bg_base',
                 orientation: Orientation = Orientation.VERTICAL, text_align: HAlignment = HAlignment.LEFT):
        self._data_type = data_type
        self._data: List = None
        self._get_data: Callable[[], List] = None

        # UI stuff
        self.base_component = UIComponent.create_base_component()
        default_row_height = HEIGHT_DATA_TYPE_MAP.get(data_type, ICON_HEIGHT)
        self.table: SimpleIconTable = self.create_table(self.base_component, rows, cols, title, row_width, bg, orientation, text_align, default_row_height)
        halign, valign = convert_align(alignment)
        self.table.props.h_alignment = halign
        self.table.props.v_alignment = valign
        self.table.margin = (10, 10, 10, 10)
        self.base_component.add_child(self.table)

        if callable(data):
            self._get_data = data
            self.set_data(self._get_data())
        else:
            self.set_data(data)

    def create_table(self, base_component, rows, cols, title, row_width, bg, orientation, text_align, entry_height) -> SimpleIconTable:
        return SimpleIconTable('table', base_component, num_rows=rows,
                               num_columns=cols, title=title, row_width=row_width,
                               background=bg, orientation=orientation,
                               option_text_align=text_align, default_row_height=entry_height)
    def set_data(self, raw_data):
        if self._data == raw_data and self._data_type not in MAP_SPRITE_DATA_TYPES:
            return
        self._data = raw_data
        parsed_data = self.parse_data(raw_data)
        self.table.set_data(parsed_data)

    def parse_data(self, data: List[str]) -> List[str] | List[Tuple[engine.Surface, str, NID]]:
        """Takes input of form:
        ['nid1', 'nid2', 'nid3', 'nid4']
        or of form:
        ['nid1|text1', 'nid2|text2', 'nid3|text3']
        """
        split_data = []
        for datum in data:
            datum = str(datum)
            processed = datum.split('|')
            nid = processed[0]
            name = None
            if len(processed) > 1:
                name = processed[1]
            split_data.append((nid, name))
        if self._data_type == 'type_base_item':
            return [self.parse_item(DB.items.get(item_nid), choice_text, item_nid) for item_nid, choice_text in split_data]
        if self._data_type == 'type_game_item':
            return [self.parse_item(game.item_registry.get(int(item_uid)), choice_text, item_uid) for item_uid, choice_text in split_data]
        elif self._data_type == 'type_skill':
            return [self.parse_skill(DB.skills.get(skill_nid), choice_text) for skill_nid, choice_text in split_data]
        elif self._data_type == 'type_unit':
            return [self.parse_unit(game.unit_registry.get(unit_nid), choice_text) for unit_nid, choice_text in split_data]
        elif self._data_type == 'type_class':
            return [self.parse_klass(DB.classes.get(klass_nid), choice_text) for klass_nid, choice_text in split_data]
        elif self._data_type == 'type_portrait':
            return [self.parse_portrait(portrait_nid) for portrait_nid, _ in split_data]
        elif self._data_type == 'type_chibi':
            return [self.parse_chibi(chibi_nid) for chibi_nid, _ in split_data]
        elif self._data_type == 'type_icon':
            parsed_data = [(datum.split('-'), choice_text) for datum, choice_text in split_data]
            return [self.parse_custom_icon_data(tup, choice_text) for tup, choice_text in parsed_data]
        else:
            return [(None, choice_text if choice_text else choice_nid, choice_nid) for choice_nid, choice_text in split_data]

    def parse_klass(self, klass: Klass, choice_name: str) -> Tuple[UIComponent, str, str]:
        if klass:
            klass_icon = UIComponent()
            klass_icon.size = (16, 16)
            klass_icon.overflow = (12, 0, 12, 0) # map sprites are much larger than an icon
            map_sprite = load_klass_sprite(klass.nid)
            if map_sprite:  # A class without a map sprite resource shows just its name
                klass_icon.add_surf(map_sprite.create_image('passive'), (-24, -24))
            return (klass_icon, klass.name if not choice_name else choice_name, klass.nid)
        else:
            return (get_icon(None), "ERR", "ERR")

    def parse_custom_icon_data(self, tup: Tuple[NID, str, str, str], choice_name: str) -> Tuple[engine.Surface, str, str]:
        icon_sheet_nid = tup[0]
        icon_x = int(tup[1])
        icon_y = int(tup[2])
        choice_nid = tup[3]
        icon = get_icon_by_nid(icon_sheet_nid, icon_x, icon_y)
        if choice_name:
            return (icon, choice_name, choice_nid)
        return (icon, choice_nid)

    def parse_skill(self, skill: SkillPrefab, choice_name: str) -> Tuple[engine.Surface, str, str]:
        if skill:
            return (get_icon(skill), skill.name if not choice_name else choice_name, skill.nid)
        else:
            return (get_icon(skill), "ERR", "ERR")

    def parse_item(self, item: ItemPrefab | ItemObject, choice_name: str, choice_value: str) -> Tuple[engine.Surface, str, str]:
        if item:
            return (get_icon(item), item.name if not choice_name else choice_name, choice_value)
        else:
            return (get_icon(item), "ERR", "ERR")

    def parse_unit(self, unit: UnitObject, choice_name: str) -> Tuple[engine.Surface, str, str]:
        if unit:
            unit_sprite = unit.sprite.create_image('passive')
            unit_icon = UIComponent()
            unit_icon.size = (16, 16)
            unit_icon.overflow = (12, 0, 12, 0) # the unit sprites are kind of enormous
            unit_icon.add_surf(unit_sprite, (-24, -24))
            return (unit_icon, unit.name if not choice_name else choice_name, unit.nid)
        else:
            return (get_icon(None), "ERR", "ERR")

    def parse_portrait(self, portrait_nid: NID) -> Tuple[engine.Surface, str, str]:
        portrait, offset = get_portrait_from_nid(portrait_nid)
        if not portrait:
            portrait = engine.create_surface((INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT))
        else:
            portrait = engine.subsurface(portrait, (*offset, INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT))
        return (portrait, "", "")

    def parse_chibi(self, chibi_nid: NID) -> Tuple[engine.Surface, str, str]:
        chibi_surf = engine.create_surface((32, 32), True)
        chibi = draw_chibi(chibi_surf, chibi_nid, (0, 0))
        return (chibi, "", "")

    def update(self):
        if self._get_data:
            new_data = self._get_data()
            self.set_data(new_data)
        elif self._data_type in MAP_SPRITE_DATA_TYPES: # we need to reset data to update sprites
            # elif because while not mutually exclusive, we only ever need one call of "set_data"
            if self._get_data:
                new_data = self._get_data()
            else:
                new_data = self._data
            self.set_data(new_data)
        return True

    def draw(self, surf):
        ui_surf = self.base_component.to_surf()
        surf.blit(ui_surf, (0, 0))
        return surf
