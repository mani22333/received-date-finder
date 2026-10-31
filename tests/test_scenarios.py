"""One test per scenario row (so a failure names the scenario ID)."""
import tempfile
import unittest
from pathlib import Path

from .scenario_runner import _fmt, run_scenario
from .scenarios import SCENARIOS


class ScenarioTests(unittest.TestCase):
    pass


def _make(scn):
    def test(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, res = run_scenario(scn, Path(tmp))
            self.assertEqual(_fmt(res.status, res.date), _fmt(*scn.expected), f"{scn.desc}: {res.reason}")
    return test


for _s in SCENARIOS:
    setattr(ScenarioTests, "test_" + _s.id.replace("-", "_"), _make(_s))

if __name__ == "__main__":
    unittest.main()
