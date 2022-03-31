import os
import time
import pytest
from minerule.statistics import HostAccessStatistics, Repository


def delete_collection(coll_ref, batch_size=1000):
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f"Deleting doc {doc.id} => {doc.to_dict()}")
        doc.reference.delete()
        deleted = deleted + 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size)


@pytest.fixture
def repository() -> Repository:
    repo = Repository(os.environ["GCP_PROJECT"])
    yield repo
    delete_collection(repo.collection)


def test_save(repository: Repository):
    repository.save(HostAccessStatistics("baidu.com", time.time()))
    assert repository.exists("baidu.com")
    assert not repository.exists("google.com")
