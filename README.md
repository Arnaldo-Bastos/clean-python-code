# Clean Python Code

Personalized Python and PySpark formatting for VS Code, based on a hierarchical indentation style for analytics code.

## Why Clean Python Code?

Clean Python Code is designed for developers and data professionals who want more control over how complex Python/PySpark expressions are laid out.

It focuses on **visual hierarchy**, not on enforcing Black or conventional PEP 8 formatting.

## Main command

Select a Python code block and press:

**Ctrl + I**

The shortcut is intentionally registered as `ctrl+i` on **Windows, Linux, and macOS**.

## What it formats

- Chained PySpark/DataFrame operations such as `.filter()`, `.withColumn()`, `.select()`, `.groupBy()`, `.agg()`, `.join()` and other method chains.
- Long one-line expressions by introducing aligned parentheses.
- Long argument lists, lists, tuples and dictionaries.
- Nested calls such as `F.when(...)`, `isin(...)`, aggregations and `Window` expressions.
- Complex boolean expressions using `&`, `|`, `and` and `or`.
- Python control-flow structures such as `for`, `if`, `elif`, `else`, `try`, `except`, `finally`, `with`, `match`, functions and classes, while preserving Python's structural indentation.
- Multiple statements, blank lines and comments.
- Python cells inside `.ipynb` notebooks opened in VS Code/Jupyter.

## Reference style

The formatter follows the supplied reference examples, including leading commas in expanded collections and function arguments.

### Before

```python
df = spark.table('database.dbo.my_table').filter(F.col('system_id') == '123#').filter(F.col('dt') > '2026-06-01').select(F.col('system_id'), F.col('client_id'))
```

### After

```python
df = (
        spark.table('database.dbo.my_table')
             .filter(F.col('system_id') == '123#')
             .filter(F.col('dt') > '2026-06-01')
             .select(
                      F.col('system_id')
                      ,F.col('client_id')
                    )
     )
```

### Complex nested expression

```python
.withColumn(
    "risk_level",
    F.when(
        (F.col('score') >= 0.8)
        & (F.col('status') == 'ACTIVE'),
        "HIGH"
    ).otherwise("LOW")
)
```

### Collection formatting

```python
accounts = [
              "abc##"
              ,"dfo..."
              ,"12009c"
           ]
```

## Settings

All options are available under **Settings → Clean Python Code**:

| Setting | Default | Purpose |
| --- | ---: | --- |
| `outerIndent` | `8` | Base continuation indentation inside wrapped assignments |
| `chainIndent` | `5` | Additional indentation for chained calls |
| `argumentIndent` | `9` | Indentation for expanded call arguments and collections |
| `maxInlineLength` | `88` | Length above which expressions are preferentially expanded |
| `leadingComma` | `true` | Uses the reference style with leading commas |
| `expandBooleanOperators` | `true` | Expands complex boolean expressions |

## Supported files

- `.py`
- Python cells in `.ipynb` notebooks supported by VS Code/Jupyter

## Design principles

Clean Python Code intentionally does **not** attempt to replace Black, Ruff, autopep8 or import sorters. The formatter is opinionated about visual structure and is intended to complement normal Python tooling.

The formatter is designed to be idempotent: applying **Ctrl + I** repeatedly should not keep changing the result.

## Installation from VSIX

For local testing:

```bash
code --install-extension clean-python-code-0.3.0.vsix
```

Or use **Extensions → Views and More Actions (`...`) → Install from VSIX...**.

## Marketplace

Clean Python Code is published under the publisher associated with the extension manifest. The package uses the Marketplace extension id:

```text
cleanpythoncode.clean-python-code
```

Replace `cleanpythoncode` in `package.json` with your actual Marketplace Publisher ID before the first publication if you use a different publisher.

## Support

For bug reports and feature requests, open an issue in the project's public repository.
