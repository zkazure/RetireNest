"""让 `python -m yishizhuxing` 可用。"""

import sys

from yishizhuxing.cli import run

if __name__ == "__main__":
    run(sys.argv)
