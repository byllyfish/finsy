import doctest
from pathlib import Path

import pytest

DOCS = Path(__file__).parent.parent / "docs"

DOC_FILES = [DOCS / "p4tableentry.md"]


@pytest.mark.parametrize("path", DOC_FILES)
def test_docs(path: Path):
    "Test the console examples in the documentation."
    parser = doctest.DocTestParser()
    runner = doctest.DocTestRunner()

    test = parser.get_doctest(path.read_text(), {}, path.name, None, None)
    for ex in test.examples:
        if ex.want.endswith("\n}\n"):
            ex.want += "<BLANKLINE>\n"

    runner.run(test)

    assert not runner.failures
