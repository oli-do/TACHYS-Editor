import os
import sys
import PyInstaller.__main__

BASE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'src')
sep = os.pathsep

args = [
    os.path.join(BASE_DIR, 'main.py'),
    '--name=TACHYS Editor',
    '--onedir',
    '--noconsole',
    f'--add-data={os.path.join(BASE_DIR, "tachys_editor", "resources")}{sep}{os.path.join("tachys_editor", "resources")}',
    '--hidden-import=sklearn.pipeline',
    '--hidden-import=sklearn.neighbors',
    '--hidden-import=sklearn.feature_extraction.text',
]

if sys.platform == 'win32':
    ico_path = os.path.join(BASE_DIR, 'tachys_editor', 'resources', 'logo.ico')
    version_path = 'file_version_info.txt'
    if os.path.exists(ico_path):
        args.append(f'--icon={ico_path}')
    if os.path.exists(version_path):
        args.append(f'--version-file={version_path}')

elif sys.platform == 'darwin':
    icns_path = os.path.join(BASE_DIR, 'tachys_editor', 'resources', 'logo.icns')
    if os.path.exists(icns_path):
        args.append(f'--icon={icns_path}')

elif sys.platform == 'linux':
    png_path = os.path.join(BASE_DIR, 'tachys_editor', 'resources', 'logo.png')
    if os.path.exists(png_path):
        args.append(f'--icon={png_path}')

if __name__ == '__main__':
    PyInstaller.__main__.run(args)
    spec_file = "TACHYS Editor.spec"
    if os.path.exists(spec_file):
        os.remove(spec_file)