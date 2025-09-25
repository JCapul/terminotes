from __future__ import annotations

from terminotes.utils.tags import extract_hashtags


def test_extract_basic_and_deduplicate() -> None:
    text = "This is a #Test with #test and #Another_tag."
    assert extract_hashtags(text) == ("test", "another_tag")


def test_does_not_match_headings_or_inline_hash() -> None:
    text = "# Heading\nC# is a language. Use #tags in text. #another"
    # '# Heading' should not match; 'C#' should not match due to preceding 'C'
    assert extract_hashtags(text) == ("tags", "another")


def test_punctuation_boundaries() -> None:
    text = "check this: (#Tag), and end with #end."
    assert extract_hashtags(text) == ("tag", "end")
