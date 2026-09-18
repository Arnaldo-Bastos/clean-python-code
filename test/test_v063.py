import unittest

from formatter import format_source, signature, lexical_signature


class V063OuterGroupRegressionTests(unittest.TestCase):
    def check(self, source):
        result = format_source(source)
        self.assertEqual(signature(source), signature(result))
        self.assertEqual(lexical_signature(source), lexical_signature(result))
        self.assertEqual(result, format_source(result))
        return result

    def test_long_assignment_name_does_not_shift_outer_pipeline(self):
        source = """df_ai_requests = (
                   spark.read
                   .csv(
                         f"{data_path}/*.csv",
                         header = True,
                         inferSchema = True,
                       )
                 )
"""
        result = self.check(source)
        lines = result.splitlines()
        self.assertEqual(lines[1], "    spark.read")
        self.assertEqual(lines[2], "    .csv(")
        self.assertEqual(lines[-1], ")")

    def test_outer_indent_is_independent_of_assignment_name_length(self):
        short = self.check("""x = (
    spark.read
    .csv(path)
)
""")
        long = self.check("""a_very_long_dataframe_variable_name = (
    spark.read
    .csv(path)
)
""")
        short_lines = short.splitlines()
        long_lines = long.splitlines()
        self.assertEqual(short_lines[1].index("spark"), 4)
        self.assertEqual(long_lines[1].index("spark"), 4)
        self.assertEqual(short_lines[-1], ")")
        self.assertEqual(long_lines[-1], ")")

    def test_nested_call_still_uses_rendered_delimiter_hierarchy(self):
        source = """df_ai_requests = (
    spark.read
    .csv(
        path,
        header = True,
        inferSchema = True,
    )
)
"""
        result = self.check(source)
        lines = result.splitlines()
        csv_line = next(line for line in lines if ".csv(" in line)
        arg_line = next(line for line in lines if line.lstrip().startswith("path"))
        close_line = lines[-2]
        open_col = csv_line.index("(")
        self.assertEqual(len(arg_line) - len(arg_line.lstrip()), open_col + 2)
        self.assertEqual(len(close_line) - len(close_line.lstrip()), open_col)


if __name__ == "__main__":
    unittest.main()
