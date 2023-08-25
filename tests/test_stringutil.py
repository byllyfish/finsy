from finsy.stringutil import minimum_edit_distance


def test_minimum_edit_distance():
    "Test the `minimum_edit_distance` function."

    examples = [
        ("", "", 0),
        ("a", "a", 0),
        ("a", "b", 1),
        ("a", "", 1),
        ("kitten", "sitting", 3),
        ("xx123456789", "123456789", 2),
        ("12345xx6789", "123456789", 2),
        ("123456789xx", "123456789", 2),
        ("123456x89", "123456789", 1),
        ("123456789", "abcdefghi", 9),
        ("123456789", "abcdef", 9),
        ("123", "3ab", 3),
        ("levenshtein", "frankenstein", 6),
        ("confide", "deceit", 6),
        ("flaw", "lawn", 2),
        ("example", "samples", 3),
        ("hello", "ello", 1),
        ("resume and cafe", "resumes and cafes", 2),
        (
            "a very long string that is meant to exceed",
            "another very long string that is meant to exceed",
            6,
        ),
    ]

    for str1, str2, result in examples:
        assert minimum_edit_distance(str1, str2) == result
        assert minimum_edit_distance(str2, str1) == result
