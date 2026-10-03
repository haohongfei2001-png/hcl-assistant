"""Run in a clean deployment-manifest environment, without live services."""
from importlib.metadata import version
from pathlib import Path
import sys
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class DeploymentDependenciesTests(unittest.TestCase):
    def test_deployment_and_ci_manifests_have_the_same_exact_runtime_pins(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['dependencies']
        locked = [line.strip() for line in (ROOT / 'requirements.lock').read_text().splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
        self.assertCountEqual(project, locked)
        for requirement in project:
            name, pinned = requirement.split('==')
            self.assertEqual(version(name), pinned)

    def test_member_auth_bootstraps_with_authenticated_session_encryption(self):
        # MemberAuth construction must work with the deployment dependencies,
        # before any account, database, email or provider request is attempted.
        from cryptography.exceptions import InvalidTag
        from packages.cloud.member_auth import MemberAuth
        auth = MemberAuth(None, 'https://fixture.example.test', '1' * 64, object())
        aad = ('https://fixture.example.test/auth/v1', 'synthetic-subject', 'session-a', 2000000000)
        token = 'SYNTHETIC_REFRESH_FIXTURE'
        sealed = auth.vault.seal(token, *aad)
        self.assertNotIn(token, sealed)
        self.assertEqual(auth.vault.open(sealed, *aad), token)
        with self.assertRaises(InvalidTag):
            auth.vault.open(sealed, aad[0], aad[1], 'session-b', aad[3])


if __name__ == '__main__':
    unittest.main()
