const vscode = require('vscode');
const { formatNotebookContent, formatSelection } = require('./formatter');

function activate(context) {
  const command = vscode.commands.registerCommand('cleanPythonCode.formatSelection', async () => {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return;
    }

    const selection = editor.selection;
    if (selection.isEmpty) {
      vscode.window.showInformationMessage('Clean Python Code: select the code you want to format first.');
      return;
    }

    const document = editor.document;
    const isPython = document.languageId === 'python';
    const isNotebookJson = document.fileName.endsWith('.ipynb') && ['json', 'jsonc'].includes(document.languageId);

    if (!isPython && !isNotebookJson) {
      vscode.window.showWarningMessage('Clean Python Code currently formats Python selections and raw .ipynb notebook JSON content.');
      return;
    }

    const config = vscode.workspace.getConfiguration('cleanPythonCode');
    const options = {
      outerIndent: config.get('outerIndent', 8),
      chainIndent: config.get('chainIndent', 5),
      argumentIndent: config.get('argumentIndent', 9),
      maxInlineLength: config.get('maxInlineLength', 88),
      leadingComma: config.get('leadingComma', true),
      expandBooleanOperators: config.get('expandBooleanOperators', true)
    };

    const original = document.getText(selection);
    const formatted = isNotebookJson
      ? formatNotebookContent(original, options)
      : formatSelection(original, options);
    if (formatted === original) {
      return;
    }

    await editor.edit(editBuilder => editBuilder.replace(selection, formatted));
  });

  context.subscriptions.push(command);
}

function deactivate() {}

module.exports = { activate, deactivate };
