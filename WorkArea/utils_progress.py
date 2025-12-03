import sys


def print_progress_bar(current: int, total: int, label: str = "", bar_length: int = 24) -> None:
    """
    Simple ASCII progress bar in a single terminal line.

    Example:
        Building trade list: [##########------------] 41.7%
    """
    if total <= 0:
        return

    # Clamp to [0, 1]
    fraction = float(current) / float(total)
    if fraction < 0.0:
        fraction = 0.0
    elif fraction > 1.0:
        fraction = 1.0

    filled_len = int(bar_length * fraction)
    bar = "#" * filled_len + "-" * (bar_length - filled_len)
    percent = fraction * 100.0

    line = f"\r{label}: [{bar}] {percent:5.1f}%"
    sys.stdout.write(line)
    sys.stdout.flush()

    # Once complete, move to next line
    if current >= total:
        sys.stdout.write("\n")
        sys.stdout.flush()
