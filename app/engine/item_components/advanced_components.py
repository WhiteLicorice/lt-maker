from app.data.database.item_components import ItemComponent, ItemTags
from app.data.database.components import ComponentType
from app.engine import action, item_funcs
from app.engine import skill_system
from app.engine.game_state import game
from app.engine.combat import playback as pb
from app.engine.movement import movement_funcs

class MultiItem(ItemComponent):
    nid = 'multi_item'
    desc = "Stores a list of other items to be included as part of this multi item. When using the item the sub-items stored within the list can each be accessed and used. Useful for Three Houses-like magic system."
    tag = ItemTags.ADVANCED

    expose = (ComponentType.List, ComponentType.Item)

class MultiItemHidesUnusableChildren(ItemComponent):
    nid = 'multi_item_hides_unavailable'
    desc = 'Multi Item will automatically hide subitems that are not usable'
    tag = ItemTags.ADVANCED

class SequenceItem(ItemComponent):
    nid = 'sequence_item'
    desc = "Item requires various sub-items to be work properly. Useful for complex items like Warp or Rescue. Items are used from list's top to bottom."
    tag = ItemTags.ADVANCED

    expose = (ComponentType.List, ComponentType.Item)

class MultiTarget(ItemComponent):
    nid = 'multi_target'
    desc = "Can target a specified number of units when used."
    tag = ItemTags.ADVANCED

    expose = ComponentType.Int
    value = 2

    def num_targets(self, unit, item) -> int:
        return self.value

class AllowSameTarget(ItemComponent):
    nid = 'allow_same_target'
    desc = "If the item is multi target this component allows it to select the same target multiple times."
    tag = ItemTags.ADVANCED

    def allow_same_target(self, unit, item) -> bool:
        return True

class AllowLessThanMaxTargets(ItemComponent):
    nid = 'allow_less_than_max_targets'
    desc = "If the item is multi target this component allows the user to select less than the required number of targets with the item"
    tag = ItemTags.ADVANCED

    def allow_less_than_max_targets(self, unit, item) -> bool:
        return True

class StoreUnit(ItemComponent):
    nid = 'store_unit'
    desc = "The targeted unit is stored in the game's memory when hit. The next time the unload unit component is called the unit is placed on the targeted tile."
    tag = ItemTags.ADVANCED

    def init(self, item):
        self.item.data['stored_unit'] = None

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if not skill_system.ignore_forced_movement(target):
            self.item.data['stored_unit'] = target.nid
            # actions.append(action.WarpOut(target))
            playback.append(pb.RescueHit(unit, item, target))

class UnloadUnit(ItemComponent):
    nid = 'unload_unit'
    desc = "Places the unit stored through the store unit component on the specified target (most often a tile)."
    tag = ItemTags.ADVANCED

    def target_restrict(self, unit, item, def_pos, splash) -> bool:
        if def_pos and not game.board.get_unit(def_pos) and movement_funcs.check_simple_traversable(def_pos):
            return True
        return False

    def on_hit(self, actions, playback, unit, item, target, item2, target_pos, mode, attack_info):
        if self.item.data.get('stored_unit'):
            rescuee = game.get_unit(self.item.data['stored_unit'])
            self.item.data['stored_unit'] = None
            if rescuee:
                actions.append(action.Warp(rescuee, target_pos))
                # Move camera over position
                game.cursor.set_pos(target_pos)

class AdditionalItemCommand(ItemComponent):
    nid = 'additional_item_command'
    desc = "Adds another item as a menu option to an existing item."
    tag = ItemTags.BASE
    
    expose = ComponentType.Item
        
    def extra_command(self, unit, item):
        if item.command_item:
            return item.command_item
        else:
            new_item = item_funcs.create_item(unit, self.value)
            game.register_item(new_item)
            item.command_item = new_item
            item.command_uid = new_item.uid
            new_item.command_parent_item = item
            return new_item