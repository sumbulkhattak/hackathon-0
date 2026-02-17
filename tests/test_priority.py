"""Tests for email priority classification."""
import pytest

from src.priority import classify_priority


def test_classify_high_on_urgency_keyword_in_subject():
    """Emails with urgency keywords in subject should be high priority."""
    result = classify_priority(subject="URGENT: Please review", body="", sender="someone@example.com")
    assert result == "high"


def test_classify_high_on_urgency_keyword_in_body():
    """Emails with urgency keywords in body should be high priority."""
    result = classify_priority(subject="Review needed", body="This is asap, please handle.", sender="someone@example.com")
    assert result == "high"


def test_classify_high_is_case_insensitive():
    """Urgency keyword detection should be case-insensitive."""
    result = classify_priority(subject="DeAdLiNe approaching", body="", sender="someone@example.com")
    assert result == "high"


def test_classify_normal_without_keywords():
    """Emails without urgency keywords should be normal priority."""
    result = classify_priority(subject="Weekly update", body="Here is the weekly report.", sender="someone@example.com")
    assert result == "normal"
