import pytest


def test_x_api_fetch_chunk(x_api, create_appointment_data):
    app_1 = create_appointment_data(1)
    app_2 = create_appointment_data(2)
    x_api.CHUNK_SIZE = 1
    x_api.PAGE_SIZE = 1
    x_api.RAW_APPOINTMENTS = [
        app_1,
        app_2,
    ]

    gen = x_api.fetch()

    assert next(gen) == [app_1]
    assert next(gen) == [app_2]
    with pytest.raises(StopIteration):
        next(gen)


def test_x_api_fetch_chunk_if_no_data(x_api):
    x_api.CHUNK_SIZE = 1
    x_api.PAGE_SIZE = 1
    x_api.RAW_APPOINTMENTS = []

    gen = x_api.fetch()

    with pytest.raises(StopIteration):
        next(gen)

