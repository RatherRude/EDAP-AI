# PyInstaller hook for paddlex
# This ensures all paddlex dependencies and data files are collected

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect all paddlex components
datas, binaries, hiddenimports = collect_all('paddlex')

# Explicitly include the utils.deps module so we can patch it
hiddenimports += [
    'paddlex.utils',
    'paddlex.utils.deps',
    'paddlex.inference',
    'paddlex.inference.pipelines',
    'paddlex.inference.pipelines.ocr',
    'paddlex.modules',
]

# Collect submodules that might be dynamically imported
hiddenimports += collect_submodules('paddlex.inference')
hiddenimports += collect_submodules('paddlex.modules')

