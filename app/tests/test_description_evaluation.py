import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pygame

import app.engine.sprites as sprites
from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine import help_menu, text_funcs
from app.engine.game_state import game
from app.engine.objects.skill import SkillObject

HEALER = 'Moulder'
# Squid's description, with the healer's MAG at 6: 15 + 6 // 3 = 17
REGENERATION = "Recover {e:15+game.get_unit(skill.initiator_nid).get_stat('MAG')//3}% of max HP"
EVALUATED = "Recover 17% of max HP"

class SkillDescriptionEvaluationTests(unittest.TestCase):
    """
    Squid: a skill description naming its skill as `skill` only evaluated in SkillHelpDialog,
    the one place that passed it, and logged "name 'skill' is not defined" everywhere else
    """
    @classmethod
    def setUpClass(cls):
        # The state modules read sprites and build surfaces at import
        sprites.load_images()
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        pygame.display.init()
        if not pygame.display.get_surface():
            pygame.display.set_mode((1, 1))

    def setUp(self):
        healer = MagicMock()
        healer.get_stat.return_value = 6
        for patcher in (patch.object(game, 'get_unit', lambda nid: healer if nid == HEALER else None),
                        patch.object(text_funcs, 'translate', lambda string: string)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.help_dialog = MagicMock()
        dialog_patch = patch.object(help_menu, 'HelpDialog', self.help_dialog)
        dialog_patch.start()
        self.addCleanup(dialog_patch.stop)

        self.skill = SkillObject('Regeneration', 'Regeneration', REGENERATION)
        self.skill.initiator_nid = HEALER

    def assert_help_box_text(self, build_help_box):
        with self.assertNoLogs(level='ERROR'):
            build_help_box()
        self.assertEqual(self.help_dialog.call_args.args[0], EVALUATED)

    def test_basic_skill_option(self):
        from app.engine.game_menus.icon_options import BasicSkillOption
        option = BasicSkillOption.__new__(BasicSkillOption)
        option._value = self.skill
        option._help_box = None
        self.assert_help_box_text(option.get_help_box)

    def test_skill_menu_option(self):
        from app.engine.game_menus.menu_options import SkillOption
        self.assert_help_box_text(SkillOption(0, self.skill).get_help_box)

    def test_feat_choice_option(self):
        from app.engine import feat_choice
        option = feat_choice.SkillOption.__new__(feat_choice.SkillOption)
        option.skill = self.skill
        self.assert_help_box_text(option.get_help_box)

    def test_player_choice_skill(self):
        from app.engine import player_choice
        state = SimpleNamespace(data_type='type_skill')
        db = SimpleNamespace(skills={self.skill.nid: self.skill})
        with patch.object(player_choice, 'DB', db):
            self.assert_help_box_text(
                lambda: player_choice.PlayerChoiceState.create_help_boxes(state, [self.skill.nid]))

if __name__ == '__main__':
    unittest.main()
