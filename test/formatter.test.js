'use strict';

const assert = require('assert');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');
const { formatNotebookContent, formatSelection } = require('../formatter');

const tests = [];

function test(name, fn) {
  tests.push({ name, fn });
}

test('preserves python return statements while formatting chained expressions', () => {
  const input = "def fn(x):\n    return spark.table('t').where((F.col('a') == 1) | (F.col('b') == 2))";
  const expected = "def fn(x):\n    return (\n            spark.table('t')\n                 .where(\n                          (F.col('a') == 1)\n                          | (F.col('b') == 2)\n                       )\n           )";

  assert.strictEqual(formatSelection(input), expected);
});

test('breaks multi-condition filter calls onto aligned boolean lines', () => {
  const input = "df.filter((F.col('a') == 1) & (F.col('b') == 2) & (F.col('c') == 3))";
  const expected = "df.filter(\n           (F.col('a') == 1)\n           & (F.col('b') == 2)\n           & (F.col('c') == 3)\n         )";

  assert.strictEqual(formatSelection(input), expected);
});

test('expands nested collections vertically instead of collapsing delimiters', () => {
  const input = 'value = ([{}])';
  const expected = "value = (\n          [\n            {\n            }\n          ]\n        )";

  assert.strictEqual(formatSelection(input), expected);
});

test('keeps structural keywords intact while formatting nested calls inside blocks', () => {
  const input = "if ready:\n    result = foo(bar, baz)";
  const output = formatSelection(input);

  assert.ok(output.startsWith('if ready:\n'));
  assert.ok(!output.includes('\n('));
  assert.ok(output.includes("    result = foo("));
});

test('expands where conditions with aligned operators and parenthesized predicates', () => {
  const input = "df.where((F.col('a')==1) & (F.col('b')==2) | (F.col('c')==3))";
  const expected = "df.where(\n          (F.col('a')==1)\n          & (F.col('b')==2)\n          | (F.col('c')==3)\n        )";

  assert.strictEqual(formatSelection(input), expected);
});

test('keeps output parseable with Python AST when input is valid code', () => {
  const input = "def fn(values):\n    return [v for v in values if v > 0]";
  const output = formatSelection(input);

  let parsed = false;
  for (const bin of ['python3', 'python']) {
    try {
      childProcess.execFileSync(bin, ['-c', 'import ast,sys;ast.parse(sys.stdin.read())'], {
        input: output,
        encoding: 'utf8'
      });
      parsed = true;
      break;
    } catch {
      continue;
    }
  }

  assert.ok(parsed, 'formatted output should parse with Python AST');
});

test('formats code cells in notebook JSON without touching markdown cells', () => {
  const fixturePath = path.join(__dirname, 'fixtures', 'sample_cases.ipynb');
  const original = fs.readFileSync(fixturePath, 'utf8');
  const formatted = formatNotebookContent(original);
  const notebook = JSON.parse(formatted);

  assert.strictEqual(notebook.cells[0].cell_type, 'markdown');
  assert.deepStrictEqual(notebook.cells[0].source, ['# Sample cases\n', 'Do not modify this markdown cell.\n']);

  const firstCodeCell = Array.isArray(notebook.cells[1].source)
    ? notebook.cells[1].source.join('')
    : notebook.cells[1].source;
  const secondCodeCell = Array.isArray(notebook.cells[2].source)
    ? notebook.cells[2].source.join('')
    : notebook.cells[2].source;

  assert.ok(firstCodeCell.includes("return (\n"));
  assert.ok(secondCodeCell.includes("& (F.col('b') == 2)\n"));
  assert.ok(secondCodeCell.includes("| (F.col('c') == 3)\n"));
});

test('surfaces invalid notebook json instead of silently no-oping', () => {
  assert.throws(
    () => formatNotebookContent('{not valid json'),
    /could not parse the selected \.ipynb content as notebook JSON/i
  );
});

let failures = 0;
for (const { name, fn } of tests) {
  try {
    fn();
    console.log(`✓ ${name}`);
  } catch (error) {
    failures += 1;
    console.error(`✗ ${name}`);
    console.error(error.stack || error.message || String(error));
  }
}

if (failures > 0) {
  process.exitCode = 1;
} else {
  console.log(`\n${tests.length} tests passed.`);
}
