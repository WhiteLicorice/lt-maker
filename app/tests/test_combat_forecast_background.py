import unittest
from dataclasses import dataclass
from unittest.mock import patch

from app.sprites import SpriteDict
from app.tests.engine_harness import EngineTestCase


@dataclass
class MockTeam():
    combat_color: str
    diverged: bool = False

    def combat_color_diverged(self) -> bool:
        return self.diverged


class RecordingSprites(SpriteDict):
    '''Notes down every sprite nid the forecast actually asks for, so a test can
    tell which of the two sprite formats was chosen.'''

    def __init__(self, base):
        super().__init__(base)
        self.requested = []

    def get(self, val, fallback='bg_black_tile'):
        self.requested.append(val)
        return super().get(val, fallback)


class CombatForecastBackgroundTests(EngineTestCase):
    def setUp(self):
        super().setUp()
        from app.engine import ui_view
        self.ui_view = ui_view

    def _build(self, a_team, d_team, **kwargs):
        '''Returns (surface, list of requested sprite nids). _build_forecast_background
        touches no instance state, so it can be called off the class.'''
        flags = dict(grandmaster=False, detailed_flag=False, crit_flag=False,
                     guard_flag=False, a_assist_flag=False, d_assist_flag=False)
        flags.update(kwargs)
        recorder = RecordingSprites(self.ui_view.SPRITES)
        with patch.object(self.ui_view, 'SPRITES', recorder):
            surf = self.ui_view.UIView._build_forecast_background(
                None, attacker_team=a_team, defender_team=d_team, **flags)
        return surf, recorder.requested

    def test_uses_new_format_for_a_color_the_old_sprites_lack(self):
        '''
        The old one-image-per-color sprites only ship in red and purple, so a team
        whose combat color is green -- which default.ltproj's 'other' team is out of
        the box -- silently rendered a red forecast. combat_color_diverged() did not
        catch it because the color was never changed at runtime, only in the editor.
        '''
        _, requested = self._build(MockTeam('blue'), MockTeam('green'))
        self.assertIn('attack_info_3_bottom_green', requested)
        self.assertNotIn('attack_info_green', requested)

    def test_prefers_an_old_format_sprite_that_does_exist(self):
        '''A project's own old-format art must keep winning, or every existing
        project's forecast changes appearance.'''
        _, requested = self._build(MockTeam('blue'), MockTeam('red'))
        self.assertIn('attack_info_red', requested)
        self.assertFalse([nid for nid in requested if nid.startswith('attack_info_3_')])

    def test_a_runtime_color_change_still_forces_the_new_format(self):
        _, requested = self._build(MockTeam('blue'), MockTeam('red', diverged=True))
        self.assertIn('attack_info_3_bottom_red', requested)
        self.assertNotIn('attack_info_red', requested)

    def test_a_color_with_no_sprites_at_all_does_not_crash(self):
        '''Both fallbacks for the top piece used to keep the requested color, so
        recoloring a team to something with no sprites at all missed twice, SPRITES.get
        returned None, and building the forecast raised on .copy().'''
        expected, _ = self._build(MockTeam('blue'), MockTeam('red', diverged=True))
        surf, _ = self._build(MockTeam('orange', diverged=True),
                              MockTeam('orange', diverged=True))
        self.assertEqual(surf.get_size(), expected.get_size())

    def test_assist_boxes_follow_the_same_fallbacks(self):
        surf, requested = self._build(MockTeam('orange', diverged=True),
                                      MockTeam('green', diverged=True),
                                      a_assist_flag=True, d_assist_flag=True)
        self.assertIn('assist_info_2_green', requested)
        # 'orange' has no assist sprite in either format, so it lands on the default
        self.assertIn('assist_info_2_blue', requested)


if __name__ == '__main__':
    unittest.main()
