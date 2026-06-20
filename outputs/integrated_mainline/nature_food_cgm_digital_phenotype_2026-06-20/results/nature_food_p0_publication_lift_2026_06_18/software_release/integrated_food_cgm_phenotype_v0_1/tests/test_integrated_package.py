import unittest
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from integrated_food_cgm import integrated_phenotype_report


class IntegratedPackageTest(unittest.TestCase):
    def test_toy_data_runs(self):
        df = pd.read_csv(ROOT / "toy_data" / "toy_integrated_input.csv")
        out = integrated_phenotype_report(df)
        self.assertEqual(len(out), 2)
        self.assertIn("phase_id", out.columns)
        self.assertIn("meal_high_iauc_ranking_score", out.columns)
        self.assertTrue(out["meal_high_iauc_ranking_score"].between(0, 1).all())


if __name__ == "__main__":
    unittest.main()
