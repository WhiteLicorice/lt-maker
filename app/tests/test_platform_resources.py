import unittest

from app.data.resources.resources import Resources

class PlatformResourceTests(unittest.TestCase):
    '''
    The terrain editor lists a platform type for every name in
    resources/platforms and shows its Melee image, and combat draws the Melee
    or the Ranged image depending on distance. A platform shipped with only
    one of the two crashed the terrain editor on open
    '''
    def setUp(self):
        self.resources = Resources()

    def test_every_platform_type_has_melee_and_ranged(self):
        platform_types = self.resources.get_platform_types()
        self.assertTrue(platform_types)
        for name, _ in platform_types:
            for suffix in ('-Melee', '-Ranged'):
                self.assertIn(name + suffix, self.resources.platforms)

if __name__ == '__main__':
    unittest.main()
