"""Execute browser-only Controller behavior without claiming browser coverage."""
from pathlib import Path
import subprocess
import unittest
class PreviewModelTests(unittest.TestCase):
    def test_original_synthetic_model_contracts(self):
        result=subprocess.run(['node','--test','tests/javascript/preview-model.test.js','tests/javascript/preview-revision.test.js'],cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
