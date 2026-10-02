import unittest
import subprocess
import os
import shutil
import tempfile
from pathlib import Path

class TestModuleIsolation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Initialize git repo
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        
        self.script_path = os.path.join(self.cwd, "scripts/check_module_isolation.py")
        # Make sure the script is executable (though we call it with python3)
        
    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.test_dir)

    def commit_files(self, files_content):
        """Creates files and commits them."""
        for path, content in files_content.items():
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            subprocess.run(["git", "add", path], check=True)
        subprocess.run(["git", "commit", "-m", "commit"], check=True)

    def run_isolation_check(self, base, module):
        result = subprocess.run(
            ["python3", self.script_path, "--base", base, "--module", module],
            capture_output=True,
            text=True
        )
        return result.returncode, result.stdout, result.stderr

    def test_isolated_changes(self):
        # Initial state
        self.commit_files({
            "modules/auth/main.py": "print(1)",
            "contracts/auth_core.sol": "pragma solidity ^0.8.0",
            "docs/intro.md": "# Intro",
            "modules/payment/main.py": "print(2)",
        })
        base_ref = "HEAD"
        
        # Modify only allowed files
        Path("modules/auth/main.py").write_text("print(1.1)")
        Path("contracts/auth_extra.sol").write_text("pragma solidity ^0.8.0")
        Path("docs/auth.md").write_text("# Auth")
        
        # We don't commit the new changes, because check_module_isolation.py 
        # diffs the current working tree against the base ref.
        
        rc, stdout, stderr = self.run_isolation_check(base_ref, "auth")
        self.assertEqual(rc, 0)

    def test_non_isolated_changes(self):
        # Initial state
        self.commit_files({
            "modules/auth/main.py": "print(1)",
            "docs/intro.md": "# Intro",
        })
        base_ref = "HEAD"
        
        # Modify an unrelated module
        Path("modules/payment/main.py").write_text("print(2)")
        
        rc, stdout, stderr = self.run_isolation_check(base_ref, "auth")
        self.assertEqual(rc, 1)
        self.assertIn("modules/payment/main.py", stderr)

    def test_non_isolated_contract(self):
        # Initial state
        self.commit_files({
            "modules/auth/main.py": "print(1)",
        })
        base_ref = "HEAD"
        
        # Modify a contract that doesn't start with auth_
        Path("contracts/payment_core.sol").write_text("pragma solidity ^0.8.0")
        
        rc, stdout, stderr = self.run_isolation_check(base_ref, "auth")
        self.assertEqual(rc, 1)
        self.assertIn("contracts/payment_core.sol", stderr)

    def test_isolation_with_docs(self):
        # Initial state
        self.commit_files({
            "modules/auth/main.py": "print(1)",
        })
        base_ref = "HEAD"
        
        # Modify only docs
        Path("docs/anything.md").write_text("info")
        
        rc, stdout, stderr = self.run_isolation_check(base_ref, "auth")
        self.assertEqual(rc, 0)

if __name__ == "__main__":
    unittest.main()
