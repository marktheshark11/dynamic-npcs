class Display:
    """Terminal display formatting helpers."""

    @staticmethod
    def header(title: str) -> None:
        print(f"\n=== {title} ===")

    @staticmethod
    def success(msg: str) -> None:
        print(f"\n* {msg}")

    @staticmethod
    def error(msg: str) -> None:
        print(f"\nx {msg}")

    @staticmethod
    def info(msg: str) -> None:
        print(f"  {msg}")

    @staticmethod
    def list_items(items: list, display_fn=None) -> None:
        """Print a numbered list of items."""
        for idx, item in enumerate(items, 1):
            text = display_fn(item) if display_fn else str(item)
            print(f"  {idx}. {text}")
