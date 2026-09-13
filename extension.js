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

function activate(context) {
  async function provideEdits(document, range, token) {
    if (!vscode.workspace.isTrusted) return [];
    const config = vscode.workspace.getConfiguration('cleanPythonCode', document.uri);
    const options = {};
    for (const key of ['outerIndent', 'chainIndent', 'argumentIndent', 'maxInlineLength', 'leadingComma', 'expandBooleanOperators', 'arithmeticLayout']) {
      options[key] = config.get(key);
    }
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
      if (!token.isCancellationRequested) vscode.window.showWarningMessage(`Clean Python Code: ${error.message} Original code preserved.`);
      return [];
    }
  }
  const selector = [{ language: 'python', scheme: 'file' }, { language: 'python', scheme: 'untitled' },
    { language: 'python', scheme: 'vscode-notebook-cell' }, { language: 'python', scheme: 'vscode-remote' }];
  context.subscriptions.push(vscode.languages.registerDocumentFormattingEditProvider(selector, {
    provideDocumentFormattingEdits(document, _options, token) {
      return provideEdits(document, new vscode.Range(document.positionAt(0), document.positionAt(document.getText().length)), token);
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
    const editor = vscode.window.activeTextEditor;
    if (!editor) return;
    if (!vscode.workspace.isTrusted) {
      vscode.window.showWarningMessage('Clean Python Code requires a trusted workspace to start Python.');
      return;
    }
    if (editor.selection.isEmpty) {
      vscode.window.showInformationMessage('Clean Python Code: select the code you want to format first.');
      return;
    }
    const document = editor.document;
    if (document.languageId !== 'python') {
      vscode.window.showWarningMessage('Clean Python Code formats Python selections, including Python notebook cells.');
      return;
    }
    let range = new vscode.Range(editor.selection.start, editor.selection.end);
    // Include the indentation if selection begins at the first code character.
    if (!document.lineAt(range.start.line).text.slice(0, range.start.character).trim()) {
      range = new vscode.Range(new vscode.Position(range.start.line, 0), range.end);
    }
    const config = vscode.workspace.getConfiguration('cleanPythonCode', document.uri);
    const options = {};
    for (const key of ['outerIndent', 'chainIndent', 'argumentIndent', 'maxInlineLength', 'leadingComma', 'expandBooleanOperators', 'arithmeticLayout']) {
      options[key] = config.get(key);
    }
    const version = document.version;
    const original = document.getText(range);
    const entireDocument = document.getText();
    try {
      const pythonPath = await interpreter(document, config);
      const formatted = await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification, title: 'Clean Python Code: formatting', cancellable: true
      }, (_progress, token) => formatSelection(original, options, {
        pythonPath, token, document: entireDocument,
        start: document.offsetAt(range.start), end: document.offsetAt(range.end)
      }));
      if (formatted === original) return;
      if (document.isClosed || document.version !== version) {
        vscode.window.showWarningMessage('Clean Python Code: document changed during formatting. Please try again.');
        return;
      }
      const applied = await editor.edit(builder => builder.replace(range, formatted));
      if (!applied) vscode.window.showWarningMessage('Clean Python Code: edit was not applied. Please try again.');
    } catch (error) {
      vscode.window.showWarningMessage(`Clean Python Code: ${error.message} Original code preserved.`);
    }
  });
  context.subscriptions.push(command);
}
function deactivate() {}
module.exports = { activate, deactivate };
