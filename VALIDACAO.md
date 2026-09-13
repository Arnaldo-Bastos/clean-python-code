# Clean Python Code 0.6.1 — equações e ícone

O problema vinha da política aritmética da versão 0.6.0: expressões com várias operações eram expandidas recursivamente, independentemente de sua largura. Isso fragmentava fórmulas curtas, como `f_s`, `x_max` e o retorno com a soma de quadrados do notebook enviado.

Foi implementada a opção independente `cleanPythonCode.arithmeticLayout`:

| Modo | Comportamento |
| --- | --- |
| `auto` — padrão | Mantém equações curtas em uma linha; divide as longas no nível principal. Produtos e potências de um termo permanecem juntos. |
| `compact` | Não força quebras nos operadores aritméticos. Comentários, chamadas, coleções e condições continuam seguindo suas próprias regras. |
| `expanded` | Mantém a expansão recursiva da aritmética da versão 0.6.0. |

O limite preferencial continua sendo `maxInlineLength`, com padrão 88. A medição considera a expressão normalizada na AST, sem o nome da variável de destino nem a indentação. Isso evita que parênteses acrescentados em uma aplicação anterior mudem a decisão na aplicação seguinte. `ast.unparse` participa apenas da medição; a saída continua baseada nos tokens originais.

No padrão novo, estas fórmulas permanecem compactas:

```python
f_s = pe * (cte * (1 - df['score']) + df['score']) / df['score']
x_max = (pe * cte) / (vl_opt + pe * (cte - 1))
return err_pct ** 2 + err_cbk ** 2
```

O quociente mais longo recebe somente a divisão principal em outra linha:

```python
cbk = (
        df_reg[df_reg['is_bad']]['PEDIDO_VALOR_TOTAL'].sum()
        / df_reg['PEDIDO_VALOR_TOTAL'].sum()
      )
```

O trecho completo tem 49 linhas na entrada, 156 depois da 0.6.0, 75 com o novo padrão `auto` e 69 com `compact`. A diferença restante em relação à entrada vem das regras mantidas para chamadas, coleções e condições. A contagem inclui linhas em branco e não representa apenas as equações.

A formatação das condições de `filter`, `where` e `when` continua independente: `expandBooleanOperators` agora controla somente as condições. Fórmulas curtas previamente expandidas podem ser recolhidas para uma linha sem remover seus parênteses. Listas de argumentos explicitamente multilinha continuam respeitadas.

## Ícone

O ícone foi substituído por `icone_clean_python_code.png`, exatamente como enviado: PNG de 128 × 128 pixels, sem redimensionamento nem alteração dos pixels. A igualdade byte a byte foi verificada dentro do VSIX final.

## Validação

- 21 testes Python aprovados em Python 3.11.4 e 3.12.14, abrangendo os corpus anteriores e as regressões novas de equações. O contador do conjunto herdado registra 1.660/1.690 casos, respectivamente; os testes adicionais de equações têm suas próprias iterações.
- Os dois notebooks foram verificados nos três modos aritméticos, com igualdade da AST, preservação de tokens e estabilidade na segunda formatação.
- Casos adicionais cobrem produtos, somas longas, quocientes, subtração e divisão com agrupamento à direita, potências, operações matriciais, Unicode, limites de largura e independência das configurações.
- 19 testes JavaScript aprovados, incluindo encaminhamento da nova configuração pelo comando de seleção e pelos provedores de formatação.
- 10 módulos da biblioteca padrão do Python 3.11 passaram pela verificação de preservação e estabilidade.
- As 31 células dos dois notebooks foram processadas pela CLI extraída do VSIX final, com validação de documento completo. O manifesto, a versão, o CRC e a igualdade dos arquivos do pacote com os fontes testados também foram conferidos.
- O notebook entregue altera somente o código da célula. Metadados e outputs foram preservados, e seu código de negócio não foi executado.

Permanece a limitação da revisão anterior: os testes JavaScript usam processos Python reais com transporte por arquivos temporários e API VS Code simulada, pois o ambiente bloqueia os pipes nativos e a inicialização do Extension Host isolado. A interface real do VS Code não foi validada nesta revisão. O adaptador é exclusivo dos testes e não é incluído no VSIX.

## Uso

Instale `clean-python-code-0.6.1.vsix` pelo comando **Extensions: Install from VSIX...**. O modo `auto` entra como padrão sem necessidade de configuração adicional.

Para não forçar quebras aritméticas, use no `settings.json`:

```json
"cleanPythonCode.arithmeticLayout": "compact"
```

`equacoes-comparacao-0.6.1.html` mostra a referência, a versão antiga e os dois modos novos. O ZIP de fontes inclui os testes e os logs atuais em `test/verification061`.
