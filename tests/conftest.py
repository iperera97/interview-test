import pytest

from solution import (
    XAPIConnector,
    AppoinmentTransformation,
    SQLITEConnector,
    AppoinmentLoader,
    Workflow
)


@pytest.fixture
def x_api() -> XAPIConnector:
    return XAPIConnector()


@pytest.fixture
def db_connector():
    conn = SQLITEConnector(":memory:")
    yield conn
    conn.connection.close()


@pytest.fixture
def appoinment_transformation() -> AppoinmentTransformation:
    return AppoinmentTransformation()


@pytest.fixture
def appoinment_loader(db_connector):
    loader = AppoinmentLoader(db_connector)
    loader.setup()
    return loader


@pytest.fixture
def workflow(
    x_api,
    db_connector,
    appoinment_transformation,
    appoinment_loader
):
    return Workflow(
        source_connector=x_api,
        target_connector=db_connector,
        transformation=appoinment_transformation,
        loader=appoinment_loader
    )


@pytest.fixture
def create_appointment_data():
    def _make(n: int = 1, **overrides) -> dict:
        appt = {
            "appt_id": f"A{n}",
            "clinic": "paws_clinic",
            "owner": "john doe",
            "pet": "buddy",
            "date": "2024-04-15",
            "time": "09:00",
            "status": "completed",
            "duration_mins": "30",
        }
        appt.update(overrides)
        return appt

    return _make