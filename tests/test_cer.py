from evaluation.cer import character_error_rate, edit_distance


def test_edit_distance_counts_character_changes() -> None:
    assert edit_distance("кот", "кит") == 1


def test_cer_ignores_extra_whitespace() -> None:
    assert character_error_rate("мой конспект", "мой   конспект\n") == 0


def test_cer_handles_empty_reference() -> None:
    assert character_error_rate("", "текст") == 1
