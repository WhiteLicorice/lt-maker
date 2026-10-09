import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.tests import qt_headless  # noqa: F401 -- before any QApplication

TEST_COMPANY = 'lt_maker_tests'
TEST_PRODUCT = 'event_editor_reopen'
PROJECT = 'default.ltproj'


class EventEditorReopenTests(unittest.TestCase):
    '''
    The event editor reopens on the event that was open when it last closed,
    rather than on the first event of the chapter selected in the main editor
    '''

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from app.editor.editor_locale import init_locale
        init_locale()
        from PyQt5.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication(sys.argv)

        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        from app.data.resources.resources import RESOURCES
        from app.data.database.database import DB
        RESOURCES.load(PROJECT, CURRENT_SERIALIZATION_VERSION)
        DB.load(PROJECT, CURRENT_SERIALIZATION_VERSION)
        cls.DB = DB
        cls.selected_level = DB.levels[0].nid
        # An event from a chapter other than the one selected in the main editor
        cls.other_event = next(event for event in DB.events
                               if event.level_nid and event.level_nid != cls.selected_level)

    def setUp(self) -> None:
        from PyQt5.QtCore import QSettings
        from app.editor.settings import MainSettingsController

        # On Windows QSettings(company, product) is the registry, which every test
        # run on the machine shares, and the settings controllers each open their
        # own handle on one key: clearing it through one left the others on a key
        # "marked for deletion". Each test gets its own settings file instead
        settings_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, settings_dir, ignore_errors=True)

        class TestSettings(QSettings):
            def __init__(self, company, product):
                super().__init__(os.path.join(settings_dir, '%s_%s.ini' % (company, product)), QSettings.IniFormat)

        for module in ('main_settings_controller', 'component_settings_controller', 'project_history_controller'):
            patcher = patch('app.editor.settings.%s.QSettings' % module, TestSettings)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('app.editor.event_editor.event_properties.MainSettingsController',
                        lambda: MainSettingsController(TEST_COMPANY, TEST_PRODUCT))
        patcher.start()
        self.addCleanup(patcher.stop)

        self.settings = MainSettingsController(TEST_COMPANY, TEST_PRODUCT)
        self.settings.set_current_project(PROJECT)
        # Off by default
        from app.editor.settings.preference_definitions import Preference
        self.settings.set_preference(Preference.EVENT_REOPEN_LAST, True)

    def open_editor(self):
        from PyQt5.QtWidgets import QWidget
        from app.editor.event_editor.event_tab import EventDatabase
        # Stands in for the dialog the tab lives in, which reaches back to the main editor
        database_editor = QWidget()
        database_editor.window = SimpleNamespace(
            app_state_manager=SimpleNamespace(state=SimpleNamespace(selected_level=self.selected_level)))
        tab = EventDatabase.create(database_editor)
        database_editor.show()
        self.addCleanup(database_editor.deleteLater)
        return tab

    def close_editor(self, tab):
        tab.parent().close()

    def select(self, tab, event):
        collection = tab.left_frame
        source_index = collection.model.index(self.DB.events.index(event.nid), 0)
        index = collection.level_filtered_model.mapFromSource(
            collection.name_filtered_model.mapFromSource(source_index))
        self.assertTrue(index.isValid(), 'event is filtered out')
        collection.view.setCurrentIndex(index)

    def level_filter(self, tab) -> str:
        return tab.left_frame.level_filter_box.edit.currentText()

    def test_first_open_shows_the_selected_chapter(self):
        tab = self.open_editor()
        self.assertEqual(self.level_filter(tab), self.selected_level)
        self.assertEqual(tab.right_frame.current.level_nid, self.selected_level)

    def test_reopens_on_the_last_event_and_its_chapter(self):
        tab = self.open_editor()
        tab.left_frame.level_filter_box.edit.setValue(self.other_event.level_nid)
        self.select(tab, self.other_event)
        self.close_editor(tab)

        tab = self.open_editor()
        self.assertIs(tab.right_frame.current, self.other_event)
        self.assertEqual(self.level_filter(tab), self.other_event.level_nid)

    def test_reopens_with_all_events_shown(self):
        tab = self.open_editor()
        tab.left_frame.level_filter_box.edit.setValue('All')
        self.select(tab, self.other_event)
        self.close_editor(tab)

        tab = self.open_editor()
        self.assertIs(tab.right_frame.current, self.other_event)
        self.assertEqual(self.level_filter(tab), 'All')

    def test_last_event_is_ignored_when_preference_is_off(self):
        from app.editor.settings.preference_definitions import Preference
        tab = self.open_editor()
        tab.left_frame.level_filter_box.edit.setValue(self.other_event.level_nid)
        self.select(tab, self.other_event)
        self.close_editor(tab)

        self.settings.set_preference(Preference.EVENT_REOPEN_LAST, False)
        tab = self.open_editor()
        self.assertEqual(self.level_filter(tab), self.selected_level)
        self.assertEqual(tab.right_frame.current.level_nid, self.selected_level)

    def test_last_event_from_another_project_is_ignored(self):
        tab = self.open_editor()
        tab.left_frame.level_filter_box.edit.setValue('All')
        self.select(tab, self.other_event)
        self.close_editor(tab)

        self.settings.set_current_project('other.ltproj')
        tab = self.open_editor()
        self.assertEqual(self.level_filter(tab), self.selected_level)

    def test_missing_last_event_is_ignored(self):
        self.settings.component_controller.set_property(
            'EventCollection', 'last_event', [PROJECT, 'Global No Such Event', 'All'])
        tab = self.open_editor()
        self.assertEqual(self.level_filter(tab), self.selected_level)
        self.assertEqual(tab.right_frame.current.level_nid, self.selected_level)


if __name__ == '__main__':
    unittest.main()
