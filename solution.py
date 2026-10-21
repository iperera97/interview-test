"""
# Todo:
- Use a thread pool to fetch pages in concurrently and cut waiting time.
- Add retry with exponential backoff (decorator) for 5xx errors. In production, i like to use tenacity library.
- In production, I like to use Polars for easier transformations and streaming processing
- Add a lint check (e.g. ruff) to catch style and code issues. Skipped this time due to limited time.

# Assumption:
- when doing resync, only status, date and time can change for an existing appt_id.
"""

import logging
import time
from collections.abc import Generator
from datetime import datetime
import sqlite3
from typing import Protocol

# init logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


############## Connectors ################

class APIConnector(Protocol):
    def fetch(self) -> Generator[list[dict], None, None]: ...

class DBConnector(Protocol):
    def execute(self, query: str, params=()) -> None: ...
    def executemany(self, query: str, params) -> None: ...
    def close(self): ...


class XAPIConnector:
    "Used for mock api calls"
    CHUNK_SIZE = 100
    RAW_APPOINTMENTS = [
        {"appt_id": "A001", "clinic": "paws_clinic", "owner": "john doe",
        "pet": "buddy", "date": "2024-04-15", "time": "09:00",
        "status": "completed", "duration_mins": "30"},

        {"appt_id": "A002", "clinic": "happy_vets", "owner": "  Jane Smith ",
        "pet": "whiskers", "date": "15-04-2024", "time": "10:30",
        "status": "NO_SHOW", "duration_mins": "45"},

        {"appt_id": "A003", "clinic": "paws_clinic", "owner": "alice brown",
        "pet": "rex", "date": "2024-04-15", "time": "14:00",
        "status": "scheduled", "duration_mins": "sixty"},

        {"appt_id": "A004", "clinic": "city_animal_care", "owner": "bob jones",
        "pet": "luna", "date": "2024-04-16", "time": "09:30",
        "status": "completed", "duration_mins": "20"},

        {"appt_id": None, "clinic": "happy_vets", "owner": "carol white",
        "pet": "milo", "date": "2024-04-16", "time": "11:00",
        "status": "completed", "duration_mins": "30"},

        {"appt_id": "A005", "clinic": "paws_clinic", "owner": "dave miller",
        "pet": "bella", "date": "2024-04-16", "time": "13:00",
        "status": "cancelled", "duration_mins": "30"},
    ]
    PAGE_SIZE = 10

    def fetch(self) -> Generator[list[dict]]:
        page = 1
        chunk = []

        while True:
            response = self._fetch_appointments(
                page=page, page_size=self.PAGE_SIZE
            )
            data = response["data"]
            page = response["page"] + 1

            if not data:
                break

            chunk.extend(data)

            if len(chunk) >= self.CHUNK_SIZE:
                yield chunk
                chunk = []

        if chunk:
            yield chunk

    def _fetch_appointments(self, page: int = 1, page_size: int = 3) -> dict:
        """Simulated paginated API with realistic latency."""
        time.sleep(0.05)
        start = (page - 1) * page_size
        end = start + page_size

        return {
            "page": page,
            "page_size": page_size,
            "total": len(self.RAW_APPOINTMENTS),
            "data": self.RAW_APPOINTMENTS[start:end],
        }

class SQLITEConnector:

    def __init__(self, path="test.db") -> None:
        self.connection = sqlite3.connect(path)

    def execute(self, query: str, params=()):
        with self.connection:
            self.connection.execute(query, params)

    def executemany(self, query: str, params=()) -> None:
        with self.connection:
            self.connection.executemany(query, params)

    def close(self):
        self.connection.close()


############## Transformations Related to Appoinment Data / Domain ################

class BaseTransformation:

    def transform(self, data: list[dict]) -> list[dict]:
        return data

class AppoinmentTransformation(BaseTransformation):

    def transform(self, data: list[dict]) -> list[dict]:
        cleaned_data = []

        for row in data:
            if not self.has_appoinment_id(row):
                logger.warning(f"appoinment record skipped due to unable to find appt id")
                continue

            if not self.clean_date(row):
                logger.warning(
                    f"appoinment record skipped due to unable to parse "
                    f"the date - {row.get('date')} "
                )
                continue

            self.rename_col_name(row, "clinic", "clinic_id")
            self.rename_col_name(row, "owner", "owner_name")
            self.rename_col_name(row, "pet", "pet_name")
            self.rename_col_name(row, "date", "appointment_date")
            self.rename_col_name(row, "time", "appointment_time")

            self.clean_owner_name(row)
            self.clean_duration(row)
            self.clean_status(row)

            cleaned_data.append(row)

        return cleaned_data

    def rename_col_name(
        self,
        row: dict,
        col_name: str,
        rename_col_name: str
    ):
        row[rename_col_name] = row.pop(col_name)

    def has_appoinment_id(self, row: dict) -> bool:
        return bool(row.get("appt_id"))

    def clean_owner_name(self, row: dict):
        if owner := row.get("owner_name"):
            owner = str(owner)
            row["owner_name"] = owner.strip().title()

    def clean_date(self, row: dict) -> bool:
        try:
            row["date"] = str(datetime.strptime(row["date"], "%Y-%m-%d").date())
            return True
        except (ValueError, AttributeError, KeyError, TypeError):
            return False

    def clean_duration(self, row: dict):
        try:
            row["duration_mins"] = int(row["duration_mins"])
        except (ValueError, KeyError):
            logger.warning(
                f"unable to parse to int in duration_mins {row.get('duration_mins')}"
            )
            row["duration_mins"] = None

    def clean_status(self, row: dict):
        if status := row.get("status"):
            status = str(status)
            row["status"] = status.lower()


############## Loaders Related to Appoinment Data / Domain ################

class BaseLoader:

    def __init__(self, connector: DBConnector):
        self.connector = connector

    def load(self, data: list[dict]):
        ...

    def setup(self):
        ...

class AppoinmentLoader(BaseLoader):

    def setup(self):
        query = """
        CREATE TABLE IF NOT EXISTS appointments (
            appt_id          TEXT PRIMARY KEY,
            clinic_id        TEXT NOT NULL,
            owner_name       TEXT NOT NULL,
            pet_name         TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            status           TEXT NOT NULL,
            duration_mins    INTEGER
        );
        """
        self.connector.execute(query)

    def load(self, data: list[dict]) -> None:
        if not data:
            return

        query = """
        INSERT INTO appointments (
            appt_id, clinic_id, owner_name, pet_name,
            appointment_date, appointment_time, status, duration_mins
        )
        VALUES (
            :appt_id, :clinic_id, :owner_name, :pet_name,
            :appointment_date, :appointment_time, :status, :duration_mins
        )
        ON CONFLICT(appt_id) DO UPDATE SET
            status           = excluded.status,
            appointment_date = excluded.appointment_date,
            appointment_time = excluded.appointment_time
        """
        self.connector.executemany(query, data)


############## Workflow to run the data pipline ################

class Workflow:

    def __init__(
        self,
        source_connector: APIConnector,
        target_connector: DBConnector,
        transformation: BaseTransformation,
        loader: BaseLoader
    ) -> None:
        self.source_connector = source_connector
        self.target_connector = target_connector
        self.transformation = transformation
        self.loader = loader
        self.total_records = 0

    def run(self):
        started_time = time.perf_counter()
        try:
            logger.info("workflow started")
            self.loader.setup()
            
            for chunk in self.source_connector.fetch():
                clean_data = self.transformation.transform(chunk)
                self.loader.load(clean_data)
                self.total_records += len(clean_data)
            
            logger.info(
                f"workflow completed successfully in "
                f"{time.perf_counter() - started_time:.2f}s"
                f"with {self.total_records} records"
            )
            return True
        except Exception as err:
            logger.critical(
                f"workflow failed due to {err} in "
                f"{time.perf_counter() - started_time:.2f}s "
                f"with {self.total_records} records"
            )
            return False

    def clean_up_resources(self):
        self.target_connector.close()
            

if __name__ == "__main__":
    target_connector = SQLITEConnector()

    workflow = Workflow(
        source_connector=XAPIConnector(),
        target_connector=target_connector,
        transformation=AppoinmentTransformation(),
        loader=AppoinmentLoader(target_connector)
    )
    workflow.run()
    workflow.clean_up_resources()