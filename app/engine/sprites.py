from app.sprites import SPRITES

from app.engine import engine

def load_images():
    # Converted to the display's pixel format once there is a display to
    # convert to. When this module is first imported there is none yet, and the
    # images are kept as loaded until driver.start loads them again
    has_display = engine.has_display()
    for sprite in SPRITES.values():
        if sprite.full_path:
            image = engine.image_load(sprite.full_path)
            # A palettized image keeps its own format. Its colorkey is a palette
            # index, which a conversion turns into a color, so any other index
            # of that same color would go see-through as well
            if has_display and image.get_bitsize() > 8:
                image = engine.convert_for_display(image)
            sprite.image = image

load_images()
