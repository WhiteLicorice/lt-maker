import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from app.engine import deferred_files

class DeferredFilesTests(unittest.TestCase):
    '''
    In the browser, a file the build deferred may not have arrived when the
    engine opens it, and ensure fetches it from the page then. A file already
    in place, or any file outside the browser, is left alone. load puts the
    file in place only while it loads it, and in the browser lets the page
    take it out again after
    '''

    def setUp(self):
        # pygbag's platform module, which reaches the page, in place of the standard library's
        window = MagicMock()
        patcher = patch.dict(sys.modules, {'platform': MagicMock(window=window)})
        patcher.start()
        self.addCleanup(patcher.stop)
        # Spelled out, as a name starting __ written in a class would be mangled
        self.fetch_now = getattr(window, '__ltDeferred').fetchNow
        self.release = getattr(window, '__ltDeferred').release
        # Fetched
        self.fetch_now.return_value = ''

    def test_a_missing_file_is_fetched_in_the_browser(self):
        path = os.path.join('default.ltproj', 'resources', 'music', 'not yet here.ogg')
        with patch.object(sys, 'platform', 'emscripten'):
            self.assertEqual(deferred_files.ensure(path), path)
        self.fetch_now.assert_called_once_with('default.ltproj/resources/music/not yet here.ogg', os.path.abspath(path))

    def test_a_file_the_page_could_not_fetch_raises(self):
        self.fetch_now.return_value = 'it is in no bundle'
        path = os.path.join('default.ltproj', 'resources', 'music', 'not yet here.ogg')
        with patch.object(sys, 'platform', 'emscripten'):
            with self.assertRaisesRegex(FileNotFoundError, 'it is in no bundle'):
                deferred_files.ensure(path)

    def test_a_file_in_place_is_not_fetched(self):
        with tempfile.NamedTemporaryFile(delete=False) as present:
            self.addCleanup(os.remove, present.name)
        with patch.object(sys, 'platform', 'emscripten'):
            deferred_files.ensure(present.name)
        self.fetch_now.assert_not_called()

    def test_nothing_is_fetched_outside_the_browser(self):
        deferred_files.ensure(os.path.join('default.ltproj', 'resources', 'music', 'not yet here.ogg'))
        self.fetch_now.assert_not_called()

    def test_load_lets_the_page_take_the_file_out_once_loaded(self):
        path = os.path.join('default.ltproj', 'resources', 'music', 'not yet here.ogg')
        def loader(loaded_path):
            self.release.assert_not_called()
            return 'decoded ' + loaded_path
        with patch.object(sys, 'platform', 'emscripten'):
            self.assertEqual(deferred_files.load(path, loader), 'decoded ' + path)
        self.fetch_now.assert_called_once()
        self.release.assert_called_once_with('default.ltproj/resources/music/not yet here.ogg', os.path.abspath(path))

    def test_load_outside_the_browser_only_loads(self):
        with tempfile.NamedTemporaryFile(delete=False) as present:
            self.addCleanup(os.remove, present.name)
        self.assertEqual(deferred_files.load(present.name, os.path.getsize), 0)
        self.assertTrue(os.path.exists(present.name))
        self.release.assert_not_called()

if __name__ == '__main__':
    unittest.main()
