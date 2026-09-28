import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.engine import action  # noqa: F401 -- avoids a circular import, see test_menu_options
from app.engine.combat import animation_combat
from app.engine.combat import playback as pb
from app.engine.combat.animation_combat import AnimationCombat
from app.engine.item_components.aesthetic_components import BattleHitTint

STONE = (64, 64, 64)

class BattleHitTintTests(unittest.TestCase):
    '''
    A spell's own Tint Enemy command only lasts a fixed number of frames, so it wears off
    before the combat does. Battle Hit Tint keeps the target tinted until the combat ends,
    even across a transform, which swaps in new battle anims mid-combat
    '''
    def setUp(self):
        self.left = SimpleNamespace(nid='Eirika', position=(0, 0))
        self.right = SimpleNamespace(nid='Bandit', position=(1, 0))
        self.combat = AnimationCombat.__new__(AnimationCombat)
        self.combat.left, self.combat.right = self.left, self.right
        self.combat.left_battle_anim, self.combat.right_battle_anim = MagicMock(hit_tint=None), MagicMock(hit_tint=None)
        self.combat.lp_battle_anim = self.combat.rp_battle_anim = None
        self.combat.at_range = False
        self.combat.battle_anim_tints = {}
        self.combat.get_actors = lambda: (self.left, None, self.right, None, self.combat.left_battle_anim)

    def hit(self, target):
        playback = []
        BattleHitTint(STONE).on_hit([], playback, self.left, None, target, None, target.position, 'attack', (0, 0))
        self.combat.playback = playback
        self.combat._handle_playback()

    def test_on_hit_adds_a_tint_brush_for_the_target(self):
        playback = []
        BattleHitTint(STONE).on_hit([], playback, self.left, None, self.right, None, (1, 0), 'attack', (0, 0))
        self.assertEqual([pb.BattleAnimTint(self.right, STONE)], playback)

    def test_hit_tints_only_the_targets_battle_anim(self):
        self.hit(self.right)
        self.assertEqual(STONE, self.combat.right_battle_anim.hit_tint)
        self.assertIsNone(self.combat.left_battle_anim.hit_tint)

    def test_tint_survives_a_transform(self):
        self.hit(self.right)
        # A transform swaps in new battle anims and re-pairs them
        self.combat.right_battle_anim = MagicMock(hit_tint=None)
        with patch.object(animation_combat, 'game', MagicMock()):
            self.combat.pair_battle_animations(0)
        self.assertEqual(STONE, self.combat.right_battle_anim.hit_tint)

if __name__ == '__main__':
    unittest.main()
