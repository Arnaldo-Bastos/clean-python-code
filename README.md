# Clean Python Code 0.6.9

Formatação personalizada de Python e PySpark, orientada pela AST e pelos tokens originais. Formata arquivos `.py` e documentos Python das células de notebooks `.ipynb`.

- Safely normalizes problematic Unicode whitespace copied into Python code (for example U+00A0), while preserving such characters inside strings and comments.

## Uso

Instale o VSIX pelo comando **Extensions: Install from VSIX...** e recarregue o VS Code, se solicitado. É necessário um interpretador Python 3.9 ou superior, compatível com a sintaxe do arquivo; f-strings PEP 701 exigem Python 3.12 ou superior.

- Selecione instruções completas e pressione **Ctrl + Alt + S**, ou execute **Clean Python Code: Format Selection**.
- Para o documento inteiro, use **Format Document With... → Clean Python Code**.
- Em notebooks, use a formatação da célula Python ou selecione o código da célula e pressione **Ctrl + Alt + S**. O provedor também pode ser usado pelo comando de formatação de notebook do VS Code.
- Se necessário, configure `cleanPythonCode.pythonPath` com o caminho do executável. Sem configuração explícita, a extensão consulta o ambiente da extensão Microsoft Python e depois o PATH.

## Regras de layout

Os delimitadores de várias linhas fecham na mesma coluna em que abrem. Cada nível interno acrescenta dois espaços por padrão. Os pontos de uma cadeia de métodos se alinham com o primeiro ponto da cadeia.

```python
df = (
       spark.table("events")
            .where(
                    (a == 1)
                    & (b == 2)
                  )
     )
```

Chamadas curtas com até dois argumentos ficam compactas quando não contêm estruturas expandidas. Listas de argumentos que o autor já colocou em várias linhas são respeitadas. Chamadas maiores e coleções são expandidas conforme sua estrutura. Grupos aninhados que contêm quebras têm abertura e fechamento em níveis próprios.

Condições com `and`, `or`, `&` e `|` recebem parênteses por operando e quebras antes dos operadores. Operações aritméticas compostas não constantes também expõem os níveis de precedência. A árvore da expressão nunca é reassociada, inclusive em subtrações, divisões e potências. Expressões constantes curtas, como `-30 * 24 * 3600`, permanecem compactas.

Chaves de dicionários usam espaço antes e depois de `:`; essa regra não é aplicada aos dois-pontos de slices, lambdas ou anotações. Vírgulas existentes são preservadas; `leadingComma` controla a posição das vírgulas em estruturas expandidas sem comentários. Strings, f-strings, comentários e grafia dos identificadores são preservados.

## Configurações

| Configuração | Padrão | Efeito |
| --- | --- | --- |
| `outerIndent` | 2 | Espaços após a coluna de abertura de um grupo externo |
| `argumentIndent` | 2 | Espaços após a coluna de abertura de chamadas e coleções |
| `chainIndent` | 0 | Deslocamento adicional em relação ao primeiro ponto da cadeia |
| `maxInlineLength` | 88 | Limite preferencial da expressão, sem quebrar literais indivisíveis |
| `leadingComma` | false | Posiciona as vírgulas no início dos itens expandidos |
| `expandBooleanOperators` | true | Expande condições e operações aritméticas compostas |

Configurações explícitas de versões anteriores continuam prevalecendo. Para reproduzir os novos padrões, remova essas substituições ou ajuste os valores conforme a tabela. O alinhamento pela coluna real pode gerar linhas largas quando há nomes longos e muitos níveis; `maxInlineLength` é um limite preferencial, não uma largura máxima garantida.

## Validação e limites

O código é analisado, nunca importado nem executado. Cada edição exige igualdade da AST e dos tokens, exceto parênteses de agrupamento. A segunda formatação deve produzir exatamente o mesmo texto. Na seleção, a validação também abrange o documento completo, usando os offsets UTF-16 do VS Code.

Cabeçalhos `def`, `for`, `if`, `else`, imports, suites de uma linha e instruções separadas por ponto e vírgula são preservados; as instruções completas dentro dos blocos podem ser formatadas. Seleções incompletas, células com comandos mágicos de IPython, sintaxe inválida ou não suportada pelo interpretador são recusadas, mantendo o original. Não há necessidade de instalar PySpark para formatar.

O VSIX contém apenas os arquivos de execução e documentação. O ZIP de fontes separado inclui os testes, o notebook de referência e o script de empacotamento. Execute `python -m unittest discover -s test -p "test_*.py"`, `node --test test/formatter.test.js` e `python test/stdlib_corpus.py`. Os testes históricos foram mantidos em `test/legacy` como corpus; suas antigas expectativas literais de indentação foram substituídas por contratos de layout desta versão.


### Notebook shortcut behavior

`Ctrl + Alt + S` formats the current Python selection. If there is no text selection, it formats the active Python notebook cell (or active Python document). The Output panel `Clean Python Code` records targeting and formatting diagnostics.


## Reviewed fluent-chain layout

The first fluent segment stays on the base-expression line; later segments break and align with that first dot:

```python
spark = (
          DatabricksSession.builder
                            .getOrCreate()
        )

df_ai_requests = (
                   spark.read
                        .csv(
                              path,
                              header = True,
                            )
                 )
```

In Python notebooks, the command also falls back to notebook kernel/language metadata. If VS Code persisted a Python code cell as another language (for example `javascript`), the cell can still be formatted when the notebook itself is Python. After successful Python parsing/validation, the extension attempts to switch that cell back to the `python` language mode.
