from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from typing_extensions import override

from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources.resource_prefab import WithResources
from app.data.serialization.dataclass_serialization import dataclass_from_dict
from app.utilities.data import Prefab
from app.utilities.typing import Color4, NestedPrimitiveDict


@dataclass
class CharGlyph:
    """Position and kerning width of a single glyph on the sprite sheet.

    ``x`` and ``y`` are pixel coordinates (already multiplied by the cell
    dimensions), so they can be used directly for cropping.
    ``char_width`` is the kerning advance width in pixels.
    """
    x: int
    y: int
    char_width: int


class FontIndex:
    """Parsed representation of a ``.idx`` bitmap-font index file.

    Attributes
    ----------
    char_width : int
        Width of each cell on the sprite sheet.
    char_height : int
        Height of each cell on the sprite sheet.
    all_uppercase : bool
        When True, every lookup key is normalised to uppercase.
    all_lowercase : bool
        When True, every lookup key is normalised to lowercase.
    stacked : bool
        When True the sprite sheet stores two vertical rows per glyph
        (primary on top, secondary/shadow below).
    space_offset : int
        Extra horizontal advance added between every character.
    chartable : Dict[str, CharGlyph]
        Maps each character to its glyph on the sheet.
    """

    def __init__(self) -> None:
        self.char_width: int = 8
        self.char_height: int = 16
        self.all_uppercase: bool = False
        self.all_lowercase: bool = False
        self.stacked: bool = False
        self.space_offset: int = 0
        self.chartable: Dict[str, CharGlyph] = {}

    @classmethod
    def from_path(cls, idx_path: str) -> 'FontIndex':
        """Parse *idx_path* and return a :class:`FontIndex`.

        The ``width`` and ``height`` header lines must appear **before** any
        glyph entries because the pixel coordinates are computed on the fly
        while reading.
        """
        index = cls()
        with open(idx_path, 'r', encoding='utf-8') as fp:
            for raw_line in fp:
                words = raw_line.strip().split()
                if not words:
                    continue
                key = words[0]
                if key == 'width':
                    index.char_width = int(words[1])
                elif key == 'height':
                    index.char_height = int(words[1])
                elif key == 'alluppercase':
                    index.all_uppercase = True
                elif key == 'alllowercase':
                    index.all_lowercase = True
                elif key == 'stacked':
                    index.stacked = True
                elif key == 'space_offset':
                    index.space_offset = int(words[1])
                else:
                    # Glyph entry: <char> <col> <row> <kerning_width>
                    if len(words) < 4:
                        continue
                    if key == 'space':
                        key = ' '
                    if index.all_uppercase:
                        key = key.upper()
                    elif index.all_lowercase:
                        key = key.lower()
                    index.chartable[key] = CharGlyph(
                        x=int(words[1]) * index.char_width,
                        y=int(words[2]) * index.char_height,
                        char_width=int(words[3]),
                    )
        return index

    def get(self, char: str) -> Optional[CharGlyph]:
        """Return the :class:`CharGlyph` for *char*, or ``None``."""
        if self.all_uppercase:
            char = char.upper()
        elif self.all_lowercase:
            char = char.lower()
        return self.chartable.get(char)

    def __contains__(self, char: str) -> bool:
        if self.all_uppercase:
            char = char.upper()
        elif self.all_lowercase:
            char = char.lower()
        return char in self.chartable

    def __repr__(self) -> str:
        return (
            f'FontIndex(char_width={self.char_width}, char_height={self.char_height}, '
            f'glyphs={len(self.chartable)})'
        )


@dataclass(slots=True)
class Font(WithResources, Prefab):
    nid: str                                                                             #: NID of the font.
    fallback_ttf: str = None                                                             #: name of the .ttf file (in this directory) to be used as a fallback if the main font cannot render anything
    fallback_size: int = 16                                                              #: what size the fallback font should be rendered at. This may well differ depending on the font, especially at these lower resolutions!
    default_color: Optional[str] = None                                                  #: The key of the default color in the palette, if any.
    outline_font: bool = False                                                           #: whether this font has an outline
    headless: bool = False #:Whether this font renders on a transparent surf
    palettes: Dict[str, List[Color4]] = field(default_factory=dict)                      #: A dictionary of color names to the palette of the font color.

    def __post_init__(self):
        self.file_name: str = None                                                       #: Root path without file ending, e.g. `project.ltproj/resources/convo`.
        self._font_index: Optional['FontIndex'] = None

    @property
    def font_index(self) -> Optional['FontIndex']:
        """Lazily parsed :class:`FontIndex` for this font. Not serialized."""
        if self._font_index is None and self.file_name:
            idx_path = self.index_path()
            if os.path.exists(idx_path):
                self._font_index = FontIndex.from_path(idx_path)
        return self._font_index

    def image_path(self):
        return self.file_name + '.png'

    def index_path(self):
        return self.file_name + '.idx'

    def ttf_path(self):
        if self.fallback_ttf:
            return str(Path(self.file_name).parent / self.fallback_ttf)

    def primary_color(self, color):
        palette = self.palettes.get(color)
        if palette:
            return palette[0]
        return None

    def secondary_color(self, color):
        palette = self.palettes.get(color)
        if palette:
            if len(palette) > 1:
                return palette[1]
            return palette[0]
        return None

    @override
    def set_full_path(self, path: str) -> None:
        self.file_name = path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        paths = [Path(self.image_path()), Path(self.index_path())]
        paths.append(Path(self.ttf_path()) if self.ttf_path() else None)
        return paths

    def save(self):
        return asdict(self)

    @classmethod
    def restore(cls, s_dict):
        return dataclass_from_dict(cls, s_dict)

class FontCatalog(ManifestCatalog[Font]):
    datatype = Font
    manifest = 'fonts.json'
    title = 'fonts'
    filetype = ''