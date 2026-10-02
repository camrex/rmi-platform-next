import pytest
from unittest.mock import patch, MagicMock
import subprocess
from scripts.check_module_isolation import main

def test_check_module_isolation_pass(monkeypatch):
    # Mock git diff to return allowed files
    def mock_git_diff(*args, **kwargs):
        return MagicMock(stdout="modules/auth/src/main.py\ncontracts/auth_api.sol\ndocs/api.md", returncode=0)

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="modules/auth/src/main.py\ncontracts/auth_api.sol\ndocs/api.md", returncode=0)
        
        monkeypatch.setattr("sys.exit", lambda x: None if x == 0 else pytest.raise(SystemExit(x)))
        
        with pytest.raises(SystemExit) as e:
            with patch("sys.argv", ["script.py", "main", "--module", "auth"]):
                main()
        # In the success case, the script should NOT exit with 1. 
        # But my main() calls sys.exit(1) only on failure. 
        # Let's check if it didn't exit with 1.
        assert e.value.code != 1

def test_check_module_isolation_fail(monkeypatch):
    with patch("subprocess.run") as mock_run:
        # File outside allowed paths
        mock_run.return_value = MagicMock(stdout="modules/auth/src/main.py\nmodules/other/src/main.py", returncode=0)
        
        with pytest.raises(SystemExit) as e:
            with patch("sys.argv", ["script.py", "main", "--module", "auth"]):
                main()
        assert e.value.code == 1

def test_check_module_isolation_contract_fail(monkeypatch):
    with patch("subprocess.run") as mock_run:
        # Contract with wrong prefix
        mock_run.return_value = MagicMock(stdout="contracts/wrong_prefix.sol", returncode=0)
        
        with pytest.raises(SystemExit) as e:
            with patch("sys.argv", ["script.py", "main", "--module", "auth"]):
                main()
        assert e.value.code == 1

def test_check_module_isolation_docs_pass(monkeypatch):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="docs/anything.md", returncode=0)
        
        # We need to capture stdout to ensure it doesn't fail
        with patch("sys.argv", ["script.py", "main", "--module", "auth"]):
            # It should not raise SystemExit(1)
            try:
                main()
            except SystemExit as e:
                assert e.code != 1
