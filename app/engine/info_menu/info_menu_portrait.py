from app.engine import engine
from app import counters
from app.constants import COLORKEY

class InfoMenuPortrait():
    def __init__(self, portrait, should_blink: bool = False):
        self.portrait = portrait
        if not self.portrait.image:
            self.portrait.image = engine.image_load(self.portrait.full_path)
        self.portrait.image = self.portrait.image.convert()
        engine.set_colorkey(self.portrait.image, COLORKEY, rleaccel=True)
        self.main_portrait = engine.subsurface(self.portrait.image, self.portrait.get_face_frame())
        self.mouth_section = engine.subsurface(self.portrait.image, self.portrait.get_neutral_mouth())

        self.should_blink = should_blink
        self.blink_counter = counters.FaceBlinkCounter(portrait.blink_frames, engine.get_time())

    def create_image(self):
        main_image = self.main_portrait.copy()

        if self.should_blink and not self.blink_counter.is_open_eyes():
            blink_image = engine.subsurface(self.portrait.image,
                                self.portrait.get_blink_frame(self.blink_counter.get_blink_index()))
            main_image.blit(blink_image, self.portrait.get_blink_coord())

        main_image.blit(self.mouth_section, self.portrait.get_mouth_coord())
        return main_image

    def update(self):
        self.blink_counter.update(engine.get_time())
