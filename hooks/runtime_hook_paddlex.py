# PyInstaller runtime hook for paddlex
# This hook MUST run BEFORE paddlex is imported anywhere
#
# Strategy:
# 1. Inject a fake paddlex.utils.deps module into sys.modules BEFORE paddlex loads
# 2. Create the .version file for paddlex
# 3. Set environment variables to signal we're in a bundled app
#
# This prevents the DependencyError: `OCR` requires additional dependencies

import os
import sys
import types


def inject_fake_deps_module():
    """
    Inject a fake paddlex.utils.deps module that does nothing.
    This MUST happen before any paddlex import.
    """
    if not hasattr(sys, '_MEIPASS'):
        return  # Only needed in PyInstaller bundle

    # Create a fake module with all the functions that paddlex.utils.deps provides
    fake_deps = types.ModuleType('paddlex.utils.deps')

    # Define no-op functions for all dependency-related functions
    def require_extra(*args, **kwargs):
        """No-op: Dependencies are bundled."""
        pass

    def check_deps(*args, **kwargs):
        """No-op: Dependencies are bundled."""
        pass

    def is_dep_available(*args, **kwargs):
        """Always return True: Dependencies are bundled."""
        return True

    def ensure_deps(*args, **kwargs):
        """No-op: Dependencies are bundled."""
        pass

    # A fake DependencyError that never gets raised
    class DependencyError(Exception):
        pass

    # Attach all functions/classes to the fake module
    fake_deps.require_extra = require_extra
    fake_deps.check_deps = check_deps
    fake_deps.is_dep_available = is_dep_available
    fake_deps.ensure_deps = ensure_deps
    fake_deps.DependencyError = DependencyError

    # Inject parent modules first (required for sub-module injection)
    if 'paddlex' not in sys.modules:
        fake_paddlex = types.ModuleType('paddlex')
        fake_paddlex.__path__ = []  # Make it a package
        sys.modules['paddlex'] = fake_paddlex

    if 'paddlex.utils' not in sys.modules:
        fake_utils = types.ModuleType('paddlex.utils')
        fake_utils.__path__ = []  # Make it a package
        sys.modules['paddlex.utils'] = fake_utils
        # Attach to parent
        sys.modules['paddlex'].utils = fake_utils

    # Inject the fake deps module
    sys.modules['paddlex.utils.deps'] = fake_deps
    sys.modules['paddlex.utils'].deps = fake_deps

    print("Runtime hook: Injected fake paddlex.utils.deps module")


def setup_import_hook():
    """
    Set up an import hook that patches paddlex.utils.deps when it's actually loaded.
    This is a backup in case the fake module gets overwritten.
    """
    if not hasattr(sys, '_MEIPASS'):
        return

    class PaddlexDepsImportHook:
        """
        Import hook that patches paddlex.utils.deps after it loads.
        """
        def find_module(self, fullname, path=None):
            if fullname == 'paddlex.utils.deps':
                return self
            return None

        def load_module(self, fullname):
            # If already in sys.modules, return it
            if fullname in sys.modules:
                return sys.modules[fullname]

            # Remove this finder temporarily to allow normal import
            sys.meta_path.remove(self)
            try:
                import importlib
                module = importlib.import_module(fullname)

                # Patch the module
                def patched_require_extra(*args, **kwargs):
                    pass

                module.require_extra = patched_require_extra

                # Also patch check_deps if it exists
                if hasattr(module, 'check_deps'):
                    module.check_deps = lambda *a, **kw: None
                if hasattr(module, 'is_dep_available'):
                    module.is_dep_available = lambda *a, **kw: True

                print(f"Runtime hook: Patched {fullname} after real import")
                return module
            except ImportError:
                # If import fails, return our fake module
                inject_fake_deps_module()
                return sys.modules.get(fullname)
            finally:
                # Re-add this finder
                if self not in sys.meta_path:
                    sys.meta_path.insert(0, self)

    # Install the import hook
    sys.meta_path.insert(0, PaddlexDepsImportHook())
    print("Runtime hook: Installed paddlex import hook")


def ensure_paddlex_version():
    """Create the paddlex .version file if it doesn't exist."""
    version = '3.3.10'  # Will be updated by build script

    if not hasattr(sys, '_MEIPASS'):
        return  # Not needed when running normally

    base_path = sys._MEIPASS
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


def set_environment_flags():
    """Set environment variables to signal we're in a bundled app."""
    if hasattr(sys, '_MEIPASS'):
        os.environ['PADDLEX_SKIP_DEPS_CHECK'] = '1'
        os.environ['PADDLEX_BUNDLED'] = '1'
        # Some packages check for frozen state
        os.environ['PYINSTALLER_BUNDLED'] = '1'


# Run all setup functions immediately when this hook is loaded
# Order matters! Fake module injection must happen first.
set_environment_flags()
inject_fake_deps_module()
setup_import_hook()
ensure_paddlex_version()

print("Runtime hook: PaddleX setup complete")
