from typing import Callable
from google.cloud.bigquery import (
    Client,
    SchemaField,
    DatasetReference,
    QueryJobConfig,
    ScalarQueryParameter,
    SqlTypeNames,
)
from datetime import datetime
from .utiltypes import TimeWindow


class SocketEventRepository:
    SCHEMA = [
        SchemaField("host", "STRING", mode="REQUIRED"),
        SchemaField("port", "INT64", mode="REQUIRED"),
        SchemaField("access_timestamp", "TIMESTAMP", mode="REQUIRED"),
    ]
    TABLE_NAME = "socketevents"

    def __init__(self, client: Client, dataset_id: str) -> None:
        self.client = client
        self.dataset_ref = DatasetReference.from_string(dataset_id, client.project)

    @classmethod
    def create_instance(cls, dataset_id: str, project: str = None):
        client = Client(project) if project else Client()
        return cls(client, dataset_id)

    def _query_parameter(self, value) -> ScalarQueryParameter:
        type_name: str
        if type(value) == int:
            type_name = SqlTypeNames.INT64
        elif type(value) == str:
            type_name = SqlTypeNames.STRING
        elif type(value) == datetime:
            type_name = SqlTypeNames.TIMESTAMP
        else:
            raise RuntimeError("Can not recognize value type: " + type(value))
        return ScalarQueryParameter(None, type_name, value)

    def _query(self, sql: str, result_extractor: Callable, *params):
        return result_extractor(
            self.client.query(
                sql,
                job_config=QueryJobConfig(
                    default_dataset=self.dataset_ref,
                    query_parameters=[self._query_parameter(param) for param in params],
                ),
            )
        )

    def aggregate_on_hosts(self, tw: TimeWindow) -> set[str]:
        return self._query(
            "SELECT DISTINCT host from socketevents WHERE access_timestamp >= ? AND access_timestamp < ?",
            lambda job: {row.host for row in job},
            datetime.utcfromtimestamp(tw.from_time),
            datetime.utcfromtimestamp(tw.to_time),
        )

    def find_correlated_hosts(self, host: str, diff_seconds: int = 30) -> set[str]:
        return self._query(
            """
            SELECT DISTINCT host
            FROM (
                SELECT
                    host,
                    COUNT(DISTINCT group_id) OVER (PARTITION BY host) / COUNT(DISTINCT group_id) OVER () AS scoring
                FROM (
                    SELECT DISTINCT c.group_id, a.host
                    FROM (
                        SELECT *, ROW_NUMBER() OVER (ORDER BY access_timestamp) AS group_id
                        FROM socketevents
                        WHERE host = ?
                        QUALIFY COUNT(*) OVER() > 1
                    ) AS c, socketevents AS a
                    WHERE
                        a.host != c.host AND
                        ABS(TIMESTAMP_DIFF(c.access_timestamp, a.access_timestamp, SECOND)) <= ?
                ) t
            ) t
            WHERE scoring > 0.95
        """,
            lambda job: {row.host for row in job},
            host,
            diff_seconds,
        )
