"""Entry point: python -m lingua_perdita [simulate]"""

import sys


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "simulate":
        from lingua_perdita.simulate import run_simulation
        run_simulation()
    else:
        from lingua_perdita.ui.app import run_app
        run_app()


if __name__ == "__main__":
    main()
