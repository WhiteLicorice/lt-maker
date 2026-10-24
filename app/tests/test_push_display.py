import unittest

import pygame

from app.engine import engine

class PushDisplayTests(unittest.TestCase):
    '''
    push_display scales an opaque frame in the screen's own format straight onto
    the screen. Any other frame must come out as scaling it and blitting it would
    '''
    def setUp(self):
        self.screen = pygame.Surface((480, 320))
        self.screen.fill((37, 90, 140))

    def scaled_then_blitted(self, frame: pygame.Surface) -> pygame.Surface:
        expected = pygame.Surface((480, 320))
        expected.fill((37, 90, 140))
        expected.blit(pygame.transform.scale(frame, (480, 320)), (0, 0))
        return expected

    def assertSameScreen(self, expected: pygame.Surface):
        self.assertEqual(pygame.image.tobytes(expected, 'RGB'), pygame.image.tobytes(self.screen, 'RGB'))

    def test_an_opaque_frame(self):
        frame = pygame.Surface((240, 160))
        frame.fill((200, 10, 60), (20, 20, 50, 30))
        engine.push_display(frame, (480, 320), self.screen)
        self.assertSameScreen(self.scaled_then_blitted(frame))

    def test_a_24_bit_frame(self):
        '''A 24-bit frame has a 32-bit screen's masks, and scaling it straight onto the screen raised'''
        frame = pygame.Surface((240, 160), 0, 24)
        frame.fill((200, 10, 60), (20, 20, 50, 30))
        engine.push_display(frame, (480, 320), self.screen)
        self.assertSameScreen(self.scaled_then_blitted(frame))

    def test_a_colorkeyed_frame_leaves_the_screen_under_its_key(self):
        '''Scaled straight onto the screen, a colorkeyed frame wrote its keyed pixels over it'''
        frame = pygame.Surface((240, 160))
        frame.fill((200, 10, 60), (20, 20, 50, 30))
        frame.set_colorkey((0, 0, 0))
        engine.push_display(frame, (480, 320), self.screen)
        self.assertEqual((37, 90, 140, 255), tuple(self.screen.get_at((300, 200))))
        self.assertSameScreen(self.scaled_then_blitted(frame))

if __name__ == '__main__':
    unittest.main()
