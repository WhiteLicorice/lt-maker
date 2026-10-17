import logging

from app.data.database.database import DB
from app.engine import (action, animations, engine, gui, health_bar,
                        item_funcs, item_system, skill_system)
from app.engine.game_state import game
from app.engine.sound import get_sound_thread
from app.engine.state import MapState
from app.events import triggers
from app.data.resources.resources import RESOURCES
from app.utilities import utils


class StatusUpkeepState(MapState):
    name = 'status_upkeep'

    # A unit that a bad status has just left is shown for a moment, as on the GBA
    wear_off_time = utils.frames2ms(66)
    # With the GBA's sound for it (song 0xAA). A project without it plays nothing
    wear_off_sound = 'DebuffRecover'

    def start(self):
        game.cursor.hide()
        if DB.constants.value('initiative'):
            self.units = [game.initiative.get_current_unit()]
        else:
            self.units = [unit for unit in game.units if
                          unit.position and
                          unit.team == game.phase.get_current() and
                          not unit.dead]
            # Handle travelers
            if DB.constants.value('pairup') or DB.constants.value('traveler_time_decrement'):
                possible_carrying_units = [unit for unit in game.units if unit.position]
                for unit in possible_carrying_units:
                    if unit.traveler and game.get_unit(unit.traveler).team == game.phase.get_current():
                        self.units.append(game.get_unit(unit.traveler))
        self.cur_unit = None

        self.health_bar = None
        self.animations = []
        self.state = 'processing'
        self.last_update = 0
        self.time_for_change = 0
        self.worn_off = False
        self.wear_off_start = None

        self.actions, self.playback = [], []

    def is_traveler(self, cur_unit):
        possible_carrying_units = [unit for unit in game.units if unit.position]
        for u in possible_carrying_units:
            if u.traveler == cur_unit.nid:
                return u
        return False

    def can_process(self, cur_unit) -> bool:
        return cur_unit.position or self.is_traveler(cur_unit)

    def bad_status_wears_off(self) -> bool:
        """Whether the actions about to be done take a bad status, one the player is shown, off the unit"""
        for act in self.actions:
            if isinstance(act, action.RemoveSkill) and act.unit is self.cur_unit:
                skill = act.skill
                if isinstance(skill, str):  # Its nid
                    skill = next((s for s in self.cur_unit.skills if s.nid == skill), None)
                if skill and skill.negative and not skill_system.hidden(skill, self.cur_unit):
                    return True
        return False

    def begin_wear_off(self) -> bool:
        """Shows the unit that a bad status has just left, if there is one to show. Returns whether there is"""
        unit = self.cur_unit
        if not self.worn_off or not unit.position or unit.get_hp() <= 0 or not game.board.in_vision(unit.position):
            return False
        self.worn_off = False
        game.cursor.set_pos(unit.position)
        game.state.change('move_camera')
        self.wear_off_start = None
        self.state = 'wear_off'
        return True

    def update(self):
        super().update()

        if self.health_bar:
            self.health_bar.update()

        if self.state == 'processing':
            if (not self.cur_unit or not self.can_process(self.cur_unit)) and self.units:
                self.cur_unit = self.units.pop()

            if self.cur_unit:
                self.actions.clear()
                self.playback.clear()
                if self.name == 'status_endstep':
                    skill_system.on_endstep(self.actions, self.playback, self.cur_unit)
                    for item in item_funcs.get_all_items(self.cur_unit):
                        item_system.on_endstep(self.actions, self.playback, self.cur_unit, item)
                    for item in skill_system.get_extra_abilities(self.cur_unit).values():
                        item_system.on_endstep(self.actions, self.playback, self.cur_unit, item)
                else:
                    skill_system.on_upkeep(self.actions, self.playback, self.cur_unit)
                    for item in item_funcs.get_all_items(self.cur_unit):
                        item_system.on_upkeep(self.actions, self.playback, self.cur_unit, item)
                    for item in skill_system.get_extra_abilities(self.cur_unit).values():
                        item_system.on_upkeep(self.actions, self.playback, self.cur_unit, item)
                self.worn_off = self.bad_status_wears_off()
                if self.playback and self.cur_unit.position:  # Travelers skip this part
                    game.cursor.set_pos(self.cur_unit.position)
                    game.state.change('move_camera')
                    self.cur_unit.sprite.change_state('selected')
                    self.health_bar = health_bar.MapCombatInfo('splash', self.cur_unit, None, None, None)
                    self.state = 'start'
                    self.last_update = engine.get_time()
                elif self.actions and self.can_process(self.cur_unit):
                    for act in self.actions:
                        action.do(act)
                    self.check_death()
                    if self.begin_wear_off():
                        return
                    self.cur_unit = None
                    return 'repeat'
                else:
                    self.cur_unit = None
                    return 'repeat'

            else:
                # About to begin the real phase
                if self.name == 'status_upkeep':
                    action.do(action.MarkPhase(game.phase.get_current()))
                game.state.back()
                return 'repeat'

        elif self.state == 'start':
            if engine.get_time() > self.last_update + 400:
                self.handle_playback(self.playback)
                for act in self.actions:
                    action.do(act)
                self.health_bar.update()  # Force update to get time for change
                self.state = 'running'
                self.last_update = engine.get_time()
                self.time_for_change = self.health_bar.get_time_for_change() + 800

        elif self.state == 'running':
            # Its animations, such as poison's, play out before the next unit's turn
            if engine.get_time() > self.last_update + self.time_for_change and not self.animations:
                self.check_death()
                if not self.begin_wear_off():
                    self.state = 'processing'
                    self.cur_unit = None

        elif self.state == 'wear_off':
            if self.wear_off_start is None:
                # Counted from here, once the camera has got there
                self.wear_off_start = engine.get_time()
                self.cur_unit.sprite.start_status_heal()
                get_sound_thread().play_sfx(self.wear_off_sound)
            elif engine.get_time() > self.wear_off_start + self.wear_off_time:
                self.state = 'processing'
                self.cur_unit = None

    def handle_playback(self, playback):
        for brush in playback:
            if brush.nid == 'unit_tint_add':
                brush.unit.sprite.begin_flicker(333, brush.color, 'add')
            elif brush.nid == 'unit_tint_sub':
                brush.unit.sprite.begin_flicker(333, brush.color, 'sub')
            elif brush.nid == 'cast_sound':
                get_sound_thread().play_sfx(brush.sound)
            elif brush.nid == 'hit_sound':
                get_sound_thread().play_sfx(brush.sound)
            elif brush.nid == 'cast_anim':
                anim = RESOURCES.animations.get(brush.anim)
                pos = game.cursor.position
                if anim:
                    anim = animations.MapAnimation(anim, pos)
                    self.animations.append(anim)
            elif brush.nid == 'damage_numbers':
                damage = brush.damage
                if damage == 0:
                    continue
                target = brush.unit
                target.sprite.add_damage_number(damage)

    def check_death(self):
        if self.cur_unit.get_hp() <= 0:
            # Handle death
            if self.is_traveler(self.cur_unit):
                # If you are a paired up unit which would die
                # leave the pair up and sit in your current position
                # until you do die!
                owner = self.is_traveler(self.cur_unit)
                action.execute(action.Separate(owner, self.cur_unit, owner.position))
            game.death.should_die(self.cur_unit)
            game.state.change('dying')
            action.UpdateRecords('death', (None, self.cur_unit.nid)).do()
            game.events.trigger(triggers.UnitDeath(self.cur_unit, None, position=self.cur_unit.position))
            skill_system.on_death(self.cur_unit)
        else:
            self.cur_unit.sprite.change_state('normal')

    def draw(self, surf):
        surf = super().draw(surf)

        self.animations = [anim for anim in self.animations if not anim.update()]
        for anim in self.animations:
            anim.draw(surf, offset=(-game.camera.get_x(), -game.camera.get_y()))

        if self.health_bar:
            self.health_bar.draw(surf)

        return surf
