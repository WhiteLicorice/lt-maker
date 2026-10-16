import unittest
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.tests.engine_harness import EngineTestCase


class MenuHandSlideTests(EngineTestCase):
    '''
    On the GBA the menu hand covers half the way left to its item each frame:
    8, 12, 14, 15 of a 16 pixel row. Here it went 4 pixels a frame
    '''

    def setUp(self):
        super().setUp()
        from app.engine import engine
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))

    def drawn_offsets(self, cursor, frames):
        '''How far from its item the hand is drawn, a frame at a time'''
        from app.engine import engine
        surf = MagicMock()
        offsets = []
        for frame in range(frames):
            engine.constants['current_time'] = 1000 + frame * 17
            cursor.draw(surf, 0, 0)
            offsets.append(surf.blit.call_args[0][1][1] - 3)
        return offsets

    def test_halfway_each_frame(self):
        from app.engine.menus import Cursor
        cursor = Cursor()
        cursor.y_offset_down()
        self.assertEqual([-8, -4, -2, -1, 0, 0], self.drawn_offsets(cursor, 6))
        cursor.y_offset_up()
        self.assertEqual([8, 4, 2, 1, 0, 0], self.drawn_offsets(cursor, 6))

    def test_once_a_frame_however_often_it_is_drawn(self):
        from app.engine import engine
        from app.engine.menus import Cursor
        cursor = Cursor()
        cursor.y_offset_down()
        engine.constants['current_time'] = 5000
        surf = MagicMock()
        cursor.draw(surf, 0, 0)
        cursor.draw(surf, 0, 0)
        self.assertEqual(-8, cursor.y_offset)

    def test_generic_menu_hand_slides_the_same(self):
        from app.engine import engine
        from app.engine.game_menus.menu_components.generic_menu.cursor_hand import CursorHand
        hand = CursorHand()
        hand.y_offset_up()
        seen = []
        for frame in range(5):
            engine.constants['current_time'] = 2000 + frame * 17
            hand.draw(MagicMock(), (0, 0))
            seen.append(hand.y_offset)
        self.assertEqual([8, 4, 2, 1, 0], seen)

    def make_menu(self, count=5, limit=10):
        from app.engine import menus
        menu = menus.Simple.__new__(menus.Simple)
        menu.options = [MagicMock(height=MagicMock(return_value=16)) for _ in range(count)]
        menu.current_index = 0
        menu.scroll = 0
        menu.limit = limit
        menu.cursor = menus.Cursor()
        return menu

    def test_menu_slides_by_how_far_the_rows_are_apart(self):
        menu = self.make_menu()
        menu.move_down()
        self.assertEqual(-16, menu.cursor.y_offset)
        menu.move_up()
        self.assertEqual(16, menu.cursor.y_offset)

    def test_wrapping_around_slides_too(self):
        '''As on the GBA. It used to jump there'''
        menu = self.make_menu()
        menu.move_up()
        self.assertEqual(4, menu.current_index)
        self.assertEqual(-64, menu.cursor.y_offset)
        menu.move_down()
        self.assertEqual(64, menu.cursor.y_offset)

    def test_no_slide_when_the_menu_scrolls_under_it(self):
        menu = self.make_menu(count=10, limit=4)
        for _ in range(3):
            menu.move_down()
        self.assertEqual(1, menu.scroll)
        self.assertEqual(0, menu.cursor.y_offset)


class ScreenFadeTests(EngineTestCase):
    def start(self, speed=None):
        from app.engine import transitions
        from app.engine.game_state import game
        game.memory['transition_speed'] = speed
        state = transitions.TransitionInState()
        state.start()
        return state

    def test_fades_take_4_frames(self):
        from app.utilities import utils
        self.assertEqual(utils.frames2ms(4), self.start().wait_time)

    def test_screen_that_asks_for_a_slower_fade_keeps_it(self):
        '''The title screen's'''
        self.assertEqual(4 * 133, self.start(4).wait_time)


class BattleShakeTests(unittest.TestCase):
    def test_normal_hit_shakes_as_on_the_gba(self):
        '''The GBA's, gEfxQuakeVecs2, the other way about as the crit's is here'''
        from app.engine.combat import mock_combat
        combat = mock_combat.MockCombat.__new__(mock_combat.MockCombat)
        combat._shake(1)
        gba = [3, 0, 0, 0, -3, 0, 0, 3, 0, 0, -3, 0, 3, 0, -3, 0, 3, -3]
        self.assertEqual([(-v, -v) for v in gba] + [(0, 0)], combat.shake_set)

    def test_no_damage_does_not_shake_the_screen(self):
        from app.engine.combat import mock_combat
        combat = mock_combat.MockCombat.__new__(mock_combat.MockCombat)
        combat._shake = MagicMock()
        combat.get_damage = MagicMock(return_value=0)
        combat.shake()
        combat._shake.assert_not_called()

    def test_no_damage_sways_toward_the_foe(self):
        '''0, 1, 2, 3, 2, 1, 0 pixels toward the foe, then still for 6 frames, as on the GBA'''
        from app.engine import battle_animation
        anim = battle_animation.BattleAnimation.__new__(battle_animation.BattleAnimation)
        anim.state = 'wait'
        anim.child_effects = []
        anim.under_child_effects = []
        anim.lr_offset = battle_animation.no_damage_sway()
        seen = []
        for _ in range(15):
            anim.update()
            seen.append(anim.lr_now)
        self.assertEqual([0, -1, -2, -3, -2, -1, 0] + [0] * 6 + [None, None], seen)

    def test_sway_is_the_same_for_every_layer_drawn_that_frame(self):
        '''It was taken once for each layer drawn, so a unit's layers came apart'''
        from app.engine import battle_animation
        anim = battle_animation.BattleAnimation.__new__(battle_animation.BattleAnimation)
        anim.state = 'wait'
        anim.child_effects = []
        anim.under_child_effects = []
        anim.lr_offset = [-1, -2]
        anim.update()
        self.assertEqual(-2, anim.lr_now)
        self.assertEqual([-1], anim.lr_offset)


class CombatTimingCase(unittest.TestCase):
    '''Runs an animation combat a frame at a time'''

    def setUp(self):
        from app.engine import engine
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))

    def frames_in(self, combat, state, limit=120):
        '''How many frames the combat stays in that state, at 60 a second'''
        from app.engine import engine
        combat.state = state
        combat.last_update = 10000
        for frame in range(1, limit):
            engine.constants['current_time'] = 10000 + frame * 1000 // 60
            with patch.object(combat, 'clean_up1', create=True):
                combat.update()
            if combat.state != state:
                return frame
        return None

    def build(self):
        from app.tests.test_animation_combat import build_combat
        combat = build_combat()
        combat._skip = False
        combat._delay_death = True
        combat.current_battle_anim = MagicMock()
        combat.left_hp_bar.done.return_value = True
        combat.right_hp_bar.done.return_value = True
        return combat


class AnimationCombatTimingTests(CombatTimingCase):
    def test_at_least_30_frames_after_a_hit(self):
        '''As on the GBA. Here it was 27'''
        self.assertEqual(31, self.frames_in(self.build(), 'hp_change'))

    def test_longer_if_the_hp_bar_takes_longer(self):
        from app.engine import engine
        combat = self.build()
        # Done draining 40 frames after the hit
        combat.left_hp_bar.done.side_effect = lambda: engine.get_time() >= 10000 + 40 * 1000 // 60
        self.assertEqual(40, self.frames_in(combat, 'hp_change'))

    def test_30_frames_before_the_exp_bar(self):
        '''As on the GBA. Here it was 450 ms, 27 frames'''
        self.assertEqual(31, self.frames_in(self.build(), 'exp_pause'))

    def test_first_round_31_frames_after_everything_has_come_in(self):
        '''As on the GBA. Here it was 25'''
        combat = self.build()
        combat.battle_background = None
        combat.start_event = MagicMock()
        self.assertEqual(32, self.frames_in(combat, 'init_pause'))

    def test_background_comes_in_over_16_frames(self):
        '''The map to black over 8 frames, then the background in over 8, as on the GBA. Here it took 25'''
        from app.utilities import utils
        combat = self.build()
        combat.battle_background = MagicMock()
        combat.ui_should_be_hidden = MagicMock(return_value=True)
        self.frames_in(combat, 'entrance')
        combat.battle_background.fade_in.assert_called_once_with(utils.frames2ms(16))


class BattleExitTests(CombatTimingCase):
    '''
    How the battle screen leaves, as on the GBA: the name tags over 7 frames, and the hp
    bars and platforms over 11, quickly at first. Here the name tags took 10 frames and
    then the rest 10 more, evenly
    '''

    def leave(self, background=None):
        '''Each frame, from the end of the wait after the exp bar, as (state, name, bars, platforms)'''
        from app.engine import engine
        combat = self.build()
        combat.arena_combat = False
        combat.left_battle_anim = MagicMock()
        combat.right_battle_anim = MagicMock()
        combat.lp_battle_anim = None
        combat.rp_battle_anim = None
        combat.battle_background = background
        combat.ui_should_be_hidden = MagicMock(return_value=False)
        combat.name_offset = combat.bar_offset = combat.platform_offset = 1
        combat.state = 'fade_out_wait'
        combat.last_update = 10000 - 820
        rows = []
        for frame in range(1, 60):
            engine.constants['current_time'] = 10000 + frame * 1000 // 60
            combat.update()
            if combat.state == 'fade_out':
                break
            rows.append((combat.state, combat.name_offset, combat.bar_offset, combat.platform_offset))
        return rows

    def test_name_tags_then_the_rest_2_frames_later(self):
        rows = self.leave()
        names = [name for _, name, _, _ in rows]
        bars = [bar for _, _, bar, _ in rows]
        self.assertEqual(1, rows[0][1])  # The frame the wait ends
        # The name tags are gone 7 frames on, and the bars start 2 frames after them
        self.assertEqual(7, next(idx for idx, name in enumerate(names) if name == 0))
        self.assertEqual(3, next(idx for idx, bar in enumerate(bars) if bar < 1))
        # Quickly at first, as the GBA's do
        self.assertGreater(1 - names[1], names[1] - names[2])
        self.assertEqual(bars, [platforms for _, _, _, platforms in rows])

    def test_zoom_back_to_the_map_16_frames_after_the_bars_start(self):
        '''11 frames for them to go and 2 more, as on the GBA'''
        rows = self.leave()
        bars = [bar for _, _, bar, _ in rows]
        start = next(idx for idx, bar in enumerate(bars) if bar < 1)
        self.assertEqual(14, len(rows) - start + 1)

    def test_with_a_background_the_bars_wait_for_the_map(self):
        '''On the GBA the background goes to black over 9 frames and the map comes in over 9 first'''
        from app.utilities import utils
        background = MagicMock()
        rows = self.leave(background)
        background.fade_out.assert_called_once_with(utils.frames2ms(18))
        bars = [bar for _, _, bar, _ in rows]
        self.assertEqual(20, next(idx for idx, bar in enumerate(bars) if bar < 1))



class HpBarGlowTests(unittest.TestCase):
    '''
    The hp bar glows as on the GBA: a step lighter every 2 frames, the lightest held 10
    frames, back down, the darkest held 10, 36 frames in all. Here it was 32, read off
    the clock so that its steps took 1 to 3 frames
    '''

    def test_glow_a_frame_at_a_time(self):
        from unittest.mock import patch
        from app.engine import engine, health_bar
        self.addCleanup(engine.constants.__setitem__, 'current_time', engine.constants.get('current_time', 0))
        gba = [1, 1, 2, 2, 3, 3, 4, 4] + [5] * 10 + [4, 4, 3, 3, 2, 2, 1, 1] + [0] * 10
        # The clock counts whole milliseconds, so frames are 16 or 17 of them apart
        clocks = {
            'rounded': lambda frame: round(frame * 1000 / 60),
            'floored': lambda frame: frame * 1000 // 60,
            '16, 17, 17': lambda frame: frame * 16 + frame * 2 // 3,
        }
        for name, clock in clocks.items():
            bar = health_bar.CombatHealthBar.__new__(health_bar.CombatHealthBar)
            bar.displayed_val = 10
            bar.get_val = lambda: 10
            engine.constants['current_time'] = 5000
            bar.glow_start = engine.get_time()
            seen = []
            for frame in range(72):
                engine.constants['current_time'] = 5000 + clock(frame)
                with patch.object(health_bar.HealthBar, 'update'):
                    bar.update()
                seen.append(bar.colors[bar.color_tick])
            self.assertEqual(gba * 2, seen, name)


if __name__ == '__main__':
    unittest.main()
