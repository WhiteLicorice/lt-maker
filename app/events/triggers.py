from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from app.engine.objects.item import ItemObject
    from app.engine.objects.unit import UnitObject
    from app.engine.objects.region import RegionObject
    from app.engine.combat.playback import PlaybackBrush

from app.utilities.typing import NID


@dataclass()
class EventTrigger():
    """
    A trigger called sometime during the engine that allows the user to execute events.

    :meta private: # Hide from Sphinx
    """
    nid: ClassVar[NID]
    hidden: ClassVar[bool] = False #: Whether or not this trigger is selectable. True for deprecated and utility triggers.

    def to_args(self):
        return self.__dict__.copy()

@dataclass()
class GenericTrigger(EventTrigger):
    """A generic trigger containing common fields. Use to trigger
    anonymous events.

    :meta private: # Hide from Sphinx
    """
    nid: ClassVar[NID] = None
    hidden: ClassVar[bool] = True
    unit1: UnitObject = None
    unit2: UnitObject = None
    position: Tuple[int, int] = None
    local_args: Dict[str, Any] = None

    def to_args(self):
        self_dict = self.__dict__.copy()
        del self_dict['local_args']
        if self.local_args:
            final_args = self.local_args.copy()
            final_args.update(self_dict)
        else:
            final_args = self_dict
        return final_args

@dataclass(init=True)
class LevelStart(EventTrigger):
    """
    Occurs at the very beginning of a level. The chapter screen and title is usually
    displayed here, as well as introductory cinematics.
    """
    nid: ClassVar[NID] = 'level_start'

@dataclass(init=True)
class LevelEnd(EventTrigger):
    """
    This occurs once `win_game` is set in another event. This is called at the
    end of gameplay, and usually handles end cinematics before going to
    the save screen or overworld.
    """
    nid: ClassVar[NID] = 'level_end'

@dataclass(init=True)
class OverworldStart(EventTrigger):
    """
    Occurs upon entering the overworld.
    """
    nid: ClassVar[NID] = 'overworld_start'

@dataclass(init=True)
class LevelSelect(EventTrigger):
    """
    Occurs when an overworld entity is about to issue a move to the node
    containing the next level. Because of implementation detail, when
    this event occurs, it supersedes any queued moves. Therefore, the
    entity will *not move* to the selected node. Any events that use
    this trigger should include a scripted move if movement is desired.
    """
    nid: ClassVar[NID] = 'level_select'

@dataclass(init=True)
class PhaseChange(EventTrigger):
    """
    Occurs whenever the phase changes.
    """
    nid: ClassVar[NID] = 'phase_change'
    team: NID #: contains the NID of the team of the new phase

@dataclass(init=True)
class TurnChange(EventTrigger):
    """
    Occurs immediately before turn changes to Player Phase. Useful for dialogue or reinforcements.
    """
    nid: ClassVar[NID] = 'turn_change'

@dataclass(init=True)
class EnemyTurnChange(EventTrigger):
    """
    Occurs immediately before turn changes to Enemy Phase.
    Useful for "same turn reinforcements" and other evil deeds.
    """
    nid: ClassVar[NID] = 'enemy_turn_change'

@dataclass(init=True)
class Enemy2TurnChange(EventTrigger):
    """
    Occurs immediately before turn changes to Second Enemy's Phase.
    """
    nid: ClassVar[NID] = 'enemy2_turn_change'

@dataclass(init=True)
class OtherTurnChange(EventTrigger):
    """
    Occurs immediately before turn changes to Other Phase.
    """
    nid: ClassVar[NID] = 'other_turn_change'

@dataclass(init=True)
class OnRegionInteract(EventTrigger):
    """
    Occurs when a unit interacts with an event region.
    All event region type events (like Shop, Armory, Visit, etc.)
    follow this trigger's format.
    """
    nid: ClassVar[NID] = 'on_region_interact'
    unit1: UnitObject  #: the unit that is interacting
    position: Tuple[int, int]  #: the position of the unit.
    region: RegionObject  #: the event region.

@dataclass(init=True)
class OnRoamInteract(EventTrigger):
    """
    Occurs when a unit interacts during free roam. If a Talk
    or Region event exists, they will trigger instead. This
    event will only trigger if Talk or Region events do not
    exist at the given location during Free Roam.
    Can be used for Generic NPC dialogue or for opening a menu
    when not interacting with other NPC's or regions.
    """
    nid: ClassVar[NID] = 'on_roam_interact'
    unit1: UnitObject #: The current roam unit.
    units: List[UnitObject] #: the closest nearby other units.

@dataclass(init=True)
class CombatDeath(EventTrigger):
    """
    Occurs during combat when any unit dies, including generics.
    If triggered, will delay the death animation of unit1 until
    after the attack animation of unit2 finishes.
    """
    nid: ClassVar[NID] = 'combat_death'
    unit1: UnitObject  #: the unit that died.
    unit2: Optional[UnitObject]  #: the unit that killed them (can be None).
    position: Tuple[int, int]  #: the position they died at.

@dataclass(init=True)
class UnitDeath(EventTrigger):
    """
    Occurs after combat when any unit dies, including generics.
    """
    nid: ClassVar[NID] = 'unit_death'
    unit1: UnitObject  #: the unit that died.
    unit2: Optional[UnitObject]  #: the unit that killed them (can be None).
    position: Tuple[int, int]  #: the position they died at.

@dataclass(init=True)
class UnitWait(EventTrigger):
    """
    Occurs when any unit waits.
    """
    nid: ClassVar[NID] = 'unit_wait'
    unit1: UnitObject  #: the unit that waited.
    position: Tuple[int, int]  #: the position they waited at.
    region: Optional[RegionObject]  #: region under the unit (can be None)
    actively_chosen: bool  #: boolean for whether the player actively selected Wait

@dataclass(init=True)
class UnitSelect(EventTrigger):
    """
    Occurs when a unit is selected by the cursor.
    """
    nid: ClassVar[NID] = 'unit_select'
    unit1: UnitObject
    position: Tuple[int, int]  #: the position they were selected at.

@dataclass(init=True)
class UnitDeselect(EventTrigger):
    """
    Occurs when a unit selected by the cursor is deselected.
    """
    nid: ClassVar[NID] = 'unit_deselect'
    unit1: UnitObject
    position: Tuple[int, int] #: the position they were deselected at.

@dataclass(init=True)
class UnitLevelUp(EventTrigger):
    """
    Occurs whenever a unit levels up.
    """
    nid: ClassVar[NID] = 'unit_level_up'
    unit1: UnitObject #: the unit that changed their level.
    stat_changes: Dict[NID, int] #: a dict containing their stat changes.
    source: str #: One of ('exp_gain', 'stat_change', 'class_change', 'promote', 'event') describing how the unit got to this point.

@dataclass(init=True)
class DuringUnitLevelUp(EventTrigger):
    """
    Occurs during a unit's level-up screen, immediately after stat changes are granted. This event is useful for implementing level-up quotes.
    """
    nid: ClassVar[NID] = 'during_unit_level_up'
    unit1: UnitObject #: the unit that gained/lost stats.
    stat_changes: Dict[NID, int] #: a dict containing their stat changes.
    source: str #: One of ('exp_gain', 'stat_change', 'class_change', 'promote') describing how the unit got to this screen.

@dataclass(init=True)
class UnitWeaponRankUp(EventTrigger):
    """
    Occurs whenever a unit gains a weapon rank.
    """
    nid: ClassVar[NID] = 'unit_weapon_rank_up'
    unit: UnitObject #: the unit that increased in weapon rank.
    weapon_type: NID #: nid of weapon type object
    old_wexp: int #: old wexp before gaining wexp
    rank: str #: new weapon rank by letter

@dataclass(init=True)
class CombatStart(EventTrigger):
    """
    Occurs when non-scripted combat is begun between any two units. Useful for boss quotes.
    """
    nid: ClassVar[NID] = 'combat_start'
    unit1: UnitObject #: the unit who initiated combat.
    unit2: UnitObject #: the target of the combat (can be None).
    position: Tuple[int, int] #: contains the position of unit1.
    item: ItemObject #: the item/ability used by unit1.
    is_animation_combat: bool #: a boolean denoting whether or not we are in an actual animation or merely a map animation.

@dataclass(init=True)
class CombatEnd(EventTrigger):
    """
    This trigger fires at the end of combat. Useful for checking win or loss conditions.
    """
    nid: ClassVar[NID] = 'combat_end'
    unit1: UnitObject #: the unit who initiated combat.
    unit2: UnitObject #: the target of the combat (can be None).
    position: Tuple[int, int] #: contains the position of unit1.
    item: ItemObject #: the item/ability used by unit1.
    playback: List[PlaybackBrush] #: a list of the playback brushes from the combat.

@dataclass(init=True)
class OnTalk(EventTrigger):
    """
    This trigger fires when two units "Talk" to one another.
    """
    nid: ClassVar[NID] = 'on_talk'
    unit1: UnitObject #: the unit who is the talk initiator.
    unit2: UnitObject #: the unit who is the talk receiver.
    position: Tuple[int, int] #: the position of unit1 (is None if triggered during free roam)

@dataclass(init=True)
class OnSupport(EventTrigger):
    """
    This trigger fires when two units "Support" to one another.
    """
    nid: ClassVar[NID] = 'on_support'
    unit1: UnitObject #: the unit who is the support initiator.
    unit2: UnitObject #: the unit who is the support receiver.
    position: Tuple[int, int] #: the position of unit1 (could be None, for instance during Base).
    support_rank_nid: NID #: contains the nid of the support rank (e.g. `A`, `B`, `C`, or `S`)
    is_replay: bool #: whether or not this is just a replay of the support convo from the base menu.

@dataclass(init=True)
class OnBaseConvo(EventTrigger):
    """
    This trigger fires when the player selects a base conversation to view.
    """
    nid: ClassVar[NID] = 'on_base_convo'
    base_convo: NID #: contains the name of the base conversation.
    unit: NID  # DEPRECATED - Just a copy of the base_convo

@dataclass(init=True)
class OnPrepStart(EventTrigger):
    """
    Occurs each time the player enters preps.
    """
    nid: ClassVar[NID] = 'on_prep_start'

@dataclass(init=True)
class OnBaseStart(EventTrigger):
    """
    Occurs each time the player enters base.
    """
    nid: ClassVar[NID] = 'on_base_start'

@dataclass(init=True)
class OnTurnwheel(EventTrigger):
    """
    Occurs after the turnwheel is used. Events that happen within are
    not recorded within the turnwheel and therefore will not be reversed
    upon turnwheel activation.
    """
    nid: ClassVar[NID] = 'on_turnwheel'

@dataclass(init=True)
class OnTitleScreen(EventTrigger):
    """
    Occurs before the title screen is shown.
    """
    nid: ClassVar[NID] = 'on_title_screen'

@dataclass(init=True)
class OnStartup(EventTrigger):
    """
    Occurs whenever the engine starts.
    """
    nid: ClassVar[NID] = 'on_startup'

@dataclass(init=True)
class TimeRegionComplete(EventTrigger):
    """
    Occurs when a time region runs out of time and would be removed.
    """
    nid: ClassVar[NID] = 'time_region_complete'
    position: Tuple[int, int] #: the position of the region that has run out of time.
    region: RegionObject #: the region that has run out of time.

@dataclass(init=True)
class OnOverworldNodeSelect(EventTrigger):
    """
    Occurs when an entity is about to issue a move to a node
    (which may or may not contain the next level, or
    any level at all). Because of implementation detail,
    when this event occurs, it supersedes any queued moves.
    Therefore, the entity will *not move* to the selected node.
    Any events that use this trigger should include a scripted move
    if movement is desired.
    """
    nid: ClassVar[NID] = 'on_overworld_node_select'
    entity_nid: NID #: Contains the id of entity that will issue a move.
    node_nid: NID #: Contains the id of the node.

@dataclass(init=True)
class RoamPressStart(EventTrigger):
    """
    Occurs when the `start` key is pressed in Free Roam.
    """
    nid: ClassVar[NID] = 'roam_press_start'
    unit1: UnitObject #: The current roam unit.
    unit2: UnitObject #: the closest nearby other unit.

@dataclass(init=True)
class RoamPressInfo(EventTrigger):
    """
    Occurs when the `info` key is pressed in Free Roam.
    """
    nid: ClassVar[NID] = 'roam_press_info'
    unit1: UnitObject #: The current roam unit.
    unit2: UnitObject #: the closest nearby other unit.

@dataclass(init=True)
class RoamPressAux(EventTrigger):
    """
    Occurs when the `aux` key is pressed in Free Roam.
    """
    nid: ClassVar[NID] = 'roam_press_aux'
    unit1: UnitObject #: The current roam unit.
    unit2: UnitObject #: the closest nearby other unit.

@dataclass(init=True)
class RoamingInterrupt(EventTrigger):
    """
    Occurs when the player enters an `interrupt` region on the map.
    """
    nid: ClassVar[NID] = 'roaming_interrupt'
    unit1: UnitObject #: The current roam unit.
    position: Tuple[int, int] #: The position of the current roam unit
    region: RegionObject #: The region that was triggered.

@dataclass(init=True)
class RegionTrigger(EventTrigger):
    """
    Special trigger. This trigger has a custom nid, and will be created whenever you make an interactable
    event region.
    """
    nid: NID #: the nid of the region event
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: The unit triggering the region
    position: Tuple[int, int] #: The position of the unit triggering the region
    region: RegionObject #: the name of the region that was triggered
    item: ItemObject = None #: the item used to trigger this region (used with unlock staves and keys)

@dataclass(init=True)
class EventOnHit(EventTrigger):
    """
    Plays before a hit, if the unit will hit with this item.

    Note: trigger is used nowhere in the engine, but is used in the EventOnHit component.
    """
    nid: ClassVar[NID] = 'event_on_hit'
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: the unit bearing the item.
    unit2: UnitObject #: the other unit in combat.
    position: Tuple[int, int] #: the position of the unit bearing the item.
    item: ItemObject #: the item/ability that the attacking unit is using.
    target_pos: Tuple[int, int] #: the position of the other unit.
    mode: str #: One of (`attack`, `defense`), depending on whether the bearer of the item is the one doing this attack, or the other unit is the one doing this attack.
    attack_info: Tuple[int, int] #: The first element is the number of attacks that have occurred before this one. The second element is the number of subattacks (think brave attacks) that have occurred within this main attack.

@dataclass(init=True)
class EventAfterCombat(EventTrigger):
    """
    Plays after combat where unit is using this item.

    Note: trigger is used nowhere in the engine, but is used in the EventAfterCombatOnHit and EventAfterCombatEvenMiss component.
    """
    nid: ClassVar[NID] = 'event_after_combat'
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: the unit bearing the item.
    unit2: UnitObject #: the other unit in combat.
    position: Tuple[int, int] #: the position of the unit bearing the item.
    item: ItemObject #: the item/ability that the attacking unit is using.
    target_pos: Tuple[int, int] #: the position of the other unit.
    mode: str #: One of (`attack`, `defense`), depending on whether the bearer of the skill/item is the one doing this attack, or the other unit is the one doing this attack.

@dataclass(init=True)
class EventAfterInitiatedCombat(EventTrigger):
    """
    Plays after combat initiated by unit bearing this skill.

    Note: trigger is used nowhere in the engine, but is used in the EventAfterInitiatedCombat component.
    """
    nid: ClassVar[NID] = 'event_after_initiated_combat'
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: the unit bearing the skill.
    unit2: UnitObject #: the other unit in combat.
    position: Tuple[int, int] #: the position of the unit bearing the skill.
    item: ItemObject #: the item/ability that the attacking unit is using.
    mode: str #: One of (`attack`, `defense`), depending on whether the bearer of the skill is the one doing this attack, or the other unit is the one doing this attack.

@dataclass(init=True)
class EventOnRemove(EventTrigger):
    """
    Plays after skill is removed from a unit.

    Note: trigger is used nowhere in the engine, but is used in the EventOnRemove component.
    """
    nid: ClassVar[NID] = 'event_on_remove'
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: the unit bearing the skill to be removed.

@dataclass(init=True)
class UnlockStaff(EventTrigger):
    """
    Plays when an unlock staff unlocks a region.

    Note: trigger is used nowhere in the engine, but is used in the UnlockStaff component.
    """
    nid: ClassVar[NID] = 'unlock_staff'
    hidden: ClassVar[bool] = True
    unit1: UnitObject #: the unit that is unlocking.
    position: Tuple[int, int] #: the position of the unlocking unit.
    item: ItemObject #: the item/ability that the unlocking unit is using.
    region: RegionObject #: the region being unlocked.


ALL_TRIGGERS = [tclass for tclass in EventTrigger.__subclasses__() if (tclass is not EventTrigger and not tclass.hidden)]
