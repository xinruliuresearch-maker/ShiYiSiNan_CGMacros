from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from phase_map import assign_phase


class PhaseMapPackageTest(unittest.TestCase):
    def test_toy_phase_assignments_match_expected(self):
        toy = pd.read_csv(ROOT / "toy_data" / "toy_input.csv")
        expected = pd.read_csv(ROOT / "toy_data" / "toy_output_expected.csv")
        observed = assign_phase(toy)
        merged = observed[["participant_id", "phase_id"]].merge(expected[["participant_id", "phase_id"]], on="participant_id", suffixes=("_observed", "_expected"))
        self.assertGreaterEqual(len(merged), 5)
        self.assertTrue((merged["phase_id_observed"] == merged["phase_id_expected"]).all())

    def test_missing_required_column_raises(self):
        toy = pd.read_csv(ROOT / "toy_data" / "toy_input.csv").drop(columns=["cgm_cv_pct"])
        with self.assertRaises(ValueError):
            assign_phase(toy)


if __name__ == "__main__":
    unittest.main()
