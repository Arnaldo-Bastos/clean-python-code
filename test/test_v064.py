import unittest
from formatter import format_source, signature, lexical_signature


class V064StructuralPipelineTests(unittest.TestCase):
    def check(self, source):
        result = format_source(source)
        self.assertEqual(signature(source), signature(result))
        self.assertEqual(lexical_signature(source), lexical_signature(result))
        self.assertEqual(result, format_source(result))
        return result

    def test_ai_requests_pipeline_and_mapping(self):
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
        self.assertIn("    spark.read", lines)
        self.assertIn("    .csv(", lines)
        self.assertIn("    df_ai_requests.drop(", lines)
        self.assertIn("    .withColumnsRenamed(", lines)
        self.assertIn("            'id_requisicao': 'request_id',", lines)
        self.assertIn("            'complexidade': 'complexity',", lines)
        self.assertFalse(any(line.lstrip().startswith(",") for line in lines))
        self.assertFalse(any("' : " in line for line in lines))


if __name__ == "__main__":
    unittest.main()
