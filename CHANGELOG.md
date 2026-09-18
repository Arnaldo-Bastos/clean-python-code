# 0.6.9 — Reviewed screenshot layout + Python-notebook language fallback

- Matches the three reviewed reference screenshots: the first fluent segment stays inline (`spark.read`, `DatabricksSession.builder`, `df_ai_requests.drop(...)`) and later segments align to the first dot.
- Restores rendered-delimiter-relative defaults: `outerIndent=2`, `argumentIndent=2`, `chainIndent=0`.
- Matching multiline closers remain aligned to their rendered opening delimiter.
- Keeps dictionary normalization: one mapping per line, trailing commas, and standard `key: value` spacing.
- Accepts notebook code cells when notebook kernel/language metadata says Python even if VS Code persisted the individual cell as another `languageId` such as `javascript`.
- After successful Python parsing/formatting, attempts to switch a misclassified notebook code cell back to the VS Code `python` language mode.
- Keeps safe Unicode-whitespace sanitization and the `Ctrl + Alt + Shift + F` shortcut.
- Adds exact regressions for the three reviewed notebook cells.

# 0.6.8 — Reliable notebook targeting and conflict-free shortcut

- Changes the default shortcut to `Ctrl + Alt + Shift + F`, avoiding the VS Code/Copilot chat shortcuts `Ctrl + I` and `Ctrl + Alt + I`.
- The shortcut is no longer gated by `editorHasSelection`, `editorLangId`, or editor-focus context keys; the command resolves the active Python target itself.
- If text is selected, the selection is formatted. If no text is selected, the active Python document or notebook cell is formatted in full.
- When a notebook has focus but no active text editor, the active Python cell is resolved directly and edited through a `WorkspaceEdit`.
- Adds a `Clean Python Code` output channel and an `Open Log` action for targeting or formatter failures.
- Keeps the 0.6.7 formatter engine unchanged, including safe Unicode-whitespace sanitization.

# 0.6.7 — Safe Unicode whitespace sanitization

- Normalizes non-ASCII Unicode whitespace such as U+00A0 NO-BREAK SPACE when it appears in Python code.
- Sanitization runs before AST parsing, allowing code copied from browsers, chat clients and rich-text sources to be formatted instead of rejected as an invalid non-printable character.
- String literals and comments are protected and keep their original Unicode whitespace unchanged.
- Document-level safety validation uses the same sanitizer, so notebook selections containing problematic whitespace can still be validated after formatting.
- Adds regression tests for U+00A0, U+2003, U+2007 and U+202F plus idempotence and literal/comment preservation.

# 0.6.6 — Shortcut conflict fix

- Changes the default **Clean Python Code: Format Selection** shortcut from `Ctrl + I` to `Ctrl + Alt + I`.
- Avoids the default VS Code / Copilot Inline Chat conflict while keeping the formatter command identifier unchanged.
- Existing users can still assign any custom shortcut through VS Code Keyboard Shortcuts.

# 0.6.5 — Definitive chain and delimiter alignment

- Outer assignment groups keep a short structural content indent, independent of assignment-name length.
- Fluent pipelines split the base expression from every visible chain segment; attribute-only segments such as `.read` and `.builder` participate in the same dot axis.
- All visible `.` tokens in a fluent chain share one vertical column.
- Every multiline `()`, `[]`, and `{}` pair closes at the exact rendered column of its own opener.
- Nested contents use `argumentIndent` relative to the actual rendered opener column, while only outer-group contents use structural indentation.
- Dictionary entries remain one-per-line with trailing commas and standard `key: value` spacing.
- Adds invariant tests for AST/token preservation, idempotence, chain-dot alignment, and delimiter-column alignment.

# 0.6.4 — Structural pipelines and normalized mappings

- Multiline calls and collections inside outer pipelines now use structural indentation instead of the exact horizontal column of their opening delimiter.
- Call arguments and collection contents default to four spaces beyond their structural line; matching closers return to the call/collection indentation.
- Fluent methods are forced vertical even when the input writes them on the same physical line.
- Multiline dictionaries use one key/value mapping per line, with trailing commas and standard `key: value` spacing.
- Adds a regression case based on the full `df_ai_requests` / `withColumnsRenamed` example.

# 0.6.3 — Structural outer-group indentation

- Top-level assignment/return grouping parentheses now behave as structural blocks: their contents are indented from the statement indentation instead of the rendered column of a long opening parenthesis.
- The closing parenthesis of an outer expression group returns to the statement indentation, preventing long variable names from shifting entire PySpark pipelines to the right.
- Nested call/collection delimiters keep their rendered-column hierarchy, so internal alignment rules remain unchanged.
- `outerIndent` now defaults to 4 spaces and represents the indentation of content inside an outer expression group relative to the statement indentation.
- Adds regression coverage for long assignment names and Spark reader chains.

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
