import sys
import os

# Allow running directly with: python db/main.py
# by ensuring the project root is on sys.path
if __name__ == "__main__" and __package__ is None:
    _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, _root)
    __package__ = "db"

from .config import Config
from .app import App


def main():
    config = Config.from_env()
    try:
        app = App(config)
        app.run()
    finally:
        config.close()


if __name__ == "__main__":
    main()
