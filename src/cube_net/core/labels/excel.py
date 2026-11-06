"""Spreadsheet-style column names: A, B, ..., Z, AA, AB, ..., AZ, BA, ..., ZZ, AAA, ..."""


def excel_label(index: int) -> str:
    """The name of column number `index` (0 -> "A", 25 -> "Z", 26 -> "AA")."""
    if index < 0:
        raise ValueError(f"index must be non-negative, got {index}")
    letters = []
    n = index + 1
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        letters.append(chr(ord("A") + remainder))
    return "".join(reversed(letters))
