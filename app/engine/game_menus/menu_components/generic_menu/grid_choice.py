from __future__ import annotations

from math import ceil, floor
from typing import Any, Dict, List, Optional, Tuple, Type

from app.constants import WINHEIGHT, WINWIDTH
from app.data.database.database import DB
from app.engine import engine
from app.engine.base_surf import create_base_surf
from app.engine.game_menus.animated_options import (BasicKlassOption,
                                                    BasicUnitOption)
from app.engine.game_menus.icon_options import (BasicIconOption,
                                                BasicItemOption,
                                                BasicSkillOption)
from app.engine.game_menus.menu_components.generic_menu.cursor_hand import (
    CursorDrawMode, CursorHand)
from app.engine.game_menus.string_options import (BasicChibiOption,
                                                  BasicPortraitOption,
                                                  IMenuOption, TextOption)
from app.engine.game_state import game
from app.engine.graphics.text.text_renderer import (font_height, render_text,
                                                    text_width)
from app.engine.graphics.ui_framework.ui_framework_layout import convert_align
from app.engine.gui import ScrollArrow, ScrollBar
from app.engine.input_manager import get_input_manager
from app.engine.objects.item import ItemObject
from app.engine.objects.skill import SkillObject
from app.engine.objects.unit import UnitObject
from app.engine.sound import get_sound_thread
from app.utilities.enums import Alignments, HAlignment, Orientation, VAlignment
from app.utilities.str_utils import is_int
from app.utilities.typing import NID
from app.utilities.utils import clamp, float_eq, sign, tuple_add, tuple_sub, calculate_distance

CHOICE_TYPES: Dict[str, Type[IMenuOption]] = {
    'type_skill': BasicSkillOption,
    'type_base_item': BasicItemOption,
    'type_game_item': BasicItemOption,
    'type_unit': BasicUnitOption,
    'type_class': BasicKlassOption,
    'type_icon': BasicIconOption,
    'type_portrait': BasicPortraitOption,
    'type_chibi': BasicChibiOption
}

def cast_value(data_type: str, val: str):
    if data_type == 'type_game_item':
        return int(val)
    return val

class ChoiceMenuOptionFactory():
    @staticmethod
    def create_option(option_type: Type[IMenuOption], idx: int, value: str, disp_value: Any = None, row_width: int = 0, text_align: HAlignment = HAlignment.LEFT):
        if option_type == TextOption:
            return TextOption(idx, value, disp_value, row_width, align=text_align)
        elif option_type == BasicItemOption:
            if not value:
                return BasicItemOption.empty_option(idx, value or disp_value, row_width, align=text_align)
            if isinstance(value, ItemObject):
                return BasicItemOption.from_item(idx, value, disp_value, row_width, align=text_align)
            elif isinstance(value, int):
                return BasicItemOption.from_uid(idx, value, disp_value, row_width, align=text_align)
            elif isinstance(value, str):
                return BasicItemOption.from_nid(idx, value, disp_value, row_width, align=text_align)
            raise ValueError("Unknown item: " + str(value))
        elif option_type == BasicSkillOption:
            if isinstance(value, SkillObject):
                return BasicSkillOption.from_skill(idx, value, disp_value, row_width, align=text_align)
            elif isinstance(value, int):
                return BasicSkillOption.from_uid(idx, value, disp_value, row_width, align=text_align)
            elif isinstance(value, str):
                return BasicSkillOption.from_nid(idx, value, disp_value, row_width, align=text_align)
            raise ValueError("Unknown skill: " + value)
        elif option_type == BasicUnitOption:
            if isinstance(value, UnitObject):
                return BasicUnitOption.from_unit(idx, value, disp_value, row_width, align=text_align)
            elif isinstance(value, str):
                return BasicUnitOption.from_nid(idx, value, disp_value, row_width, align=text_align)
            raise ValueError("Unknown unit: " + value)
        elif option_type == BasicKlassOption:
            return BasicKlassOption(idx, value, disp_value, row_width, align=text_align)
        elif option_type == BasicIconOption:
            return BasicIconOption(idx, value, disp_value, row_width, align=text_align)
        elif option_type == BasicPortraitOption:
            return BasicPortraitOption(idx, value)
        elif option_type == BasicChibiOption:
            return BasicChibiOption(idx, value)
        return TextOption(idx, value, disp_value, row_width, align=text_align)


class LayoutManager():
    @staticmethod
    def align_to_screen_position(alignment: Alignments, margin: int, size: Tuple[int, int], window_size: Tuple[int, int] = (WINWIDTH, WINHEIGHT)) -> Tuple[int, int]:
        halign, valign = convert_align(alignment)
        x, y = 0, 0
        sw, sh = size
        screen_w, screen_h = window_size
        if halign is HAlignment.LEFT:
            x = margin
        elif halign is HAlignment.RIGHT:
            x = screen_w - sw - margin
        else:
            x = screen_w // 2 - sw // 2

        if valign is VAlignment.TOP:
            y = margin
        elif valign is VAlignment.BOTTOM:
            y = screen_h - sh - margin
        else:
            y = screen_h // 2 - sh // 2

        return x, y


class GridChoiceMenu():
    def __init__(self, data: List, display_values: Optional[List] = None, title: Optional[str] = None, data_type: str = "text",
                 size: Optional[Tuple[int, int]] = None, row_width: int = 0, alignment: Alignments | Tuple[int, int] = Alignments.CENTER,
                 orientation: Orientation = Orientation.VERTICAL,
                 bg: NID = 'menu_bg_base', text_align: HAlignment = HAlignment.LEFT) -> None:
        self._should_autosize = not bool(size)
        self._grid_size: Tuple[int, int] = size or self._autosize_grid(data)
        self._data_type: str = data_type
        self._row_width: int = row_width
        self._title: Optional[str] = title
        self._bg_name = bg
        self._orientation: Orientation = orientation
        self._alignment: Alignments | Tuple[int, int] = alignment
        self._text_align = text_align

        self._option_data = self._build_data(
            data, display_values, self._data_type, self._row_width)
        self._data = data
        self._display_values = display_values
        self._item_size = self._determine_item_size(
            self._option_data, self._row_width)

        self._cursor_idx: int = 0

        self._scroll: Tuple[float, float] = (0, 0)
        self._scroll_to: Tuple[float, float] = (0, 0)

        self._cached_data_surf: engine.Surface = self._build_full_grid_surf()

        self.cursor_hand = CursorHand()
        self._should_draw_arrows = False
        self._create_arrows()
        self.scroll_bar = ScrollBar()
        self._should_draw_scrollbar = False
        if self._total_grid_size()[1] > self.num_rows():
            self._should_draw_scrollbar = True
        self._cached_bg: engine.Surface = self._build_bg()
        self._next_scroll_time = 0

    def set_scrollbar(self, should_draw_scrollbar):
        if self._orientation == Orientation.VERTICAL and self._total_grid_size()[1] > self.num_rows():
            self._should_draw_scrollbar = should_draw_scrollbar
        else:
            self._should_draw_scrollbar = False
        self._cached_bg = self._build_bg()

    def set_arrows(self, should_draw_arrows):
        if self._orientation == Orientation.HORIZONTAL:
            self._should_draw_arrows = should_draw_arrows
        else:
            self._should_draw_arrows = False

    def _create_arrows(self):
        left, top = self._get_screen_position()
        width, height = self._get_pixel_size()
        v_offset = 16 if self._title else 0
        h_offset = -5
        v_offset -= 4
        arrow_height = (height - v_offset) / 2 + v_offset
        self.lscroll_arrow = ScrollArrow(
            'left', (left + h_offset, top + arrow_height))
        self.rscroll_arrow = ScrollArrow(
            'right', (left + width + h_offset, top + arrow_height))
        if self.num_rows() == 1 and self.num_cols() > self._total_grid_size()[0]:
            self._should_draw_arrows = True

    def num_rows(self):
        return self._grid_size[1]

    def num_cols(self):
        return self._grid_size[0]

    def relative_cursor_coord(self) -> Tuple[int, int]:
        scroll_x, scroll_y = map(int, self._scroll)
        cursor_x, cursor_y = self._get_coord_of_option_idx(self._cursor_idx)
        return max(0, cursor_x - scroll_x), max(0, cursor_y - scroll_y)

    def set_data(self, data: List, display_values: Optional[List] = None):
        selected_idx = self.get_selected_idx()
        if self._should_autosize:
            self._grid_size: Tuple[int, int] = self._autosize_grid(data)
        self._option_data = self._build_data(
            data, display_values, self._data_type, self._row_width)
        self._data = data
        self._display_values = display_values
        self._item_size = self._determine_item_size(
            self._option_data, self._row_width)
        self._cached_bg: engine.Surface = self._build_bg()
        self._cached_data_surf: engine.Surface = self._build_full_grid_surf()
        self.move_cursor(selected_idx)

    def set_cursor_mode(self, draw_mode: CursorDrawMode):
        self.cursor_hand.mode = draw_mode

    def move_right(self, first_push: bool = False) -> bool:
        """Move the cursor to the right.

        Args:
            first_push (bool, optional): Whether this movement is due to button press or button hold.

        Returns:
            bool: Whether the cursor actually moved.
        """
        cursor_rx, _ = self.relative_cursor_coord()
        if cursor_rx == self.num_cols() - 1:
            self.rscroll_arrow.pulse()
        if first_push:
            next_idx = (self._cursor_idx + 1) % len(self._option_data)
        else:
            next_idx = min(self._cursor_idx + 1, len(self._option_data) - 1)
        if next_idx == self._cursor_idx:
            return False
        self.move_cursor(next_idx)
        return True

    def move_left(self, first_push: bool = False) -> bool:
        """Move the cursor to the left.

        Args:
            first_push (bool, optional): Whether this movement is due to button press or button hold.

        Returns:
            bool: Whether the cursor actually moved.
        """
        cursor_rx, _ = self.relative_cursor_coord()
        if cursor_rx == 0:
            self.lscroll_arrow.pulse()
        if first_push:
            next_idx = (self._cursor_idx - 1) % len(self._option_data)
        else:
            next_idx = max(0, self._cursor_idx - 1)
        if next_idx == self._cursor_idx:
            return False
        self.move_cursor(next_idx)
        return True

    def move_up(self, first_push: bool = False) -> bool:
        """ Move the cursor up.

        Args:
            first_push (bool, optional): Whether this movement is due to button press or button hold.

        Returns:
            bool: Whether the cursor actually moved.
        """
        num_cols, num_rows = self._total_grid_size()
        if first_push:
            next_idx = self._cursor_idx - num_cols
            if next_idx < 0:
                next_idx += num_cols * num_rows
            while(next_idx >= len(self._option_data)):
                next_idx -= num_cols
        else:
            next_idx = self._cursor_idx - num_cols
            if next_idx < 0:
                return
        if next_idx == self._cursor_idx:
            return False
        self.move_cursor(next_idx)
        return True

    def move_down(self, first_push: bool = False) -> bool:
        """ Move the cursor down.

        Args:
            first_push (bool, optional): Whether this movement is due to button press or button hold.

        Returns:
            bool: Whether the cursor actually moved.
        """
        num_cols = self._total_grid_size()[0]
        next_idx = self._cursor_idx + num_cols
        if next_idx >= len(self._option_data):
            if first_push:
                next_idx = next_idx % num_cols
            else:
                return
        if next_idx == self._cursor_idx:
            return False
        self.move_cursor(next_idx)
        return True

    def move_cursor(self, idx: int) -> bool:
        curr_scroll = self._scroll
        idx = clamp(idx, 0, len(self._option_data) - 1)
        old_coord = self._get_coord_of_option_idx(self._cursor_idx)
        new_coord = self._get_coord_of_option_idx(idx)
        self._cursor_idx = idx
        scroll_to = self._identify_minimum_scroll_to_loc(
            tuple(map(int, self._scroll)), tuple(map(float, new_coord)))
        self.scroll_to(scroll_to)
        if new_coord[1] > old_coord[1]:
            self.cursor_hand.y_offset_down()
        # Only if no scrolling
        elif new_coord[1] < old_coord[1]:
            self.cursor_hand.y_offset_up()
        return not (curr_scroll == self._scroll == self._scroll_to)

    def scroll_to(self, coord: Tuple[float, float]):
        # If it's really far away, don't bother even scrolling, just jump
        if calculate_distance(self._scroll, coord) > 4:
            self._scroll_to = coord
            self._scroll = coord
        else:
            self._scroll_to = coord

    def _total_grid_size(self) -> Tuple[int, int]:
        if self._orientation == Orientation.VERTICAL:
            # constraint on num_cols
            num_cols = self.num_cols()
            return num_cols, ((len(self._option_data) - 1) // num_cols) + 1
        else:
            # constraint on num_rows
            num_rows = self.num_rows()
            return ((len(self._option_data) - 1) // num_rows) + 1, num_rows

    def _get_index_of_coord(self, coord: Tuple[int, int]) -> int:
        nx, _ = self._total_grid_size()
        x, y = coord
        return x + y * nx

    def _get_coord_of_option_idx(self, idx: int) -> Tuple[int, int]:
        x, _ = self._total_grid_size()
        return idx % x, idx // x

    def _is_option_visible(self, idx: int) -> bool:
        top_left_coord = tuple(map(floor, self._scroll))
        bottom_right_coord = tuple(
            map(ceil, tuple_add(self._scroll, self._grid_size)))
        option_coord = self._get_coord_of_option_idx(idx)
        tlx, tly = top_left_coord
        brx, bry = bottom_right_coord
        ox, oy = option_coord
        return tlx <= ox < brx and tly <= oy < bry

    def _get_pixel_coord_of_coord(self, coord: Tuple[float, float]) -> Tuple[int, int]:
        iw, ih = self._item_size
        x, y = coord
        return int(x * iw), int(y * ih)

    def _get_pixel_size(self) -> Tuple[int, int]:
        title_width, title_height = 0, 0
        if self._title:
            title_width, title_height = text_width(
                'text', self._title), font_height('text')
        item_width, item_height = self._item_size
        total_height = self.num_rows() * item_height + title_height
        total_width = max(self.num_cols() * item_width, title_width)
        return total_width + 16, total_height + 8

    def _get_screen_position(self) -> Tuple[int, int]:
        if isinstance(self._alignment, Alignments):
            return LayoutManager.align_to_screen_position(self._alignment, 10, self._get_pixel_size())
        return self._alignment

    def get_selected_idx(self) -> int:
        if self._cursor_idx < len(self._option_data):
            return self._cursor_idx
        raise ValueError("Cursor at invalid index")

    def get_selected(self) -> Any:
        if self._cursor_idx < len(self._option_data):
            return self._data[self._cursor_idx]
        raise ValueError("Cursor at invalid index")

    def get_topleft_of_idx(self, idx: int) -> Tuple[int, int]:
        """
        Return the pixel position of the topleft of this index
        """
        menu_left, menu_top = self._get_screen_position()
        if self._title:
            menu_top += 16
        sel_x, sel_y = self._get_coord_of_option_idx(idx)
        scroll_x, scroll_y = self._scroll
        offset_coord = sel_x - scroll_x, sel_y - scroll_y
        px, py = self._get_pixel_coord_of_coord(offset_coord)
        px = clamp(px + menu_left, 0, WINWIDTH)
        py = clamp(py + menu_top, 0, WINHEIGHT)
        return (px, py)
        
    def _get_rects(self) -> List[Tuple[int, Tuple[int, int, int, int]]]:
        """
        Return a list of pairs of: indexes of visible choices, rectangles (x, y, width, height) of bounding boxes around those choices
        """
        choices = self._option_data
        indexed_rects = []
        for idx, choice in enumerate(choices):
            if self._is_option_visible(idx):
                left, top = self.get_topleft_of_idx(idx)
                rect = (left, top, choice.width(), choice.height())
                indexed_rects.append((idx, rect))

        return indexed_rects
        
    def _is_scrolling(self) -> bool:
        return not ((1.0*self._scroll[0]).is_integer() and (1.0*self._scroll[1]).is_integer())
        
    def _mouse_move(self, idx: int):
        if engine.get_time() > self._next_scroll_time and not self._is_scrolling():
            did_scroll = self.move_cursor(idx)
            if did_scroll:
                self._next_scroll_time = engine.get_time() + 50
        
    def handle_mouse(self) -> bool:
        mouse_position = get_input_manager().get_mouse_position()
        if mouse_position:
            mouse_x, mouse_y = mouse_position
            for idx, option_rect in self._get_rects():
                x, y, width, height = option_rect
                if x <= mouse_x <= x + width and y <= mouse_y <= y + height:
                    self._mouse_move(idx)
                    return True
        return False

    def _autosize_grid(self, data: List[Any]):
        return (1, min(len(data), 1))

    def _resolve_data_type(self, data_type: str) -> Type[IMenuOption]:
        return CHOICE_TYPES.get(data_type, TextOption)

    def _is_option_oversize(self):
        return self._resolve_data_type(self._data_type).is_oversize()

    def _build_bg(self) -> engine.Surface:
        tw, th = self._get_pixel_size()
        if self._bg_name:
            bg_surf = create_base_surf(tw, th, self._bg_name)
        else:  # No bg
            bg_surf = engine.create_surface((tw, th), transparent=True)
        return bg_surf

    def _build_data(self, data: List[Any], display_values: Optional[List[Any]], data_type: str, row_width: int) -> List[IMenuOption]:
        display_values = display_values or data
        options: List[IMenuOption] = []
        max_width = 0
        for i in range(len(data)):
            value = data[i]
            disp_value = display_values[i]
            new_option = ChoiceMenuOptionFactory.create_option(self._resolve_data_type(
                data_type), i, cast_value(data_type, value), disp_value, row_width, self._text_align)
            options.append(new_option)
            max_width = max(max_width, new_option.width())
        # normalize option width
        for option in options:
            option.set_width(max_width)
        return options

    def _build_full_grid_surf(self) -> engine.Surface:
        x, y = self._total_grid_size()
        iwidth, iheight = self._item_size
        width = x * iwidth
        height = y * iheight
        blank_surf = engine.create_surface((width, height), True)
        ox, oy = 0, 0
        for option in self._option_data:
            option.draw(blank_surf, ox, oy)
            ox += iwidth
            if ox == width:
                oy += iheight
                ox = 0
        return blank_surf

    def _determine_item_size(self, option_data: List[IMenuOption], row_width: int) -> Tuple[int, int]:
        if not option_data:
            # arbitrarily chosen as a typical field size
            return 80, 16
        max_height = 16
        max_width = 0
        for option in option_data:
            max_width = max(max_width, option.width())
            max_height = max(max_height, option.height())
        if self._title:
            title_width = text_width('text', self._title)
            per_col_width = title_width // self.num_cols()
            max_width = max(per_col_width, max_width)
        return (row_width or max_width), max_height

    def _identify_minimum_scroll_to_loc(self, scroll: Tuple[float, float], loc: Tuple[float, float]) -> Tuple[float, float]:
        """Identifies the scroll location that allows loc to be visible with a minimum of net movement.
        Scrolls pre-emptively to buffer the next row.
        """
        ncols, nrows = self.num_cols(), self.num_rows()
        sx, sy = scroll
        lb, rb = sx, sx + ncols
        ub, db = sy, sy + nrows
        nx, ny = loc

        fx, fy = scroll
        if nx < lb:
            fx = nx
        elif nx >= rb:
            fx = nx - ncols + 1

        if ny < ub:
            fy = ny
        elif ny >= db:
            fy = ny - nrows + 1
        return fx, fy

    def _handle_scrolling(self):
        EPSILON = 0.25
        SCROLL_SPEED = 0.25
        sx, sy = self._scroll
        goal_sx, goal_sy = self._scroll_to
        if not float_eq(sx, goal_sx, EPSILON):
            sx += SCROLL_SPEED * sign(goal_sx - sx)
        else:
            sx = goal_sx

        if not float_eq(sy, goal_sy, EPSILON):
            sy += SCROLL_SPEED * sign(goal_sy - sy)
        else:
            sy = goal_sy

        self._scroll = sx, sy

    def update(self):
        # handle cursor
        self.cursor_hand.update()
        # handle scrolling
        self._handle_scrolling()

    def _draw_grid_with_padding(self) -> engine.Surface:
        # draws an entirely new grid with the visible options
        # required if options overlap; since if you crop the visible options,
        # you might crop half the overlapped option that's not visible
        if self._scroll_to == self._scroll:  # stationary
            padding = 16, 16
        else:  # currently scrolling
            padding = 0, 0
        px, py = padding
        x, y = self._total_grid_size()
        iwidth, iheight = self._item_size
        width = x * iwidth
        height = y * iheight
        blank_surf = engine.create_surface((width + px, height + py), True)
        ox, oy = px, py
        # draw normal options
        for idx, option in enumerate(self._option_data):
            if idx == self.get_selected_idx():
                pass
            elif not self._is_option_visible(idx):
                pass
            else:
                option.draw(blank_surf, ox, oy)
            ox += iwidth
            if ox == width + px:
                oy += iheight
                ox = px
        # draw highlighted option
        cursor_coord = self._get_coord_of_option_idx(self._cursor_idx)
        option_x, option_y = tuple_add(
            self._get_pixel_coord_of_coord(cursor_coord), padding)
        option = self._option_data[self._cursor_idx]
        option.draw_highlight(blank_surf, option_x, option_y, iwidth)
        offset_x, offset_y = self._get_pixel_coord_of_coord(self._scroll)
        gx, gy = self._grid_size
        gridw, gridh = iwidth * gx, iheight * gy
        choices = engine.subsurface(
            blank_surf, (offset_x, offset_y, gridw + px, gridh + py))
        return choices, padding

    def _draw_cropped_cached_grid(self) -> Tuple[engine.Surface, Tuple[int, int]]:
        # crops the cached grid surf to specific data squares.
        # if options are not oversized (i.e. two adjacent options overlap in terms of sprites),
        # then we use this efficient method
        data_surf = engine.copy_surface(self._cached_data_surf)
        cursor_coord = self._get_coord_of_option_idx(self._cursor_idx)
        option_x, option_y = self._get_pixel_coord_of_coord(cursor_coord)
        option = self._option_data[self._cursor_idx]
        iw, ih = self._item_size
        option.draw_highlight(data_surf, option_x, option_y, iw)
        offset_x, offset_y = self._get_pixel_coord_of_coord(self._scroll)
        gx, gy = self._grid_size
        gridw, gridh = iw * gx, ih * gy
        return engine.subsurface(data_surf, (offset_x, offset_y, gridw, gridh)), (0, 0)

    def _draw_grid(self, surf: engine.Surface, options_top_left: Tuple[int, int]):
        if self._is_option_oversize():  # redraw the entire grid each time
            data_surf, data_offset = self._draw_grid_with_padding()
        else:
            data_surf, data_offset = self._draw_cropped_cached_grid()
        top_left = tuple_sub(options_top_left, data_offset)
        engine.blit(surf, data_surf, top_left)

    def _draw_cursor(self, surf, options_top_left) -> engine.Surface:
        selected_idx = self.get_selected_idx()
        sel_x, sel_y = self._get_coord_of_option_idx(selected_idx)
        scroll_x, scroll_y = self._scroll
        offset_coord = sel_x - scroll_x, sel_y - scroll_y
        px, py = self._get_pixel_coord_of_coord(offset_coord)
        bw, bh = self._get_pixel_size()
        # minor adjustments for visuals
        ox, oy = options_top_left
        if py < -16 or py > bh - (16 if self._title else 0):
            return
        if px < 0 or px > bw:
            return
        px = px + ox - 13
        py = py + oy + 3
        return self.cursor_hand.draw(surf, (px, py))

    def _draw_other_ui(self, surf, options_top_left) -> engine.Surface:
        # draw scroll bars
        if self._should_draw_arrows:
            self.lscroll_arrow.draw(surf)
            self.rscroll_arrow.draw(surf)
        if self._should_draw_scrollbar:
            _, total_height = self._total_grid_size()
            if total_height > self.num_rows():
                x, y = options_top_left
                y -= 3
                x += self._get_pixel_size()[0]
                self.scroll_bar.draw(surf, (x, y), int(
                    self._scroll[1]), self.num_rows(), total_height, self._item_size[1])

    def draw(self, surf) -> engine.Surface:
        left, top = self._get_screen_position()
        # draw bg
        engine.blit(surf, self._cached_bg, (left, top))
        # draw title and options
        title_pos = left + 5, top + 3
        options_y = 3
        if self._title:
            render_text(surf, ['text'], [self._title], [None], title_pos)
            options_y += 16
        options_pos = left, top + options_y
        self._draw_grid(surf, options_pos)
        self._draw_cursor(surf, (left, top + options_y))
        self._draw_other_ui(surf, (left, top + options_y))
        return surf
