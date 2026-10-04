from __future__ import annotations

import unittest

from typing import Tuple

from app.engine.graphics.text.tagged_text import TaggedText, TaggedTextChunk
from app.engine.graphics.text.text_effects import TextSettings, TextEffect
from app.engine.graphics.text.styled_text_parser import parse_styled_text
from app.utilities.typing import NID
from app.engine import fonts
from app.tests.engine_harness import EngineTestCase


class StyledTextParsingTest(unittest.TestCase):
    """
    Tests parsing of styled text into tagged text
    """

    def _tagged_text_color(self, chunk: TaggedTextChunk) -> NID:
        settings = TextSettings("default_color", (0, 0))
        settings.apply(chunk.effects)
        return settings.color

    def _tagged_offsets(self, chunk: TaggedTextChunk) -> Tuple[float, float]:
        offsets = []
        for effect in chunk.effects:
            if effect.nid != "color":
                offsets.append(str(effect))
        return offsets

    def setUp(self):
        from app.data.resources.resources import RESOURCES
        from app.data.serialization.versions import CURRENT_SERIALIZATION_VERSION
        RESOURCES.load("testing_proj.ltproj", CURRENT_SERIALIZATION_VERSION)

    def test_tagged_text_chunk_does_not_override_eq(self):
        self.assertEqual(id(TaggedTextChunk.__eq__), id(object.__eq__))

    def test_parsing(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = ("<blue>this <iconvo>is</> some <red>red</> "
                            "and some <jitter>jittering <green>green</></> text</>")
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = [
            "this ",
            "is",
            " some ",
            "red",
            " and some ",
            "jittering ",
            "green",
            " text",
        ]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [
            default_font,
            "iconvo",
            default_font,
            default_font,
            default_font,
            default_font,
            default_font,
            default_font,
        ]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = [
            "blue",
            "blue",
            "blue",
            "red",
            "blue",
            "blue",
            "green",
            "blue",
        ]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], [], [], [], [], ["jitter"], ["jitter"], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_parsing_unclosed_tag_pair(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "<blue>blue text? <red>red text?</> but did not close blue"
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = ["blue text? ", "red text?", " but did not close blue"]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [default_font, default_font, default_font]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = ["blue", "red", "blue"]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], [], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_parsing_doubled_up_tag(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = (
            "<blue>blue text <blue>more blue text<red> "
            "now it's red text</> back to blue</> still blue</> now white")
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = [
            "blue text ",
            "more blue text",
            " now it's red text",
            " back to blue",
            " still blue",
            " now white",
        ]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [
            default_font,
            default_font,
            default_font,
            default_font,
            default_font,
            default_font,
        ]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = ["blue", "blue", "red", "blue", "blue", default_color]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], [], [], [], [], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_parsing_nonexistent(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "some text with <???>a non-existent tag</>"
        # The parser shows the malformed tag as plain text, and warns about it
        with self.assertLogs(level='WARNING'):
            tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = ["some text with ", "<???>", "a non-existent tag", "</>"]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [default_font, default_font, default_font, default_font]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = [default_color, default_color, default_color, default_color]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], [], [], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_parsing_unclosed_opening_tag(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "another tag <blue that is simply never closed oops</>"
        # The parser shows the malformed tag as plain text, and warns about it
        with self.assertLogs(level='WARNING'):
            tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = ["another tag <blue that is simply never closed oops", "</>"]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [default_font, default_font]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = [default_color, default_color]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_parsing_orphaned_closing_tag(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "some </>text with <red>extra closing tags</></>"
        # The parser shows the malformed tag as plain text, and warns about it
        with self.assertLogs(level='WARNING'):
            tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that the text is parsed correctly based on tags
        actual_texts = [x.text for x in tagged_text]
        expected_texts = ["some ", "</>", "text with ", "extra closing tags", "</>"]
        self.assertEqual(actual_texts, expected_texts)

        # test that the font is correct
        actual_fonts = [x.font for x in tagged_text]
        expected_fonts = [
            default_font,
            default_font,
            default_font,
            default_font,
            default_font,
        ]
        self.assertEqual(actual_fonts, expected_fonts)

        # test that the colors are correct
        actual_colors = [self._tagged_text_color(x) for x in tagged_text]
        expected_colors = [
            default_color,
            default_color,
            default_color,
            "red",
            default_color,
        ]
        self.assertEqual(actual_colors, expected_colors)

        # test that offsets are correct
        actual_offsets = [self._tagged_offsets(x) for x in tagged_text]
        expected_offsets = [[], [], [], [], []]
        self.assertEqual(actual_offsets, expected_offsets)

    def test_indexing(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "<blue>this is some <red>red</> text</>"
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that single indices work as expected
        indexed_text = tagged_text[0]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "t")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[12]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, " ")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[13]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "r")
        self.assertEqual(self._tagged_text_color(chunk), "red")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[15]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "d")
        self.assertEqual(self._tagged_text_color(chunk), "red")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[16]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, " ")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[20]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "t")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        # test that indexing out of bounds asserts
        with self.assertRaises(IndexError):
            tagged_text[-1]
        with self.assertRaises(IndexError):
            tagged_text[len(tagged_text)]

    def test_slicing(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "<blue>this is some <red>red</> text</>"
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        # test that slicing entire tagged text works
        indexed_text = tagged_text[:]
        self.assertEqual(indexed_text, tagged_text)

        # test that slicing to end works
        indexed_text = tagged_text[:len(tagged_text)]
        self.assertEqual(indexed_text, tagged_text)

        # test that slicing past the end works
        indexed_text = tagged_text[:len(tagged_text) + 1]
        self.assertEqual(indexed_text, tagged_text)
        indexed_text = tagged_text[:len(tagged_text) + 2]
        self.assertEqual(indexed_text, tagged_text)

        # test that slicing from beginning works
        indexed_text = tagged_text[0:]
        self.assertEqual(indexed_text, tagged_text)

        # test that 0 length slice works
        indexed_text = tagged_text[0:0]
        self.assertEqual(len(indexed_text.chunks), 0)
        indexed_text = tagged_text[len(tagged_text):len(tagged_text)]
        self.assertEqual(len(indexed_text.chunks), 0)

        # test that slicing starting from past the end works
        indexed_text = tagged_text[len(tagged_text):len(tagged_text) + 1]
        self.assertEqual(len(indexed_text.chunks), 0)

        # regular slicing
        indexed_text = tagged_text[3:13]
        self.assertEqual(len(indexed_text.chunks), 1)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "s is some ")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[3:14]
        self.assertEqual(len(indexed_text.chunks), 2)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "s is some ")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])
        chunk = indexed_text.chunks[1]
        self.assertEqual(chunk.text, "r")
        self.assertEqual(self._tagged_text_color(chunk), "red")
        self.assertEqual(self._tagged_offsets(chunk), [])

        indexed_text = tagged_text[3:20]
        self.assertEqual(len(indexed_text.chunks), 3)
        chunk = indexed_text.chunks[0]
        self.assertEqual(chunk.text, "s is some ")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])
        chunk = indexed_text.chunks[1]
        self.assertEqual(chunk.text, "red")
        self.assertEqual(self._tagged_text_color(chunk), "red")
        self.assertEqual(self._tagged_offsets(chunk), [])
        chunk = indexed_text.chunks[2]
        self.assertEqual(chunk.text, " tex")
        self.assertEqual(self._tagged_text_color(chunk), "blue")
        self.assertEqual(self._tagged_offsets(chunk), [])

        # test backward slicing
        indexed_text = tagged_text[5:0]
        self.assertEqual(len(indexed_text.chunks), 0)
        indexed_text = tagged_text[len(tagged_text) + 1:0]
        self.assertEqual(len(indexed_text.chunks), 0)

        # test that slicing with out of bounds and invalid slices
        with self.assertRaises(IndexError):
            tagged_text[-1:]
        with self.assertRaises(IndexError):
            tagged_text[:-1]
        with self.assertRaises(IndexError):
            tagged_text[-1:-1]
        with self.assertRaises(IndexError):
            tagged_text[-1:-5]
        with self.assertRaises(IndexError):
            tagged_text[0:-5]
        with self.assertRaises(ValueError):
            tagged_text[0:5:1]

    def test_indexing_and_slicing_empty_string(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = ""
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)

        with self.assertRaises(IndexError):
            tagged_text[0]

        indexed_text = tagged_text[0:0]
        self.assertEqual(len(indexed_text.chunks), 0)

        indexed_text = tagged_text[10:10]
        self.assertEqual(len(indexed_text.chunks), 0)


class TaggedTextCachingTest(EngineTestCase):
    def setUp(self):
        super().setUp()
        # Caching measures the text, which needs its font
        fonts.load_fonts(headless=True)

    def test_huge_cycle_period_does_not_cache(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "<jitter>this is some <red>red</> text</>"
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)
        tagged_text.set_caching_if_recommended()
        self.assertFalse(tagged_text.caching_enabled)
        tagged_text.set_caching_if_under_max_threshold()
        self.assertFalse(tagged_text.caching_enabled)
        tagged_text.force_enable_caching()
        self.assertTrue(tagged_text.caching_enabled)

    def test_text_does_not_cache_when_disabled(self):
        default_font = "convo"
        default_color = "white"
        test_styled_text = "<wave>this is some <red>red</> text</>"
        tagged_text = parse_styled_text(test_styled_text, default_font, default_color)
        self.assertFalse(tagged_text.caching_enabled)
        self.assertGreater(tagged_text.get_cycle_period(), 1)

        from unittest.mock import MagicMock
        surf = MagicMock()
        cache_surf = MagicMock()
        for i in range(tagged_text.get_cycle_period()):
            tagged_text.test_draw(surf, (0, 0), cache_counter=i, test_surf=cache_surf)

        for i in range(tagged_text.get_cycle_period()):
            self.assertFalse(i in tagged_text._cache)

    def test_text_can_cache_when_enabled(self):

        class TestEffect(TextEffect):
            cycle_period = 3

            def __init__(self):
                pass

        tagged_text = TaggedText()
        tagged_text.append("test", "convo", [TestEffect()])
        tagged_text.set_caching_if_recommended()
        self.assertTrue(tagged_text.caching_enabled)
        self.assertEqual(tagged_text.get_cycle_period(), 3)

        from unittest.mock import MagicMock
        surf = MagicMock()
        cache_surf = MagicMock()
        for i in range(tagged_text.get_cycle_period()):
            tagged_text.test_draw(surf, (0, 0), cache_counter=i, test_surf=cache_surf)

        for i in range(tagged_text.get_cycle_period()):
            self.assertTrue(i in tagged_text._cache)

    def test_text_can_cache_handles_lcm(self):

        class TestEffect(TextEffect):
            cycle_period = 3

            def __init__(self):
                pass

        class TestEffect2(TextEffect):
            cycle_period = 4

            def __init__(self):
                pass

        tagged_text = TaggedText()
        tagged_text.append("test", "convo", [TestEffect(), TestEffect2()])
        tagged_text.set_caching_if_recommended()
        self.assertTrue(tagged_text.caching_enabled)
        self.assertEqual(tagged_text.get_cycle_period(), 12)

        from unittest.mock import MagicMock
        surf = MagicMock()
        cache_surf = MagicMock()
        for i in range(tagged_text.get_cycle_period()):
            tagged_text.test_draw(surf, (0, 0), cache_counter=i, test_surf=cache_surf)

        for i in range(tagged_text.get_cycle_period()):
            self.assertTrue(i in tagged_text._cache)


def load_tests(loader, tests, ignore):
    import doctest
    from app.engine.graphics.text import styled_text_parser

    tests.addTests(doctest.DocTestSuite(styled_text_parser))
    return tests


if __name__ == "__main__":
    unittest.main()
