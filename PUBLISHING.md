# Publishing checklist

1. Create or use a Visual Studio Marketplace Publisher.
2. Set the Publisher ID in `package.json` and `extension.vsixmanifest` to the exact Publisher ID you own.
3. If the Publisher ID is `cleanpythoncode`, no change is required.
4. Run `node test/formatter.test.js`.
5. Install the VSIX locally and test `.py` and `.ipynb` selections.
6. Publish with the current official `vsce` workflow or upload the VSIX from the Publisher management page.

The Marketplace identifier is `<publisher-id>.clean-python-code`.
