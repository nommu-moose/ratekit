import pytest
from ratekit.func.mail.text_match import StringMatch


# Test standard string matching with partial match
def test_partial_match_standard():
    sm = StringMatch(pattern="test", match_against="this is a test string")
    assert sm.found is True
    assert sm.index == 10
    assert sm.matched_string == "this is a test string"
    assert sm.matched_groups == ["this is a test string"]


# Test standard string matching with complete match
def test_complete_match_standard():
    sm = StringMatch(pattern="test", match_against="test", complete_match=True)
    assert sm.found is True
    assert sm.index == 0
    assert sm.matched_string == "test"
    assert sm.matched_groups == ["test"]


# Test standard string matching with no match
def test_no_match_standard():
    sm = StringMatch(pattern="notfound", match_against="this is a test string")
    assert sm.found is False
    assert sm.index is None
    assert sm.matched_string is None
    assert sm.matched_groups == []


# Test regex matching with partial match
def test_partial_match_regex():
    sm = StringMatch(pattern=r"\d+", match_against="there are 123 numbers", is_regex=True)
    assert sm.found is True
    assert sm.index == 10
    assert sm.matched_string == "123"
    assert sm.matched_groups == []


# Test regex matching with complete match
def test_complete_match_regex():
    sm = StringMatch(pattern=r"\d+", match_against="123", is_regex=True, complete_match=True)
    assert sm.found is True
    assert sm.index == 0
    assert sm.matched_string == "123"
    assert sm.matched_groups == ["123"]


# Test regex matching with no match
def test_no_match_regex():
    sm = StringMatch(pattern=r"\d+", match_against="no numbers here", is_regex=True)
    assert sm.found is False
    assert sm.index is None
    assert sm.matched_string is None
    assert sm.matched_groups == []


# Test __bool__ method
def test_bool_method():
    sm = StringMatch(pattern="test", match_against="this is a test string")
    assert bool(sm) is True

    sm_no_match = StringMatch(pattern="nomatch", match_against="this is a test string")
    assert bool(sm_no_match) is False


# Test __eq__ method
def test_eq_method():
    sm = StringMatch(pattern="test", match_against="test")
    assert sm == "test"

    sm_no_match = StringMatch(pattern="nomatch", match_against="this is a test string")
    assert sm_no_match != "nomatch"


# Test __ne__ method
def test_ne_method():
    sm = StringMatch(pattern="test", match_against="test")
    assert sm != "different"

    sm_no_match = StringMatch(pattern="nomatch", match_against="this is a test string")
    assert sm_no_match == sm_no_match


if __name__ == "__main__":
    pytest.main()
