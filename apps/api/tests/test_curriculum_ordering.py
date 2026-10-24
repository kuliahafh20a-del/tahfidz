from app.modules.curriculum.ordering import memorization_code, memorization_sort_key


def test_theme_codes_start_from_the_end_of_juz_30() -> None:
    assert memorization_code(5, 11) == "T01"
    assert memorization_code(5, 10) == "T02"
    assert memorization_code(1, 1) == "T38"
    assert memorization_code(1, 2) == "T39"
    assert memorization_code(1, 3) == "T40"


def test_memorization_sort_key_orders_later_surahs_first() -> None:
    themes = [(1, 3), (1, 1), (5, 10), (5, 11), (1, 2)]

    assert sorted(themes, key=lambda item: memorization_sort_key(*item)) == [
        (5, 11),
        (5, 10),
        (1, 1),
        (1, 2),
        (1, 3),
    ]
