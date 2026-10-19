from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, override, Set, Tuple

from app.data.category import CategorizedCatalog
from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources.resource_prefab import WithResources
from app.utilities import utils
from app.utilities.data import Prefab
from app.utilities.typing import NID, Rect

if TYPE_CHECKING:
    from PyQt5.QtGui import QPixmap
    from app.engine import engine

# CONSTANTS
CHIBI_WIDTH, CHIBI_HEIGHT = 32, 32
INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT = 80, 72
GBA_PORTRAIT_WIDTH, GBA_PORTRAIT_HEIGHT = 128, 112

class PortraitPrefab(WithResources, Prefab):
    def __init__(self, nid, full_path=None, pix=None):
        self.nid:       NID = nid
        self.full_path: str = full_path
        self.image:     Optional[engine.Surface] = None
        self.pixmap:    Optional[QPixmap] = pix

        self.blinking_offset:   Tuple[int, int] = [0, 0]
        self.smiling_offset:    Tuple[int, int] = [0, 0]
        self.info_offset:       Tuple[int, int] = (0, 0)

        self.chibi_coord:   Tuple[int, int] = (128, 80)
        self.full_size:     Tuple[int, int] = (160, 112)
        self.face_size:     Tuple[int, int] = (96, 80)
        self.blink_size:    Tuple[int, int] = (32, 16)
        self.mouth_size:    Tuple[int, int] = (32, 16)
        self.blink_frames:  int = 2
        self.mouth_frames:  int = 3

    @override
    def set_full_path(self, full_path: str):
        self.full_path = full_path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        return [Path(self.full_path)]

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['blinking_offset'] = self.blinking_offset
        s_dict['smiling_offset'] = self.smiling_offset
        s_dict['info_offset'] = self.info_offset

        s_dict['chibi_coord'] = self.chibi_coord
        s_dict['full_size'] = self.full_size
        s_dict['face_size'] = self.face_size
        s_dict['blink_size'] = self.blink_size
        s_dict['mouth_size'] = self.mouth_size
        s_dict['blink_frames'] = self.blink_frames
        s_dict['mouth_frames'] = self.mouth_frames
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.blinking_offset = [int(_) for _ in s_dict['blinking_offset']]
        self.smiling_offset = [int(_) for _ in s_dict['smiling_offset']]
        self.info_offset = tuple(int(_) for _ in s_dict['info_offset'])

        self.chibi_coord = tuple(int(_) for _ in s_dict['chibi_coord'])
        self.full_size = tuple(int(_) for _ in s_dict['full_size'])
        self.face_size = tuple(int(_) for _ in s_dict['face_size'])
        self.blink_size = tuple(int(_) for _ in s_dict['blink_size'])
        self.mouth_size = tuple(int(_) for _ in s_dict['mouth_size'])
        self.blink_frames = int(s_dict.get('blink_frames', 0))
        self.mouth_frames = int(s_dict.get('mouth_frames', 0))
        return self

    def get_face_frame(self) -> Rect:
        return (self.full_size[0] - self.face_size[0] - self.blink_size[0],
                self.full_size[1] - self.face_size[1] - self.mouth_size[1]*2,
                *self.face_size)

    def get_blink_frame(self, idx: int) -> Rect:
        return (self.full_size[0] - self.blink_size[0],
                self.full_size[1] - self.mouth_size[1]*2 - self.blink_size[1]*(idx+1),
                *self.blink_size)

    def get_mouth_frame(self, idx: int, smile: bool = False) -> Rect:
        return (self.full_size[0] - self.blink_size[0] - self.mouth_size[0]*(idx+2),
                self.full_size[1] - self.mouth_size[1] * (2 if smile else 1),
                *self.mouth_size)

    def get_minimug(self) -> Rect:
        return (*self.chibi_coord, CHIBI_WIDTH, CHIBI_HEIGHT)

    def get_neutral_mouth(self) -> Rect:
        return (self.full_size[0] - self.blink_size[0] - self.mouth_size[0],
                self.full_size[1] - self.mouth_size[1]*2,
                *self.mouth_size)

    def get_blink_coord(self) -> Tuple[int, int]:
        return self.blinking_offset

    def get_mouth_coord(self) -> Tuple[int, int]:
        return self.smiling_offset

    def get_wink(self, left_wink: bool = True) -> Rect:
        return (self.full_size[0] - (self.blink_size[0] if left_wink else self.blink_size[0]//2),
                self.full_size[1] - self.mouth_size[1]*2 - self.blink_size[1],
                self.blink_size[0] // 2,
                self.blink_size[1])

    def get_wink_coord(self, left_wink: bool = True) -> Tuple[int, int]:
        return (self.blinking_offset[0] + (0 if left_wink else self.blink_size[0]//2),
                self.blinking_offset[1])

    def get_info_coord(self) -> Tuple[int, int]:
        return self.info_offset

class PortraitCatalog(ManifestCatalog[PortraitPrefab], CategorizedCatalog[PortraitPrefab]):
    manifest = 'portraits.json'
    title = 'portraits'
    datatype = PortraitPrefab
