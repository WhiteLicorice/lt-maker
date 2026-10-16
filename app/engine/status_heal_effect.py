"""
How a unit looks for a moment as a bad status leaves it, as on the GBA:
its outline goes from black to white and back, while a column of blue light
scrolls up through it, added onto its colors
"""
from typing import Optional

from app.data.resources.resources import RESOURCES
from app.engine import engine, image_mods
from app.utilities.typing import Color3

# How long the unit is drawn this way
FRAMES = 66
# The map animation the light is drawn from: a picture tiled down the unit's tile
TEXTURE_NID = 'StatusHeal'
# Added onto the unit instead, at the light's strength, for a project without one
FALLBACK_TINT = (144, 144, 144)

def outline_level(frame: int) -> int:
    """How bright the outline is (0 to 31, black to white): up a step a frame for 32 frames, then back down"""
    if frame < 32:
        return max(0, frame)
    return max(0, min(31, 64 - frame))

def light_strength(frame: int) -> int:
    """How much of the light is added (out of 16): rising over 16 frames, held for 32, falling over 16"""
    if frame < 0:
        return 0
    if frame < 16:
        return frame + 1
    if frame < 48:
        return 16
    return max(0, 63 - frame)

def get_texture() -> Optional[engine.Surface]:
    anim = RESOURCES.animations.get(TEXTURE_NID)
    if not anim:
        return None
    if not anim.image:
        anim.image = engine.image_load(anim.full_path)
        anim.image = anim.image.convert_alpha()
    return anim.image

def draw(image: engine.Surface, frame: int, outline: Color3) -> engine.Surface:
    """
    The unit's image on that frame of the effect. The image is centered on the
    unit's tile, and outline is the color its outline is drawn in
    """
    image = image.convert_alpha()
    grey = outline_level(frame) * 8
    image = image_mods.color_convert_alpha(image, {outline: (grey, grey, grey)})

    strength = light_strength(frame)
    if not strength:
        return image
    texture = get_texture()
    if not texture:
        return image_mods.add_tint(image, tuple(c * strength // 16 for c in FALLBACK_TINT))

    # The light covers the unit's tile from top to bottom, and moves up a pixel a frame
    width, height = image.get_size()
    tex_width, tex_height = texture.get_size()
    light = engine.create_surface((width, height))
    x = (width - tex_width) // 2
    for y in range(-(frame % tex_height), height, tex_height):
        light.blit(texture, (x, y))
    level = min(255, strength * 16)
    engine.fill(light, (level, level, level), None, engine.BLEND_RGB_MULT)
    # Added only where the unit is: the clear pixels stay clear
    image.blit(light, (0, 0), special_flags=engine.BLEND_RGB_ADD)
    return image
