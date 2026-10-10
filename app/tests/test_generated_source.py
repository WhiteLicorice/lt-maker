import os
import tempfile
import unittest

from app.engine.codegen.codegen_utils import GeneratedSource


class GeneratedSourceTests(unittest.TestCase):
    '''Generated source reaches the disk only when it has changed'''

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = os.path.join(directory.name, 'generated.py')

    def generate(self, *lines):
        source = GeneratedSource(self.path)
        source.writelines('# header\n')
        for line in lines:
            source.write(line)
        source.close()

    def read(self) -> str:
        with open(self.path) as generated:
            return generated.read()

    def test_a_file_that_does_not_exist_yet_is_written(self):
        self.generate('a = 1\n')
        self.assertEqual('# header\na = 1\n', self.read())

    def test_a_file_whose_source_has_changed_is_rewritten(self):
        self.generate('a = 1\n')
        self.generate('a = 2\n', 'b = 3\n')
        self.assertEqual('# header\na = 2\nb = 3\n', self.read())

    def test_a_file_whose_source_is_the_same_is_left_alone(self):
        self.generate('a = 1\n')
        os.chmod(self.path, 0o444)  # a write would now fail
        self.addCleanup(os.chmod, self.path, 0o666)
        self.generate('a = 1\n')
        self.assertEqual('# header\na = 1\n', self.read())

    def test_nothing_is_on_disk_until_the_source_is_closed(self):
        source = GeneratedSource(self.path)
        source.write('a = 1\n')
        self.assertFalse(os.path.exists(self.path))
        source.close()
        self.assertTrue(os.path.exists(self.path))


if __name__ == '__main__':
    unittest.main()
