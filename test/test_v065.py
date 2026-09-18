import io
import tokenize
import unittest

from formatter import format_source, signature, lexical_signature


class V065DefinitiveAlignmentTests(unittest.TestCase):
    def check(self, source):
        result = format_source(source)
        self.assertEqual(signature(source), signature(result))
        self.assertEqual(lexical_signature(source), lexical_signature(result))
        self.assertEqual(result, format_source(result))
        self.assert_multiline_delimiters_align(result)
        return result

    def assert_multiline_delimiters_align(self, source):
        stack = []
        pairs = {')': '(', ']': '[', '}': '{'}
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type != tokenize.OP:
                continue
            if tok.string in '([{':
                stack.append(tok)
            elif tok.string in ')]}':
                opener = stack.pop()
                self.assertEqual(opener.string, pairs[tok.string])
                if opener.start[0] != tok.start[0]:
                    self.assertEqual(opener.start[1], tok.start[1])

    def assert_dot_axis(self, source, expected=8):
        dot_cols = [len(line) - len(line.lstrip())
                    for line in source.splitlines()
                    if line.lstrip().startswith('.')]
        self.assertTrue(dot_cols)
        self.assertEqual(set(dot_cols), {expected}, msg=source)

    def test_spark_read_attribute_and_call_chain_align(self):
        source = """df_ai_requests = (
    spark.read.csv(
        f"{data_path}/*.csv",
        header=True,
        inferSchema=True,
    )
)
"""
        result = self.check(source)
        self.assertIn('    spark', result.splitlines())
        self.assertIn('        .read', result.splitlines())
        self.assertIn('        .csv(', result.splitlines())
        self.assert_dot_axis(result)

    def test_drop_and_with_columns_renamed_share_dot_axis(self):
        source = """df_ai_requests = (
    df_ai_requests.drop('moeda','referencia_tarifa','dado_sintetico').withColumnsRenamed(
        {
            'id_requisicao': 'request_id',
            'mes_ref': 'month', 'departamento': 'sector', 'caso_uso': 'use_case',
            'idioma': 'language'
            , 'complexidade': 'complexity'
        }
    )
)
"""
        result = self.check(source)
        lines = result.splitlines()
        self.assertIn('    df_ai_requests', lines)
        self.assertIn('        .drop(', lines)
        self.assertIn('        .withColumnsRenamed(', lines)
        self.assert_dot_axis(result)
        self.assertFalse(any(line.lstrip().startswith(',') for line in lines))
        keys = ['id_requisicao', 'mes_ref', 'departamento', 'caso_uso', 'idioma', 'complexidade']
        mapping_lines = [line for line in lines if any(f"'{key}'" in line for key in keys)]
        self.assertEqual(len(mapping_lines), len(keys))
        self.assertTrue(all(sum(f"'{key}'" in line for key in keys) == 1 for line in mapping_lines))

    def test_databricks_builder_attribute_is_part_of_chain(self):
        source = """spark = (
    DatabricksSession.builder.getOrCreate()
)
"""
        result = self.check(source)
        lines = result.splitlines()
        self.assertIn('    DatabricksSession', lines)
        self.assertIn('        .builder', lines)
        self.assertIn('        .getOrCreate()', lines)
        self.assert_dot_axis(result)

    def test_nested_collections_keep_exact_matching_columns(self):
        source = """value = (
    fn(
        [
            {
                "a": (1, 2),
                "b": [3, 4],
            }
        ]
    )
)
"""
        self.check(source)


if __name__ == '__main__':
    unittest.main()
