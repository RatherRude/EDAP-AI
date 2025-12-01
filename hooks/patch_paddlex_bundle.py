"""
Post-build script to patch paddlex dependency checking in PyInstaller bundle.

This script modifies the bundled paddlex source files to bypass runtime dependency
checks that fail in PyInstaller environments.

Run this after PyInstaller builds but before packaging the artifact.
"""

import os
import sys
import re
from pathlib import Path


def find_deps_module(internal_dir: Path) -> Path | None:
    """
    Find the paddlex.utils.deps module in the bundle.
    It could be in several locations depending on how PyInstaller bundled it.
    """
    possible_paths = [
        internal_dir / 'paddlex' / 'utils' / 'deps.py',
        internal_dir / 'paddlex' / 'utils' / 'deps.pyc',
    ]
    
    # Also search recursively for deps.py in paddlex directories
    for paddlex_dir in internal_dir.glob('**/paddlex'):
        deps_path = paddlex_dir / 'utils' / 'deps.py'
        if deps_path.exists():
            return deps_path
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def patch_deps_file(deps_path: Path) -> bool:
    """
    Patch the deps.py file to make require_extra a no-op.
    """
    print(f"Patching {deps_path}")
    
    try:
        content = deps_path.read_text(encoding='utf-8')
        original_content = content
        
        # Pattern 1: Replace the require_extra function definition
        # This handles various forms of the function
        patterns = [
            # Match: def require_extra(...): with body
            (
                r'def require_extra\s*\([^)]*\)\s*:.*?(?=\ndef |\nclass |\Z)',
                '''def require_extra(*args, **kwargs):
    """Patched: Skip dependency check in PyInstaller bundle."""
    pass

'''
            ),
            # Match: def check_deps(...): with body
            (
                r'def check_deps\s*\([^)]*\)\s*:.*?(?=\ndef |\nclass |\Z)',
                '''def check_deps(*args, **kwargs):
    """Patched: Skip dependency check in PyInstaller bundle."""
    pass

'''
            ),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # If content changed, write it back
        if content != original_content:
            deps_path.write_text(content, encoding='utf-8')
            print(f"Successfully patched {deps_path}")
            return True
        else:
            print(f"No patterns matched in {deps_path}, trying alternative approach")
            return patch_deps_file_alternative(deps_path)
            
    except Exception as e:
        print(f"Error patching {deps_path}: {e}")
        return False


def patch_deps_file_alternative(deps_path: Path) -> bool:
    """
    Alternative patching approach: prepend a monkey-patch at the start of the file.
    """
    try:
        content = deps_path.read_text(encoding='utf-8')
        
        # Check if already patched
        if '# PATCHED_FOR_PYINSTALLER' in content:
            print(f"File already patched: {deps_path}")
            return True
        
        # Prepend our patch
        patch_code = '''# PATCHED_FOR_PYINSTALLER
# This file has been patched to skip dependency checks in PyInstaller bundles
import sys as _sys

# Store original functions before they're defined
_original_require_extra = None
_original_check_deps = None

def _patched_require_extra(*args, **kwargs):
    """Patched: Skip dependency check in PyInstaller bundle."""
    if hasattr(_sys, '_MEIPASS'):
        return  # Skip in PyInstaller
    if _original_require_extra:
        return _original_require_extra(*args, **kwargs)

def _patched_check_deps(*args, **kwargs):
    """Patched: Skip dependency check in PyInstaller bundle."""
    if hasattr(_sys, '_MEIPASS'):
        return  # Skip in PyInstaller
    if _original_check_deps:
        return _original_check_deps(*args, **kwargs)

# End of patch header

'''
        
        content = patch_code + content
        
        # Also add at the end of the file to override the definitions
        content += '''

# PATCHED_FOR_PYINSTALLER: Override functions at module level
import sys as _sys_check
if hasattr(_sys_check, '_MEIPASS'):
    require_extra = lambda *a, **kw: None
    check_deps = lambda *a, **kw: None
    is_dep_available = lambda *a, **kw: True
'''
        
        deps_path.write_text(content, encoding='utf-8')
        print(f"Successfully patched {deps_path} using alternative approach")
        return True
        
    except Exception as e:
        print(f"Error in alternative patching {deps_path}: {e}")
        return False


def create_deps_stub(internal_dir: Path) -> bool:
    """
    Create a stub deps.py file that does nothing.
    This is used if we can't find the original to patch.
    """
    paddlex_utils_dir = internal_dir / 'paddlex' / 'utils'
    paddlex_utils_dir.mkdir(parents=True, exist_ok=True)
    
    deps_path = paddlex_utils_dir / 'deps.py'
    
    stub_content = '''"""
Stub module for paddlex.utils.deps
Created by PyInstaller post-build patch script.
All dependency checks are disabled in bundled applications.
"""

class DependencyError(Exception):
    """Exception for missing dependencies (never raised in bundle)."""
    pass


def require_extra(*args, **kwargs):
    """No-op: Dependencies are bundled with the application."""
    pass


def check_deps(*args, **kwargs):
    """No-op: Dependencies are bundled with the application."""
    pass


def is_dep_available(*args, **kwargs):
    """Always returns True: Dependencies are bundled."""
    return True


def ensure_deps(*args, **kwargs):
    """No-op: Dependencies are bundled with the application."""
    pass


def get_extra_deps(*args, **kwargs):
    """Returns empty dict: No extra deps needed in bundle."""
    return {}
'''
    
    try:
        deps_path.write_text(stub_content, encoding='utf-8')
        print(f"Created stub deps module at {deps_path}")
        
        # Also create __init__.py if it doesn't exist
        init_path = paddlex_utils_dir / '__init__.py'
        if not init_path.exists():
            init_path.write_text('# paddlex.utils package\n', encoding='utf-8')
            print(f"Created {init_path}")
        
        return True
    except Exception as e:
        print(f"Error creating stub: {e}")
        return False


def patch_pipeline_init(internal_dir: Path) -> bool:
    """
    Patch paddlex pipeline __init__ files that might import and check deps.
    """
    patterns_to_find = [
        '**/paddlex/**/pipelines/**/__init__.py',
        '**/paddlex/**/pipelines/**/ocr*.py',
        '**/paddlex/**/__init__.py',
    ]
    
    patched_any = False
    
    for pattern in patterns_to_find:
        for filepath in internal_dir.glob(pattern):
            try:
                content = filepath.read_text(encoding='utf-8')
                
                # Skip if already patched
                if '# DEPS_PATCHED' in content:
                    continue
                
                # Check if file imports or uses require_extra
                if 'require_extra' in content or 'from .deps import' in content or 'from ..deps import' in content:
                    # Add a patch at the start of the file
                    patch = '''# DEPS_PATCHED
import sys as _patch_sys
if hasattr(_patch_sys, '_MEIPASS'):
    # In PyInstaller bundle, mock the require_extra function
    import paddlex.utils.deps as _deps_module
    _deps_module.require_extra = lambda *a, **kw: None
    if hasattr(_deps_module, 'check_deps'):
        _deps_module.check_deps = lambda *a, **kw: None

'''
                    content = patch + content
                    filepath.write_text(content, encoding='utf-8')
                    print(f"Patched {filepath}")
                    patched_any = True
                    
            except Exception as e:
                print(f"Error processing {filepath}: {e}")
    
    return patched_any


def main():
    """Main entry point for the patch script."""
    # Determine the bundle directory
    if len(sys.argv) > 1:
        bundle_dir = Path(sys.argv[1])
    else:
        # Default location
        bundle_dir = Path('.') / 'dist' / 'EDAP-Autopilot'
    
    internal_dir = bundle_dir / '_internal'
    
    if not internal_dir.exists():
        print(f"ERROR: Bundle directory not found: {internal_dir}")
        print("Usage: python patch_paddlex_bundle.py [bundle_directory]")
        sys.exit(1)
    
    print(f"Patching PaddleX in bundle: {internal_dir}")
    print("=" * 60)
    
    success = True
    
    # Step 1: Try to find and patch the deps module
    deps_path = find_deps_module(internal_dir)
    if deps_path:
        print(f"Found deps module: {deps_path}")
        if not patch_deps_file(deps_path):
            success = False
    else:
        print("deps.py not found, creating stub module")
        if not create_deps_stub(internal_dir):
            success = False
    
    # Step 2: Patch any pipeline files that use require_extra
    print("\nPatching pipeline files...")
    patch_pipeline_init(internal_dir)
    
    # Step 3: Create/verify the .version file
    version_file = internal_dir / 'paddlex' / '.version'
    if not version_file.exists():
        try:
            version_file.parent.mkdir(parents=True, exist_ok=True)
            version_file.write_text('3.3.10', encoding='utf-8')
            print(f"Created version file: {version_file}")
        except Exception as e:
            print(f"Error creating version file: {e}")
    else:
        print(f"Version file exists: {version_file}")
    
    print("\n" + "=" * 60)
    if success:
        print("Patching completed successfully!")
    else:
        print("Patching completed with some errors (see above)")
        sys.exit(1)


if __name__ == '__main__':
    main()

