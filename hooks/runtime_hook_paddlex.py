# PyInstaller runtime hook for paddlex
# This hook creates the .version file before paddlex is imported
# Must run BEFORE paddlex/__init__.py tries to read .version

import os
import sys


def ensure_paddlex_version():
    """Create the paddlex .version file if it doesn't exist."""
    version = '3.3.10'  # Will be updated by build script

    # Determine base path based on PyInstaller mode
    if hasattr(sys, '_MEIPASS'):
        # Running as PyInstaller bundle (both onefile and onedir)
        base_path = sys._MEIPASS
    else:
        # Running as normal Python script
        return  # Not needed when running normally

    paddlex_dir = os.path.join(base_path, 'paddlex')
    version_file = os.path.join(paddlex_dir, '.version')

    # Create directory if it doesn't exist
    try:
        os.makedirs(paddlex_dir, exist_ok=True)
    except Exception as e:
        print(f"Warning: Could not create paddlex directory: {e}")
        return

    # Create .version file if it doesn't exist
    if not os.path.exists(version_file):
        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(version)
            print(f"Runtime hook: Created {version_file} with version {version}")
        except Exception as e:
            print(f"Warning: Could not create .version file: {e}")
    else:
        print(f"Runtime hook: {version_file} already exists")


# Run immediately when this hook is loaded (before other imports)
ensure_paddlex_version()
