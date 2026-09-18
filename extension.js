'use strict';
const vscode = require('vscode');
const { formatSelection } = require('./formatter');

async function interpreter(document, config) {
  const explicit = config.get('pythonPath', '').trim();
  if (explicit) return explicit;
  const python = vscode.extensions.getExtension('ms-python.python');
  if (python) {
    try {
      const api = python.isActive ? python.exports : await python.activate();
      if (api.environments) {
        const selected = api.environments.getActiveEnvironmentPath(document.uri);
        const resolved = await api.environments.resolveEnvironment(selected);
        if (resolved && resolved.executable && resolved.executable.uri) return resolved.executable.uri.fsPath;
      }
    } catch (_) { /* Fall back to Python on PATH. */ }
  }
  return undefined;
}

function fullDocumentRange(document) {
  return new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length));
}

function activePythonTarget() {
  const editor = vscode.window.activeTextEditor;
  if (editor && editor.document && editor.document.languageId === 'python') {
    const document = editor.document;
    let range = editor.selection.isEmpty
      ? fullDocumentRange(document)
      : new vscode.Range(editor.selection.start, editor.selection.end);
    if (!editor.selection.isEmpty && !document.lineAt(range.start.line).text.slice(0, range.start.character).trim()) {
      range = new vscode.Range(new vscode.Position(range.start.line, 0), range.end);
    }
    return { document, range, editor, source: editor.selection.isEmpty ? 'active Python document/cell' : 'text selection' };
  }

  const notebookEditor = vscode.window.activeNotebookEditor;
  if (notebookEditor && notebookEditor.notebook && notebookEditor.notebook.cellCount > 0) {
    const selection = notebookEditor.selection;
    const index = Math.min(selection ? selection.start : 0, notebookEditor.notebook.cellCount - 1);
    const cell = notebookEditor.notebook.cellAt(index);
    if (cell && cell.document && cell.document.languageId === 'python') {
      return {
        document: cell.document,
        range: fullDocumentRange(cell.document),
        editor: undefined,
        source: `active notebook cell ${index + 1}`
      };
    }
  }
  return undefined;
}

function activate(context) {
  const output = vscode.window.createOutputChannel('Clean Python Code');
  context.subscriptions.push(output);

  function optionsFor(document) {
    const config = vscode.workspace.getConfiguration('cleanPythonCode', document.uri);
    const options = {};
    for (const key of ['outerIndent', 'chainIndent', 'argumentIndent', 'maxInlineLength', 'leadingComma', 'expandBooleanOperators', 'arithmeticLayout']) {
      options[key] = config.get(key);
    }
    return { config, options };
  }

  async function formatTarget(document, range, editor, token) {
    if (!vscode.workspace.isTrusted) throw new Error('A trusted workspace is required to start Python.');
    if (document.languageId !== 'python') throw new Error(`Active language is ${document.languageId || 'unknown'}, not Python.`);

    const { config, options } = optionsFor(document);
    const original = document.getText(range);
    const version = document.version;
    const pythonPath = await interpreter(document, config);
    const formatted = await formatSelection(original, options, {
      pythonPath,
      token,
      document: document.getText(),
      start: document.offsetAt(range.start),
      end: document.offsetAt(range.end)
    });

    if (token && token.isCancellationRequested) return false;
    if (document.isClosed || document.version !== version) throw new Error('Document changed during formatting. Please try again.');
    if (formatted === original) return true;

    if (editor && editor.document.uri.toString() === document.uri.toString()) {
      const applied = await editor.edit(builder => builder.replace(range, formatted));
      if (!applied) throw new Error('The editor rejected the formatting edit.');
      return true;
    }

    const edit = new vscode.WorkspaceEdit();
    edit.replace(document.uri, range, formatted);
    const applied = await vscode.workspace.applyEdit(edit);
    if (!applied) throw new Error('VS Code rejected the notebook-cell formatting edit.');
    return true;
  }

  async function provideEdits(document, range, token) {
    if (!vscode.workspace.isTrusted) return [];
    const { config, options } = optionsFor(document);
    const original = document.getText(range);
    const version = document.version;
    try {
      const formatted = await formatSelection(original, options, {
        pythonPath: await interpreter(document, config), token,
        document: document.getText(), start: document.offsetAt(range.start), end: document.offsetAt(range.end)
      });
      if (document.isClosed || version !== document.version || token.isCancellationRequested || formatted === original) return [];
      return [vscode.TextEdit.replace(range, formatted)];
    } catch (error) {
      output.appendLine(`[provider] ${error && error.stack ? error.stack : error}`);
      if (!token.isCancellationRequested) vscode.window.showWarningMessage(`Clean Python Code: ${error.message} Original code preserved.`);
      return [];
    }
  }

  const selector = [
    { language: 'python', scheme: 'file' },
    { language: 'python', scheme: 'untitled' },
    { language: 'python', scheme: 'vscode-notebook-cell' },
    { language: 'python', scheme: 'vscode-remote' }
  ];

  context.subscriptions.push(vscode.languages.registerDocumentFormattingEditProvider(selector, {
    provideDocumentFormattingEdits(document, _options, token) {
      return provideEdits(document, fullDocumentRange(document), token);
    }
  }));

  context.subscriptions.push(vscode.languages.registerDocumentRangeFormattingEditProvider(selector, {
    provideDocumentRangeFormattingEdits(document, range, _options, token) {
      if (!document.lineAt(range.start.line).text.slice(0, range.start.character).trim()) {
        range = new vscode.Range(new vscode.Position(range.start.line, 0), range.end);
      }
      return provideEdits(document, range, token);
    }
  }));

  const command = vscode.commands.registerCommand('cleanPythonCode.formatSelection', async () => {
    const target = activePythonTarget();
    if (!target) {
      output.appendLine('[command] No active Python text editor or Python notebook cell was found.');
      const action = await vscode.window.showWarningMessage(
        'Clean Python Code: no active Python editor/cell found. Click inside a Python cell and try Ctrl+Alt+Shift+F again.',
        'Open Log'
      );
      if (action === 'Open Log') output.show(true);
      return;
    }

    output.appendLine(`[command] Formatting ${target.source}; language=${target.document.languageId}; scheme=${target.document.uri.scheme}; chars=${target.document.getText(target.range).length}`);
    try {
      await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Clean Python Code: formatting ${target.source}`,
        cancellable: true
      }, (_progress, token) => formatTarget(target.document, target.range, target.editor, token));
      output.appendLine('[command] Formatting completed successfully.');
    } catch (error) {
      output.appendLine(`[command] ${error && error.stack ? error.stack : error}`);
      const action = await vscode.window.showWarningMessage(
        `Clean Python Code: ${error.message} Original code preserved.`,
        'Open Log'
      );
      if (action === 'Open Log') output.show(true);
    }
  });
  context.subscriptions.push(command);
}

function deactivate() {}
module.exports = { activate, deactivate };
