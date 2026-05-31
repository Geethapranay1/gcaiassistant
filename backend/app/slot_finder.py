from datetime import datetime

from app.mock_data import MOCK_CALENDAR


def get_common_slots(participants):
    if not participants:
        return []

    participant_slots = []
    for participant in participants:
        if participant not in MOCK_CALENDAR:
            return []
        participant_slots.append(
            {
                datetime.strptime(slot, "%Y-%m-%d %H:%M")
                for slot in MOCK_CALENDAR[participant]
            }
        )

    common_slots = participant_slots[0]
    for slots in participant_slots[1:]:
        common_slots &= slots

    return sorted(common_slots)


def find_common_slot(participants, duration_minutes):
    common = get_common_slots(participants)
    if not common:
        return None
    return common[0].strftime("%Y-%m-%d %H:%M")


def list_available_slots(participants):
    return [dt.strftime("%Y-%m-%d %H:%M") for dt in get_common_slots(participants)]
