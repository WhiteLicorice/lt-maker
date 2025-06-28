from __future__ import annotations
from enum import Enum
import string

class Alignments(Enum):
    TOP_LEFT = "top_left"
    TOP = "top"
    TOP_RIGHT = "top_right"
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    BOT_LEFT = "bottom_left"
    BOT = "bottom"
    BOT_RIGHT = "bottom_right"

class HAlignment(Enum):
    LEFT = 'left'
    CENTER = 'center'
    RIGHT = 'right'
    NONE = 'none'

class VAlignment(Enum):
    TOP = 'top'
    CENTER = 'center'
    BOTTOM = 'bottom'
    NONE = 'none'

class Orientation(Enum):
    HORIZONTAL = 'horizontal'
    VERTICAL = 'vertical'

class Strike(Enum):
    HIT = 'hit'
    MISS = 'miss'
    CRIT = 'crit'

class CharacterSet(Enum):
    UPPERCASE = list(string.ascii_uppercase)
    LOWERCASE = list(string.ascii_lowercase)
    UPPERCASE_UTF8 = [
        'Á', 'À', 'Â', 'Ä', 'Å', 'Ç', 'Ð', 'É', 'È', 'Ê', 'Ë', 'Í', 'Ì', 'Î', 'Ï',
        'Ñ', 'Ó', 'Ò', 'Ô', 'Ö', 'Ø', 'Þ', 'Ú', 'Ù', 'Û', 'Ü', 'Ý', 'Ÿ', 'Ƿ', 'Æ', 'Œ'
    ]
    LOWERCASE_UTF8 = [
        'á', 'à', 'â', 'ä', 'å', 'ç', 'ð', 'é', 'è', 'ê', 'ë', 'í', 'ì', 'î', 'ï',
        'ñ', 'ó', 'ò', 'ô', 'ö', 'ø', 'þ', 'ú', 'ù', 'û', 'ü', 'ý', 'ÿ', 'ƿ', 'æ', 'œ'
    ]
    NUMBERS_AND_PUNCTUATION = [
        '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        '!', '¡', '?', '¿', '&', '-', '+', ';', ':', "'", ',', '.', '"'
    ] + [' '] * (26 - 7)

    @property
    def chars(self) -> list[str]:
        return self.value
    
    @property
    def charset(self) -> set[str]:
        return set(self.chars)