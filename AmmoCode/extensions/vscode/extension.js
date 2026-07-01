const vscode = require("vscode");
const path = require("path");

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand("ammocode.open", () => {
      const panel = vscode.window.createWebviewPanel(
        "ammocode",
        "AmmoCode",
        vscode.ViewColumn.One,
        { enableScripts: true, retainContextWhenHidden: true },
      );
      const root = path.join(context.extensionPath, "..", "..");
      panel.webview.html = `<!DOCTYPE html><html><head><meta charset="UTF-8" />
        <link rel="stylesheet" href="${panel.webview.asWebviewUri(vscode.Uri.file(path.join(root, "assets/syntax.css")))}" />
        <link rel="stylesheet" href="${panel.webview.asWebviewUri(vscode.Uri.file(path.join(root, "assets/editor.css")))}" />
        </head><body class="ac"><p>Open AmmoCode standalone at file://${root}/index.html</p></body></html>`;
    }),
  );
}

function deactivate() {}

module.exports = { activate, deactivate };