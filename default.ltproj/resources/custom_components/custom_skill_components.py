from __future__ import annotations

from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.database.skill_components import SkillComponent, SkillTags

from app.engine import (action, banner, combat_calcs, engine, equations,
                        image_mods, item_funcs, item_system, skill_system)
from app.engine.game_state import game
from app.engine.objects.unit import UnitObject
from app.engine.source_type import SourceType
from app.engine.combat import playback as pb
from app.engine.movement import movement_funcs

from app.utilities import utils, static_random
from app.utilities.enums import Strike

import logging

# Importing methods
from app.engine.skill_components.advanced_components import get_proc_rate, get_weapon_filter
from app.engine.skill_components.charge_components import get_marks
from app.engine.skill_components.combat2_components import get_pc_damage


class DoNothing(SkillComponent):
    nid = 'do_nothing'
    desc = 'does nothing'
    tag = SkillTags.CUSTOM

    expose = ComponentType.Int
    value = 1
