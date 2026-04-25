from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    LEAD_FOUND = "lead_found"
    QUALIFIED = "qualified"
    OUTREACHED = "outreached"
    REPLIED = "replied"
    INTERESTED = "interested"
    PAID = "paid"
    SUBMITTED = "submitted"
    GENERATED = "generated"
    SENT = "sent"
    FAILED = "failed"


@dataclass
class StateMachineService:
    current_state: EventType = EventType.LEAD_FOUND

    allowed_transitions = {
        EventType.LEAD_FOUND: {EventType.QUALIFIED, EventType.FAILED},
        EventType.QUALIFIED: {EventType.OUTREACHED, EventType.FAILED},
        EventType.OUTREACHED: {EventType.REPLIED, EventType.FAILED},
        EventType.REPLIED: {EventType.INTERESTED, EventType.FAILED},
        EventType.INTERESTED: {EventType.PAID, EventType.FAILED},
        EventType.PAID: {EventType.SUBMITTED, EventType.FAILED},
        EventType.SUBMITTED: {EventType.GENERATED, EventType.FAILED},
        EventType.GENERATED: {EventType.SENT, EventType.FAILED},
        EventType.SENT: set(),
        EventType.FAILED: set(),
    }

    def apply_event(self, target_state: EventType) -> EventType:
        if target_state == self.current_state:
            return self.current_state
        allowed = self.allowed_transitions.get(self.current_state, set())
        if target_state not in allowed:
            return self.current_state
        self.current_state = target_state
        return self.current_state
