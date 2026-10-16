import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tests import engine_harness
from app.tests.engine_harness import EngineTestCase


class LungeCounterTests(unittest.TestCase):
    def test_one_step_a_frame_however_often_it_is_read(self):
        '''
        A unit's sprite reads the counter twice a frame, for its x and its y,
        and each read used to step it: the lunge played at twice its speed
        '''
        from app.counters import movement_counter
        counter = movement_counter()
        counter.reset()
        seen = []
        for frame in range(20):
            if frame == 12:
                counter.retreat()
            counter.update(frame * 16)
            counter.update(frame * 16)
            seen.append(counter.value())
        # As on the GBA: out a pixel a frame, held until it is told to
        # retreat, back a pixel a frame, then at rest
        self.assertEqual([1, 2, 3, 4] + [4] * 8 + [3, 2, 1, 0] + [0] * 4, seen)


class MapCombatHealthBarTests(EngineTestCase):
    def make_unit(self, hp, max_hp=40):
        unit = SimpleNamespace(hp=hp)
        unit.get_hp = lambda: unit.hp
        unit.get_max_hp = lambda: max_hp
        return unit

    def test_hp_lost_drains_a_point_a_frame(self):
        from app.engine.health_bar import MapCombatHealthBar
        from app.utilities import utils
        unit = self.make_unit(30)
        bar = MapCombatHealthBar(unit)
        unit.hp = 10
        bar.update()
        self.assertEqual(20 * utils.frames2ms(1), bar.time_for_change)

    def test_hp_gained_fills_a_point_every_four_frames(self):
        from app.engine.health_bar import MapCombatHealthBar
        from app.utilities import utils
        unit = self.make_unit(10)
        bar = MapCombatHealthBar(unit)
        unit.hp = 30
        bar.update()
        self.assertEqual(20 * utils.frames2ms(4), bar.time_for_change)

    def test_box_reports_how_long_its_bar_takes(self):
        '''
        The box of bars reported a fixed 200 ms whatever its bars were doing, so
        map combat stopped waiting for a long drain to finish
        '''
        from app.engine.health_bar import BarType, MultiGenericBar
        from app.utilities import utils
        unit = self.make_unit(30)
        bars = MultiGenericBar(unit, [BarType.HP])
        self.assertFalse(bars.transition_flag)
        unit.hp = 5
        bars.update()
        self.assertTrue(bars.transition_flag)
        self.assertEqual(25 * utils.frames2ms(1), bars.time_for_change)


class LeadInTests(unittest.TestCase):
    def make_combat(self, cast_pose=False, playback=(), skill_icons=()):
        from app.engine.combat.map_combat import MapCombat
        combat = MapCombat.__new__(MapCombat)
        combat.cast_pose = cast_pose
        combat.playback = [SimpleNamespace(nid=nid) for nid in playback]
        combat.health_bars = {'unit': SimpleNamespace(skill_icons=list(skill_icons))}
        return combat

    def test_plain_strike_needs_none(self):
        self.assertFalse(self.make_combat(playback=['damage_hit', 'hit_sound', 'cast_sound']).needs_lead_in())

    def test_things_shown_before_the_strike_need_one(self):
        self.assertTrue(self.make_combat(cast_pose=True).needs_lead_in())
        self.assertTrue(self.make_combat(playback=['cast_anim']).needs_lead_in())
        self.assertTrue(self.make_combat(playback=['target_cast_anim']).needs_lead_in())
        self.assertTrue(self.make_combat(skill_icons=['Vantage']).needs_lead_in())


class MapCombatPacingTests(EngineTestCase):
    def fight(self):
        '''
        Seth attacks the Fighter at (8, 6) from (8, 5), at 60 frames a second.
        Returns a row a frame: the combat's state, Seth's offset in pixels,
        and the target's HP
        '''
        import pygame
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        game = harness.game
        seth, target = game.get_unit('Seth'), game.get_unit('102')
        harness.move_unit('Seth', (8, 5))
        harness.choose('Attack')
        harness.run_until_state('weapon_choice')
        harness.press('SELECT')
        harness.run_until_state('combat_targeting')
        harness.step(events=[harness._key_event(pygame.KEYDOWN, 'SELECT')])

        self.addCleanup(setattr, engine_harness, 'FRAME_MS', engine_harness.FRAME_MS)
        rows = []
        for frame in range(1500):
            # A frame is 16 or 17 ms on a clock of whole milliseconds
            engine_harness.FRAME_MS = 16 if frame % 3 == 2 else 17
            harness.step()
            if 'combat' not in game.state.state_names():
                if rows:
                    break
                continue
            combat = game.memory['current_combat']
            rows.append((combat.state, tuple(seth.sprite.offset), target.get_hp()))
        return rows

    def phases(self, rows):
        '''The rows of each strike, from the frame its phase begins'''
        phases = []
        last_state = None
        for row in rows:
            if row[0] == 'begin_phase' and last_state != 'begin_phase':
                phases.append([])
            if phases:
                phases[-1].append(row)
            last_state = row[0]
        return phases

    def frames_in(self, rows, state):
        return sum(1 for row in rows if row[0] == state)

    def test_striker_leans_in_until_the_hp_bar_settles(self):
        '''
        As on the GBA: 4 pixels toward the target at a pixel a frame, held there
        while the HP bar drains, and back at a pixel a frame
        '''
        first = self.phases(self.fight())[0]
        lunge = [(state, offset) for state, offset, _ in first if offset != (0, 0)]
        # Down at the Fighter
        self.assertEqual([(0, 1), (0, 2), (0, 3), (0, 4)], [offset for _, offset in lunge[:4]])
        waiting = [offset for state, offset in lunge if state == 'hp_bar_wait']
        self.assertGreater(len(waiting), 13)
        self.assertEqual({(0, 4)}, set(waiting))
        self.assertEqual([(0, 4), (0, 3), (0, 2), (0, 1)], [offset for state, offset in lunge if state == 'end_phase_anim'])

    def test_plain_strike_keeps_the_gba_pace(self):
        '''
        The GBA starts a strike 7 frames after the last one's rest, and rests 20
        frames once the units are back. Here each strike waited 29 frames before
        the lunge and 34 after the HP bar, whatever it had to show
        '''
        first, second = self.phases(self.fight())[:2]
        for phase in (first, second):
            self.assertEqual(1, self.frames_in(phase, 'sound'))
            self.assertIn(self.frames_in(phase, 'end_phase_anim'), (23, 24))
        # The first strike waits for the HP boxes to open
        self.assertIn(self.frames_in(first, 'start_anim'), (12, 13))
        self.assertIn(self.frames_in(second, 'start_anim'), (3, 4))

    def test_hp_boxes_are_updated_once_a_frame(self):
        '''
        They were updated twice on the frame a hit landed, once to learn how long
        the HP bar would take and once with every other frame: a box's shake,
        which steps on each update, never showed its first frame
        '''
        from app.engine import engine
        from app.engine.health_bar import MapCombatInfo
        updates = {}
        update = MapCombatInfo.update

        def counted(box, *args, **kwargs):
            key = (id(box), engine.get_time())
            updates[key] = updates.get(key, 0) + 1
            return update(box, *args, **kwargs)

        with patch.object(MapCombatInfo, 'update', counted):
            self.fight()
        self.assertTrue(updates)
        self.assertEqual({1}, set(updates.values()))

    def test_strike_waits_for_the_hp_bar(self):
        rows = self.fight()
        first = self.phases(rows)[0]
        damage = rows[0][2] - first[-1][2]
        self.assertGreater(damage, 13, "Seth's first strike should take longer to drain than the shortest wait")
        self.assertIn(self.frames_in(first, 'hp_bar_wait'), (damage, damage + 1))


if __name__ == '__main__':
    unittest.main()
