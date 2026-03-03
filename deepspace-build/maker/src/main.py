"""
DeepSpace — Focus Timer Desktop App
Entry point. Run with: python main.py
"""

import logging
import sys
import os

# Ensure the src directory is on the path so sibling imports work
# regardless of where python is invoked from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui import DeepSpaceUI


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    _setup_logging()
    app = DeepSpaceUI()
    app.run()


if __name__ == "__main__":
    main()
