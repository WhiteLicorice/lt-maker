from typing import Dict
from app.data.resources.resources import RESOURCES
from app.engine import bmpfont
from app.utilities.typing import NID

NORMAL_FONT_COLORS = ['white', 'blue', 'green', 'red', 'orange', 'grey', 'yellow', 'brown', 'purple', 'navy']

# Load in default, uncolored fonts
FONT: Dict[NID, bmpfont.BmpFont] = {}
NORMAL_FONT_COLORS = set()
def load_fonts(headless: bool = False):
    """Load all fonts from RESOURCES into the FONT registry.

    Args:
        headless: If True, surfaces are created without convert_alpha().
            Pass True when no pygame display has been initialised
            (e.g. tests, editor tooling). Defaults to False for normal
            in-game use.
    """
    global FONT
    global NORMAL_FONT_COLORS
    FONT.clear()
    for font in RESOURCES.fonts.values():
        bmp_font = bmpfont.BmpFont(font, headless=headless)
        FONT[font.nid] = bmp_font
        for color_name in font.palettes:
            font_name_with_color = '%s-%s' % (font.nid, color_name)
            FONT[font_name_with_color] = bmp_font.with_default_color(color_name)
    NORMAL_FONT_COLORS = RESOURCES.fonts.get("text").palettes.keys()

def get_text_color_options() -> list[str]:
    text_font = RESOURCES.fonts.get('text')
    if not text_font or not text_font.palettes:
        return ['white']
    return list(text_font.palettes.keys())
