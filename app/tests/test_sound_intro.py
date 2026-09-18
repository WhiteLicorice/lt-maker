import os
import time
import unittest
from unittest.mock import patch

import pygame

from app.engine import sound

INTRO_SONG = 'Strawberry Crisis'
PLAIN_SONG = 'Plain Song'

class FrameClock:
    """engine.get_time() is stamped once at the start of each frame"""
    def __init__(self):
        self.time = 1000

    def get_time(self):
        return self.time

def silence(seconds: float) -> pygame.mixer.Sound:
    frequency, size, channels = pygame.mixer.get_init()
    return pygame.mixer.Sound(buffer=bytes(int(frequency * seconds) * abs(size) // 8 * channels))

class FakeSong:
    """Stands in for a SongObject with silent tracks, so no project audio is needed"""
    def __init__(self, nid, intro_seconds=None):
        self.nid = nid
        self.song = silence(30)
        self.intro = silence(intro_seconds) if intro_seconds else None
        self.battle = None
        self.channel = None

class SoundIntroTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The end events that drive a channel from its intro to its song need the event queue
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))
        if not pygame.mixer.get_init():
            try:
                pygame.mixer.init()
            except pygame.error as e:
                raise unittest.SkipTest("No audio mixer available: %s" % e)

    def setUp(self):
        self.clock = FrameClock()
        engine_patch = patch.object(sound, 'engine', self.clock)
        engine_patch.start()
        self.addCleanup(engine_patch.stop)
        self.songs = {INTRO_SONG: FakeSong(INTRO_SONG, intro_seconds=10),
                      PLAIN_SONG: FakeSong(PLAIN_SONG)}
        music_patch = patch.dict(sound.MUSIC, self.songs)
        music_patch.start()
        self.addCleanup(music_patch.stop)
        pygame.event.get()  # Drop anything left in the queue

        self.controller = sound.DefaultSoundController()
        self.controller.set_music_volume(1.0)

    def frame(self, commands=None, extra_ms=0):
        """One pass of driver.run: stamp the time, read events, run event commands, update sound"""
        self.clock.time += 16 + extra_ms
        events = pygame.event.get()
        if commands:
            commands()
        self.controller.update(events)

    def current_sound(self, song: FakeSong) -> pygame.mixer.Sound:
        return song.channel.channel._channel.get_sound()

    def test_music_after_music_fade_back_plays_its_intro(self):
        '''
        MKCocoon 7/19/25: `music_fade_back; music;Strawberry Crisis` skipped the intro. Stopping
        the song that was fading out posted its end event, and loading the new song made that
        frame long enough for the event to pass the 32ms guard, so the channel moved on to the
        main track as if the intro had finished
        '''
        self.frame(lambda: self.controller.fade_in(PLAIN_SONG))
        for _ in range(60):
            self.frame()

        def script():
            self.controller.fade_back()
            self.controller.fade_in(INTRO_SONG)
        self.frame(script)
        self.frame(extra_ms=300)  # The frame that loaded the new song took this much longer
        for _ in range(60):
            self.frame()

        song = self.songs[INTRO_SONG]
        self.assertIs(self.current_sound(song), song.intro)

    def test_intro_that_finishes_moves_on_to_song(self):
        song = FakeSong(INTRO_SONG, intro_seconds=0.05)
        sound.MUSIC[INTRO_SONG] = song
        self.frame(lambda: self.controller.fade_in(INTRO_SONG))
        self.assertIs(self.current_sound(song), song.intro)

        time.sleep(0.3)  # Let the intro really finish, so SDL posts its end event
        self.frame(extra_ms=300)
        self.assertIs(self.current_sound(song), song.song)

if __name__ == '__main__':
    unittest.main()
