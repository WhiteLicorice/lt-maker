import unittest
from unittest.mock import MagicMock

from app.tests.engine_harness import EngineTestCase


class SelectedFacingTests(EngineTestCase):
    def build_sprite(self, tags):
        from app.engine.unit_sprite import UnitSprite
        sprite = UnitSprite.__new__(UnitSprite)
        sprite.unit = MagicMock()
        sprite.unit.tags = tags
        sprite.image_state = 'passive'
        return sprite

    def test_mounted_unit_faces_right_while_choosing_a_destination(self):
        sprite = self.build_sprite({'Mounted'})
        sprite.change_state('selected')
        self.assertEqual('right', sprite.image_state)

    def test_unmounted_unit_faces_down_while_choosing_a_destination(self):
        sprite = self.build_sprite({'Armor'})
        sprite.change_state('selected')
        self.assertEqual('down', sprite.image_state)

    def test_picking_a_destination_uses_the_move_select_facing(self):
        '''
        The 'selected' sprite state used to face every unit down. Mounted units
        face right instead while the player picks a destination. In testing_proj
        Seth is a Paladin, which is Mounted, and Eirika is not
        '''
        harness = self.start_harness()
        harness.start_level('0')
        harness.run_until_state('free')
        for unit_nid, facing in (('Seth', 'right'), ('Eirika', 'down')):
            harness.select_unit(unit_nid)
            self.assertEqual(facing, harness.game.get_unit(unit_nid).sprite.image_state, unit_nid)
            harness.press('BACK')
            harness.run_until_state('free')


if __name__ == '__main__':
    unittest.main()
