import unittest

from app.tests import qt_headless  # noqa: F401 -- before any QApplication


class TabResetRefreshesPropertiesTests(unittest.TestCase):
    '''
    A properties widget draws on data other tabs own -- a unit's stat columns are
    whichever stats the Stat Types tab left visible -- so coming back to a tab has
    to re-push its current entry. Without it the stale columns survive until the
    whole editor is closed and reopened
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
        RESOURCES.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        DB.load('testing_proj.ltproj', CURRENT_SERIALIZATION_VERSION)
        cls.DB = DB
        cls.stat_nid = list(DB.stats.get_visible_stats().keys())[-1]

    def setUp(self) -> None:
        self.DB.stats.get(self.stat_nid).hidden_stat = False

    def tearDown(self) -> None:
        self.DB.stats.get(self.stat_nid).hidden_stat = False

    def columns(self, unit_tab):
        model = unit_tab.right_frame.unit_stat_widget.model
        return [model.headerData(i, 1) for i in range(model.columnCount(None))]

    def test_reset_picks_up_a_stat_hidden_by_another_tab(self):
        from app.editor.unit_editor.new_unit_tab import NewUnitDatabase
        unit_tab = NewUnitDatabase.create()
        unit_tab.on_select(self.DB.units[0].nid)
        self.assertIn(self.stat_nid, self.columns(unit_tab))

        self.DB.stats.get(self.stat_nid).hidden_stat = True
        unit_tab.reset()
        self.assertNotIn(self.stat_nid, self.columns(unit_tab))

    def test_reset_survives_an_empty_selection(self):
        from app.editor.unit_editor.new_unit_tab import NewUnitDatabase
        unit_tab = NewUnitDatabase.create()
        self.assertIsNone(unit_tab.right_frame.current)
        unit_tab.reset()


if __name__ == '__main__':
    unittest.main()
