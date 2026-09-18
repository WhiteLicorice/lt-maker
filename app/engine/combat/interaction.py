from app.utilities import utils

from app.engine import item_system, skill_system, battle_animation
from app.engine.game_state import game
from app.engine.input_manager import get_input_manager

from app.engine.combat.simple_combat import SimpleCombat
from app.engine.combat.map_combat import MapCombat
from app.engine.combat.base_combat import BaseCombat
from app.engine.combat.animation_combat import AnimationCombat
from app.engine import config as cf

from app.engine.objects.unit import UnitObject
from app.engine.objects.item import ItemObject

def has_animation(attacker: UnitObject, item: ItemObject, main_target: tuple, force_animation=False, force_no_animation=False) -> bool:
    defender: UnitObject = game.board.get_unit(main_target)
    if not defender:
        return False

    def animation_wanted(attacker: UnitObject, defender: UnitObject) -> bool:
        return cf.SETTINGS['animation'] == 'Always' or \
            (cf.SETTINGS['animation'] == 'Your Turn' and attacker.team == 'player') or \
            (cf.SETTINGS['animation'] == 'Combat Only' and skill_system.check_enemy(attacker, defender))

    toggle_anim = get_input_manager().is_pressed('START')
    anim = animation_wanted(attacker, defender) != toggle_anim
    if attacker is not defender and (anim or force_animation) and not force_no_animation:
        if attacker.position and defender.position:
            distance = utils.calculate_distance(attacker.position, defender.position)
        else:
            distance = 1
        attacker_anim = battle_animation.get_battle_anim(attacker, item, distance)
        def_item = defender.get_weapon()
        defender_anim = battle_animation.get_battle_anim(defender, def_item, distance)
        return bool(attacker_anim and defender_anim)

    return False

def engage(attacker: UnitObject, positions: list, main_item: ItemObject, skip: bool = False, script: list = None,
           total_rounds: int = 1, force_animation: bool = False, force_no_animation: bool = False, arena_combat: bool = False):
    """
    Builds the correct combat controller for this interaction

    Targets each of the positions in "positions" with the item
    Determines what kind of combat (Simple, Map, or Animation), should be used for this kind of interaction
    "positions" is a list. The subelements of positions can also be a list, if the item is a multitargeting item
    """
    target_positions = []
    main_targets = []
    splashes = []
    if main_item.sequence_item:
        items = main_item.subitems
    else:
        items = [main_item]

    multitarget_items = items[:]
    for idx, position in enumerate(positions):
        item = items[idx]

        if isinstance(position, list):  # Treat multi-target like sequence item
            for pos in position:
                main_target, splash = item_system.splash(attacker, item, pos)
                target_positions.append(pos)
                main_targets.append(main_target)
                splashes.append(splash)

            # To separate out each instance of the multi-target item so that
            # each positional target pretends to be it's own item-target pair for the next combat.
            # Earlier multi-target items are already expanded, so this item sits where its first target does
            first_target_idx = len(target_positions) - len(position)
            multitarget_items[first_target_idx:first_target_idx] = [item] * (len(position) - 1)

        elif position:
            main_target, splash = item_system.splash(attacker, item, position)
            target_positions.append(position)
            main_targets.append(main_target)
            splashes.append(splash)

        else:  # Using an item in the base/prep
            target_positions.append(None)
            main_targets.append(None)
            splashes.append([])

    # To account for any multitarget items that have been duplicated in the preceding for loop
    items = multitarget_items

    if target_positions[0] is None:
        # If we are targeting None, (which means we're in base using an item)
        combat = BaseCombat(attacker, main_item, attacker, script, total_rounds)
    elif skip:
        # If we are skipping
        combat = SimpleCombat(attacker, main_item, items, target_positions, main_targets, splashes, script, total_rounds)
        game.highlight.remove_highlights()
    # If more than one target position or more than one item being used, cannot use animation combat
    elif len(positions) > 1 or len(items) > 1:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script, total_rounds)
    # If affecting more than one target, cannot use animation combat
    elif not main_targets[0] or splashes[0]:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script, total_rounds)
    elif has_animation(attacker, item, main_target, force_animation, force_no_animation):
        defender = game.board.get_unit(main_target)
        def_item = defender.get_weapon()
        combat = AnimationCombat(attacker, item, defender, def_item, script, total_rounds, arena_combat)
    else:
        combat = MapCombat(attacker, main_item, items, target_positions, main_targets, splashes, script, total_rounds)
    return combat

def start_combat(unit: UnitObject, target: tuple, item: ItemObject, skip: bool = False,
                 ai_combat: bool = False, event_combat: bool = False, script: list = None,
                 total_rounds: int = 1, arena: bool = False, force_animation: bool = False, 
                 force_no_animation: bool = False):
    """
    Target is a position tuple
    """
    # Set up the target positions
    if item.sequence_item:
        targets = []
        for subitem in item.subitems:
            num_targets = item_system.num_targets(unit, subitem)
            if num_targets > 1:
                targets.append([target] * num_targets)
            else:
                targets.append(target)
    else:
        num_targets = item_system.num_targets(unit, item)
        if num_targets > 1:
            targets = [[target] * num_targets]
        else:
            targets = [target]

    # State change happens first, so if anything changes state during 
    # initialization of combat, that will happen before combat really
    # starts
    game.state.change('combat')
    combat = engage(
        unit, targets, item, skip=skip, script=script, total_rounds=total_rounds,
        arena_combat=arena, force_animation=force_animation, force_no_animation=force_no_animation)
    combat.ai_combat = ai_combat  # Must mark this so we can come back!
    combat.event_combat = event_combat  # Must mark this so we can come back!
    combat.arena_combat = arena
    game.combat_instance.append(combat)
