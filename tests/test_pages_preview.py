from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PagesPreviewBoundaryTests(unittest.TestCase):
    def test_static_preview_assets_are_browser_only_and_explicit(self):
        index = (ROOT / "pages-preview/index.html").read_text(encoding="utf-8")
        app = (ROOT / "pages-preview/app.js").read_text(encoding="utf-8")
        self.assertIn("未接入真实 HCL", index)
        self.assertIn("localStorage", app)
        self.assertNotIn("fetch(", app)
        self.assertNotIn("/v1/", app)
        self.assertIn("Provider calls</dt><dd>0", app)

    def test_pages_workflow_has_only_builtin_static_deploy_permissions(self):
        workflow = (ROOT / ".github/workflows/pages-preview.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("actions/deploy-pages@", workflow)
        self.assertNotIn("secrets.", workflow)
        self.assertIn("path: pages-preview", workflow)

    def test_plan_keeps_l3_gate_while_authorizing_static_preview(self):
        plan = json.loads((ROOT / "control/plan.json").read_text(encoding="utf-8"))
        boundary = plan["boundary"]
        self.assertFalse(boundary["public_deployment_allowed"])
        self.assertTrue(boundary["synthetic_static_preview_allowed"])
        self.assertEqual(boundary["synthetic_static_preview_mode"], "GITHUB_PAGES_BROWSER_ONLY")
        states={r['id']:r['state'] for r in plan['packages']}
        if states['L2.5-01']!='COMPLETE':
            self.assertEqual(plan['next_ready'],'L2.5-01_PINNED_RUNTIME_BRIDGE_CONTRACT_AND_HANDSHAKE')
            self.assertEqual(plan['phase'],'L2_5_READY')
        elif states['L2.5-02']!='COMPLETE':
            self.assertEqual(plan['next_ready'],'L2.5-02_EXPERIMENTAL_MECHANISM_SYNTHETIC_E2E')
            self.assertEqual(plan['phase'],'L2_5_IMPLEMENTING')
        else:
            self.assertEqual(plan['next_ready'],'STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED')
            self.assertEqual(plan['phase'],'L2_5_COMPLETE')
        self.assertIn("I06_DISPOSITION", plan["l3_gates"])
        self.assertFalse(plan["invariants"]["l2_5_production_activation_allowed"])


if __name__ == "__main__":
    unittest.main()
