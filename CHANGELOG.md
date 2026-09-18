# 0.6.2 — Fluent chain alignment

- Corrige o alinhamento de cadeias fluent API dentro de agrupamentos externos, incluindo `DatabricksSession.builder.getOrCreate()` e `spark.read.schema(...).option(...).csv(...)`.
- Os métodos encadeados passam a usar como âncora o início renderizado da expressão-base, evitando que o primeiro ponto da cadeia caia na coluna zero.
- Mantém equivalência AST, assinatura léxica e idempotência.
- Adiciona testes de regressão específicos para DatabricksSession e Spark reader chains.

# 0.6.1 ? Equa??es compactas e novo ?cone

- Nova op??o `arithmeticLayout`, com padr?o `auto`: equa??es curtas ficam compactas e as longas recebem quebras no n?vel principal.
- Modo `compact` desativa a expans?o for?ada da aritm?tica; modo `expanded` mant?m a pol?tica aritm?tica da 0.6.0.
- A aritm?tica passa a ser independente de `expandBooleanOperators`; filtros e condi??es mant?m a hierarquia anterior.
- O or?amento de largura vem da AST, evitando mudan?as de decis?o causadas por par?nteses acrescentados em uma formata??o anterior.
- F?rmulas curtas j? expandidas podem ser recolhidas sem remover seus par?nteses ou alterar a preced?ncia.
- ?cone substitu?do pelo PNG fornecido pelo usu?rio, preservado byte a byte.
- Regress?es espec?ficas para `equacoes.ipynb`, quocientes, produtos, pot?ncias, configura??es e limiares de largura.

# 0.6.0 — 2026-09-13

- Alinhamento dos pontos das cadeias pela primeira chamada, incluindo cadeias aninhadas.
- Alinhamento de todos os delimitadores expandidos pela coluna real de abertura; hierarquia padrão de dois espaços.
- Preservação de chamadas curtas e de listas de argumentos previamente expandidas.
- Planejamento estrutural até propagação completa das quebras entre filhos e pais, antes de renderizar.
- Parênteses de condições calculados por pares reais de tokens e posições UTF-8 da AST. Corrigidas inserções coincidentes e uso de posições de árvores anteriores a uma edição.
- Quebras para condições aninhadas e aritmética composta com preservação de precedência.
- Espaçamento dos dicionários determinado pela AST, sem afetar slices ou lambdas.
- Provedores de formatação de documento e seleção para arquivos Python e células de notebook, além do comando Ctrl+I.
- Suíte atual reutiliza os corpus históricos e acrescenta contratos visuais, 30 células em duas representações, Unicode, opções, equivalência sintática e idempotência.


## 0.5.6
- Improved recursive clause breaking inside `when(...)` boolean predicates.
- Exposes nested `&` and `|` clauses at their actual delimiter hierarchy.
- Preserves AST/token safety and idempotence.

## 0.5.4
- Fixed nested delimiter indentation for multiline calls and collections.
- Prevented source-line indentation from leaking into rendered token columns.
- Preserved RHS grouping such as `value = (...)` without breaking assignment syntax.
- Added recursive detection for collections nested inside PySpark calls such as `where(col(...).isin([...]))`.

# Changelog

## 0.5.2

- Fixed hierarchical delimiter layout for multiline calls containing nested collections.
- Multiline method/function calls now keep `name(` together while nested `{}`, `[]`, and `()` move to the next hierarchy level.
- Added an outer grouping level when needed so the call itself has a matching, vertically aligned `(` / `)`.
- Preserved AST/token equivalence and idempotent formatting guarantees.


## 0.5.1
- Added hierarchical vertical alignment for multiline `()`, `[]`, and `{}` pairs.
- Directly nested multiline delimiters now receive their own indentation level, including cases such as `([{}])`.
- Kept AST/token validation, PySpark chain formatting, boolean/filter/where handling, comment preservation, trailing-comma behavior, and idempotence safeguards from 0.5.0.

## 0.4.3 — 2026-09-11

- Format statements containing f-strings instead of skipping them on Python 3.12+.
- Group tokenizer-defined f-string spans as opaque literals, preserving their exact spelling, nested interpolation, debug whitespace, conversions and format specifications.
- Preserve multiline string contents while formatting the surrounding code. Interpolation expressions are not rewritten.
- Format statements with external trailing comments while keeping the comment attached to the same statement.
- Align return pipelines at one continuation level and expand starred comprehensions within vertical argument lists.
- Add the complete join fixture, seven Python string/layout test groups, 192 f-string combinations and a full-document bridge test.
- Preserve existing heatmap/rules snapshots, AST/token checks, idempotence and runtime safeguards.


## 0.4.2 — 2026-09-11

- Add AST-directed multiline layout for list/set/dict comprehensions and generators, including nested clauses, tuple/starred targets, filters and `async for`.
- Align repeated nested fluent methods to their first call's nesting level; retain top-level chain settings.
- Distinguish call-argument parentheses from outer expression wrappers, preventing top-level indentation inside nested arguments.
- Expand parent calls when an argument is multiline, including `.otherwise(F.array_union(...))`.
- Keep short predicate suffixes such as `.isin(...)` inline.
- Add the complete rules fixture, six new Python test groups, 114 expression/settings combinations and a full-document bridge test.
- Retain the reviewed heatmap output, existing settings, AST/token validation and idempotence checks.


## 0.4.1 — 2026-09-11

- Fix excessive argument indentation by using nesting levels instead of delimiter columns. Default `argumentIndent` is now 4; explicit user values remain respected.
- Align closing delimiters with the indentation of the opening line, including long assignment wrappers.
- Measure each chained method locally instead of counting every preceding operation; keep short `.where()`, `.select()` and `.distinct()` calls inline.
- Format internal comments in calls and collections while preserving their text, order and attachment. Use trailing separators for comment-bearing delimiters.
- Avoid unnecessary outer parentheses around collections and unnecessary breaks in short column predicates.
- Add six layout test groups, 63 comment/configuration cases, the complete user-supplied heatmap fixture, a reviewed output snapshot and a real bridge/document validation test.
- Retain AST/token equivalence, idempotence, cancellation and document-version checks.


## 0.4.0 — 2026-09-11

- Replace the handwritten JavaScript expression parser with a Python AST-directed formatter using standard-library `ast` and `tokenize`.
- Fix `or` inside identifiers (`color`, `cursor`), generator `for` clauses and string literals.
- Preserve operator precedence, tuple commas, argument order, literal spelling and Python block structure.
- Verify AST equivalence and token preservation before returning any edit, and verify idempotence on every request.
- Validate the complete Python document around a selection; reject incomplete or unsupported syntax without editing it.
- Preserve statements containing comments, multiline string tokens and Python 3.12+ f-string tokens verbatim. Keep structural headers and inline suites intact.
- Make the formatting bridge asynchronous, cancellable and bounded by a timeout; refuse edits after document changes.
- Honor indentation settings consistently; `argumentIndent` now defaults to 3, matching the old call renderer's hardcoded three-space offset. Explicit user values are respected.
- Add `cleanPythonCode.pythonPath`, selected Python environment discovery, workspace trust support and UTF-16 offset handling.
- Require Python 3.9+ on the extension host; newer syntax requires a compatible interpreter. No pip dependencies.
- Include regression tests, generated cases, host integration tests, validation notes and an offline VSIX packaging script.

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
