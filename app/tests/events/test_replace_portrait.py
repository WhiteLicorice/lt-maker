import logging
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from app.data.resources.portraits import PortraitPrefab
from app.engine import engine
from app.events import event_functions
from app.events.event_portrait import EventPortrait

class ReplacePortraitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

    def setUp(self):
        self.time = 1000
        time_patch = patch.object(engine, 'get_time', lambda: self.time)
        time_patch.start()
        self.addCleanup(time_patch.stop)

        self.prefabs = {nid: self.build_prefab(nid) for nid in ('Eirika', 'EirikaAngry', 'Seth')}
        self.event = SimpleNamespace(
            portraits={}, text_boxes=[], do_skip=False, wait_time=0, state='processing',
            logger=logging.getLogger('test_replace_portrait'),
            _get_portrait=lambda nid: (self.prefabs.get(nid), nid))

        self.original = EventPortrait(self.prefabs['Eirika'], (24, 80), 7, mirror=True, name='Eirika')
        self.original.set_expression(['Smile', 'CloseEyes'])
        self.original.saturation = 0
        self.event.portraits['Eirika'] = self.original

    def build_prefab(self, nid):
        prefab = PortraitPrefab(nid)
        prefab.image = pygame.Surface(prefab.full_size)
        return prefab

    def replace(self, portrait='Eirika', new_portrait='EirikaAngry', flags=None):
        return event_functions.replace_portrait(self.event, portrait, new_portrait, flags=flags)

    def test_replacement_keeps_the_originals_state(self):
        self.assertTrue(self.replace(flags={'immediate'}))
        replacement = self.event.portraits['EirikaAngry']
        self.assertIs(replacement.portrait, self.prefabs['EirikaAngry'])
        self.assertEqual(replacement.position, (24, 80))
        self.assertEqual(replacement.priority, 7)
        self.assertTrue(replacement.mirror)
        self.assertEqual(replacement.saturation, 0)
        self.assertEqual(replacement.expressions, {'Smile', 'CloseEyes'})

    def test_replacement_is_known_by_its_new_name(self):
        self.replace(flags={'immediate'})
        self.assertEqual(list(self.event.portraits.keys()), ['EirikaAngry'])
        self.assertEqual(self.event.portraits['EirikaAngry'].name, 'EirikaAngry')

    def test_immediate_does_not_fade_or_block(self):
        self.replace(flags={'immediate'})
        replacement = self.event.portraits['EirikaAngry']
        self.assertFalse(replacement.transition)
        self.assertIsNone(replacement.outgoing)
        self.assertEqual(self.event.state, 'processing')

    def test_skipping_does_not_fade_or_block(self):
        self.event.do_skip = True
        self.replace()
        self.assertFalse(self.event.portraits['EirikaAngry'].transition)
        self.assertEqual(self.event.state, 'processing')

    def test_fade_draws_over_the_original_until_it_finishes(self):
        self.replace()
        replacement = self.event.portraits['EirikaAngry']
        self.assertTrue(replacement.transition)
        self.assertIs(replacement.outgoing, self.original)
        self.assertEqual(self.event.state, 'waiting')
        self.assertEqual(self.event.wait_time, self.time + replacement.transition_speed + 33)

        self.time += replacement.transition_speed / 2
        self.assertFalse(replacement.update())
        replacement.draw(pygame.Surface((240, 160)))
        self.assertIs(replacement.outgoing, self.original)

        self.time += replacement.transition_speed
        self.assertFalse(replacement.update())
        self.assertFalse(replacement.transition)
        self.assertIsNone(replacement.outgoing)

    def test_no_block_fades_without_waiting(self):
        self.replace(flags={'no_block'})
        self.assertTrue(self.event.portraits['EirikaAngry'].transition)
        self.assertEqual(self.event.state, 'processing')

    def test_removing_mid_fade_drops_the_original(self):
        self.replace(flags={'no_block'})
        replacement = self.event.portraits['EirikaAngry']
        replacement.end()
        self.assertIsNone(replacement.outgoing)

    def test_text_box_follows_the_replacement(self):
        text_box = SimpleNamespace(portrait=self.original)
        self.event.text_boxes.append(text_box)
        self.replace(flags={'immediate'})
        self.assertIs(text_box.portrait, self.event.portraits['EirikaAngry'])

    def test_portrait_not_on_screen_does_nothing(self):
        self.assertFalse(self.replace(portrait='Seth'))
        self.assertEqual(self.event.portraits, {'Eirika': self.original})

    def test_unknown_new_portrait_does_nothing(self):
        with self.assertLogs('test_replace_portrait', level='ERROR'):
            self.assertFalse(self.replace(new_portrait='Nobody'))
        self.assertEqual(self.event.portraits, {'Eirika': self.original})

    def test_new_portrait_already_on_screen_does_nothing(self):
        seth = EventPortrait(self.prefabs['Seth'], (120, 80), 8, name='Seth')
        self.event.portraits['Seth'] = seth
        with self.assertLogs('test_replace_portrait', level='ERROR'):
            self.assertFalse(self.replace(new_portrait='Seth'))
        self.assertEqual(self.event.portraits, {'Eirika': self.original, 'Seth': seth})

if __name__ == '__main__':
    unittest.main()
