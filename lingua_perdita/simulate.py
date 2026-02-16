"""Economy simulation — the fail-fast checkpoint.

Run with: python -m lingua_perdita simulate
"""

from __future__ import annotations

from idleengine import (
    ClickProfile,
    GameDefinition,
    GreedyCheapest,
    PacingBound,
    Simulation,
    SimulationReport,
    Terminal,
    format_text_report,
)

from lingua_perdita.constants import (
    PACING_ALL_WORDS_MAX,
    PACING_ALL_WORDS_MIN,
    PACING_FIRST_ROOT_MAX,
    PACING_FIRST_ROOT_MIN,
    PACING_FIRST_WORD_MAX,
    PACING_FIRST_WORD_MIN,
    PACING_MAX_DEAD_TIME_RATIO,
    PACING_MAX_EARLY_GAP,
    PACING_MAX_LATE_GAP,
    SIM_CLICK_RATE,
    SIM_TICK_RESOLUTION,
    SIM_TIME_CAP,
)
from lingua_perdita.game_def import build_definition
from lingua_perdita.language import LanguageModel, generate_language


def build_pacing_bounds(language: LanguageModel) -> list[PacingBound]:
    """Build pacing bounds for simulation validation."""
    all_word_ids = [w.id for w in language.word_list]
    root_ids = [f"root_{r.id}" for r in language.root_list]

    bounds = [
        # No stalls
        PacingBound.no_stalls(severity="error"),

        # First word timing
        PacingBound.milestone_between(
            "first_word", PACING_FIRST_WORD_MIN, PACING_FIRST_WORD_MAX,
            severity="error",
        ),

        # First root discovery
        PacingBound.milestone_between(
            f"root_{language.root_list[0].id}",
            PACING_FIRST_ROOT_MIN, PACING_FIRST_ROOT_MAX,
            severity="warning",
        ),

        # All words translated — use total_time since the terminal fires on the
        # same tick as the last word purchase, before the milestone can evaluate
        PacingBound.custom(
            condition=lambda r: PACING_ALL_WORDS_MIN <= r.total_time <= PACING_ALL_WORDS_MAX,
            description=f"Total time {PACING_ALL_WORDS_MIN:.0f}-{PACING_ALL_WORDS_MAX:.0f}s",
            severity="error",
        ),

        # Purchase gap limits
        PacingBound.max_gap_between_purchases(
            PACING_MAX_EARLY_GAP, after_time=0.0, severity="warning",
        ),

        # Dead time ratio
        PacingBound.dead_time_ratio(
            PACING_MAX_DEAD_TIME_RATIO, severity="warning",
        ),
    ]

    return bounds


def run_simulation(
    seed: int = 42,
    verbose: bool = True,
) -> tuple[SimulationReport, list[PacingBound]]:
    """Run the economy simulation and return results."""
    language = generate_language(seed)
    definition = build_definition(language)

    all_word_ids = [w.id for w in language.word_list]

    strategy = GreedyCheapest(
        click_profile=ClickProfile(targets={"insight": SIM_CLICK_RATE}),
    )

    terminal = Terminal.any(
        Terminal.all_purchased(element_ids=all_word_ids),
        Terminal.time(SIM_TIME_CAP),
    )

    sim = Simulation(
        definition=definition,
        strategy=strategy,
        terminal=terminal,
        tick_resolution=SIM_TICK_RESOLUTION,
        seed=seed,
    )

    report = sim.run()
    bounds = build_pacing_bounds(language)

    if verbose:
        print(format_text_report(report, bounds))
        print()

        # Print purchase log (first 30 and last 10)
        print("PURCHASE LOG (first 30):")
        for p in report.purchases[:30]:
            mins = p.time / 60
            print(f"  {mins:6.1f}m  {p.element_id:<25s}  cost={p.cost_paid}")
        if len(report.purchases) > 30:
            print(f"  ... ({len(report.purchases) - 40} more) ...")
            for p in report.purchases[-10:]:
                mins = p.time / 60
                print(f"  {mins:6.1f}m  {p.element_id:<25s}  cost={p.cost_paid}")

    return report, bounds


if __name__ == "__main__":
    run_simulation()
