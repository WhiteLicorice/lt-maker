import os
import pickle
import tempfile
import threading
import unittest
from unittest.mock import patch

from app.engine import persistent_data

class PersistentDataTests(unittest.TestCase):
    '''
    Persistent records and achievements outlive every save, so a save of them
    that fails part way must leave the last good file in place, never a
    half-written one the engine cannot load at its next start
    '''

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name
        self.location = os.path.join(self.directory, 'game-persistent_records.p')
        persistent_data.serialize(self.location, ['old'])

    def test_a_save_that_dies_part_way_keeps_the_old_data(self):
        def dump_then_die(data, fp):
            fp.write(pickle.dumps(data)[:4])
            raise RuntimeError("the game closed")
        with patch.object(persistent_data.pickle, 'dump', side_effect=dump_then_die):
            with self.assertRaises(RuntimeError):
                persistent_data.serialize(self.location, ['new'])
        self.assertEqual(persistent_data.deserialize(self.location), ['old'])
        self.assertEqual(os.listdir(self.directory), ['game-persistent_records.p'])

    def test_data_that_cannot_be_pickled_keeps_the_old_data(self):
        persistent_data.serialize(self.location, ['new', threading.Lock()])
        self.assertEqual(persistent_data.deserialize(self.location), ['old'])
        self.assertEqual(os.listdir(self.directory), ['game-persistent_records.p'])

    def test_a_save_waits_out_a_file_in_use(self):
        # What Windows raises while another process has the old file open
        real_replace = os.replace
        refusals = [PermissionError, PermissionError]
        def replace_once_free(source, destination):
            if refusals:
                raise refusals.pop()
            real_replace(source, destination)
        with patch.object(persistent_data.os, 'replace', side_effect=replace_once_free):
            persistent_data.serialize(self.location, ['new'])
        self.assertEqual(persistent_data.deserialize(self.location), ['new'])
        self.assertEqual(os.listdir(self.directory), ['game-persistent_records.p'])

    def test_a_load_waits_out_a_file_in_use(self):
        with patch.object(persistent_data, '_read', side_effect=[PermissionError, ['loaded']]):
            self.assertEqual(persistent_data.deserialize(self.location), ['loaded'])

    def test_a_save_replaces_the_old_data(self):
        persistent_data.serialize(self.location, ['new'])
        self.assertEqual(persistent_data.deserialize(self.location), ['new'])

    def test_clearing_leaves_no_records(self):
        persistent_data.clear(self.location)
        self.assertEqual(persistent_data.deserialize(self.location), [])
