"""Email priority classification based on rules."""
import logging

logger = logging.getLogger("digital_fte.priority")

URGENCY_KEYWORDS = ["urgent", "asap", "deadline", "overdue"]


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
    if vip_senders:
        sender_lower = sender.lower()
        for vip in vip_senders:
            if vip.lower() == sender_lower:
                return "high"

    return "normal"
