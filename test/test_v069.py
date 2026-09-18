import unittest

from formatter import format_source, signature, lexical_signature


class V069ScreenshotContractTests(unittest.TestCase):
    def check_exact(self, source, expected):
        result = format_source(source)
        self.assertEqual(result, expected)
        self.assertEqual(signature(source), signature(result))
        self.assertEqual(lexical_signature(source), lexical_signature(result))
        self.assertEqual(format_source(result), result)

    def test_session_cell_matches_reviewed_layout(self):
        source = """from databricks.connect import DatabricksSession

spark = (
    DatabricksSession
        .builder
        .getOrCreate()
        )
"""
        expected = """from databricks.connect import DatabricksSession

spark = (
          DatabricksSession.builder
                           .getOrCreate()
        )
"""
        self.check_exact(source, expected)

    def test_csv_cell_matches_reviewed_layout(self):
        source = """data_path = "/Volumes/workspace/default/ai_cost_data"

df_ai_requests = (
    spark
        .read
        .csv(
                f"{data_path}/*.csv",
                header = True,
                inferSchema = True,
            )
                 )
"""
        expected = """data_path = "/Volumes/workspace/default/ai_cost_data"

df_ai_requests = (
                   spark.read
                        .csv(
                              f"{data_path}/*.csv",
                              header = True,
                              inferSchema = True,
                            )
                 )
"""
        self.check_exact(source, expected)

    def test_rename_cell_matches_reviewed_layout(self):
        source = """df_ai_requests = (
    df_ai_requests.drop('moeda','referencia_tarifa','dado_sintetico')
    .withColumnsRenamed(
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
        expected = """df_ai_requests = (
                   df_ai_requests.drop(
                                        'moeda',
                                        'referencia_tarifa',
                                        'dado_sintetico'
                                      )
                                 .withColumnsRenamed(
                                                      {
                                                        'id_requisicao': 'request_id',
                                                        'id_demanda': 'demand_id',
                                                        'data_hora_utc': 'request_timestamp',
                                                        'mes_ref': 'month',
                                                        'departamento': 'sector',
                                                        'caso_uso': 'use_case',
                                                        'idioma': 'language',
                                                        'complexidade': 'complexity',
                                                        'provedor_modelo': 'ai_model_provider',
                                                        'modelo': 'ai_model',
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
        self.check_exact(source, expected)


if __name__ == "__main__":
    unittest.main()
