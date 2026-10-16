from enum import Enum
from app.engine import engine
from app.sprites import SPRITES

def slide_hand(offset: int) -> int:
    """
    How far the menu hand still is from its item a frame later. As on the GBA,
    it covers half of what is left each frame (there, it rests a pixel short
    after moving down; here it gets there)
    """
    return int(offset / 2)


class CursorDrawMode(Enum):
    NO_DRAW = 0
    DRAW = 1
    DRAW_STATIC = 2

class CursorHand():
    def __init__(self) -> None:
        self.cursor_sprite = SPRITES.get('menu_hand')
        self.offsets = [0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        self.offset_index = 0
        # How far the hand is from its item, in pixels, as it slides to it
        self.y_offset = 0
        self._last_slide = None
        self.mode: CursorDrawMode = CursorDrawMode.DRAW

    def y_offset_up(self, distance: int = 16):
        self.y_offset = distance

    def y_offset_down(self, distance: int = 16):
        self.y_offset = -distance

    def get_offset(self):
        return self.offsets[self.offset_index]

    def update(self):
        self.offset_index = (self.offset_index + 1) % len(self.offsets)

    def update_y_offset(self):
        # Once a frame, however many times the hand is drawn
        current_time = engine.get_time()
        if current_time != self._last_slide:
            self._last_slide = current_time
            self.y_offset = slide_hand(self.y_offset)

    def draw(self, surf, topleft) -> engine.Surface:
        self.update_y_offset()
        x, y = topleft
        if self.mode == CursorDrawMode.DRAW:
            engine.blit(surf, self.cursor_sprite, (x + self.get_offset(), y + self.y_offset))
        elif self.mode == CursorDrawMode.DRAW_STATIC:
            engine.blit(surf, self.cursor_sprite, (x, y + self.y_offset))
        else:
            pass  # Don't draw
        return surf
