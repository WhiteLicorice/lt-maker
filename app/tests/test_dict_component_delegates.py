import unittest

from app.tests import qt_headless  # noqa: F401 -- before any QApplication


class DictDelegateIsolationTests(unittest.TestCase):
    '''
    A dict component's value column is edited as a number, a float or an expression
    depending on the kind of dict, while the delegate is chosen by what the key
    column holds -- so one delegate serves several kinds. Recording the choice on
    the delegate reconfigures every component that shares it, which turned a stat
    change expression into the stat multiplier's float box and zeroed it
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

    def build(self, component_class, delegate):
        from PyQt5.QtWidgets import QWidget
        from app.data.database.skill_components import SkillComponent

        class Host(QWidget):
            def remove_component(self, widget):
                pass

        class Dummy(SkillComponent):
            nid = 'dummy'
            desc = 'dummy'
            value = []

        return component_class(Dummy(None), Host(), delegate)

    def value_editor(self, widget):
        from PyQt5.QtWidgets import QWidget

        class ValueColumn:
            def column(self):
                return 1

        delegate = widget.value_delegate()(None)
        return type(delegate.createEditor(QWidget(), None, ValueColumn())).__name__

    def test_one_delegate_serves_several_kinds_of_dict_at_once(self):
        from app.editor.component_database import (DictItemComponent,
                                                   FloatDictItemComponent,
                                                   StringDictItemComponent)
        from app.editor.component_editor_delegates import StatDelegate

        plain = self.build(DictItemComponent, StatDelegate)
        floating = self.build(FloatDictItemComponent, StatDelegate)
        expression = self.build(StringDictItemComponent, StatDelegate)

        self.assertEqual('QSpinBox', self.value_editor(plain))
        self.assertEqual('QDoubleSpinBox', self.value_editor(floating))
        self.assertEqual('CodeLineEdit', self.value_editor(expression))
        # ...and building all three left the shared delegate untouched
        self.assertFalse(StatDelegate.is_float)
        self.assertFalse(StatDelegate.is_string)

    def test_the_reported_pair_keeps_its_own_editor(self):
        from app.editor.component_database import get_display_widget
        from app.engine import skill_component_access
        from PyQt5.QtWidgets import QWidget

        class Host(QWidget):
            def remove_component(self, widget):
                pass

        host = Host()
        expression = get_display_widget(
            skill_component_access.get_component('stat_change_expression'), host)
        multiplier = get_display_widget(
            skill_component_access.get_component('stat_multiplier'), host)

        self.assertEqual('CodeLineEdit', self.value_editor(expression))
        self.assertEqual('QDoubleSpinBox', self.value_editor(multiplier))


if __name__ == '__main__':
    unittest.main()
