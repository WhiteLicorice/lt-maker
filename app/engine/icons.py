from __future__ import annotations

import math
from typing import TYPE_CHECKING, Tuple, Optional, Protocol, runtime_checkable

from app.utilities import utils
from app.utilities.enums import HAlignment
import app.utilities.algorithms.interpolation as interp

from app.constants import COLORKEY
from app.data.resources.portraits import INFO_PORTRAIT_WIDTH, INFO_PORTRAIT_HEIGHT, PortraitPrefab
from app.data.resources.resources import RESOURCES
from app.data.database.database import DB

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine import engine, skill_system, image_mods, unit_funcs

if TYPE_CHECKING:
    from app.data.database import factions, skills, units
    from app.engine.objects import skill, unit
    from app.engine.bmpfont import BmpFont

@runtime_checkable
class HasIcon(Protocol):
    icon_nid: str
    icon_index: Tuple[int, int]

def get_icon_by_name(name: str) -> Optional[engine.Surface]:
    image, index = None, None
    for icon_sheet in RESOURCES.icons16:
        if icon_sheet.get_index(name):
            image = icon_sheet
            index = icon_sheet.get_index(name)
    if not image or not index:
        return None
    if not image.image:
        image.image = engine.image_load(image.full_path)
    x, y = index
    image = engine.subsurface(image.image, (x * 16, y * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def get_icon_by_nid(nid: str, x: int, y: int) -> Optional[engine.Surface]:
    image = RESOURCES.icons16.get(nid)
    if not image:
        return None
    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (x * 16, y * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def get_icon(item: Optional[HasIcon]) -> Optional[engine.Surface]:
    # Basically `item` can be any Prefab with `icon_nid` attribute
    if not item:
        return None
    image = RESOURCES.icons16.get(item.icon_nid)
    if not image:
        return None

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (item.icon_index[0] * 16, item.icon_index[1] * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def draw_item(surf: engine.Surface, item: Optional[HasIcon],
              topleft: Tuple[int, int], cooldown:bool=False) -> Optional[engine.Surface]:
    # Basically `item` can be any Prefab with `icon_nid` attribute
    image = get_icon(item)
    if not image:
        return None

    surf.blit(image, topleft)

    return surf

def draw_skill(surf: engine.Surface, skill: skill.SkillObject | skills.SkillPrefab,
               topleft: Tuple[int, int], compact:bool=True, simple:bool=False, grey:bool=False) -> Optional[engine.Surface]:
    image = get_icon(skill)
    if not image:
        return None

    if grey:
        image = image_mods.make_gray_colorkey(image)

    surf.blit(image, topleft)
    if simple:
        return surf
    frac = skill_system.get_cooldown(skill)
    if frac is not None and frac < 1:
        cooldown_surf = SPRITES.get('icon_cooldown')
        index = utils.clamp(int(8 * frac), 0, 7)
        c = engine.subsurface(cooldown_surf, (16 * index, 0, 16, 16))
        surf.blit(c, topleft, None, engine.BLEND_RGB_MULT)

    if compact:
        pass
    else:
        text = skill_system.get_text(skill)
        if text is not None:
            FONT['text-blue'].blit(text, surf, (topleft[0] + 16, topleft[1]))

    return surf

def draw_icon_by_alias(surf: engine.Surface, icon_alias: str, topleft: Tuple[int, int]) -> Optional[engine.Surface]:
    image = get_icon_by_name(icon_alias)
    if not image:
        return None
    surf.blit(image, topleft)
    return surf

def draw_weapon(surf: engine.Surface, weapon_type: str, topleft: Tuple[int, int], gray:bool=False) -> engine.Surface:
    w_type_obj = DB.weapons.get(weapon_type)
    if not w_type_obj:
        return surf
    image = RESOURCES.icons16.get(w_type_obj.icon_nid)
    if not image:
        return surf

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (w_type_obj.icon_index[0] * 16, w_type_obj.icon_index[1] * 16, 16, 16))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    if gray:
        image = image_mods.make_gray(image.convert_alpha())

    surf.blit(image, topleft)
    return surf

def draw_faction(surf: engine.Surface, faction: factions.Faction, topleft: Tuple[int, int]) -> engine.Surface:
    image = RESOURCES.icons32.get(faction.icon_nid)
    if not image:
        return surf

    if not image.image:
        image.image = engine.image_load(image.full_path)
    image = engine.subsurface(image.image, (faction.icon_index[0] * 32, faction.icon_index[1] * 32, 32, 32))
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    surf.blit(image, topleft)
    return surf

def get_portrait(unit: unit.UnitObject | units.UnitPrefab) -> Tuple[Optional[engine.Surface], Tuple[int, int]]:
    image = RESOURCES.portraits.get(unit.portrait_nid)
    if image:
        offset = image.get_info_coord()
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, image.get_face_frame())
    else:  # Generic class portrait
        klass = DB.classes.get(unit.klass)
        image = RESOURCES.icons80.get(klass.icon_nid)
        if not image:
            return None, (0, 0)
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, (klass.icon_index[0] * 80, klass.icon_index[1] * 72, 80, 72))
        offset = (0, 0)

    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)

    return image, offset

def get_portrait_from_nid(portrait_nid: str) -> Tuple[Optional[engine.Surface], Tuple[int, int]]:
    image = RESOURCES.portraits.get(portrait_nid)
    if image:
        offset = image.get_info_coord()
        if not image.image:
            image.image = engine.image_load(image.full_path)
        image = engine.subsurface(image.image, image.get_face_frame())
        image = image.convert()
        engine.set_colorkey(image, COLORKEY, rleaccel=True)
    else:
        offset = (0, 0)
    return image, offset

def get_portrait_with_size(unit: unit.UnitObject | units.UnitPrefab, width: int, height: int) -> Optional[engine.Surface]:
    # Sub-surface out the best portion of the portrait given the size
    image, offset = get_portrait(unit)
    if not image:
        return None
    x_offset = max(min(offset[0] + (min( INFO_PORTRAIT_WIDTH,  image.get_width()) -  width)//2,
                        image.get_width() -  width), 0)
    y_offset = max(min(offset[1] + (min(INFO_PORTRAIT_HEIGHT, image.get_height()) - height)//2,
                        image.get_height()- height), 0)
    portrait = engine.subsurface(image, (x_offset, y_offset, width, height))
    return portrait

def draw_portrait(surf: engine.Surface, unit: unit.UnitObject | units.UnitPrefab,
                  topleft: Optional[Tuple[int, int]] = None,
                  bottomright: Optional[Tuple[int, int]] = None) -> Optional[engine.Surface]:
    image, _ = get_portrait(unit)
    if not image:
        return None

    if topleft:
        surf.blit(image, topleft)
    elif bottomright:
        surf.blit(image, utils.tuple_sub(bottomright, image.get_size()))
    return surf

def get_chibi(portrait: PortraitPrefabs) -> engine.Surface:
    if not portrait.image:
        portrait.image = engine.image_load(portrait.full_path)
    image = engine.subsurface(portrait.image, portrait.get_minimug())
    image = image.convert()
    engine.set_colorkey(image, COLORKEY, rleaccel=True)
    return image

def draw_chibi(surf: engine.Surface, nid: str,
               topleft: Optional[Tuple[int, int]] = None,
               bottomright: Optional[Tuple[int, int]] = None) -> engine.Surface:
    portrait = RESOURCES.portraits.get(nid)
    if not portrait:
        return surf
    image = get_chibi(portrait)

    if topleft:
        surf.blit(image, topleft)
    elif bottomright:
        surf.blit(image, utils.tuple_sub(bottomright, image.get_size()))
    return surf

def draw_stat(surf: engine.Surface, stat_nid: str, unit: unit.UnitObject,
              topright: Tuple[int, int], compact:bool=False) -> None:
    if stat_nid not in DB.stats:
        FONT['text-yellow'].blit_right('--', surf, topright)
        return
    value = unit.stats.get(stat_nid, 0)
    bonus = unit.stat_bonus(stat_nid)
    subtle_bonus = unit.subtle_stat_bonus(stat_nid)
    max_stat = unit.get_stat_cap(stat_nid)
    if compact:
        if value >= max_stat:
            draw_glow(surf, FONT['text-green'], str(value + bonus), topright, HAlignment.RIGHT)
            return

        if bonus > 0:
            typeface = FONT['text-green']
        elif bonus < 0:
            typeface = FONT['text-red']
        else:
            typeface = FONT['text-blue']
        typeface.blit_right(str(value + bonus), surf, topright)
    else:
        # Recalc these values for full display
        value = value + subtle_bonus
        bonus = bonus - subtle_bonus
        if value >= max_stat:
            draw_glow(surf, FONT['text-green'], str(value), topright, HAlignment.RIGHT)
        else:
            FONT['text-blue'].blit_right(str(value), surf, topright)
        if bonus > 0:
            draw_glow(surf, FONT['small-green'], "+%d" % bonus, topright)
        elif bonus < 0:
            draw_glow(surf, FONT['small-red'], str(bonus), topright)

def draw_growth(surf: engine.Surface, stat_nid: str, unit: unit.UnitObject,
                topright: Tuple[int, int], compact:bool=False, percent: bool = False) -> None:
    if stat_nid not in DB.stats:
        FONT['text-yellow'].blit_right('--', surf, topright)
        return
    value = unit_funcs.base_growth_rate(unit, stat_nid)
    value_and_bonus = unit_funcs.growth_rate(unit, stat_nid)
    bonus = value_and_bonus - value
    if compact:
        pass
    else:
        FONT['text-blue'].blit_right(str(value), surf, topright)
        # The bonus follows the percent sign
        bonus_pos = topright
        if percent:
            FONT['text-blue'].blit('%', surf, topright)
            bonus_pos = (topright[0] + FONT['text-blue'].width('%'), topright[1])
        if bonus > 0:
            FONT['small-green'].blit("+%d" % bonus, surf, bonus_pos)
        elif bonus < 0:
            FONT['small-red'].blit(str(bonus), surf, bonus_pos)

def draw_glow(surf: engine.Surface, font_obj: BmpFont, text: str, topright: Tuple[int, int],
              align: HAlignment = HAlignment.LEFT, color: str = None) -> engine.Surface:
    interval = 800   # ms
    progress = engine.get_time() % (interval*2)  # Between 0 and 1600
    white = math.sin(progress / interval * math.pi)  # Returns between -1 and 1
    # Rescale to be between 0 and 1
    white = (white + 1) / 2
    
    stat_surf = engine.create_surface(surf.get_size(), True)

    if align == HAlignment.RIGHT:
        font_obj.blit_right(text, stat_surf, topright)
    elif align == HAlignment.CENTER:
        font_obj.blit_center(text, stat_surf, topright)
    else:
        font_obj.blit(text, stat_surf, topright)

    if not color:
        color = font_obj.default_color
    new_palette = font_obj.font_info.palettes[color]
    default_palette = font_obj.font_info.palettes[font_obj.default_color]
    conv_dict = {}
    for idx, default_color in enumerate(default_palette):
        if idx == 1:
            continue
        other_color = new_palette[idx]
        new_color = [utils.clamp(interp.lerp(rgb, 255, white), 0, 255) for rgb in other_color[:3]] + [255]
        conv_dict[tuple(default_color)] = tuple(new_color)

    image_mods.color_convert_alpha(stat_surf, conv_dict)
    surf.blit(stat_surf, (0, 0))

    return surf
