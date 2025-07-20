from __future__ import annotations

from app.data.database.components import ComponentType
from app.data.database.database import DB
from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.difficulty_modes import RNGOption

from app.events.regions import RegionType
from app.events import triggers

from app.engine import (action, banner, combat_calcs, engine, equations,
                        image_mods, item_funcs, item_system, skill_system)
from app.engine.game_state import game
from app.engine.objects.unit import UnitObject
from app.engine.exp_calculator import ExpCalcType, ExpCalculator
from app.engine.combat import playback as pb
from app.engine.movement import movement_funcs

from app.utilities import utils, static_random

import logging

# Importing methods
from app.engine.item_components.exp_components import (determine_all_defenders, 
                                                       determine_all_damaged_defenders,
                                                       determine_all_healed_defenders, 
                                                       modify_exp)


class DoNothing(ItemComponent):
    nid = 'do_nothing'
    desc = 'does nothing'
    tag = ItemTags.CUSTOM

    expose = ComponentType.Int
    value = 1
