import unittest
from unittest.mock import MagicMock, patch

# icon_options must not be the first engine module imported, or its import chain
# (help_menu -> icons -> unit_funcs -> item_funcs -> text_funcs) is circular
from app.engine import action  # noqa: F401
from app.engine.game_menus import icon_options
from app.engine.objects.item import ItemObject
from app.utilities.data import Data


class ItemOptionColorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.item = ItemObject('Sword', 'Sword', 'A sword', None, (0, 0), Data())
        self.item.owner_nid = 'Eirika'

    def get_color(self, available: bool, text_color=None):
        with patch.object(icon_options, 'game') as mock_game, \
                patch.object(icon_options, 'item_funcs') as mock_item_funcs:
            mock_game.get_unit.return_value = MagicMock()
            mock_item_funcs.available.return_value = available
            option = icon_options.BasicItemOption(0, self.item, text_color=text_color)
            return option.get_color()

    def test_unusable_item_is_grey(self):
        '''
        An item its owner can't use is greyed out. A color tag used to override
        that, leaving an unusable weapon looking like a usable one
        '''
        self.assertEqual(('grey', 'grey'), self.get_color(False, text_color='red'))
        self.assertEqual(('grey', 'grey'), self.get_color(False))

    def test_usable_item_keeps_its_color(self):
        self.assertEqual(('red', 'blue'), self.get_color(True, text_color='red'))
        self.assertEqual(('white', 'blue'), self.get_color(True))


if __name__ == '__main__':
    unittest.main()
