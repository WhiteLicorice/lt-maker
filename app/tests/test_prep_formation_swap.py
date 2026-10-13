import unittest
from unittest.mock import patch

from app.tests.engine_harness import EngineTestCase


class SwapArcPathTests(unittest.TestCase):
    def test_flight_time_grows_with_distance(self):
        from app.engine.unit_sprite import swap_arc_frames
        # One tile, two tiles, fourteen tiles, in pixels
        self.assertEqual([13, 14, 27], [swap_arc_frames(d) for d in (16, 32, 224)])

    def test_path_is_the_gba_one(self):
        '''
        A unit moving two tiles to the right, frame by frame, as FE8 draws it
        (PrepUnitSwapProc_MainLoop run with the ROM's sine table)
        '''
        from app.engine.unit_sprite import swap_arc_frames, swap_arc_offset
        gba = [(0, 0), (2, -2), (4, -4), (6, -6), (9, -8), (11, -9), (13, -10), (16, -10),
               (18, -10), (20, -9), (22, -8), (25, -6), (27, -4), (29, -2), (32, 0)]
        frames = swap_arc_frames(32)
        path = []
        for frame in range(frames + 1):
            x, y = swap_arc_offset((-32, 0), frame / frames)
            path.append((x + 32, y))
        self.assertEqual(gba, path)

    def test_bow_is_never_much_more_than_a_tile(self):
        from app.engine.unit_sprite import swap_arc_offset
        # Halfway through a flight of 1, 2, 3, 5, 8 and 14 tiles to the right
        peaks = [swap_arc_offset((-16 * tiles, 0), 0.5)[1] for tiles in (1, 2, 3, 5, 8, 14)]
        self.assertEqual([-8, -10, -12, -13, -14, -15], peaks)


class PrepFormationSwapTests(EngineTestCase):
    '''
    testing_proj has no prep screen, so the formation states are entered by hand
    over the Prologue, where Eirika stands at (4, 5) and Seth at (4, 4)
    '''

    def start_formation(self):
        from app.engine import action
        from app.engine.objects.region import RegionObject
        from app.events.regions import RegionType
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        action.AddRegion(RegionObject('formation_test', RegionType.FORMATION, (3, 3), (3, 3))).do()
        harness.game.state.change('prep_formation')
        harness.run_until_state('prep_formation')
        return harness

    def pick_up(self, harness, unit_nid):
        harness.move_cursor_to(harness.game.get_unit(unit_nid).position)
        harness.press('SELECT')
        harness.run_until_state('prep_formation_select')

    def land(self, harness, *units):
        harness.run_until(lambda: all(unit.sprite.transition_state == 'normal' for unit in units),
                          60, 'units landed')

    def test_two_units_trade_places_in_an_arc(self):
        harness = self.start_formation()
        eirika, seth = harness.game.get_unit('Eirika'), harness.game.get_unit('Seth')
        self.pick_up(harness, 'Eirika')
        harness.move_cursor_to((4, 4))
        harness.press('SELECT')

        self.assertEqual('prep_formation', harness.state)
        self.assertEqual(((4, 4), (4, 5)), (eirika.position, seth.position))
        self.assertEqual(('swap_arc', 'swap_arc'), (eirika.sprite.transition_state, seth.sprite.transition_state))
        # Still on the way: Eirika, heading up, bows out to the left of the screen and
        # Seth, heading down, to the right, so they pass without overlapping
        self.assertGreater(eirika.sprite.offset[1], 0)
        self.assertLess(seth.sprite.offset[1], 0)
        self.assertLess(eirika.sprite.offset[0], 0)
        self.assertGreater(seth.sprite.offset[0], 0)

        self.land(harness, eirika, seth)
        self.assertEqual(([0, 0], [0, 0]), (eirika.sprite.offset, seth.sprite.offset))

    def test_nothing_can_be_done_until_the_units_land(self):
        harness = self.start_formation()
        eirika, seth = harness.game.get_unit('Eirika'), harness.game.get_unit('Seth')
        self.pick_up(harness, 'Eirika')
        harness.move_cursor_to((4, 4))
        harness.press('SELECT')

        harness.press('RIGHT')
        self.assertEqual('swap_arc', eirika.sprite.transition_state)
        self.assertEqual((4, 4), harness.game.cursor.position)

        self.land(harness, eirika, seth)
        harness.press('RIGHT')
        self.assertEqual((5, 4), harness.game.cursor.position)

    def test_unit_flies_to_an_empty_tile(self):
        harness = self.start_formation()
        eirika = harness.game.get_unit('Eirika')
        self.pick_up(harness, 'Eirika')
        harness.move_cursor_to((3, 3))
        harness.press('SELECT')

        self.assertEqual((3, 3), eirika.position)
        self.assertEqual('swap_arc', eirika.sprite.transition_state)
        self.land(harness, eirika)
        self.assertEqual([0, 0], eirika.sprite.offset)

    def test_hand_over_the_cursor_bobs_as_on_the_gba(self):
        '''
        FE8's hand takes 22 frames to go up and back down 5 pixels, resting 4 frames
        at each end. Here the counter that picks its height was never advanced at
        first, so the hand stood still
        '''
        harness = self.start_formation()
        self.pick_up(harness, 'Eirika')
        select_state = harness.game.state.state[-1]
        # From the start of a bob, a frame at a time
        harness.step()
        harness.run_until(lambda: select_state.counter == 0, 30, 'start of a bob')
        heights = [select_state.marker_offset[select_state.counter]]
        for _ in range(43):
            harness.step()
            heights.append(select_state.marker_offset[select_state.counter])
        up_and_down = [5, 5, 5, 5, 3, 3, 3, 2, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 2, 3, 3, 3]
        self.assertEqual(up_and_down * 2, heights)

    def test_hands_are_drawn_where_the_gba_draws_them(self):
        '''
        3 pixels right of the tile's left edge. The hand over the picked unit is 12
        pixels above the tile, and the one over the cursor bobs from 14 down to 9
        pixels above it and slides with the cursor from tile to tile
        '''
        import pygame
        from app.engine.prep import PrepFormationSelectState
        # A hand of one color found nowhere else, to pick out of the picture
        color = (255, 0, 254)
        hand = pygame.Surface(PrepFormationSelectState.marker.get_size())
        hand.fill(color)
        patcher = patch.object(PrepFormationSelectState, 'marker', hand)
        patcher.start()
        self.addCleanup(patcher.stop)

        harness = self.start_formation()
        self.pick_up(harness, 'Eirika')  # At (4, 5)
        harness.move_cursor_to((3, 3))
        select_state = harness.game.state.state[-1]
        cursor = harness.game.cursor

        def hands():
            mask = pygame.mask.from_threshold(harness.surf, color, (1, 1, 1, 255))
            return sorted(rect.topleft for rect in mask.get_bounding_rects())

        def bob():
            return select_state.marker_offset[select_state.counter]

        harness.step()
        self.assertEqual([(3 * 16 + 3, 3 * 16 - 14 + bob()), (4 * 16 + 3, 5 * 16 - 12)], hands())

        # One tile to the right: the hand is with the cursor all the way
        harness.step(events=[harness._key_event(pygame.KEYDOWN, 'RIGHT')])
        seen = []
        while cursor.offset_x:
            (x, y), _ = hands()
            self.assertEqual(int(4 * 16 - cursor.offset_x + 3), x)
            self.assertEqual(3 * 16 - 14 + bob(), y)
            seen.append(x)
            harness.step()
        self.assertGreater(len(seen), 2)
        self.assertEqual(sorted(set(seen)), seen)
        self.assertEqual((4 * 16 + 3, 3 * 16 - 14 + bob()), hands()[0])


if __name__ == '__main__':
    unittest.main()
