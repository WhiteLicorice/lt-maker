from __future__ import annotations

from typing import Optional
import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QFileDialog
from app.editor.settings.main_settings_controller import MainSettingsController

import app.engine.skill_component_access as SCA
from app.data.database.skills import SkillCatalog, SkillPrefab
from app.data.database import item_components, skill_components
from app.data.database.components import swap_values, ComponentType
from app.editor import timer
from app.editor.new_editor_tab import NewEditorTab
from app.editor.data_editor import SingleDatabaseEditor
from app.editor.component_editor_properties import NewComponentProperties, component_search_text
from app.editor.skill_editor import skill_model, skill_import
from app.extensions.custom_gui import DeletionTab, DeletionDialog
from app.editor.custom_widgets import SkillBox

from app.utilities.typing import NID


class NewSkillProperties(NewComponentProperties[SkillPrefab]):
    title = "Skill"
    get_components = staticmethod(SCA.get_skill_components)
    get_templates = staticmethod(SCA.get_templates)
    get_tags = staticmethod(SCA.get_skill_tags)


class NewSkillDatabase(NewEditorTab):
    catalog_type = SkillCatalog
    properties_type = NewSkillProperties

    @classmethod
    def edit(cls, parent=None):
        timer.get_timer().stop_for_editor()  # Don't need these while running game
        window = SingleDatabaseEditor(NewSkillDatabase, parent)
        window.exec_()
        timer.get_timer().start_for_editor()

    @property
    def data(self):
        return self._db.skills

    def get_icon(self, skill_nid) -> Optional[QIcon]:
        pix = skill_model.get_pixmap(self.data.get(skill_nid))
        if pix:
            return QIcon(pix.scaled(32, 32))
        return None

    def get_search_text(self, nid: NID) -> str:
        return component_search_text(self.data.get(nid))

    def _on_delete(self, nid: NID) -> bool:
        """
        Returns whether the user wants to proceed with deletion
        """
        skill = self.data.get(nid)
        affected_units = [unit for unit in self._db.units if nid in unit.get_skills()]
        affected_classes = [k for k in self._db.classes if nid in k.get_skills()]
        affected_levels = [level for level in self._db.levels if any(nid in unit.get_skills() for unit in level.units)]
        affected_items = item_components.get_items_using(ComponentType.Skill, nid, self._db)
        affected_skills = skill_components.get_skills_using(ComponentType.Skill, nid, self._db)
        affected_terrain = [terrain for terrain in self._db.terrain if terrain.status == nid]

        deletion_tabs = []
        if affected_units:
            from app.editor.unit_editor.unit_model import UnitModel
            model = UnitModel
            msg = "Deleting Skill <b>%s</b> would affect these objects." % nid
            deletion_tabs.append(DeletionTab(affected_units, model, msg, "Units"))
        if affected_classes:
            from app.editor.class_editor.class_model import ClassModel
            model = ClassModel
            msg = "Deleting Skill <b>%s</b> would affect these objects." % nid
            deletion_tabs.append(DeletionTab(affected_classes, model, msg, "Classes"))
        if affected_levels:
            from app.editor.global_editor.level_menu import LevelModel
            model = LevelModel
            msg = "Deleting Skill <b>%s</b> would affect units in these levels." % nid
            deletion_tabs.append(DeletionTab(affected_levels, model, msg, "Levels"))
        if affected_items:
            from app.editor.item_editor.item_model import ItemModel
            model = ItemModel
            msg = "Deleting Skill <b>%s</b> would affect these items" % nid
            deletion_tabs.append(DeletionTab(affected_items, model, msg, "Items"))
        if affected_skills:
            from app.editor.skill_editor.skill_model import SkillModel
            model = SkillModel
            msg = "Deleting Skill <b>%s</b> would affect these skills" % nid
            deletion_tabs.append(DeletionTab(affected_skills, model, msg, "Skills"))
        if affected_terrain:
            from app.editor.terrain_editor.terrain_model import TerrainModel
            model = TerrainModel
            msg = "Deleting Skill <b>%s</b> would affect these terrain" % nid
            deletion_tabs.append(DeletionTab(affected_terrain, model, msg, "Terrain"))

        if deletion_tabs:
            swap, ok = DeletionDialog.get_swap(deletion_tabs, SkillBox(self, exclude=skill), self)
            if ok:
                self._on_nid_changed(nid, swap.nid)
            else:
                return False
        return True

    def _on_nid_changed(self, old_nid: NID, new_nid: NID) -> None:
        for unit in self._db.units:
            unit.replace_skill_nid(old_nid, new_nid)
        for k in self._db.classes:
            k.replace_skill_nid(old_nid, new_nid)
        for level in self._db.levels:
            for unit in level.units:
                unit.replace_skill_nid(old_nid, new_nid)
        swap_values(self._db.items.values(), ComponentType.Skill, old_nid, new_nid)
        swap_values(self._db.skills.values(), ComponentType.Skill, old_nid, new_nid)
        for terrain in self._db.terrain:
            if terrain.status == old_nid:
                terrain.status = new_nid

    def import_xml(self):
        settings = MainSettingsController()
        starting_path = settings.get_last_open_path()
        fn, ok = QFileDialog.getOpenFileName(self, _("Import skills from status.xml"), starting_path, "Status XML (status.xml);;All Files(*)")
        if ok and fn.endswith('status.xml'):
            parent_dir = os.path.split(fn)[0]
            settings.set_last_open_path(parent_dir)
            new_skills = skill_import.get_from_xml(parent_dir, fn)
            for skill in new_skills:
                self.data.append(skill)
            self.reset()

    def import_csv(self):
        return

# Testing
# Run "python -m app.editor.skill_editor.new_skill_tab" from main directory
if __name__ == '__main__':
    import sys
    from app.data.database.database import DB
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    from app.data.resources.resources import RESOURCES
    from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
    DB.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    RESOURCES.load('default.ltproj', CURRENT_SERIALIZATION_VERSION)
    window = NewSkillDatabase(None, DB)
    window.show()
    app.exec_()
