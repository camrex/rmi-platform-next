from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rmi_core.loader import load_modules
from rmi_core.manifest import ModuleManifest
from rmi_core.resolve import ResolutionError


@pytest.fixture
def mock_manifest_a():
    return ModuleManifest(
        key="mod_a",
        version="1.0",
        display_name="Mod A",
        accent="blue",
    )


@pytest.fixture
def mock_manifest_b():
    return ModuleManifest(
        key="mod_b",
        version="1.0",
        display_name="Mod B",
        accent="green",
    )


def test_load_modules_success(mock_manifest_a, mock_manifest_b):
    # Mock entry points
    ep_a = MagicMock()
    ep_a.name = "mod_a"
    ep_a.load.return_value = mock_manifest_a

    ep_b = MagicMock()
    ep_b.name = "mod_b"
    ep_b.load.return_value = mock_manifest_b

    with patch("rmi_core.loader.entry_points") as mock_eps:
        mock_eps.return_value = [ep_a, ep_b]
        res, manifests = load_modules()

    assert res.load_order == ("mod_a", "mod_b") or res.load_order == ("mod_b", "mod_a")
    assert manifests == {"mod_a": mock_manifest_a, "mod_b": mock_manifest_b}


def test_load_modules_type_error():
    ep = MagicMock()
    ep.name = "bad_mod"
    ep.load.return_value = "not a manifest"

    with patch("rmi_core.loader.entry_points") as mock_eps:
        mock_eps.return_value = [ep]
        with pytest.raises(TypeError, match="did not return a ModuleManifest"):
            load_modules()


def test_load_modules_resolution_error(mock_manifest_a):
    # Create a manifest that requires something that doesn't exist
    from rmi_core.manifest import SeamRef

    manifest_fail = ModuleManifest(
        key="mod_fail",
        version="1.0",
        display_name="Fail",
        accent="red",
        requires=[SeamRef(name="missing.seam", range=">=1")],
    )

    ep = MagicMock()
    ep.name = "mod_fail"
    ep.load.return_value = manifest_fail

    with patch("rmi_core.loader.entry_points") as mock_eps:
        mock_eps.return_value = [ep]
        with pytest.raises(ResolutionError, match="no loaded module offers seam 'missing.seam'"):
            load_modules()


def test_load_modules_core_revision(mock_manifest_a):
    # Manifest that requires core revision 2.0
    manifest_rev = ModuleManifest(
        key="mod_rev",
        version="1.0",
        display_name="Rev",
        accent="blue",
        core_revision=">=2.0",
        db_schema="mod_rev",
        migrations="v1",
    )

    ep = MagicMock()
    ep.name = "mod_rev"
    ep.load.return_value = manifest_rev

    with patch("rmi_core.loader.entry_points") as mock_eps:
        mock_eps.return_value = [ep]
        # Should fail with core_revision "1.0"
        with pytest.raises(
            ResolutionError, match="needs core revision '>=2.0', but core is at '1.0'"
        ):
            load_modules(core_revision="1.0")
        # Should succeed with core_revision "2.0"
        res, manifests = load_modules(core_revision="2.0")
        assert res.load_order == ("mod_rev",)
        assert manifests == {"mod_rev": manifest_rev}
