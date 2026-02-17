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


def test_classify_high_on_vip_sender():
    """Emails from VIP senders should be high priority."""
    result = classify_priority(
        subject="Hello", body="Regular message.",
        sender="ceo@company.com", vip_senders=["ceo@company.com"],
    )
    assert result == "high"


def test_classify_vip_sender_case_insensitive():
    """VIP sender matching should be case-insensitive."""
    result = classify_priority(
        subject="Hello", body="",
        sender="CEO@Company.com", vip_senders=["ceo@company.com"],
    )
    assert result == "high"


def test_classify_normal_when_vip_list_empty():
    """Non-VIP sender with empty VIP list should be normal."""
    result = classify_priority(
        subject="Hello", body="Regular message.",
        sender="someone@example.com", vip_senders=[],
    )
    assert result == "normal"


def test_classify_normal_when_vip_list_none():
    """When vip_senders is None, VIP check should be skipped."""
    result = classify_priority(
        subject="Hello", body="",
        sender="ceo@company.com", vip_senders=None,
    )
    assert result == "normal"
