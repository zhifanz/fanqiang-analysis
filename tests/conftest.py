import pytest
import os


from google.cloud import bigquery


@pytest.fixture(scope="package")
def bigquery_client() -> bigquery.Client:
    dataset_ref = bigquery.DatasetReference(
        os.environ["TESTING_GOOGLE_CLOUD_PROJECT"], "minerule_integration_test"
    )
    client = bigquery.Client(
        default_query_job_config=bigquery.QueryJobConfig(default_dataset=dataset_ref)
    )
    client.create_dataset(dataset_ref)
    yield client
    client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
    client.close()
