#!/usr/bin/env python3
"""
Sync shared Python dependencies to /data/shared-deps/pip.

This script ensures that:
1. The shared-deps directory structure exists
2. Cache directory exists with correct permissions
3. Common packages are pre-installed for agent code execution
"""

import os
import subprocess
import sys
from pathlib import Path

# Shared dependencies directory
SHARED_DEPS_DIR = Path("/data/shared-deps")
PIP_DIR = SHARED_DEPS_DIR / "pip"
CACHE_DIR = PIP_DIR / "cache"
NODE_MODULES_DIR = SHARED_DEPS_DIR / "node_modules"

# Common packages for agent code execution
COMMON_PACKAGES = [
    "requests>=2.31.0",
    "pandas>=2.0.0",
    "numpy>=1.24.0",
    "python-docx>=1.1.0",
    "Pillow>=10.0.0",
    "openpyxl>=3.1.0",
    "fpdf2>=2.7.0",
    "reportlab>=4.0.0",
]


def create_directory_structure():
    """Create shared-deps directory structure."""
    print("[sync_shared_deps] Creating directory structure...")

    # Create main directories
    for directory in [SHARED_DEPS_DIR, PIP_DIR, CACHE_DIR, NODE_MODULES_DIR]:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ Created: {directory}")
        except PermissionError:
            print(f"  ✗ Permission denied: {directory}")
            return False

    # Set permissions for cache directory (must be writable)
    try:
        CACHE_DIR.chmod(0o777)
        print(f"  ✓ Set cache permissions: {CACHE_DIR}")
    except Exception as e:
        print(f"  ✗ Failed to set cache permissions: {e}")
        return False

    return True


def install_common_packages():
    """Install common packages to shared-deps directory."""
    print("[sync_shared_deps] Installing common packages...")

    # Set pip environment to install to shared-deps directory
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PIP_DIR)
    env["PIP_TARGET"] = str(PIP_DIR)
    env["PIP_CACHE_DIR"] = str(CACHE_DIR)

    for package in COMMON_PACKAGES:
        try:
            print(f"  → Installing {package}...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", package,
                 "--target", str(PIP_DIR),
                 "--cache-dir", str(CACHE_DIR)],
                capture_output=True,
                text=True,
                env=env,
                timeout=120,
            )

            if result.returncode == 0:
                print(f"    ✓ {package} installed")
            else:
                print(f"    ✗ {package} failed: {result.stderr[:100]}")

        except subprocess.TimeoutExpired:
            print(f"    ✗ {package} timeout")
        except Exception as e:
            print(f"    ✗ {package} error: {e}")


def verify_packages():
    """Verify that common packages are importable from shared-deps."""
    print("[sync_shared_deps] Verifying packages...")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(PIP_DIR)

    test_imports = [
        ("requests", "import requests"),
        ("pandas", "import pandas"),
        ("docx", "from docx import Document"),
        ("PIL", "from PIL import Image"),
        ("fpdf", "from fpdf import FPDF"),
        ("reportlab", "from reportlab.lib.pagesizes import letter"),
    ]

    for package_name, import_statement in test_imports:
        try:
            result = subprocess.run(
                [sys.executable, "-c", import_statement],
                capture_output=True,
                text=True,
                env=env,
                timeout=10,
            )

            if result.returncode == 0:
                print(f"  ✓ {package_name}")
            else:
                print(f"  ✗ {package_name}: {result.stderr[:50]}")

        except Exception as e:
            print(f"  ✗ {package_name}: {e}")


def main():
    """Main sync function."""
    print("[sync_shared_deps] Starting dependency sync...")

    if not create_directory_structure():
        print("[sync_shared_deps] ✗ Directory structure creation failed")
        return 1

    install_common_packages()
    verify_packages()

    print("[sync_shared_deps] ✓ Dependency sync completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
