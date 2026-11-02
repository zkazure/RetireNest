import json
import unittest

from medical import estimate_medical_cost, estimate_medical_costs


class SimpleMedicalCostTests(unittest.TestCase):
    def test_only_three_inputs_and_simple_output(self):
        r = estimate_medical_cost(35, "上海", "职工医保")
        self.assertEqual(
            set(r), {"age_group", "annual_medical_cost", "monthly_medical_cost", "note"}
        )
        self.assertEqual(r["age_group"], "18–39岁")
        self.assertEqual(r["annual_medical_cost"], 1976.06)
        self.assertIn("演示", r["note"])
        json.dumps(r, ensure_ascii=False, allow_nan=False)

    def test_age_band_boundaries(self):
        expected = {
            0: "0–17岁",
            17: "0–17岁",
            18: "18–39岁",
            39: "18–39岁",
            40: "40–59岁",
            59: "40–59岁",
            60: "60–74岁",
            74: "60–74岁",
            75: "75岁及以上",
            120: "75岁及以上",
        }
        for age, group in expected.items():
            with self.subTest(age=age):
                self.assertEqual(estimate_medical_cost(age, "上海", "居民医保")["age_group"], group)

    def test_same_age_band_same_budget(self):
        self.assertEqual(
            estimate_medical_cost(18, "上海", "居民医保"),
            estimate_medical_cost(39, "上海", "居民医保"),
        )

    def test_city_suffix_and_insurance_alias(self):
        self.assertEqual(
            estimate_medical_cost(35, "上海市", "城镇职工医保"),
            estimate_medical_cost(35, "上海", "职工医保"),
        )

    def test_unknown_city_uses_explicit_fallback(self):
        result = estimate_medical_cost(35, "长沙", "居民医保")
        self.assertIn("全国地区系数", result["note"])
        self.assertGreater(result["annual_medical_cost"], 0)

    def test_invalid_inputs(self):
        cases = [
            (-1, "上海", "居民医保"),
            (121, "上海", "居民医保"),
            (True, "上海", "居民医保"),
            (35.5, "上海", "居民医保"),
            ("35", "上海", "居民医保"),
            (35, "", "居民医保"),
            (35, None, "居民医保"),
            (35, "市", "居民医保"),
            (35, "上海", "商业保险"),
            (35, "上海", None),
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(ValueError):
                estimate_medical_cost(*args)

    def test_old_function_name_has_same_simple_interface(self):
        self.assertEqual(
            estimate_medical_costs(35, "上海", "职工医保"),
            estimate_medical_cost(35, "上海", "职工医保"),
        )


if __name__ == "__main__":
    unittest.main()
