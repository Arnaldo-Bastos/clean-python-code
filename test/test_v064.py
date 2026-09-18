import unittest

from formatter import format_source, signature, lexical_signature


class V064PipelineAndDictRegressionTests(unittest.TestCase):
    def check(self, source):
        result = format_source(source)
        self.assertEqual(signature(source), signature(result))
        self.assertEqual(lexical_signature(source), lexical_signature(result))
        self.assertEqual(result, format_source(result))
        return result

    def test_user_ai_requests_example(self):
        source = """data_path = "/Volumes/workspace/default/ai_cost_data"

df_ai_requests = (
                   spark.read
                   .csv(
                         f"{data_path}/*.csv",
                         header = True,
                         inferSchema = True,
                       )
                 )

df_ai_requests = (
    df_ai_requests.drop('moeda','referencia_tarifa','dado_sintetico').withColumnsRenamed(
        {
            'id_requisicao': 'request_id',
            'id_demanda': 'demand_id',
            'data_hora_utc': 'request_timestamp',
            'mes_ref': 'month', 'departamento': 'sector', 'caso_uso': 'use_case',
            'idioma': 'language'
            , 'complexidade': 'complexity'
            , 'provedor_modelo': 'ai_model_provider'
            , 'modelo': 'ai_model',
            'tokens_entrada': 'input_tokens',
            'tokens_saida': 'output_tokens',
            'preco_entrada_usd_1m': 'input_price_usd_1m',
            'preco_saida_usd_1m': 'output_price_usd_1m',
            'custo_entrada_usd': 'input_cost_usd',
            'custo_saida_usd': 'output_cost_usd',
            'custo_total_usd': 'total_cost_usd'
        }
    )
)

df_ai_requests.show(20, truncate = False)
"""
        result = self.check(source)
        lines = result.splitlines()

        # Outer wrappers are structural: long assignment names do not create
        # a huge left margin.
        spark_line = next(line for line in lines if "spark.read" in line)
        self.assertEqual(len(spark_line) - len(spark_line.lstrip()), 4)

        # A chain written inline in the input is still expanded vertically.
        drop_line = next(line for line in lines if "df_ai_requests.drop(" in line)
        rename_line = next(line for line in lines if ".withColumnsRenamed(" in line)
        self.assertEqual(len(drop_line) - len(drop_line.lstrip()), 4)
        self.assertEqual(len(rename_line) - len(rename_line.lstrip()), 4)

        # Every rename entry occupies its own physical line and commas stay
        # trailing rather than beginning the next entry.
        mapping_keys = [
            "id_requisicao", "id_demanda", "data_hora_utc", "mes_ref",
            "departamento", "caso_uso", "idioma", "complexidade",
            "provedor_modelo", "modelo", "tokens_entrada", "tokens_saida",
            "preco_entrada_usd_1m", "preco_saida_usd_1m",
            "custo_entrada_usd", "custo_saida_usd", "custo_total_usd",
        ]
        entry_lines = [line for line in lines if any(f"'{key}'" in line for key in mapping_keys)]
        self.assertEqual(len(entry_lines), len(mapping_keys))
        self.assertTrue(all(not line.lstrip().startswith(",") for line in entry_lines))
        self.assertTrue(all(sum(f"'{key}'" in line for key in mapping_keys) == 1 for line in entry_lines))


if __name__ == "__main__":
    unittest.main()
