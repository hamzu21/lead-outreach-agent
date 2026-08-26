import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestGoogleServicesUnpacking(unittest.TestCase):
    def _read(self, rel_path: str) -> str:
        return (REPO_ROOT / rel_path).read_text(encoding="utf-8")

    def test_outreach_agent_uses_flexible_unpacking(self):
        content = self._read("src/agent.py")
        self.assertRegex(
            content,
            re.compile(r"self\.sheets_service,\s*self\.gmail_service,\s*\*_\s*=\s*get_google_services\(\)")
        )

    def test_job_agent_uses_flexible_unpacking(self):
        content = self._read("src/modules/job_agent/job_pipeline.py")
        self.assertRegex(
            content,
            re.compile(r"self\.sheets_service,\s*self\.gmail_service,\s*\*_\s*=\s*get_google_services\(\)")
        )


if __name__ == "__main__":
    unittest.main()
