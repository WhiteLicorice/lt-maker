import unittest

class StrUtilsTests(unittest.TestCase):
    def test_get_prefix(self):
        from app.utilities.str_utils import get_prefix
        self.assertEqual(get_prefix('image0.png'), 'image')
        self.assertEqual(get_prefix('image1.png'), 'image')
        self.assertEqual(get_prefix('image10.png'), 'image')
        self.assertEqual(get_prefix('image.png'), 'image')
        self.assertEqual(get_prefix('image.png.png'), 'image')

    def test_split_comma(self):
        from app.utilities.str_utils import split_expr_on_comma
        # basic tests
        self.assertEqual(split_expr_on_comma('expr'), ('expr', None))
        self.assertEqual(split_expr_on_comma('expr,'), ('expr', ''))
        self.assertEqual(split_expr_on_comma(',fallback'), ('', 'fallback'))
        self.assertEqual(split_expr_on_comma('expr,fallback'), ('expr', 'fallback'))

        # quote tests
        self.assertEqual(split_expr_on_comma('"expr,fallback"'), ('"expr,fallback"', None))
        self.assertEqual(split_expr_on_comma("'expr,fallback'"), ("'expr,fallback'", None))
        self.assertEqual(split_expr_on_comma('"\\",expr",fallback'), ('"\\",expr"', 'fallback'))
        self.assertEqual(split_expr_on_comma('"\\"",fallback'), ('"\\""', 'fallback'))

        # bracket tests
        self.assertEqual(split_expr_on_comma('(expr,fallback)'), ('(expr,fallback)', None))
        self.assertEqual(split_expr_on_comma('[expr,fallback]'), ('[expr,fallback]', None))
        self.assertEqual(split_expr_on_comma('{expr,fallback}'), ('{expr,fallback}', None))
        self.assertEqual(split_expr_on_comma('(expr),fallback'), ('(expr)','fallback'))
        self.assertEqual(split_expr_on_comma('((expr),fallback)'), ('((expr),fallback)', None))

        # mixed tests
        # quotes and brackets
        self.assertEqual(split_expr_on_comma('"(expr,fallback)"'), ('"(expr,fallback)"', None))
        # brackets and quotes
        self.assertEqual(split_expr_on_comma('("expr,fallback")'), ('("expr,fallback")', None))
        # bracket in quotes does not close
        self.assertEqual(split_expr_on_comma('(")" + expr,fallback)'), ('(")" + expr,fallback)', None))
        # bracket in quotes does not open
        self.assertEqual(split_expr_on_comma('"(" + expr,(fallback)'), ('"(" + expr','(fallback)'))

if __name__ == '__main__':
    unittest.main()
