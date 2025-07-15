"""Central repository of rapid‑test performance numbers.

The data is copied verbatim from the previous calculate_test_risk() logic so
that refactoring the algorithm does *not* alter results.  Keeping the numbers
in one place avoids future inconsistencies and makes updates simpler.

LIMIT OF DETECTION (LoD) UNITS:
- Lucira, Metrix, Pluslife: genome equivalents/mL (ge/mL)
- All other tests: TCID₅₀/mL (50% tissue culture infectious dose per mL)

Note: LoD values represent the 95% limit of detection (concentration at which
the test detects 95% of positive samples).
"""

# Each entry maps ``test_name`` -> {"yes"|"no": {...}}
# Where "yes" means symptomatic users, "no" means asymptomatic users.
# Each test entry will include a "lod_95" field for the 95% limit of detection.

TEST_PERFORMANCE: dict = {
    "Metrix": {
        "lod_95": 667,  # LoD in genome equivalents/mL (ge/mL)
        "yes": {
            "sens": 0.95,
            "spec": 0.971,
            "sens_low": 0.835,
            "sens_high": 0.986,
            "spec_low": 0.855,
            "spec_high": 0.995,

            "sens_k": 38,  # number of successes for sensitivity measurement


            "sens_n": 40,  # sample size for sensitivity measurement


            "spec_k": 34,  # number of successes for specificity measurement


            "spec_n": 35,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.94,
            "spec": 0.992,
            "sens_low": 0.845,
            "sens_high": 1.0,
            "spec_low": 0.972,
            "spec_high": 0.998,

            "sens_k": 21,  # number of successes for sensitivity measurement


            "sens_n": 21,  # sample size for sensitivity measurement


            "spec_k": 259,  # number of successes for specificity measurement


            "spec_n": 261,  # sample size for specificity measurement
        },
    },
    "Other RAT (Rapid Antigen Test)": {
        "lod_95": 7185.1,  # Average LoD of all TCID₅₀/mL tests
        "yes": {
            "sens": 0.874,
            "spec": 0.999,
            "sens_low": 0.837,
            "sens_high": 0.904,
            "spec_low": 0.997,
            "spec_high": 0.999,

            "sens_k": 333,  # number of successes for sensitivity measurement


            "sens_n": 381,  # sample size for sensitivity measurement


            "spec_k": 9770,  # number of successes for specificity measurement


            "spec_n": 9788,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.998,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.996,
            "spec_high": 1.0,

            "sens_k": 114,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 3127,  # number of successes for specificity measurement


            "spec_n": 3132,  # sample size for specificity measurement
        },
    },
    "Pluslife": {
        "lod_95": 400,  # LoD in genome equivalents/mL (ge/mL)
        "yes": {
            "sens": 0.987,
            "spec": 0.993,
            "sens_low": 0.931,
            "sens_high": 0.998,
            "spec_low": 0.987,
            "spec_high": 0.996,

            "sens_k": 77,  # number of successes for sensitivity measurement


            "sens_n": 78,  # sample size for sensitivity measurement


            "spec_k": 1323,  # number of successes for specificity measurement


            "spec_n": 1332,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.973,
            "spec": 0.993,
            "sens_low": 0.862,
            "sens_high": 0.995,
            "spec_low": 0.987,
            "spec_high": 0.996,

            "sens_k": 36,  # number of successes for sensitivity measurement


            "sens_n": 37,  # sample size for sensitivity measurement


            "spec_k": 1323,  # number of successes for specificity measurement


            "spec_n": 1332,  # sample size for specificity measurement
        },
    },
    "Flowflex Plus (Covid & Flu)": {
        "lod_95": 1270,  # Enter LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.906,
            "spec": 0.993,
            "sens_low": 0.854,
            "sens_high": 0.944,
            "spec_low": 0.982,
            "spec_high": 0.998,

            "sens_k": 164,  # number of successes for sensitivity measurement


            "sens_n": 181,  # sample size for sensitivity measurement


            "spec_k": 551,  # number of successes for specificity measurement


            "spec_n": 555,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.275,
            "spec": 0.993,
            "sens_low": 0.213,
            "sens_high": 0.343,
            "spec_low": 0.982,
            "spec_high": 0.998,

            "sens_k": 53,  # number of successes for sensitivity measurement


            "sens_n": 193,  # sample size for sensitivity measurement


            "spec_k": 551,  # number of successes for specificity measurement


            "spec_n": 555,  # sample size for specificity measurement
        },
    },
    "Flowflex (Covid-only)": {
        "lod_95": 2500,  # Enter LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.847,
            "spec": 0.993,
            "sens_low": 0.797,
            "sens_high": 0.886,
            "spec_low": 0.985,
            "spec_high": 0.998,

            "sens_k": 210,  # number of successes for sensitivity measurement


            "sens_n": 248,  # sample size for sensitivity measurement


            "spec_k": 149,  # number of successes for specificity measurement


            "spec_n": 150,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.275,
            "spec": 0.998,
            "sens_low": 0.213,
            "sens_high": 0.343,
            "spec_low": 0.996,
            "spec_high": 0.999,

            "sens_k": 53,  # number of successes for sensitivity measurement


            "sens_n": 193,  # sample size for sensitivity measurement


            "spec_k": 1034,  # number of successes for specificity measurement


            "spec_n": 1036,  # sample size for specificity measurement
        },
    },
    "iHealth (Covid-only)": {
        "lod_95": 20000,  # Enter LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.725,
            "spec": 0.984,
            "sens_low": 0.636,
            "sens_high": 0.803,
            "spec_low": 0.968,
            "spec_high": 0.992,

            "sens_k": 87,  # number of successes for sensitivity measurement


            "sens_n": 120,  # sample size for sensitivity measurement


            "spec_k": 435,  # number of successes for specificity measurement


            "spec_n": 442,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.984,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.968,
            "spec_high": 0.992,

            "sens_k": 118,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 435,  # number of successes for specificity measurement


            "spec_n": 442,  # sample size for specificity measurement
        },
    },
    "CorDx (Covid & Flu)": {
        "lod_95": 400,  # Enter LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.891,
            "spec": 0.998,
            "sens_low": 0.819,
            "sens_high": 0.936,
            "spec_low": 0.991,
            "spec_high": 1.0,

            "sens_k": 98,  # number of successes for sensitivity measurement


            "sens_n": 110,  # sample size for sensitivity measurement


            "spec_k": 637,  # number of successes for specificity measurement


            "spec_n": 638,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.998,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.991,
            "spec_high": 1.0,

            "sens_k": 118,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 637,  # number of successes for specificity measurement


            "spec_n": 638,  # sample size for specificity measurement
        },
    },
    "Lucira": {
        "lod_95": 363,  # LoD in genome equivalents/mL (ge/mL)
        "yes": {
            "sens": 0.883,
            "spec": 0.999,
            "sens_low": 0.802,
            "sens_high": 0.933,
            "spec_low": 0.996,
            "spec_high": 1.0,

            "sens_k": 83,  # number of successes for sensitivity measurement


            "sens_n": 94,  # sample size for sensitivity measurement


            "spec_k": 858,  # number of successes for specificity measurement


            "spec_n": 858,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.840,
            "spec": 0.982,
            "sens_low": 0.751,
            "sens_high": 0.903,
            "spec_low": 0.952,
            "spec_high": 0.995,

            "sens_k": 68,  # number of successes for sensitivity measurement


            "sens_n": 81,  # sample size for sensitivity measurement


            "spec_k": 218,  # number of successes for specificity measurement


            "spec_n": 222,  # sample size for specificity measurement
        },
    },
    "iHealth (Covid & Flu)": {
        "lod_95": 1580,  # Enter LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.842,
            "spec": 0.984,
            "sens_low": 0.756,
            "sens_high": 0.902,
            "spec_low": 0.968,
            "spec_high": 0.992,

            "sens_k": 80,  # number of successes for sensitivity measurement


            "sens_n": 95,  # sample size for sensitivity measurement


            "spec_k": 435,  # number of successes for specificity measurement


            "spec_n": 442,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.984,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.968,
            "spec_high": 0.992,

            "sens_k": 118,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 435,  # number of successes for specificity measurement


            "spec_n": 442,  # sample size for specificity measurement
        },
    },
    "WELLLife (Covid & Flu)": {
        "lod_95": 790,  # LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.875,
            "spec": 0.997,
            "sens_low": 0.807,
            "sens_high": 0.922,
            "spec_low": 0.989,
            "spec_high": 0.999,

            "sens_k": 112,  # number of successes for sensitivity measurement


            "sens_n": 128,  # sample size for sensitivity measurement


            "spec_k": 639,  # number of successes for specificity measurement


            "spec_n": 641,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.997,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.989,
            "spec_high": 0.999,

            "sens_k": 118,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 639,  # number of successes for specificity measurement


            "spec_n": 641,  # sample size for specificity measurement
        },
    },
    "BinaxNOW": {
        "lod_95": 140.6,  # LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.74,
            "spec": 0.992,
            "sens_low": 0.668,
            "sens_high": 0.804,
            "spec_low": 0.954,
            "spec_high": 0.999,

            "sens_k": 128,  # number of successes for sensitivity measurement


            "sens_n": 173,  # sample size for sensitivity measurement


            "spec_k": 118,  # number of successes for specificity measurement


            "spec_n": 119,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.496,
            "spec": 0.994,
            "sens_low": 0.405,
            "sens_high": 0.586,
            "spec_low": 0.977,
            "spec_high": 0.998,

            "sens_k": 56,  # number of successes for sensitivity measurement


            "sens_n": 113,  # sample size for sensitivity measurement


            "spec_k": 310,  # number of successes for specificity measurement


            "spec_n": 312,  # sample size for specificity measurement
        },
    },
    "OSOM (Covid & Flu)": {
        "lod_95": 30800,  # LoD in TCID₅₀/mL
        "yes": {
            "sens": 0.597,
            "spec": 0.991,
            "sens_low": 0.516,
            "sens_high": 0.674,
            "spec_low": 0.979,
            "spec_high": 0.996,

            "sens_k": 86,  # number of successes for sensitivity measurement


            "sens_n": 144,  # sample size for sensitivity measurement


            "spec_k": 554,  # number of successes for specificity measurement


            "spec_n": 559,  # sample size for specificity measurement
        },
        "no": {
            "sens": 0.252,
            "spec": 0.991,
            "sens_low": 0.215,
            "sens_high": 0.293,
            "spec_low": 0.979,
            "spec_high": 0.996,

            "sens_k": 118,  # number of successes for sensitivity measurement


            "sens_n": 468,  # sample size for sensitivity measurement


            "spec_k": 554,  # number of successes for specificity measurement


            "spec_n": 559,  # sample size for specificity measurement
        },
    },
}


from typing import Dict


def get_performance(test_name: str, symptomatic: bool) -> Dict[str, float]:
    """Return performance metrics for *test_name*.

    If the requested test is unknown this returns an all‑zero placeholder so the
    calling maths can proceed without special‑casing ``None``.
    """

    record = TEST_PERFORMANCE.get(test_name)
    if record is None:
        return {
            "sens": 0.0,
            "spec": 0.0,
            "sens_low": 0.0,
            "sens_high": 0.0,
            "spec_low": 0.0,
            "spec_high": 0.0,
            "sens_k": None,
            "sens_n": None,
            "spec_k": None,
            "spec_n": None,
            "lod_95": None,
        }

    # Get symptom-specific data and add the LoD (which is test-specific, not symptom-specific)
    result = record["yes" if symptomatic else "no"].copy()
    result["lod_95"] = record.get("lod_95")
    return result
