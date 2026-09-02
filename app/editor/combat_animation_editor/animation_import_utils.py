from typing import Dict, List, Optional, Set, Tuple

from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, qRgb

import app.editor.utilities as editor_utilities

def convert_gba(pixmap: QPixmap) -> QPixmap:
    im = pixmap.toImage()
    im.convertTo(QImage.Format_Indexed8)
    im = editor_utilities.convert_gba(im)
    pixmap = QPixmap.fromImage(im)
    return pixmap

def simple_crop(pixmap: QPixmap) -> QPixmap:
    if pixmap.width() == 248:
        pixmap = pixmap.copy(0, 0, 240, pixmap.height())
    elif pixmap.width() == 488:
        pixmap = pixmap.copy(0, 0, 480, pixmap.height())
    return pixmap

def crop_imported_frames(nid: str, pixmap: QPixmap) -> List[Tuple[str, QPixmap, tuple]]:
    """Turns one imported file into the frames it holds, trimmed to their artwork.

    A GBA format frame is 240 wide with the palette parked in an extra 8 pixel
    column on the right, so that column has to go before the bounding box is
    measured. It is not the background color, so it would otherwise count as
    artwork and stretch the box across the whole frame -- and get_bbox reads the
    top right pixel to recognize the colorkey, which lands inside the palette.

    A 480 wide frame is two frames side by side, the second of which is what gets
    drawn under the unit, and each half needs its own bounding box.

    Returns a (nid, pixmap, rect) per frame; the rect is kept as the frame's
    offset. A half holding nothing but background is dropped rather than becoming
    an empty frame.
    """
    halves = split_doubles({nid: simple_crop(pixmap)})
    frames = []
    for frame_nid, half in halves.items():
        x, y, width, height = editor_utilities.get_bbox(half.toImage())
        if width <= 0 or height <= 0:  # nothing but background
            continue
        frames.append((frame_nid, half.copy(x, y, width, height), (x, y, width, height)))
    return frames

def split_doubles(pixmaps: Dict[str, QPixmap]) -> dict:
    new_pixmaps = {}
    for name in pixmaps.keys():
        pix = pixmaps[name]
        if pix.width() == 480:
            pix1 = pix.copy(0, 0, 240, pix.height())
            pix2 = pix.copy(240, 0, 240, pix.height())
            new_pixmaps[name] = pix1
            new_pixmaps[name + '_under'] = pix2
    pixmaps.update(new_pixmaps)
    return pixmaps

def find_empty_pixmaps(pixmaps: Dict[str, QPixmap], exclude_color: Optional[qRgb] = None) -> Set[str]:
    empty_pixmaps = set()
    for name, pixmap in pixmaps.items():
        x, y, width, height = editor_utilities.get_bbox(pixmap.toImage(), exclude_color)
        if width > 0 and height > 0:
            pass
        else:
            empty_pixmaps.add(name)
    return empty_pixmaps

def remove_top_right_palette_indicator(pixmaps: Dict[str, QPixmap]) -> Dict[str, QPixmap]:
    new_pixmaps = {}
    for name in pixmaps.keys():
        pix = pixmaps[name]
        width = pix.width()
        image = pix.toImage()
        # Black out the the 8x2 palette in the top right with the top right color
        top_right_color = image.pixel(width - 1, 0)
        for x in range(8):
            for y in range(2):
                image.setPixel(width - x - 1, y, top_right_color)
        pix = QPixmap(image)
        new_pixmaps[name] = pix
    pixmaps.update(new_pixmaps)
    return pixmaps

def stretch_vertically(pixmap: QPixmap) -> QPixmap:
    return pixmap.scaled(pixmap.width(), pixmap.height() * 2)

def combine_identical_commands(pose):
    """
    The GBA import likes to put identical commands next to one another.
    Like f;3;Unarmed0 will be followed by f;1;Unarmed0.
    This could more simply be rendered as f;4;Unarmed0
    """
    last_command = None
    new_timeline = []
    for command in pose.timeline[:]:
        if command.has_frames():
            if last_command and last_command.nid == command.nid and last_command.value[1:] == command.value[1:]:
                # Combine these two
                last_command.value = (last_command.value[0] + command.value[0], *last_command.value[1:])
            elif last_command:
                new_timeline.append(last_command)
                last_command = command
            else:
                last_command = command
        elif command.nid == 'wait':
            if last_command and last_command.nid == 'wait':
                # Combine waits
                last_command.value = (last_command.value[0] + command.value[0], )
            elif last_command:
                new_timeline.append(last_command)
                last_command = command
            else:
                last_command = command
        elif last_command:
            new_timeline.append(last_command)
            last_command = None
            new_timeline.append(command)
        else:
            new_timeline.append(command)
    if last_command:
        new_timeline.append(last_command)
    pose.timeline = new_timeline

def update_anim_full_image(anim):
    """
    Takes the frames of the weapon animation and collates them into a spritesheet
    anim can also be an EffectAnimation
    """
    width_limit = 1200
    left = 0
    heights = []
    max_heights = []
    for frame in anim.frames:
        width, height = frame.pixmap.width(), frame.pixmap.height()
        if left + width > width_limit:
            max_heights.append(max(heights))
            frame.rect = (0, sum(max_heights), width, height)
            heights = [height]
            left = width
        else:
            frame.rect = (left, sum(max_heights), width, height)
            left += width
            heights.append(height)
    if heights:
        max_heights.append(max(heights))

    total_width = min(width_limit, sum(frame.rect[2] for frame in anim.frames))
    total_height = sum(max_heights)
    new_pixmap = QPixmap(total_width, total_height)
    new_pixmap.fill(QColor(0, 0, 0))
    painter = QPainter()
    painter.begin(new_pixmap)
    for frame in anim.frames:
        x, y, width, height = frame.rect
        painter.drawPixmap(x, y, frame.pixmap)
    painter.end()
    anim.pixmap = new_pixmap
    anim.full_path = None  # So we can save our changes
