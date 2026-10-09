from types import SimpleNamespace

from app.tests.engine_harness import EngineTestCase  # first: icons.py alone hits a circular import

from app.constants import WINHEIGHT, WINWIDTH
from app.data.database.database import DB
from app.engine import engine, icons, menus

class MissingPortraitTests(EngineTestCase):
    '''
    A unit with no portrait whose class has no 80x72 icon either has nothing to
    draw. get_portrait_with_size crashed on it with "'NoneType' object has no
    attribute 'get_width'" (seen in the item help window, ui_view.py)
    '''
    def setUp(self):
        super().setUp()
        klass = DB.classes[0]
        klass.icon_nid = None
        self.unit = SimpleNamespace(portrait_nid=None, klass=klass.nid)

    def test_no_portrait_is_none(self):
        self.assertIsNone(icons.get_portrait_with_size(self.unit, 96, 68))

    def test_unit_face_draws_nothing(self):
        surf = engine.create_surface((WINWIDTH, WINHEIGHT), transparent=True)
        blank = surf.copy()
        menus.draw_unit_face(surf, (0, 0), self.unit, right=True)
        self.assertEqual(engine.surf_to_raw(surf, 'RGBA'), engine.surf_to_raw(blank, 'RGBA'))
