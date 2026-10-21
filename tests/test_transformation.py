import pytest


def test_transformation_has_appoinment_id(
    appoinment_transformation,
    create_appointment_data
):
    assert not appoinment_transformation.has_appoinment_id(
        create_appointment_data(appt_id=None)
    )
    assert appoinment_transformation.has_appoinment_id(
        create_appointment_data(1)
    )


def test_transformation_drop_if_null_on_appt_id(
    create_appointment_data,
    appoinment_transformation
):
    data = [
        create_appointment_data(appt_id=None),
        create_appointment_data(1),
        create_appointment_data(2),
        create_appointment_data(appt_id=None),
    ]
    cleaned_data = appoinment_transformation.transform(data)
    assert len(cleaned_data) == 2
    assert cleaned_data[0]["appt_id"]
    assert cleaned_data[1]["appt_id"]


def test_transformation_clean_owner_name(
    create_appointment_data,
    appoinment_transformation
):
    test_title = "   dave miller "
    data = create_appointment_data(1, owner_name=test_title)
    appoinment_transformation.clean_owner_name(data)

    assert data["owner_name"] == "Dave Miller"


@pytest.mark.parametrize(
    "raw, expected_result, expected_date",
    [
        ("2024-04-15", True, "2024-04-15"),
        ("15-04-2024", False, "15-04-2024"),
        ("xxxx", False, "xxxx"),
        ("", False, ""),
        (None, False, None),
    ],
)
def test_transformation_clean_date(
    create_appointment_data,
    appoinment_transformation,
    raw,
    expected_result,
    expected_date,
):
    data = create_appointment_data(1, date=raw)

    assert appoinment_transformation.clean_date(data) is expected_result
    assert data["date"] == expected_date


def test_transformation_drop_if_invalid_date(
    create_appointment_data,
    appoinment_transformation     
):
    data = [
        create_appointment_data(1, date="2024-04-15"),
        create_appointment_data(1, date="05-04-2024"),
        create_appointment_data(1, date="xxxx"),
        create_appointment_data(1, date=None)
    ]
    cleaned_data = appoinment_transformation.transform(data)

    assert len(cleaned_data) == 1



@pytest.mark.parametrize(
    "raw, expected",
    [
        ("30", 30),
        ("45", 45),
        (30, 30),
        ("xxx", None),
        ("", None),
        ("30.5", None),
    ],
)
def test_transformation_duration(
    create_appointment_data,
    appoinment_transformation,
    raw,
    expected,
):
    data = create_appointment_data(1, duration_mins=raw)
    appoinment_transformation.clean_duration(data)

    assert data["duration_mins"] == expected

@pytest.mark.parametrize(
    "raw, expected",
    [
        ("completed", "completed"),
        ("NO_SHOW", "no_show"),
        ("Scheduled", "scheduled"),
        ("CANCELLED", "cancelled"),
        (None, None),
    ],
)
def test_transformation_clean_status(
    create_appointment_data,
    appoinment_transformation,
    raw,
    expected,
):
    data = create_appointment_data(1, status=raw)
    appoinment_transformation.clean_status(data)

    assert data["status"] == expected