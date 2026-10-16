import itertools
import unittest

from app.tests import engine_harness
from app.tests.engine_harness import EngineTestCase


class StatusWearOffTests(EngineTestCase):
    '''
    On the GBA a unit is lit up for a moment when a bad status leaves it at the
    start of its phase. In testing_proj Sleep is one, timed and marked negative
    '''

    def upkeep(self, skill_nid, turns=1):
        '''
        Eirika's upkeep with the skill on her and that many turns of it left, at
        60 frames a second. Returns (step of the upkeep, whether she is lit up) a frame
        '''
        from app.engine import action
        harness = self.harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        game = harness.game
        self.unit = game.get_unit('Eirika')
        action.do(action.AddSkill(self.unit, skill_nid))
        skill = next(s for s in self.unit.skills if s.nid == skill_nid)
        skill.data['turns'] = turns
        game.state.change('status_upkeep')

        self.addCleanup(setattr, engine_harness, 'FRAME_MS', engine_harness.FRAME_MS)
        rows = []
        for frame in range(600):
            # A frame is 16 or 17 ms on a clock of whole milliseconds
            engine_harness.FRAME_MS = 16 if frame % 3 == 2 else 17
            harness.step()
            if 'status_upkeep' not in game.state.state_names():
                if rows:
                    break
                continue
            upkeep = next(s for s in game.state.state if s.name == 'status_upkeep')
            if getattr(upkeep, 'state', None):  # Once it has started
                rows.append((upkeep.state, self.unit.sprite.status_heal_start is not None))
        return rows

    def has(self, skill_nid) -> bool:
        return any(skill.nid == skill_nid for skill in self.unit.skills)

    def test_unit_is_lit_up_as_a_bad_status_leaves_it(self):
        rows = self.upkeep('Sleep')
        self.assertFalse(self.has('Sleep'))
        steps = [(step, len(list(frames))) for step, frames in itertools.groupby(step for step, _ in rows)]
        lengths = [length for step, length in steps if step == 'wear_off']
        self.assertEqual(1, len(lengths), steps)
        # 66 frames, and the few the camera takes to be sure it is there
        self.assertIn(lengths[0], range(66, 72))
        lit = [is_lit for step, is_lit in rows if step == 'wear_off']
        self.assertGreaterEqual(sum(lit), 64)

    def test_with_the_gbas_sound(self):
        '''The GBA plays song 0xAA, which is DebuffRecover here. Restore was four seconds long'''
        from unittest.mock import patch
        from app.engine import status_upkeep
        with patch.object(status_upkeep, 'get_sound_thread') as sound:
            self.upkeep('Sleep')
        played = [call.args[0] for call in sound.return_value.play_sfx.call_args_list]
        self.assertEqual(['DebuffRecover'], played)

    def test_no_sound_for_a_project_without_it(self):
        '''Nothing in its place'''
        from unittest.mock import MagicMock, patch
        from app.engine import sound
        resources = MagicMock()
        resources.sfx.get.return_value = None
        with patch.object(sound, 'RESOURCES', resources), patch.dict(sound.SFX, clear=True):
            self.assertIsNone(sound.DefaultSoundController.play_sfx(MagicMock(), 'DebuffRecover'))

    def test_status_with_turns_left_stays(self):
        rows = self.upkeep('Sleep', turns=3)
        self.assertTrue(self.has('Sleep'))
        self.assertNotIn('wear_off', [step for step, _ in rows])

    def test_nothing_for_a_status_that_is_not_a_bad_one(self):
        '''As on the GBA, where a boost from a dancer's ring leaves without a show'''
        from app.data.database.database import DB
        DB.skills.get('Sleep').components.remove_key('negative')
        rows = self.upkeep('Sleep')
        self.assertFalse(self.has('Sleep'))
        self.assertNotIn('wear_off', [step for step, _ in rows])


if __name__ == '__main__':
    unittest.main()
