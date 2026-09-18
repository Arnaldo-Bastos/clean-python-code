import unittest

from formatter import format_source, signature, lexical_signature


class ChainAlignmentRegressionTests(unittest.TestCase):
    def assert_safe_and_stable(self, source):
        formatted = format_source(source)
        self.assertEqual(signature(source), signature(formatted))
        self.assertEqual(lexical_signature(source), lexical_signature(formatted))
        self.assertEqual(formatted, format_source(formatted))
        return formatted

    def test_databricks_session_builder_chain_stays_aligned(self):
        source = """spark = (
          DatabricksSession.builder
.getOrCreate()
        )
"""
        formatted = self.assert_safe_and_stable(source)
        lines = [line for line in formatted.splitlines()
                 if "DatabricksSession.builder" in line or ".getOrCreate()" in line]
        self.assertEqual(len(lines), 2)
        self.assertEqual(len(lines[0]) - len(lines[0].lstrip()),
                         len(lines[1]) - len(lines[1].lstrip()))

    def test_spark_read_chain_stays_aligned(self):
        source = """df = (
       spark.read
.schema(schema)
.option("header", True)
.option("mode", "FAILFAST")
.option("timestampFormat", "yyyy-MM-dd'T'HH:mm:ss'Z'")
.csv(data_path)
     )
"""
        formatted = self.assert_safe_and_stable(source)
        lines = [line for line in formatted.splitlines()
                 if "spark.read" in line or line.lstrip().startswith(".")]
        indents = {len(line) - len(line.lstrip()) for line in lines}
        self.assertEqual(len(indents), 1)


if __name__ == "__main__":
    unittest.main()
