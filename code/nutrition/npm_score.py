"""UK Ofcom / FSA Nutrient Profiling Model (2004-05).

Implements the scoring exactly as set out in the Department of Health's
"Nutrient Profiling Technical Guidance" (January 2011):
https://www.gov.uk/government/publications/the-nutrient-profiling-model

All inputs are per 100 g of the food as consumed. A LOWER score is healthier.
A food scoring 4 or more (a drink scoring 1 or more) is classified "less healthy".
"""
from dataclasses import dataclass

# 'A' nutrients: 0-10 points. A value scores n points when it is > the n-th threshold.
ENERGY_KJ = (335, 670, 1005, 1340, 1675, 2010, 2345, 2680, 3015, 3350)
SAT_FAT_G = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
SUGARS_G = (4.5, 9, 13.5, 18, 22.5, 27, 31, 36, 40, 45)
SODIUM_MG = (90, 180, 270, 360, 450, 540, 630, 720, 810, 900)

# 'C' nutrients: 0-5 points.
FIBRE_AOAC_G = (0.9, 1.9, 2.8, 3.7, 4.7)
FIBRE_NSP_G = (0.7, 1.4, 2.1, 2.8, 3.5)
PROTEIN_G = (1.6, 3.2, 4.8, 6.4, 8.0)

FOOD_LESS_HEALTHY_AT = 4
DRINK_LESS_HEALTHY_AT = 1


def points(value, thresholds):
    """Number of thresholds the value strictly exceeds."""
    if value < 0:
        raise ValueError(f"negative nutrient value: {value}")
    return sum(value > t for t in thresholds)


def fvn_points(fvn_percent):
    """Fruit, vegetables and nuts: >40 % -> 1, >60 % -> 2, >80 % -> 5 (3 and 4 are not awarded)."""
    if not 0 <= fvn_percent <= 100:
        raise ValueError(f"FVN % out of range: {fvn_percent}")
    if fvn_percent > 80:
        return 5
    if fvn_percent > 60:
        return 2
    if fvn_percent > 40:
        return 1
    return 0


def fvn_percent(fvn_g, dried_fvn_g, other_g):
    """% fruit, vegetables and nuts, counting dried fruit/veg (and tomato puree concentrate) twice.

    (fvn + 2 * dried) / (fvn + 2 * dried + other) * 100      -- guidance, section 2
    """
    top = fvn_g + 2 * dried_fvn_g
    total = top + other_g
    return 100 * top / total if total > 0 else 0.0


@dataclass(frozen=True)
class NPMResult:
    energy_pts: int
    sat_fat_pts: int
    sugars_pts: int
    sodium_pts: int
    a_points: int
    fvn_pts: int
    fibre_pts: int
    protein_pts: int        # points the protein content earns on the table
    protein_counted: bool   # False when the 11-'A'-point rule removes them
    c_points: int           # points actually subtracted
    score: int
    less_healthy: bool


def npm_score(energy_kj, sat_fat_g, sugars_g, sodium_mg, fvn_pct, fibre_g, protein_g,
              fibre_method="AOAC", is_drink=False):
    """Nutrient profile score from per-100 g values."""
    e = points(energy_kj, ENERGY_KJ)
    sf = points(sat_fat_g, SAT_FAT_G)
    su = points(sugars_g, SUGARS_G)
    na = points(sodium_mg, SODIUM_MG)
    a = e + sf + su + na

    fvn = fvn_points(fvn_pct)
    fib = points(fibre_g, {"AOAC": FIBRE_AOAC_G, "NSP": FIBRE_NSP_G}[fibre_method])
    pro = points(protein_g, PROTEIN_G)

    # 11 or more 'A' points: protein only counts if the food also scores 5 for fruit, veg and nuts
    protein_counted = a < 11 or fvn == 5
    c = fvn + fib + (pro if protein_counted else 0)
    score = a - c
    limit = DRINK_LESS_HEALTHY_AT if is_drink else FOOD_LESS_HEALTHY_AT
    return NPMResult(e, sf, su, na, a, fvn, fib, pro, protein_counted, c, score, score >= limit)
