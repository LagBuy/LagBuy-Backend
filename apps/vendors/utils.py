import csv
from io import StringIO


def build_lost_customers_csv(users, last_map):
    """Return CSV bytes for given users and last_purchase mapping.

    Args:
        users: iterable of CustomUser objects (with optional user_profile relation)
        last_map: dict mapping user id -> last_p urchase datetime

    Returns:
        bytes: UTF-8 encoded CSV bytes
    """
    csv_buffer = StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(["id", "email", "first_name", "last_name", "last_purchase"])
    for u in users:
        lp = last_map.get(str(u.id)) or last_map.get(u.id)
        writer.writerow(
            [
                str(u.id),
                u.email,
                getattr(getattr(u, "user_profile", None), "first_name", ""),
                getattr(getattr(u, "user_profile", None), "last_name", ""),
                lp.isoformat() if lp is not None else "",
            ]
        )
    return csv_buffer.getvalue().encode("utf-8")
