import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from app.engine import save
import app.engine.config as cf


class SuspendDeletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.meta_loc = os.path.join(self.tmp_dir, 'test-suspend.pmeta')
        self.save_loc = os.path.join(self.tmp_dir, 'test-suspend.p')
        self.old_debug = cf.SETTINGS['debug']
        self.patcher = patch.object(save, 'SUSPEND_LOC', self.meta_loc)
        self.patcher.start()

    def tearDown(self) -> None:
        self.patcher.stop()
        cf.SETTINGS['debug'] = self.old_debug
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def write_suspend(self):
        for loc in (self.meta_loc, self.save_loc):
            with open(loc, 'wb') as fp:
                fp.write(b'suspend')

    def suspend_exists(self):
        return os.path.exists(self.meta_loc), os.path.exists(self.save_loc)

    def test_remove_suspend_keeps_the_suspend_in_debug(self):
        '''remove_suspend consumes a suspend that was just loaded, but debug
        deliberately holds onto it so it can be resumed again'''
        cf.SETTINGS['debug'] = 0
        self.write_suspend()
        save.remove_suspend()
        self.assertFalse(self.suspend_exists()[0])

        cf.SETTINGS['debug'] = 1
        self.write_suspend()
        save.remove_suspend()
        self.assertTrue(self.suspend_exists()[0])

    def test_delete_suspend_removes_both_files_even_in_debug(self):
        '''
        Starting a new game must invalidate the old suspend whatever the debug
        setting -- it points at a playthrough that has been overwritten. Test
        Full Game runs in debug, which is how this went unnoticed
        '''
        for debug in (0, 1):
            cf.SETTINGS['debug'] = debug
            self.write_suspend()
            save.delete_suspend()
            self.assertEqual((False, False), self.suspend_exists())


if __name__ == '__main__':
    unittest.main()
