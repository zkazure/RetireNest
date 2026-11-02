"""让 `python -m living` 可用。"""

import sys

from living.cli import run

if __name__ == "__main__":
    run(sys.argv)
