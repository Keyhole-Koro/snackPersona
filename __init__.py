"""Compatibility package shim for src-layout imports.

Allows `import snackPersona.*` from repository root by extending package
search path to `snackPersona/src/snackPersona`.
"""

from pathlib import Path

_pkg_root = Path(__file__).resolve().parent
_src_pkg = _pkg_root / "src" / "snackPersona"

if _src_pkg.is_dir():
    __path__.append(str(_src_pkg))
