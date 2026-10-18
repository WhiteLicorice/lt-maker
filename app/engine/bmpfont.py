import copy
from typing import Dict, Optional, Tuple
from functools import lru_cache
from app.data.resources.fonts import Font, FontIndex

from app.engine import engine, image_mods
import pygame

from app.utilities.typing import Color4

OUTLINE_WIDTH = 1

class FallbackFont():
    """TTF font wrapper used when a BmpFont character is not in its sprite sheet.

    Args:
        font: The pygame TTF font to render with.
        height: Row height in pixels, matching the parent BmpFont's char height.
        outline: Whether to render characters with a 1px cardinal outline
            (internal color + outline color), as opposed to plain rendering.
        headless: If True, surfaces are created without convert_alpha(). Required
            when no pygame display has been initialised (e.g. editor previews).
    """
    def __init__(self, font: pygame.font.Font, height: int, outline: bool, headless: bool = False):
        self.font = font
        self.height = height
        self.outline = outline
        self.headless = headless

    def _make_surface(self, size: Tuple[int, int]) -> pygame.Surface:
        if self.headless:
            return pygame.Surface(size, pygame.SRCALPHA, 32)
        return engine.create_surface(size, transparent=True)

    @lru_cache()
    def char_width(self, c: str) -> int:
        text_width = self.font.size(c)[0]
        if self.outline:
            text_width += 2 * OUTLINE_WIDTH
        return text_width

    @lru_cache()
    def render_char(self, c: str, color: Color4, outline_color: Color4 = None) -> Tuple[engine.Surface, int]:
        text_width = self.font.size(c)[0]
        if self.outline:
            surf = self._make_surface((text_width + 2 * OUTLINE_WIDTH, self.height))
            internal = self.font.render(c, False, color)
            outline = self.font.render(c, False, outline_color)
            for i in -OUTLINE_WIDTH, OUTLINE_WIDTH:
                surf.blit(outline, (i + OUTLINE_WIDTH, OUTLINE_WIDTH))
                surf.blit(outline, (OUTLINE_WIDTH, i + OUTLINE_WIDTH))
            surf.blit(internal, (OUTLINE_WIDTH, OUTLINE_WIDTH))
        else:
            surf = self._make_surface((text_width, self.height))
            surf.blit(self.font.render(c, False, color), (0, 0))
        return surf, text_width

class BmpFont():
    """Bitmap font renderer backed by a sprite sheet PNG.

    Args:
        font_info: Font metadata including color palettes, fallback TTF path, and
            the character index mapping glyphs to sprite sheet coordinates.
        headless: If True, surfaces are created without
            convert_alpha() and the sprite sheet is loaded without conversion.
            Must be True when no pygame display has been initialised (e.g. editor
            previews). Defaults to False for normal in-game use.
    """
    def __init__(self, font_info: Font, headless: bool = False):
        self.png_path = font_info.image_path()
        self.memory: Dict[str, Dict[str, Tuple[engine.Surface, int]]] = {}

        self.font_info = font_info
        # The caller forces headless when no display exists at all (editor
        # previews, tests); the font itself can also opt in for its own sake
        headless = headless or self.font_info.headless
        self.fallback_font = None
        if self.font_info.ttf_path():
            self.fallback_font = FallbackFont(
                pygame.font.Font(self.font_info.ttf_path(), font_info.fallback_size),
                font_info.font_index.char_height,
                font_info.outline_font,
                headless=headless,
            )

        self.index = font_info.font_index

        self.default_color = font_info.default_color or 'default'
        self.surfaces: Dict[str, engine.Surface] = {}
        base_surf = engine.image_load(self.png_path, convert_alpha=not headless)
        # Covers a default_color that names no palette at all; the loop below
        # replaces this as soon as the default is a real, recolorable palette
        self.surfaces[self.default_color] = base_surf
        # A recoloring reads from the palette that names the sheet's own colors,
        # not from whichever palette text defaults to. Without it there is
        # nothing to map *from*, so every palette just renders as the sheet.
        base_color = font_info.base_palette_nid
        base_palette = font_info.palettes.get(base_color, [])
        for color_name, palette in font_info.palettes.items():
            if color_name == base_color or not base_palette:
                self.surfaces[color_name] = base_surf
            else:
                palette_map = {orig: new for orig, new in zip(map(tuple, base_palette), map(tuple, palette))}
                self.surfaces[color_name] = image_mods.color_convert_alpha(base_surf.copy(), palette_map)

    def with_default_color(self, color: str) -> 'BmpFont':
        """This font, writing in color when given none. It shares this font's
        sheets, each palette recolored once at load"""
        recolored = copy.copy(self)
        recolored.default_color = color
        return recolored

    @property
    def all_uppercase(self) -> bool:
        return self.index.all_uppercase

    @property
    def all_lowercase(self) -> bool:
        return self.index.all_lowercase

    @property
    def stacked(self) -> bool:
        return self.index.stacked

    @property
    def space_offset(self) -> int:
        return self.index.space_offset

    @property
    def _width(self) -> int:
        return self.index.char_width

    @property
    def height(self) -> int:
        return self.index.char_height

    @property
    def chartable(self):
        return self.index.chartable

    def get_base_surf(self) -> engine.Surface:
        return self.surfaces[self.default_color]

    def modify_string(self, string: str) -> str:
        if self.all_uppercase:
            string = string.upper()
        if self.all_lowercase:
            string = string.lower()
        # string = string.replace('_', ' ')
        return string

    @lru_cache()
    def _get_char_width(self, c: str) -> int:
        if c in self.chartable:
            return self.chartable[c].char_width
        if self.fallback_font:
            return self.fallback_font.char_width(c)
        return 8

    @lru_cache()
    def _get_char_from_surf(self, c: str, color: str = None) -> Tuple[engine.Surface, int]:
        if not color:
            color = self.default_color
        if c in self.chartable:
            c_info = self.chartable[c]
            cx, cy, cwidth = c_info.x, c_info.y, c_info.char_width
        elif self.fallback_font:
            return self.fallback_font.render_char(c, tuple(self.font_info.primary_color(color)), tuple(self.font_info.secondary_color(color)))
        else:
            cx, cy, cwidth = 0, 0, 8
        base_surf = self.surfaces.get(color, self.surfaces[self.default_color])
        char_surf = engine.subsurface(base_surf, (cx, cy, self._width, self.height))
        return (char_surf, cwidth)

    @lru_cache()
    def _get_stacked_char_from_surf(self, c: str, color: str = None) -> Tuple[engine.Surface, engine.Surface, int]:
        if not color:
            color = self.default_color
        if c not in self.chartable:
            cx, cy, cwidth = 0, 0, 8
        else:
            c_info = self.chartable[c]
            cx, cy, cwidth = c_info.x, c_info.y, c_info.char_width
        base_surf = self.surfaces.get(color, self.surfaces[self.default_color])
        high_surf = engine.subsurface(base_surf, (cx, cy, self._width, self.height))
        lowsurf = engine.subsurface(base_surf, (cx, cy + self.height, self._width, self.height))
        return (high_surf, lowsurf, cwidth)

    def blit(self, string, surf, pos=(0, 0), color: Optional[str] = None, no_process=False):
        if not color:
            color = self.default_color
        def normal_render(left, top, string: str, bcolor):
            for c in string:
                c_surf, char_width = self._get_char_from_surf(c, bcolor)
                engine.blit(surf, c_surf, (left, top))
                left += char_width + self.space_offset

        def stacked_render(left, top, string: str, bcolor):
            for c in string:
                highsurf, lowsurf, char_width = self._get_stacked_char_from_surf(c, bcolor)
                engine.blit(surf, lowsurf, (left, top))
                engine.blit(surf, highsurf, (left, top))
                left += char_width + self.space_offset

        x, y = pos

        string = self.modify_string(string)

        if self.stacked:
            stacked_render(x, y, string, color)
        else:
            normal_render(x, y, string, color)

    def blit_right(self, string, surf, pos, color=None):
        width = self.width(string)
        self.blit(string, surf, (pos[0] - width, pos[1]), color)

    def blit_center(self, string, surf, pos, color=None):
        width = self.width(string)
        self.blit(string, surf, (pos[0] - width//2, pos[1]), color)

    def size(self, string):
        """
        Returns the length and width of a bitmapped string
        """
        return (self.width(string), self.height)

    def width(self, string):
        """
        Returns the width of a bitmapped string
        """
        length = 0
        string = self.modify_string(string)
        for c in string:
            length += self._get_char_width(c)
        return length
