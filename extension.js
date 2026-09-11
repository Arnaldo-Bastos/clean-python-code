const vscode = require('vscode');
const { formatSelection } = require('./formatter');

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
    if (document.languageId !== 'python') {
      vscode.window.showWarningMessage('Clean Python Code currently formats Python selections, including Python cells in .ipynb notebooks.');
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
    const formatted = formatSelection(original, options);
    if (formatted === original) {
      return;
    }

    await editor.edit(editBuilder => editBuilder.replace(selection, formatted));
  });

  context.subscriptions.push(command);
}

function deactivate() {}

module.exports = { activate, deactivate };
