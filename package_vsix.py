"""Build a dependency-free VSIX from this extracted extension directory."""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
FILES = ['package.json', 'extension.js', 'formatter.js', 'formatter.py', 'icon.png',
         'README.md', 'CHANGELOG.md', 'LICENSE.txt', 'SUPPORT.md']


def build(output):
    package = json.loads((ROOT / 'package.json').read_text())
    ns = 'http://schemas.microsoft.com/developer/vsx-schema/2011'
    ET.register_namespace('', ns)
    tag = lambda name: '{' + ns + '}' + name
    manifest = ET.Element(tag('PackageManifest'), {'Version': '2.0.0'})
    metadata = ET.SubElement(manifest, tag('Metadata'))
    ET.SubElement(metadata, tag('Identity'), {'Language': 'en-US', 'Id': package['name'],
                                          'Version': package['version'], 'Publisher': package['publisher']})
    for key, value in [('DisplayName', package['displayName']), ('Description', package['description']),
                       ('Tags', ','.join(package['keywords'])), ('Categories', ', '.join(package['categories'])),
                       ('GalleryFlags', 'Public')]:
        ET.SubElement(metadata, tag(key)).text = value
    props = ET.SubElement(metadata, tag('Properties'))
    for key, value in [('Microsoft.VisualStudio.Code.Engine', package['engines']['vscode']),
                       ('Microsoft.VisualStudio.Services.Content.Types', 'Microsoft.VisualStudio.Code'),
                       ('Microsoft.VisualStudio.Services.Content.Pricing', 'Free')]:
        ET.SubElement(props, tag('Property'), {'Id': key, 'Value': value})
    ET.SubElement(metadata, tag('Icon')).text = 'extension/icon.png'
    ET.SubElement(metadata, tag('License')).text = 'extension/LICENSE.txt'
    installation = ET.SubElement(manifest, tag('Installation'))
    ET.SubElement(installation, tag('InstallationTarget'), {'Id': 'Microsoft.VisualStudio.Code'})
    ET.SubElement(manifest, tag('Dependencies'))
    assets = ET.SubElement(manifest, tag('Assets'))
    for kind, name in [('Microsoft.VisualStudio.Code.Manifest', 'package.json'),
                       ('Microsoft.VisualStudio.Services.Content.Details', 'README.md'),
                       ('Microsoft.VisualStudio.Services.Content.Changelog', 'CHANGELOG.md'),
                       ('Microsoft.VisualStudio.Services.Content.License', 'LICENSE.txt'),
                       ('Microsoft.VisualStudio.Services.Icons.Default', 'icon.png')]:
        ET.SubElement(assets, tag('Asset'), {'Type': kind, 'Path': 'extension/' + name, 'Addressable': 'true'})
    types_ns = 'http://schemas.openxmlformats.org/package/2006/content-types'
    types = ET.Element('Types', {'xmlns': types_ns})
    for extension, mime in [('json', 'application/json'), ('js', 'application/javascript'), ('py', 'text/x-python'),
                            ('md', 'text/markdown'), ('txt', 'text/plain'), ('png', 'image/png'), ('vsixmanifest', 'text/xml')]:
        ET.SubElement(types, 'Default', {'Extension': extension, 'ContentType': mime})
    entries = {'extension.vsixmanifest': ET.tostring(manifest, encoding='utf-8', xml_declaration=True),
               '[Content_Types].xml': ET.tostring(types, encoding='utf-8', xml_declaration=True)}
    entries.update({'extension/' + name: (ROOT / name).read_bytes() for name in FILES})
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(entries.items()):
            info = ZipInfo(name, date_time=(2026, 9, 13, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with ZipFile(output) as archive:
        assert archive.testzip() is None
        identity = ET.fromstring(archive.read('extension.vsixmanifest')).find('.//' + tag('Identity'))
        assert identity.attrib['Version'] == package['version']
        assert identity.attrib['Publisher'] == package['publisher']
        assert identity.attrib['Id'] == package['name']
        assert set(entries) == set(archive.namelist())
    print(str(output.resolve()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT.parent / ('clean-python-code-' + json.loads((ROOT / 'package.json').read_text())['version'] + '.vsix'))
    build(parser.parse_args().output)
