import unittest

from formatter import format_source, sanitize_unicode_whitespace


class V067UnicodeWhitespaceTests(unittest.TestCase):
    def test_nbsp_indentation_is_normalized(self):
        source = (
            "df = (\n"
            "\u00a0\u00a0\u00a0\u00a0spark\n"
            "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0.read\n"
            "\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0.csv(path)\n"
            ")\n"
        )
        result = format_source(source)
        self.assertNotIn("\u00a0", result)
        compile(result, "<formatted>", "exec")
        self.assertEqual(result, format_source(result))

    def test_multiple_unicode_space_types_are_normalized_in_code(self):
        source = "x\u2003=\u202f1\ny\u2007=\u00a02\n"
        result = format_source(source)
        self.assertEqual(result, "x = 1\ny = 2\n")
        compile(result, "<formatted>", "exec")

    def test_unicode_spaces_inside_string_and_comment_are_preserved(self):
        source = "text = 'hello\u00a0world'  # keep\u202fthis\nvalue\u00a0=\u00a01\n"
        result = format_source(source)
        self.assertIn("'hello\u00a0world'", result)
        self.assertIn("# keep\u202fthis", result)
        self.assertNotIn("value\u00a0=", result)
        compile(result, "<formatted>", "exec")

    def test_sanitizer_is_idempotent(self):
        source = "value\u00a0=\u20031\ntext = 'x\u00a0y'\n"
        once = sanitize_unicode_whitespace(source)
        twice = sanitize_unicode_whitespace(once)
        self.assertEqual(once, twice)
        self.assertIn("'x\u00a0y'", once)


if __name__ == "__main__":
    unittest.main()
