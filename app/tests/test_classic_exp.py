import unittest
from types import SimpleNamespace

from app.engine.exp_calculator import ExpCalculator


def classic_exp(unit_level, unit_tier, target_level, target_tier, kill=False, boss=False, mode_coeff=1):
    '''The classic formula with the constants' default values, for classes in none of the lists'''
    unit = SimpleNamespace(level=unit_level)
    target = SimpleNamespace(level=target_level, is_dying=kill, tags=['Boss'] if boss else [], klass='Fighter')
    return ExpCalculator.classic_curve_calculator(
        unit, target,
        SimpleNamespace(nid='Fighter', tier=unit_tier), SimpleNamespace(nid='Fighter', tier=target_tier),
        damage_bonus=31, kill_bonus=20, boss_bonus=40, thief_bonus=20, thief_list='Thief',
        class_bonus_a=20, class_bonus_a_tier=2,
        class_bonus_b=60, class_bonus_b_tier=2, class_bonus_b1=40, class_bonus_b1_list='Bishop',
        class_power_1=1, class_power_1_list='Entombed', class_power_1_tier=0,
        class_power_2=2, class_power_2_list='Soldier',
        class_power_3=3, class_power_4=5, class_power_4_tier=3,
        mode_coeff=mode_coeff)


class ClassicExpTests(unittest.TestCase):
    def test_hit_on_an_equal(self):
        self.assertEqual(31 // 3, classic_exp(5, 1, 5, 1))

    def test_kill_of_an_equal(self):
        self.assertEqual(31 // 3 + 20, classic_exp(5, 1, 5, 1, kill=True))

    def test_hit_far_below_own_level_gives_nothing(self):
        # A level 20 promoted unit counts as level 40: 31 + 5 - 40 is below 0
        self.assertEqual(0, classic_exp(20, 2, 5, 1))

    def test_hit_far_below_own_level_takes_nothing_from_the_kill(self):
        '''
        FE8 before the route split: a level 20 promoted unit that kills a level 5
        boss gets 20 + (15 - 120 / 2) + 40 = 15 for the kill and 0 for the hit.
        The hit used to come to (31 + 5 - 40) // 3 = -2 and leave 13
        '''
        self.assertEqual(15, classic_exp(20, 2, 5, 1, kill=True, boss=True, mode_coeff=2))


if __name__ == '__main__':
    unittest.main()
