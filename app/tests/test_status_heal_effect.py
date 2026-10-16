import json
import os
import unittest
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase


class StatusHealEffectTests(EngineTestCase):
    '''
    On the GBA, as a bad status leaves a unit, its outline goes from black to
    white and back while a column of blue light scrolls up through it
    '''
    outline = (64, 56, 56)
    body = (100, 50, 20)
    light = (0, 64, 192)

    def setUp(self):
        super().setUp()
        from app.engine import engine
        engine.constants.setdefault('current_time', 0)

    def make_image(self):
        '''A map sprite frame, 64 by 48, centered on its tile: an outline and a body, in and out of the tile's column'''
        import pygame
        from app.constants import COLORKEY
        from app.engine import engine
        image = engine.create_surface((64, 48))
        image.fill(COLORKEY)
        # In the tile's column (24 to 40) and out of it
        for x in (25, 10):
            image.set_at((x, 30), self.outline)
            image.set_at((x, 31), self.body)
        engine.set_colorkey(image, COLORKEY)
        return image

    def make_texture(self):
        from app.engine import engine
        texture = engine.create_surface((16, 32))
        texture.fill(self.light)
        return texture

    def draw(self, frame, texture=True):
        from app.engine import status_heal_effect
        with patch.object(status_heal_effect, 'get_texture', return_value=self.make_texture() if texture else None):
            return status_heal_effect.draw(self.make_image(), frame, self.outline)

    def test_outline_goes_to_white_and_back(self):
        from app.engine.status_heal_effect import outline_level
        levels = [outline_level(frame) for frame in range(66)]
        self.assertEqual(list(range(32)), levels[:32])
        # Down a step a frame, held black at the end
        self.assertEqual([31, 31, 30], levels[32:35])
        self.assertEqual([1, 0, 0], levels[63:66])

    def test_light_rises_holds_and_falls(self):
        from app.engine.status_heal_effect import light_strength
        strengths = [light_strength(frame) for frame in range(66)]
        self.assertEqual(list(range(1, 17)), strengths[:16])
        self.assertEqual([16] * 32, strengths[16:48])
        self.assertEqual(list(range(15, -1, -1)), strengths[48:64])
        self.assertEqual([0, 0], strengths[64:])

    def test_outline_is_grey_at_the_level(self):
        image = self.draw(20)
        self.assertEqual((160, 160, 160, 255), tuple(image.get_at((10, 30))))

    def test_light_is_added_only_in_the_tiles_column(self):
        image = self.draw(30)
        # At full strength the light is added on
        self.assertEqual((100, 50 + 64, 20 + 192, 255), tuple(image.get_at((25, 31))))
        self.assertEqual(self.body + (255,), tuple(image.get_at((10, 31))))
        # and none of the clear pixels show
        self.assertEqual(0, image.get_at((25, 10))[3])
        self.assertEqual(0, image.get_at((0, 0))[3])

    def test_light_is_added_at_its_strength(self):
        image = self.draw(3)
        # 4 of 16
        self.assertEqual((100, 50 + 16, 20 + 48, 255), tuple(image.get_at((25, 31))))

    def test_without_the_light_the_unit_is_tinted_instead(self):
        image = self.draw(30, texture=False)
        self.assertEqual((244, 194, 164, 255), tuple(image.get_at((10, 31))))

    def test_sprite_draws_it_for_66_frames(self):
        from app.engine import engine, status_heal_effect
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        sprite = harness.game.get_unit('Eirika').sprite
        sprite.start_status_heal()
        start = engine.get_time()
        frames = []
        with patch.object(status_heal_effect, 'draw', side_effect=lambda image, frame, outline: frames.append(frame) or image):
            for frame in range(70):
                engine.constants['current_time'] = start + frame * 1000 // 60
                sprite.draw(engine.create_surface((240, 160)), (0, 0, 240, 160))
        self.assertEqual(list(range(66)), frames)
        self.assertIsNone(sprite.status_heal_start)

    def test_sprite_knows_its_outline(self):
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        map_sprite = harness.game.get_unit('Eirika').sprite.map_sprite
        image = map_sprite.create_image('passive')
        colors = {tuple(image.get_at((x, y)))[:3] for x in range(image.get_width()) for y in range(image.get_height())}
        self.assertIn(map_sprite.outline_color, colors)


class DefaultProjectLightTests(unittest.TestCase):
    def test_default_project_has_the_light(self):
        root = 'default.ltproj/resources/animations/'
        with open(root + 'animations.json') as f:
            anims = {anim['nid']: anim for anim in json.load(f)}
        self.assertEqual(1, anims['StatusHeal']['num_frames'])
        self.assertTrue(os.path.exists(root + 'StatusHeal.png'))


if __name__ == '__main__':
    unittest.main()
