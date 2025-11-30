# PyInstaller runtime hook for paddlex
# This hook:
# 1. Creates the .version file before paddlex is imported
# 2. Patches the dependency checker to skip runtime checks
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


def patch_paddlex_dependency_check():
    """Patch paddlex to skip dependency checks in PyInstaller bundle."""
    if not hasattr(sys, '_MEIPASS'):
        return  # Only patch in PyInstaller bundle

    # Set environment variable to signal we're in a bundled app
    os.environ['PADDLEX_SKIP_DEPS_CHECK'] = '1'

    # Monkey-patch the require_extra function to do nothing
    try:
        import paddlex.utils.deps as deps_module

        def patched_require_extra(*args, **kwargs):
            """Patched version that does nothing - deps are bundled."""
            pass

        deps_module.require_extra = patched_require_extra
        print("Runtime hook: Patched paddlex dependency checker")
    except ImportError:
        # paddlex.utils.deps might not exist yet, we'll patch it later
        pass
    except Exception as e:
        print(f"Warning: Could not patch paddlex deps: {e}")


# Run immediately when this hook is loaded (before other imports)
ensure_paddlex_version()
patch_paddlex_dependency_check()
