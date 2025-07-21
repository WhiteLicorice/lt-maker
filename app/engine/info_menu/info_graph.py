from typing import List
from dataclasses import dataclass

from app.engine import engine, help_menu, menus

info_states = ('personal_data', 'equipment', 'support_skills', 'notes')

@dataclass
class BoundingBox():
    idx: int = 0
    aabb: tuple = None
    help_box: help_menu.HelpDialog = None
    state: str = None
    first: bool = False

def find_closest(current_bb: BoundingBox, boxes: List[BoundingBox], horiz: bool) -> BoundingBox:
    center_point = (current_bb.aabb[0] + current_bb.aabb[2]/2,
                    current_bb.aabb[1] + current_bb.aabb[3]/2)
    closest_box = None
    max_distance = 1e6
    # First try to find a close box by moving in the right direction
    if horiz:
        horiz_penalty, vert_penalty = 1, 10
    else:
        horiz_penalty, vert_penalty = 10, 1

    for bb in boxes:
        curr_topleft = current_bb.aabb[:2]
        other_topleft = bb.aabb[:2]
        distance = horiz_penalty * (curr_topleft[0] - other_topleft[0])**2 \
            + vert_penalty * (curr_topleft[1] - other_topleft[1])**2
        if distance < max_distance:
            max_distance = distance
            closest_box = bb

    # Find the closest box from boxes by comparing center points
    if not closest_box:
        for bb in boxes:
            bb_center = (bb.aabb[0] + bb.aabb[2]/2, bb.aabb[1] + bb.aabb[3]/2)
            distance = (center_point[0] - bb_center[0])**2 + (center_point[1] - bb_center[1])**2
            if distance < max_distance:
                max_distance = distance
                closest_box = bb
    return closest_box

class InfoGraph():
    draw_all_bbs: bool = False

    def __init__(self):
        self.registry = {state: [] for state in info_states}
        self.registry.update({'growths': []})
        self.current_bb = None
        self.last_bb = None
        self.current_state = None
        self.cursor = menus.Cursor()

    def clear(self, keep_last_aabb=False):
        self.registry = {state: [] for state in info_states}
        self.registry.update({'growths': []})
        self.last_bb_aabb = self.last_bb.aabb if keep_last_aabb and self.last_bb else None
        self.current_bb = None
        self.last_bb = None

    def set_current_state(self, state):
        self.current_state = state

    def register(self, aabb, help_box, state, first=False):
        if isinstance(help_box, str):
            help_box = help_menu.HelpDialog(help_box)

        if state == 'all':
            for s in self.registry:
                idx = len(self.registry[s])
                self.registry[s].append(BoundingBox(idx, aabb, help_box, s, first))
        else:
            idx = len(self.registry[state])
            self.registry[state].append(BoundingBox(idx, aabb, help_box, state, first))

    def set_transition_in(self):
        # only display help if registry has help
        if self.registry:
            last_info_menu_bbs = [bb for bb in self.registry[self.current_state] if bb.aabb == self.last_bb_aabb]
            if self.last_bb and self.last_bb.state == self.current_state:
                # restore last bb selected before transition out
                self.current_bb = self.last_bb
                self.current_bb.help_box.set_transition_in()
            elif last_info_menu_bbs:
                # then check if last_bb_aabb exists in registry after last info menu transition
                self.current_bb = last_info_menu_bbs[0]
                self.current_bb.help_box.set_transition_in()
            else:
                for bb in self.registry[self.current_state]:
                    if bb.first:
                        self.current_bb = bb
                        self.current_bb.help_box.set_transition_in()
                        break
                else:
                    # For now, just use first help dialog
                    self.current_bb = self.registry[self.current_state][0]
                    self.current_bb.help_box.set_transition_in()
        # reset last_bb_aabb, if it needs to be used it should have already been
        # prevents accidentally becoming valid again when transitioning info menus
        self.last_bb_aabb = None

    def set_transition_out(self):
        if self.current_bb:
            self.current_bb.help_box.set_transition_out()
        self.last_bb = self.current_bb
        self.current_bb = None

    def _move(self, boxes, horiz=False) -> bool:
        """Move the current_bb to the closest box in the given direction

        Args:
            boxes (list): List of bounding boxes to compare against
            horiz (bool): Whether to move horizontally or vertically

        Returns:
            bool: Whether the current_bb was moved"""
        if not boxes:
            return False
        if not self.current_bb:
            return False
        closest_box = find_closest(self.current_bb, boxes, horiz)
        if closest_box == self.current_bb:
            return False
        self.current_bb = closest_box
        return True

    def move_left(self) -> bool:
        boxes = [bb for bb in self.registry[self.current_state] if bb.aabb[0] < self.current_bb.aabb[0]]
        return self._move(boxes, horiz=True)

    def move_right(self) -> bool:
        boxes = [bb for bb in self.registry[self.current_state] if bb.aabb[0] > self.current_bb.aabb[0]]
        return self._move(boxes, horiz=True)

    def move_up(self) -> bool:
        boxes = [bb for bb in self.registry[self.current_state] if bb.aabb[1] < self.current_bb.aabb[1]]
        return self._move(boxes)

    def move_down(self) -> bool:
        boxes = [bb for bb in self.registry[self.current_state] if bb.aabb[1] > self.current_bb.aabb[1]]
        return self._move(boxes)

    def handle_mouse(self, mouse_position):
        x, y = mouse_position
        for bb in self.registry[self.current_state]:
            if bb.aabb[0] <= x < bb.aabb[0] + bb.aabb[2] and \
                    bb.aabb[1] <= y < bb.aabb[1] + bb.aabb[3]:
                self.current_bb = bb

    def draw(self, surf):
        if self.draw_all_bbs:
            for bb in self.registry[self.current_state]:
                s = engine.create_surface((bb.aabb[2], bb.aabb[3]), transparent=True)
                engine.fill(s, (10 * bb.idx, 10 * bb.idx, 0, 128))
                surf.blit(s, (bb.aabb[0], bb.aabb[1]))
        if self.current_bb:
            # right = self.current_bb.aabb[0] >= int(0.75 * WINWIDTH)
            right = False
            pos = (max(0, self.current_bb.aabb[0] - 32), self.current_bb.aabb[1] + 13)

            cursor_pos = (max(0, self.current_bb.aabb[0] - 4), self.current_bb.aabb[1])
            self.cursor.update()
            self.cursor.draw(surf, *cursor_pos)

            self.current_bb.help_box.draw(surf, pos, right)
