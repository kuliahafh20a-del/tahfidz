"""Canonical memorization order for the 40 themes in Juz 30."""

PART_OFFSETS = {1: 0, 2: 10, 3: 18, 4: 24, 5: 29}

# Surahs are memorized from the end of Juz 30, while multiple themes that
# belong to the same surah retain their natural low-to-high ayah order.
MEMORIZATION_ASCENDING_ORDINALS = (
    40,
    39,
    38,
    37,
    36,
    35,
    34,
    33,
    32,
    31,
    30,
    29,
    28,
    27,
    26,
    25,
    24,
    22,
    23,
    21,
    20,
    19,
    17,
    18,
    16,
    14,
    15,
    13,
    11,
    12,
    8,
    9,
    10,
    4,
    5,
    6,
    7,
    1,
    2,
    3,
)


def _ascending_ordinal(part_sequence: int, theme_sequence: int) -> int:
    return PART_OFFSETS[part_sequence] + theme_sequence


def memorization_code(part_sequence: int, theme_sequence: int) -> str:
    """Number themes from the end of Juz 30, where the final theme is T01."""
    ascending_ordinal = _ascending_ordinal(part_sequence, theme_sequence)
    return f"T{MEMORIZATION_ASCENDING_ORDINALS.index(ascending_ordinal) + 1:02d}"


def memorization_sort_key(part_sequence: int, theme_sequence: int) -> tuple[int, int]:
    """Sort themes from the end of Juz 30 toward An-Naba."""
    ascending_ordinal = _ascending_ordinal(part_sequence, theme_sequence)
    return (MEMORIZATION_ASCENDING_ORDINALS.index(ascending_ordinal), 0)
