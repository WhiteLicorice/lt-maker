import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.data.database.database import Database
from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
from app.utilities import web_export

PROJECT = Path('default.ltproj').resolve()

class WebExportTests(unittest.TestCase):
    '''
    The browser build of a project: an archive of the engine and the project
    for the page to unpack, the files the page fetches later in bundles, and
    the page itself
    '''

    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp())
        cls.web_dir = cls.temp / 'web'
        web_export.build(PROJECT, cls.web_dir)
        cls.archive = zipfile.ZipFile(cls.web_dir / 'game.apk')
        cls.names = set(cls.archive.namelist())

    @classmethod
    def tearDownClass(cls):
        cls.archive.close()
        shutil.rmtree(cls.temp)

    def test_the_archive_holds_the_engine_and_the_page_scripts(self):
        for name in ('main.py', 'page.js', 'bench.py', 'built.txt', 'favicon.ico',
                     'app/engine/driver.py', 'app/engine/item_system.py', 'sprites', 'resources/platforms'):
            with self.subTest(name=name):
                self.assertTrue(any(n == 'assets/' + name or n.startswith('assets/%s/' % name) for n in self.names))

    def test_the_archive_holds_nothing_the_engine_never_imports(self):
        for excluded in web_export.APP_EXCLUDES:
            with self.subTest(excluded=excluded):
                self.assertFalse(any(n.startswith('assets/app/%s/' % excluded) for n in self.names))
        self.assertFalse(any('__pycache__' in n or n.endswith('.pyc') for n in self.names))
        self.assertFalse(any(n.startswith('assets/resources/') and not n.startswith('assets/resources/platforms/')
                             for n in self.names))

    def test_a_project_unpacked_from_the_archive_loads_in_the_project_order(self):
        # pygbag left out dotfiles, and with them each folder's .orderkeys
        unpacked = self.temp / 'unpacked'
        prefix = 'assets/%s/' % PROJECT.name
        self.archive.extractall(unpacked, [n for n in self.names if n.startswith(prefix)])
        original, from_archive = Database(), Database()
        original.load(PROJECT, CURRENT_SERIALIZATION_VERSION)
        from_archive.load(unpacked / 'assets' / PROJECT.name, CURRENT_SERIALIZATION_VERSION)
        for key in ('units', 'items', 'skills', 'classes', 'levels', 'events'):
            with self.subTest(key=key):
                self.assertEqual(getattr(from_archive, key).keys(), getattr(original, key).keys())

    def test_each_deferred_file_is_in_a_bundle_and_not_the_archive(self):
        bundles = json.loads((self.web_dir / 'deferred.json').read_text(encoding='utf-8'))
        deferred = [entry for bundle in bundles for entry in bundle['files']]
        self.assertTrue(deferred)
        for bundle in bundles:
            data = (self.web_dir / 'deferred' / bundle['name']).read_bytes()
            for path, offset, size in bundle['files']:
                with self.subTest(path=path):
                    self.assertNotIn('assets/' + path, self.names)
                    self.assertEqual(data[offset:offset + size], (PROJECT.parent / path).read_bytes())

    def test_the_title_music_stays_in_the_archive(self):
        title_music = web_export.read_constants(PROJECT)['music_main']
        self.assertIn('assets/%s/resources/music/%s.ogg' % (PROJECT.name, title_music), self.names)

    def test_the_page_unpacks_the_zip_on_any_host(self):
        page = (self.web_dir / 'index.html').read_text(encoding='utf-8')
        self.assertIn('platform.fopen("game.apk"', page)
        self.assertNotIn('tar.gz', page)
        self.assertNotIn('itch.zone', page)
        self.assertIn('<title>%s</title>' % web_export.read_constants(PROJECT)['title'], page)
        # pygbag leaves this one unfilled too, in a part of the page nothing reads
        self.assertEqual(page.count('{{cookiecutter.'), 1)

    def test_the_page_images_are_served_beside_it(self):
        for image in web_export.PAGE_IMAGES:
            with self.subTest(image=image):
                self.assertTrue((self.web_dir / image).is_file())

    def test_the_package_has_the_page_at_its_top(self):
        zip_path = self.temp / 'web.zip'
        web_export.package(self.web_dir, zip_path)
        with zipfile.ZipFile(zip_path) as package:
            names = set(package.namelist())
        self.assertIn('index.html', names)
        self.assertIn('game.apk', names)
        self.assertIn('deferred/0.zip', names)

class WebExportRefusalTests(unittest.TestCase):
    def test_a_title_cannot_break_out_of_the_page(self):
        page = web_export.page_html('<script>"\\N"</script>')
        self.assertNotIn('<script>"', page)
        self.assertNotIn('\\N', page)

    def test_a_project_with_fatal_errors_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'broken.ltproj'
            project.mkdir()
            (project / 'metadata.json').write_text(json.dumps({'has_fatal_errors': True}), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fatal errors'):
                web_export.build(project, Path(temp) / 'web')

    def test_a_folder_with_files_in_it_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            web_dir = Path(temp) / 'web'
            web_dir.mkdir()
            (web_dir / 'keep.txt').write_text('mine', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'not empty'):
                web_export.build(PROJECT, web_dir)
            self.assertEqual((web_dir / 'keep.txt').read_text(encoding='utf-8'), 'mine')

if __name__ == '__main__':
    unittest.main()
