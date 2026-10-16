import os
import unittest
from unittest.mock import patch

import pygame

from app.engine import sound


class FakeClock:
    def __init__(self):
        self.time = 1000

    def get_time(self):
        return self.time


class SoundLowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error as e:
                raise unittest.SkipTest("No audio mixer available: %s" % e)

    def setUp(self):
        self.clock = FakeClock()
        engine_patch = patch.object(sound, 'engine', self.clock)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.controller = sound.DefaultSoundController()
        self.controller.set_music_volume(0.8)

    def volumes(self):
        '''The volume each music channel has been set to'''
        return {round(channel.channel.global_volume, 3) for channel in self.controller.channel_stack}

    def advance(self, frames):
        for _ in range(frames):
            self.clock.time += 16
            self.controller.update([])

    def test_lower_and_unmute_are_at_once_unless_given_a_fade(self):
        self.controller.lower()
        self.assertEqual({0.2}, self.volumes())
        self.controller.unmute()
        self.assertEqual({0.8}, self.volumes())

    def test_lower_fades_down_a_step_a_frame(self):
        '''To half over 16 frames, quick at first, as the GBA does for its level up banner'''
        self.controller.lower(0.5, fade=16 * 16)
        self.assertEqual({0.8}, self.volumes())
        heard = []
        for _ in range(16):
            self.advance(1)
            heard.append(self.volumes().pop())
        self.assertEqual(sorted(heard, reverse=True), heard)
        self.assertEqual(16, len(set(heard)))
        # Three quarters of the way down by halfway
        self.assertEqual(0.5, heard[7])
        self.assertGreater(heard[0] - heard[1], heard[-2] - heard[-1])
        self.assertEqual(0.4, heard[-1])
        # And it stays there
        self.advance(30)
        self.assertEqual({0.4}, self.volumes())

    def test_unmute_fades_back_up(self):
        self.controller.lower(0.5)
        self.controller.unmute(fade=16 * 16)
        self.advance(8)
        self.assertEqual({0.7}, self.volumes())
        self.advance(8)
        self.assertEqual({0.8}, self.volumes())

    def test_fade_turned_around_starts_from_where_it_was(self):
        self.controller.lower(0.5, fade=16 * 16)
        self.advance(8)
        self.controller.unmute(fade=16 * 16)
        self.assertEqual({0.5}, self.volumes())
        self.advance(16)
        self.assertEqual({0.8}, self.volumes())

    def test_volume_setting_changed_while_lowered_stays_lowered(self):
        self.controller.lower(0.5)
        self.controller.set_music_volume(1.0)
        self.assertEqual({0.5}, self.volumes())
        self.controller.unmute()
        self.assertEqual({1.0}, self.volumes())


if __name__ == '__main__':
    unittest.main()
