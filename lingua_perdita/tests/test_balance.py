"""Balance tests — simulation must meet pacing criteria."""

import pytest

from lingua_perdita.simulate import build_pacing_bounds, run_simulation


def test_simulation_completes():
    """Simulation runs to completion without errors."""
    report, bounds = run_simulation(seed=42, verbose=False)
    assert report.total_time > 0
    assert len(report.purchases) > 0


def test_no_stalls():
    """Simulation has no stalls."""
    report, bounds = run_simulation(seed=42, verbose=False)
    assert len(report.stalls) == 0, f"Stalls detected: {report.stalls}"


def test_pacing_bounds_pass():
    """All pacing bounds pass (errors only — warnings OK)."""
    report, bounds = run_simulation(seed=42, verbose=False)

    failures = []
    for bound in bounds:
        result = bound.evaluate(report)
        if not result.passed and bound.severity == "error":
            failures.append(f"{bound.description}: {result.message}")

    assert not failures, f"Pacing failures:\n" + "\n".join(failures)


def test_all_words_purchased():
    """All 30 words are eventually purchased."""
    report, _ = run_simulation(seed=42, verbose=False)
    word_purchases = {p.element_id for p in report.purchases if p.element_id.startswith("word_")}
    assert len(word_purchases) == 30, f"Only {len(word_purchases)} words purchased"


def test_first_word_timing():
    """First word is translated within pacing bounds."""
    report, _ = run_simulation(seed=42, verbose=False)
    first_word_time = report.milestone_time("first_word")
    assert first_word_time is not None, "first_word milestone never reached"
    assert first_word_time <= 120.0, f"First word at {first_word_time:.1f}s (max 120s)"


def test_deterministic():
    """Same seed produces same simulation results."""
    report1, _ = run_simulation(seed=42, verbose=False)
    report2, _ = run_simulation(seed=42, verbose=False)
    assert report1.total_time == report2.total_time
    assert len(report1.purchases) == len(report2.purchases)
