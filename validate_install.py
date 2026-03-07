#!/usr/bin/env python3
"""Installation validator for OCRExtractor"""

import sys
import shutil
from pathlib import Path


def validate():
    issues = []

    if sys.version_info < (3, 10):
        issues.append("Python 3.10+ required")
    else:
        print(f"  [OK] Python {sys.version_info.major}.{sys.version_info.minor}")

    try:
        from PIL import Image
        print("  [OK] Pillow")
    except ImportError:
        issues.append("Missing: Pillow")

    try:
        import pytesseract
        print("  [OK] pytesseract")
    except ImportError:
        issues.append("Missing: pytesseract")

    # Check Tesseract binary
    if shutil.which('tesseract'):
        print("  [OK] Tesseract binary (system)")
    else:
        # Check standard Windows locations
        import string
        found = False
        if sys.platform == 'win32':
            for drive in string.ascii_uppercase:
                path = f"{drive}:\\Program Files\\Tesseract-OCR\\tesseract.exe"
                if Path(path).exists():
                    print(f"  [OK] Tesseract binary ({path})")
                    found = True
                    break
        if not found:
            print("  [!!] Tesseract binary not found - run installer in bin/windows/ or install manually")

    # Optional packages
    for pkg, name in [('fitz', 'pymupdf'), ('easyocr', 'easyocr')]:
        try:
            __import__(pkg)
            print(f"  [OK] {name}")
        except ImportError:
            print(f"  [--] {name} (optional)")

    base = Path(__file__).parent.parent
    for d in ['inputs', 'outputs']:
        dp = base / d
        if not dp.exists():
            dp.mkdir(exist_ok=True)
        print(f"  [OK] {d}/ directory")

    print()
    if issues:
        print("VALIDATION FAILED:")
        for i in issues:
            print(f"   - {i}")
        return 1
    print("All checks passed - ready to use!")
    return 0


if __name__ == "__main__":
    sys.exit(validate())
