import unittest
from unittest.mock import MagicMock, patch

from app.tests.engine_harness import EngineTestCase

SUPPRESSION_HOOKS = ('no_map_hp_display', 'no_map_hit_flash', 'no_map_hit_sfx',
                     'no_map_combat_movement', 'no_map_damage_numbers')


class SuppressionComponentTests(unittest.TestCase):
    """The AESTHETIC components that switch off default map combat flourishes."""

    def call_hook(self, hook_name, components):
        from app.engine import item_system
        mock_item = MagicMock()
        mock_item.components = components
        mock_item.parent_item = None
        mock_unit = MagicMock()
        mock_unit.skills = []
        return getattr(item_system, hook_name)(mock_unit, mock_item)

    def test_each_component_only_answers_its_own_hook(self):
        from app.engine.item_components import aesthetic_components as ac

        pairs = [(ac.NoMapHitFlash(), 'no_map_hit_flash'),
                 (ac.NoMapHitSFX(), 'no_map_hit_sfx'),
                 (ac.NoMapCombatMovement(), 'no_map_combat_movement'),
                 (ac.NoMapDamageNumbers(), 'no_map_damage_numbers')]
        for component, own_hook in pairs:
            for hook in SUPPRESSION_HOOKS:
                expected = hook == own_hook
                self.assertEqual(expected, self.call_hook(hook, [component]),
                                 '%s answered %s with %s' % (component.nid, hook, not expected))

    def test_super_component_answers_every_suppression_hook(self):
        from app.engine.item_components.aesthetic_components import NoMapCombatFX

        for hook in SUPPRESSION_HOOKS:
            self.assertTrue(self.call_hook(hook, [NoMapCombatFX()]), hook)

    def test_hooks_default_to_false_with_no_components(self):
        for hook in SUPPRESSION_HOOKS:
            self.assertFalse(self.call_hook(hook, []), hook)


class SpriteMovementSuppressionTests(EngineTestCase):
    def build_sprite(self, position):
        from app.engine.unit_sprite import UnitSprite
        sprite = UnitSprite.__new__(UnitSprite)
        sprite.unit = MagicMock()
        sprite.unit.position = position
        sprite.state = 'normal'
        sprite.image_state = 'down'
        sprite.net_position = None
        sprite.offset = [0, 0]
        sprite.suppress_combat_movement = False
        sprite._roam_position = None
        sprite._fake_position = None
        sprite.transition_state = 'normal'
        sprite.transition_counter = 0
        sprite.transition_time = UnitSprite.default_transition_time
        return sprite

    def test_attacker_turns_to_face_its_target_by_default(self):
        from app.engine import unit_sprite

        sprite = self.build_sprite((1, 1))
        with patch.object(unit_sprite, 'game') as mock_game:
            mock_game.cursor.position = (4, 1)
            sprite.change_state('combat_attacker')
        self.assertEqual('right', sprite.image_state)

    def test_no_combat_movement_holds_the_attacker_facing(self):
        from app.engine import unit_sprite

        sprite = self.build_sprite((1, 1))
        with patch.object(unit_sprite, 'game') as mock_game:
            mock_game.cursor.position = (4, 1)
            sprite.change_state('combat_attacker', suppress_movement=True)
        self.assertEqual('down', sprite.image_state)
        # net_position is still recorded -- downstream combat code reads it
        self.assertEqual((3, 0), sprite.net_position)

    def test_no_combat_movement_keeps_the_jostle_offset_at_zero(self):
        from app.engine import unit_sprite

        sprite = self.build_sprite((1, 1))
        with patch.object(unit_sprite, 'game') as mock_game:
            mock_game.cursor.position = (4, 1)
            sprite.change_state('combat_anim', suppress_movement=True)
            sprite.update_state()
        self.assertEqual([0, 0], sprite.offset)

    def test_suppression_does_not_leak_into_the_next_combat(self):
        from app.engine import unit_sprite

        sprite = self.build_sprite((1, 1))
        with patch.object(unit_sprite, 'game') as mock_game:
            mock_game.cursor.position = (4, 1)
            sprite.change_state('combat_attacker', suppress_movement=True)
            sprite.change_state('normal')
            sprite.change_state('combat_attacker')
        self.assertFalse(sprite.suppress_combat_movement)
        self.assertEqual('right', sprite.image_state)


class PlaybackSuppressionTests(EngineTestCase):
    """_handle_playback must drop the brushes the suppression hooks switch off."""

    def build_combat(self, **flags):
        from app.engine.combat.map_combat import MapCombat

        combat = MapCombat.__new__(MapCombat)
        combat.playback = []
        combat.animations = []
        combat.health_bars = {}
        combat.no_hit_flash = flags.get('no_hit_flash', False)
        combat.no_hit_sfx = flags.get('no_hit_sfx', False)
        combat.no_combat_movement = flags.get('no_combat_movement', False)
        combat.no_damage_numbers = flags.get('no_damage_numbers', False)
        return combat

    def build_target(self):
        target = MagicMock()
        target.position = (2, 2)
        target.sprite.damage_numbers = []
        return target

    def handle(self, combat):
        from app.engine.combat import map_combat
        with patch.object(map_combat, 'get_sound_thread') as mock_sound:
            combat._handle_playback()
        return mock_sound.return_value.play_sfx

    def test_hit_flash_plays_by_default_and_is_suppressed_by_the_hook(self):
        from app.engine.combat import playback as pb

        for suppress, expected_calls in ((False, 1), (True, 0)):
            target = self.build_target()
            combat = self.build_combat(no_hit_flash=suppress)
            combat.playback = [pb.UnitTintAdd(target, (255, 255, 255))]
            self.handle(combat)
            self.assertEqual(expected_calls, target.sprite.begin_flicker.call_count)

    def test_crit_tint_is_suppressed_by_the_hit_flash_hook(self):
        from app.engine.combat import playback as pb

        target = self.build_target()
        combat = self.build_combat(no_hit_flash=True)
        combat.playback = [pb.CritTint(target, (255, 255, 255))]
        self.handle(combat)
        target.sprite.begin_flicker.assert_not_called()
        target.sprite.start_flicker.assert_not_called()

    def test_crit_vibrate_is_suppressed_by_the_combat_movement_hook(self):
        from app.engine.combat import playback as pb

        for suppress, expected_calls in ((False, 1), (True, 0)):
            target = self.build_target()
            combat = self.build_combat(no_combat_movement=suppress)
            combat.playback = [pb.CritVibrate(target)]
            self.handle(combat)
            self.assertEqual(expected_calls, target.sprite.start_vibrate.call_count)

    def test_hit_sound_is_suppressed_by_the_hit_sfx_hook(self):
        from app.engine.combat import playback as pb

        for suppress, expected_calls in ((False, 1), (True, 0)):
            combat = self.build_combat(no_hit_sfx=suppress)
            combat.playback = [pb.HitSound('Attack Hit 1')]
            play_sfx = self.handle(combat)
            self.assertEqual(expected_calls, play_sfx.call_count)

    def test_damage_numbers_are_suppressed_by_the_damage_numbers_hook(self):
        from app.engine.combat import playback as pb

        brush_types = ('damage_hit', 'damage_crit', 'heal_hit')
        for suppress in (False, True):
            for brush_type in brush_types:
                target = self.build_target()
                attacker, item = MagicMock(), MagicMock()
                if brush_type == 'damage_hit':
                    brush = pb.DamageHit(attacker, item, target, 12, 12)
                elif brush_type == 'damage_crit':
                    brush = pb.DamageCrit(attacker, item, target, 12, 12)
                else:
                    brush = pb.HealHit(attacker, item, target, 12, 12)
                combat = self.build_combat(no_damage_numbers=suppress)
                combat.playback = [brush]
                self.handle(combat)
                expected = 0 if suppress else len('12')
                self.assertEqual(expected, len(target.sprite.damage_numbers),
                                 '%s with suppress=%s' % (brush_type, suppress))


if __name__ == '__main__':
    unittest.main()
