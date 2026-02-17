"""Email priority classification based on rules."""
import logging

logger = logging.getLogger("digital_fte.priority")

URGENCY_KEYWORDS = ["urgent", "asap", "deadline", "overdue"]

NEWSLETTER_PATTERNS = ["noreply@", "no-reply@", "newsletter@", "notifications@", "mailer-daemon@"]


def classify_priority(
    subject: str = "",
    body: str = "",
    sender: str = "",
    vip_senders: list[str] | None = None,
) -> str:
    """Classify email priority as 'high', 'normal', or 'low'.

    Rules (evaluated in order):
    - High: urgency keyword in subject/body OR sender in VIP list
    - Low: sender matches newsletter/notification patterns
    - Normal: everything else
    """
    subject_lower = subject.lower()
    body_lower = body.lower()

    # Check urgency keywords
    for keyword in URGENCY_KEYWORDS:
        if keyword in subject_lower or keyword in body_lower:
            return "high"

    # Check VIP senders
    sender_lower = sender.lower()
    if vip_senders:
        for vip in vip_senders:
            if vip.lower() == sender_lower:
                return "high"

    # Check newsletter/notification patterns
    for pattern in NEWSLETTER_PATTERNS:
        if pattern in sender_lower:
            return "low"

    return "normal"
