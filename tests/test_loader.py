import pytest

from unittest.mock import MagicMock
from solution import AppoinmentLoader


def fetch_all(db_connector):
    return db_connector.connection.execute(
        "SELECT * FROM appointments ORDER BY appt_id"
    ).fetchall()


def test_setup_creates_table(appoinment_loader, db_connector):
    row = db_connector.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'"
    ).fetchone()
    assert row[0]


def test_load_empty_list_does_nothing():
    connector = MagicMock()
    AppoinmentLoader(connector).load([])
    connector.executemany.assert_not_called()


def test_load_inserts_all_rows(
    appoinment_transformation,
    appoinment_loader,
    db_connector,
    create_appointment_data
):
    data = [
        create_appointment_data(1),
        create_appointment_data(2)
    ]
    cleaned_data = appoinment_transformation.transform(data)
    appoinment_loader.load(cleaned_data)
    rows = fetch_all(db_connector)
    assert len(rows) == 2