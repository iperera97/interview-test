import pytest
from solution import Workflow


def fetch_all(db_connector):
    return db_connector.connection.execute(
        "SELECT * FROM appointments ORDER BY appt_id"
    ).fetchall()

def fetch_one(db_connector, appt_id):
    return db_connector.connection.execute(
        "SELECT * FROM appointments WHERE appt_id = ?", (appt_id,)
    ).fetchone()

def test_workflow_insert(workflow, create_appointment_data):
    app_1 = create_appointment_data(1)
    app_2 = create_appointment_data(2)
    workflow.source_connector.CHUNK_SIZE = 1
    workflow.source_connector.PAGE_SIZE = 1
    workflow.source_connector.RAW_APPOINTMENTS = [
        app_1,
        app_2,
    ]

    assert workflow.run() == True
    assert len(fetch_all(workflow.target_connector)) == 2


def test_workflow_update(workflow, create_appointment_data):
    app_1 = create_appointment_data(1)
    app_2 = create_appointment_data(2)
    workflow.source_connector.CHUNK_SIZE = 1
    workflow.source_connector.PAGE_SIZE = 1
    workflow.source_connector.RAW_APPOINTMENTS = [
        app_1,
        app_2,
    ]

    # first and second attempts
    assert workflow.run() == True
    assert workflow.run() == True
    assert len(fetch_all(workflow.target_connector)) == 2

    # rerun again with the updated data
    workflow.source_connector.RAW_APPOINTMENTS = [
        create_appointment_data(1, status="cancelled")
    ]
    assert workflow.run() == True
    assert len(fetch_all(workflow.target_connector)) == 2
    assert fetch_one(workflow.target_connector, "A1")[6] == "cancelled"



