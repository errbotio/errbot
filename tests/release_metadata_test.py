"""Release-time gate.

When ``errbot/version.py`` has been bumped past the dev sentinel ``9.9.9``,
``CHANGES.rst`` must contain a section heading for that version. On master
the sentinel keeps this test skipped; it only fires once a release is being
prepared (or a release branch is checked out), at which point it forces the
maintainer to update CHANGES.rst before the tag goes out.

This replaces the install-time check that lived in setup.py.
"""
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEV_SENTINEL = "9.9.9"


def _read_version() -> str:
    """Read VERSION from errbot/version.py without importing the package."""
    ns: dict = {}
    exec((REPO_ROOT / "errbot" / "version.py").read_text(), ns)
    return ns["VERSION"]


def test_changes_rst_has_section_for_current_version():
    version = _read_version()
    if version == DEV_SENTINEL:
        pytest.skip(f"dev sentinel {DEV_SENTINEL} — no CHANGES.rst entry expected")

    changes = (REPO_ROOT / "CHANGES.rst").read_text()
    pattern = rf"^v?{re.escape(version)}\b"
    assert re.search(pattern, changes, re.MULTILINE), (
        f"CHANGES.rst is missing a section heading for version {version}. "
        f"Rename the 'v{DEV_SENTINEL} (unreleased)' heading to the new "
        "version, or add a new release section, before tagging."
    )
