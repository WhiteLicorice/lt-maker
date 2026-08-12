import types
import unittest
from unittest.mock import patch

from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION


class AskForPaletteTests(unittest.TestCase):
    '''
    Add Frames stores imported frames in the coordinate space of whichever
    palette it ingests them with, and the engine picks an animation's palette by
    name. Guessing wrong there produces frames that preview correctly in the
    editor but render wrong in game, so an unrecognized palette has to ask.
    '''

    def setUp(self) -> None:
        from app.data.resources.resources import RESOURCES
        RESOURCES.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        self.resources = RESOURCES
        from app.editor.combat_animation_editor.frame_selector import FrameSelector
        self.FrameSelector = FrameSelector

        self.palette_a = RESOURCES.combat_palettes[0]
        self.palette_b = RESOURCES.combat_palettes[1]
        combat_anim = types.SimpleNamespace(nid='TestAnim')
        combat_anim.palettes = [['GenericBlue', self.palette_a.nid],
                                ['GenericRed', self.palette_b.nid]]
        self.selector = types.SimpleNamespace(
            combat_anim=combat_anim,
            current_palette_nid=self.palette_b.nid,
            NEW_PALETTE_OPTION=FrameSelector.NEW_PALETTE_OPTION,
            create_palette=lambda colors: FrameSelector.create_palette(self.selector, colors))

    def ask(self, chosen, ok=True):
        with patch('app.editor.combat_animation_editor.frame_selector.QInputDialog.getItem') as get_item:
            get_item.return_value = (chosen, ok)
            result = self.FrameSelector.ask_for_palette(self.selector, [(1, 2, 3)])
            self.offered, self.default_idx = get_item.call_args.args[3], get_item.call_args.args[4]
        return result

    def test_offers_every_palette_of_the_animation(self):
        self.ask('GenericBlue')
        self.assertEqual(['GenericBlue', 'GenericRed', self.FrameSelector.NEW_PALETTE_OPTION], self.offered)
        # Defaults to the palette the editor is currently showing
        self.assertEqual(1, self.default_idx)

    def test_chosen_palette_is_used_and_previewed(self):
        result = self.ask('GenericBlue')
        self.assertIs(self.palette_a, result)
        self.assertEqual(self.palette_a.nid, self.selector.current_palette_nid)

    def test_cancelling_imports_nothing(self):
        self.assertIsNone(self.ask('GenericBlue', ok=False))

    def test_new_palette_is_created_with_an_unused_name(self):
        before = len(self.selector.combat_anim.palettes)
        first = self.ask(self.FrameSelector.NEW_PALETTE_OPTION)
        second = self.ask(self.FrameSelector.NEW_PALETTE_OPTION)

        self.assertIsNotNone(first)
        self.assertIsNot(first, second)
        self.assertEqual(before + 2, len(self.selector.combat_anim.palettes))
        names = [name for name, nid in self.selector.combat_anim.palettes]
        self.assertEqual(len(names), len(set(names)))


if __name__ == '__main__':
    unittest.main()
