"""Small deterministic records independent of the real workbook."""

from credit_risk.data.schema import BILL_COLUMNS, PAYMENT_COLUMNS, STATUS_COLUMNS


def make_record(client_id=1, target=0):
    record = {
        "client_id": client_id,
        "limit_bal": 1000,
        "sex": 2,
        "education": 2,
        "marriage": 1,
        "age": 30,
        "default_next_month": target,
    }
    record.update(zip(STATUS_COLUMNS, (-2, -1, 0, 1, 2, 3), strict=True))
    record.update(zip(BILL_COLUMNS, (-100, 0, 100, 200, 400, 600), strict=True))
    record.update(zip(PAYMENT_COLUMNS, (0, 10, 20, 30, 40, 50), strict=True))
    return record


def make_records(count=120):
    """Two-customer financial-profile groups, with deliberately mixed labels."""
    records = []
    for index in range(count):
        record = make_record(index + 1, int(index % 5 == 0))
        profile = index // 2
        record["limit_bal"] += profile * 100
        record["age"] += index % 20
        records.append(record)
    return records
