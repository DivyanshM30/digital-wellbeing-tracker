# Build from the repository root with the project's Python environment.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'main.py')], pathex=[str(root)],
    datas=collect_data_files('sv_ttk'),
    hiddenimports=collect_submodules('pyttsx3.drivers') + [
        'plyer.platforms.win.notification', 'pystray._win32',
        'sklearn.utils._cython_blas', 'win32timezone',
    ],
    hookspath=[], hooksconfig={'matplotlib': {'backends': ['TkAgg']}},
    excludes=['IPython', 'pytest', 'tk'], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True,
          name='DigitalWellbeingTracker', console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas,
               name='DigitalWellbeingTracker', upx=False)
