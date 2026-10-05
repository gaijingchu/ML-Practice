"""Tests for npm_score.py: the six worked examples in the DH technical guidance, plus boundaries.

Run:  python -m pytest test_npm_score.py      (or: python test_npm_score.py)
"""
from npm_score import fvn_percent, fvn_points, npm_score, points, ENERGY_KJ, SODIUM_MG, SUGARS_G


def check(result, a, c, score, less_healthy):
    assert (result.a_points, result.c_points, result.score, result.less_healthy) == (a, c, score, less_healthy), result


def test_example_1_fromage_frais():
    r = npm_score(459, 1.8, 13.4, 0.1, 8, 0.6, 6.5)
    assert (r.energy_pts, r.sat_fat_pts, r.sugars_pts, r.sodium_pts) == (1, 1, 2, 0)
    assert (r.fvn_pts, r.fibre_pts, r.protein_pts) == (0, 0, 4)
    check(r, 4, 4, 0, False)


def test_example_2_ice_cream_protein_not_counted():
    r = npm_score(741, 6.1, 18.7, 60, 0, 0, 3.6, fibre_method="NSP")
    assert (r.energy_pts, r.sat_fat_pts, r.sugars_pts, r.sodium_pts) == (2, 6, 4, 0)
    assert r.protein_pts == 2 and not r.protein_counted      # 12 'A' points, FVN < 5
    check(r, 12, 0, 12, True)


def test_example_3_milkshake():
    r = npm_score(299, 1.0, 8.9, 41, 0, 0.5, 3.2, is_drink=True)
    assert r.protein_pts == 1                                 # 3.2 is not > 3.2
    check(r, 1, 1, 0, False)


def test_example_4_cup_soup():
    r = npm_score(155, 0.4, 3.6, 471, 0, 0.2, 0.3)
    assert r.sodium_pts == 5
    check(r, 5, 0, 5, True)


def test_example_5_cereal_bar_dried_fruit():
    pct = fvn_percent(fvn_g=0, dried_fvn_g=30, other_g=70)
    assert round(pct) == 46
    r = npm_score(1504, 1.4, 35.7, 0, pct, 4.8, 4.3)
    assert (r.energy_pts, r.sat_fat_pts, r.sugars_pts, r.sodium_pts) == (4, 1, 7, 0)
    assert (r.fvn_pts, r.fibre_pts) == (1, 5) and not r.protein_counted
    check(r, 12, 6, 6, True)


def test_example_6_juice_drink():
    r = npm_score(184, 0, 10.3, 0, 15, 0, 0.1, is_drink=True)
    check(r, 2, 0, 2, True)


def test_thresholds_are_strict_inequalities():
    assert points(335, ENERGY_KJ) == 0 and points(335.01, ENERGY_KJ) == 1
    assert points(3350, ENERGY_KJ) == 9 and points(3351, ENERGY_KJ) == 10
    assert points(4.5, SUGARS_G) == 0 and points(31.5, SUGARS_G) == 7 and points(45.1, SUGARS_G) == 10
    assert points(90, SODIUM_MG) == 0 and points(900.5, SODIUM_MG) == 10
    assert [fvn_points(p) for p in (0, 40, 40.1, 60, 60.1, 80, 80.1, 100)] == [0, 0, 1, 1, 2, 2, 5, 5]


def test_protein_counts_with_11_a_points_only_if_fvn_scores_5():
    kw = dict(energy_kj=1400, sat_fat_g=4.5, sugars_g=14, sodium_mg=95, fibre_g=0, protein_g=9)
    assert npm_score(fvn_pct=85, **kw).a_points == 12
    assert npm_score(fvn_pct=85, **kw).score == 12 - 5 - 5      # FVN 5 + protein 5
    assert npm_score(fvn_pct=70, **kw).score == 12 - 2          # FVN 2, protein dropped
    assert npm_score(fvn_pct=0, **{**kw, "sat_fat_g": 3.5}).score == 11 - 0   # exactly 11: dropped
    assert npm_score(fvn_pct=0, **{**kw, "sat_fat_g": 2.5}).score == 10 - 5   # 10: protein counts


def test_food_and_drink_cut_offs():
    assert npm_score(700, 0, 0, 95, 0, 0, 0).score == 3 and not npm_score(700, 0, 0, 95, 0, 0, 0).less_healthy
    assert npm_score(700, 1.5, 0, 95, 0, 0, 0).less_healthy                    # 4 -> less healthy food
    assert npm_score(400, 0, 0, 0, 0, 0, 0, is_drink=True).less_healthy        # 1 -> less healthy drink


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)} tests passed")
