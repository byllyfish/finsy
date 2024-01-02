import doctest
from pathlib import Path

import pytest

DOCS = Path(__file__).parents[1] / "docs"

DOC_FILES = [
    DOCS / "table_entry.md",
    DOCS / "replication_entry.md",
    DOCS / "packets.md",
]


@pytest.mark.parametrize("path", DOC_FILES)
def test_docs(path: Path):
    "Test the console examples in the documentation."
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner()

    test = parser.get_doctest(path.read_text("utf-8"), {}, path.name, None, None)
    for ex in test.examples:
        # P4Runtime text representation always adds an extra blank line at the
        # end. Make sure we match '<BLANKLINE>' because '\n' ends the pattern.
        if ex.want.endswith("\n}\n"):
            ex.want += "<BLANKLINE>\n"

    runner.run(test)

    assert not runner.failures
