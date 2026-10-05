import math

from enum import Enum

class ExpCalcType(Enum):
  STANDARD = 'standard'
  GOMPERTZ = 'gompertz'
  # FE6/7/8
  CLASSIC = 'classic'

class ExpCalculator():
  @classmethod
  def standard_curve_calculator(cls, level_diff, exp_offset, exp_curve, exp_magnitude):
    adjusted_level_diff = level_diff + exp_offset
    exp_gained = math.exp(adjusted_level_diff * exp_curve)
    total_exp_gained = exp_magnitude * exp_gained
    return total_exp_gained

  @classmethod
  def gompertz_curve_calculator(cls, level_diff, max_exp, min_exp, slope, zero_diff_exp):
    base = min_exp
    max_exp = max_exp + 1 # because we use floor
    magnitude = max_exp - min_exp
    offset = ExpCalculator.gompertz_offset_calculator(magnitude, min_exp, slope, zero_diff_exp)
    return base + magnitude * math.exp(-1 * math.exp(-slope * (level_diff - offset)))

  @classmethod
  def gompertz_offset_calculator(cls, magnitude, min_exp, slope, intercept):
    return 1.0 / slope * math.log(-1 * math.log((intercept - min_exp) / magnitude))
  
  @classmethod
  def classic_curve_calculator(cls,
                               unit,
                               target,
                               unit_klass,
                               target_klass,
                               damage_bonus,
                               kill_bonus,
                               boss_bonus,
                               thief_bonus,
                               thief_list,
                               class_bonus_a,
                               class_bonus_a_tier,
                               class_bonus_b,
                               class_bonus_b_tier,
                               class_bonus_b1,
                               class_bonus_b1_list,
                               class_power_1,
                               class_power_1_list,
                               class_power_1_tier,
                               class_power_2,
                               class_power_2_list,
                               class_power_3,
                               class_power_4,
                               class_power_4_tier,
                               mode_coeff
                              ):
    def get_class_bonus_a(klass):
      if klass.tier >= class_bonus_a_tier:
        return class_bonus_a
      return 0
    
    def get_class_bonus_b(klass):
      if klass.nid in class_bonus_b1_list.split(','):
        return class_bonus_b1
      elif klass.tier >= class_bonus_b_tier:
        return class_bonus_b
      return 0

    def get_class_power(klass):
      if klass.tier <= class_power_1_tier or klass.nid in class_power_1_list.split(','):
        return class_power_1
      elif klass.nid in class_power_2_list.split(','):
        return class_power_2
      elif klass.tier >= class_power_4_tier:
        return class_power_4
      return class_power_3
        
    result = (damage_bonus + target.level + get_class_bonus_a(target_klass) - (unit.level + get_class_bonus_a(unit_klass)))//get_class_power(unit_klass)
    if target.is_dying:
        base = target.level*get_class_power(target_klass) + get_class_bonus_b(target_klass) - (unit.level*get_class_power(unit_klass) + get_class_bonus_b(unit_klass))
        if mode_coeff > 1 and base <= 0:
            # apply mode coefficient
            base = target.level*get_class_power(target_klass) + get_class_bonus_b(target_klass) - (unit.level*get_class_power(unit_klass) + get_class_bonus_b(unit_klass))//mode_coeff
        boss = boss_bonus if 'Boss' in target.tags else 0
        thief = thief_bonus if target.klass in thief_list.split(',') else 0
        result = result + max(0, kill_bonus + base + boss + thief)

    return result

if __name__ == "__main__":
  # generate some curves
  max_exp = 20
  min_exp = 1
  slope = 0.5
  zero_diff_exp = 10
  for diff in range(-10, 10):
    exp = ExpCalculator.gompertz_curve_calculator(diff, max_exp, min_exp, slope, zero_diff_exp)
    print("%d,\t%d" % (diff, exp * 3))