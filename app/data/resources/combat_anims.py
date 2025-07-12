import os
from pathlib import Path
from typing import List, Optional, Set
from typing_extensions import override

from app.data.category import CategorizedCatalog
from app.data.resources.base_catalog import ManifestCatalog
from app.data.resources import combat_commands
from app.data.resources.resource_prefab import WithResources
from app.utilities.data import Data, Prefab

import logging

from app.utilities.typing import NID, NestedPrimitiveDict

required_poses = ('Stand', 'Attack', 'Miss', 'Dodge')
other_poses = ('RangedStand', 'RangedDodge', 'Critical', 'Damaged', 'RangedDamaged')

class Pose():
    def __init__(self, nid):
        self.nid = nid
        self.timeline = []

    def save(self):
        return (self.nid, [command.save() for command in self.timeline])

    @classmethod
    def restore(cls, s_tuple):
        self = cls(s_tuple[0])
        for command_save in s_tuple[1]:
            nid, value = command_save
            command = combat_commands.get_command(nid)
            if command:
                command.value = value
                self.timeline.append(command)
            else:
                logging.error("Unable to restore command with nid %s.", nid)
        return self

class Frame():
    def __init__(self, nid, rect, offset, pixmap=None, image=None):
        self.nid = nid

        self.rect = rect
        self.offset = offset

        self.pixmap = pixmap
        self.image = image

    def save(self):
        return (self.nid, self.rect, self.offset)

    @classmethod
    def restore(cls, s_tuple):
        self = cls(*s_tuple)
        self.rect = tuple(self.rect)
        self.offset = tuple(self.offset)
        return self

class WeaponAnimation(WithResources):
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.full_path = full_path
        self.poses = Data()
        self.frames = Data()

        self.pixmap = None
        self.image = None

    @override
    def set_full_path(self, full_path):
        self.full_path = full_path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        return [Path(self.full_path)]

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['poses'] = [pose.save() for pose in self.poses]
        s_dict['frames'] = [frame.save() for frame in self.frames]
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        for frame_save in s_dict['frames']:
            self.frames.append(Frame.restore(frame_save))
        for pose_save in s_dict['poses']:
            self.poses.append(Pose.restore(pose_save))
        return self

class CombatAnimation(WithResources, Prefab):
    nid: NID
    weapon_anims: Data[WeaponAnimation]

    def __init__(self, nid):
        self.nid = nid
        self.weapon_anims = Data()
        self.palettes = []  # Palette name -> Palette nid

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['weapon_anims'] = [weapon_anim.save() for weapon_anim in self.weapon_anims]
        s_dict['palettes'] = self.palettes[:]
        return s_dict

    @override
    def set_full_path(self, full_path):
        for weapon_anim in self.weapon_anims:
            short_path = "%s-%s.png" % (self.nid, weapon_anim.nid)
            weapon_anim.set_full_path(str(Path(full_path).parent / short_path))

    @override
    def used_resources(self) -> List[Optional[Path]]:
        return [Path(weapon_anim.full_path) for weapon_anim in self.weapon_anims]

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.palettes = []
        for palette_name, palette_nid in s_dict['palettes'][:]:
            self.palettes.append([palette_name, palette_nid])
        for weapon_anim_save in s_dict['weapon_anims']:
            self.weapon_anims.append(WeaponAnimation.restore(weapon_anim_save))
        return self

class EffectAnimation(WithResources, Prefab):
    def __init__(self, nid, full_path=None):
        self.nid = nid
        self.full_path = full_path
        self.poses = Data[Pose]()
        self.frames = Data[Frame]()
        self.palettes = []  # Palette name -> Palette nid

        self.pixmap = None
        self.image = None

    @override
    def set_full_path(self, full_path):
        self.full_path = full_path

    @override
    def used_resources(self) -> List[Optional[Path]]:
        if self.full_path:
            return [Path(self.full_path)]
        return []

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['poses'] = [pose.save() for pose in self.poses]
        s_dict['frames'] = [frame.save() for frame in self.frames]
        s_dict['palettes'] = self.palettes[:]
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        for frame_save in s_dict['frames']:
            self.frames.append(Frame.restore(frame_save))
        for pose_save in s_dict['poses']:
            self.poses.append(Pose.restore(pose_save))
        self.palettes = []
        for palette_name, palette_nid in s_dict['palettes'][:]:
            self.palettes.append([palette_name, palette_nid])
        return self

class CombatCatalog(ManifestCatalog, CategorizedCatalog):
    manifest = 'combat_anims.json'
    title = 'Combat Animations'
    datatype = CombatAnimation

    def save_image(self, loc, combat_anim, temp=False):
        for weapon_anim in combat_anim.weapon_anims:
            short_path = "%s-%s.png" % (combat_anim.nid, weapon_anim.nid)
            new_full_path = os.path.join(loc, short_path)
            if temp and weapon_anim.pixmap:
                weapon_anim.pixmap.save(new_full_path, "PNG")
            elif not weapon_anim.full_path and weapon_anim.pixmap:
                weapon_anim.pixmap.save(new_full_path, "PNG")
                weapon_anim.set_full_path(new_full_path)
            elif not weapon_anim.full_path:  # You don't have a pixmap, so there is nothing to save
                logging.warning("Could not find pixmap to save for weapon_anim %s in combat_anim %s", weapon_anim.nid, combat_anim.nid)
            elif os.path.abspath(weapon_anim.full_path) != os.path.abspath(new_full_path):
                self.make_copy(weapon_anim.full_path, new_full_path)
                weapon_anim.set_full_path(new_full_path)

    def save_resources(self, loc):
        for combat_anim in self:
            self.save_image(loc, combat_anim)

class CombatEffectCatalog(ManifestCatalog, CategorizedCatalog):
    manifest = 'combat_effects.json'
    title = 'Combat Effects'
    datatype = EffectAnimation

    def save_image(self, loc, effect_anim, temp=False):
        new_full_path = os.path.join(loc, '%s.png' % effect_anim.nid)
        if temp and effect_anim.pixmap:
            effect_anim.pixmap.save(new_full_path, "PNG")
        elif not effect_anim.full_path and effect_anim.pixmap:
            effect_anim.pixmap.save(new_full_path, "PNG")
            effect_anim.set_full_path(new_full_path)
        elif not effect_anim.full_path:
            # Not actually possible because this is checked earlier in the call stack
            logging.warning("Could not find pixmap to save for effect_anim %s", effect_anim.nid)
        elif os.path.abspath(effect_anim.full_path) != os.path.abspath(new_full_path):
            self.make_copy(effect_anim.full_path, new_full_path)
            effect_anim.set_full_path(new_full_path)

    def save_resources(self, loc):
        for effect_anim in self:
            if effect_anim.pixmap or effect_anim.full_path:  # Possible that no pixmap is associated with a simple control script
                self.save_image(loc, effect_anim)