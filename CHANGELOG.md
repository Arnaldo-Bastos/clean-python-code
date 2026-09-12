## 0.3.12

- Added notebook fixture coverage for `sample_cases.ipynb` style selections and code-cell formatting assertions.
- Added explicit test coverage for multiline `where` boolean conditions with aligned `&` and `|` operators.
- Added a Python `ast` safety guard: when the original selected code is valid Python, the formatter now avoids returning a result that would become syntactically invalid.

## 0.3.10

- Fixed VSIX deployment manifest namespace for Marketplace publication.

## 0.3.9

- Aligns all subsequent chain-operation dots with the first member-access dot in the base expression, preserving previously correct patterns such as `df.groupBy(...).agg(...).show()` while keeping `spark.table(...).filter(...)` aligned.

## 0.3.8

- Keep terminal modifiers such as `.alias()`, `.cast()`, `.otherwise()` and `.over()` attached to the preceding expression.
- Treat `SparkSession.builder`, `SparkSession.read` and `SparkSession.write` as fluent chain boundaries so subsequent calls align vertically.
- Preserve member access such as `df[col].value_counts().index` without spaces around `.`.
- Strengthen nested delimiter alignment for calls, lists, tuples and dictionaries.

## 0.3.7

- Fixed member-access formatting so chained expressions such as `df[col].value_counts().index` never receive spaces around `.`.

## 0.3.6

- Keeps the first method operation on the same line as its object when the expression is inside a call argument.
- Improved vertical alignment of chained method dots in indented Python blocks.
- Improved nested delimiter alignment with matching opening/closing columns.
- Refined indentation offsets for nested lists, dictionaries, and parenthesized expressions based on nesting level.

## 0.3.5

- Improved nested delimiter alignment for parentheses, brackets, and braces.
- Preserves the first operation on the same line as an object when it is inside a call argument.
- Aligns chained method dots vertically.
- Aligns matching opening and closing delimiters at the same column.
- Improved nested call formatting for structures such as StructType, DataFrame and np.hstack.

## 0.3.4

- Reworked the formatter around the supplied CORRETO examples.
- Added support for standalone chained expressions and wrapper calls.
- Improved recursive formatting of lists, tuples, dictionaries, nested calls and keyword arguments.
- Preserved Python block indentation for for/def/if/try/with structures.
- Improved handling of multiline notebook selections and idempotent reformatting.

## 0.3.3

- Updated the extension icon.

# Changelog

## 0.3.2

- Updated the Marketplace Overview reference example with generic database/table and column names.
- No formatter behavior changes.

## 0.3.1

- Fixed Marketplace license packaging by including `LICENSE.txt` in the VSIX.

## 0.3.0

- Marketplace-ready package with documentation, support information, icon and publishing metadata.
