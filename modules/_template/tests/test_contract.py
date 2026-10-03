"""The contract test every module runs (rmi_core.testing.contract). Do not edit."""

from modules.{{MODULE_KEY}}.manifest import manifest
from rmi_core.testing.contract import assert_contract


def test_contract() -> None:
    assert_contract(manifest)
