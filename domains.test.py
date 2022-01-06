import time
import unittest
from decimal import Decimal

import boto3

from domains import Domain, PingResult, PingStatistics, DomainRepository


def create_dynamodb_table(table, endpoint_url):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    dynamodb.create_table(
        TableName=table,
        KeySchema=[
            {
                'AttributeName': 'domainName',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'domainName',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )


def delete_dynamodb_table(table, endpoint_url):
    dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url)
    dynamodb.Table(table).delete()


class Foo:
    def __init__(self) -> None:
        self.k1 = None
        self.k2 = None


class TestMain(unittest.TestCase):
    def test_create(self):
        self.assertIsNotNone(Foo())

    def test_json_to_object(self):
        foo = Foo()
        foo.__dict__.update(**{'k1': 7, 'k2': 12})
        self.assertEqual(7, foo.k1)

    def test_ping_result_to_dict(self):
        s = PingStatistics()
        s.destPublicIp = '8.8.8.8'
        s.transmitted = 10
        s.received = 9
        s.avg = 12.34
        s.min = 10.81
        s.max = 15.09
        s.mdev = 10.71
        d = PingResult(0, 'success', s).to_dict()
        self.assertEqual(0, d['code'])
        self.assertEqual('success', d['message'])
        self.assertEqual('8.8.8.8', d['statistics']['destPublicIp'])
        self.assertEqual(10, d['statistics']['transmitted'])
        self.assertEqual(9, d['statistics']['received'])
        self.assertEqual(12.34, d['statistics']['avg'])
        self.assertEqual(10.81, d['statistics']['min'])
        self.assertEqual(15.09, d['statistics']['max'])
        self.assertEqual(10.71, d['statistics']['mdev'])

    def test_create_domain_from_dict(self):
        d = Domain({'domainName': 'aws.amazon.com', 'lastAccessEpoch': 10000,
                    'globalPingResults': {'domestic': {'code': 0, 'message': 'success',
                                                       'statistics': {'destPublicIp': '8.8.8.8', 'transmitted': 10,
                                                                      'received': 9, 'avg': 12.43}},
                                          'eu': {'code': 1, 'message': 'failed'}}})
        self.assertEqual('aws.amazon.com', d.domainName)
        self.assertEqual(10000, d.lastAccessEpoch)
        self.assertEqual(0, d.globalPingResults.ping_results['domestic'].code)
        self.assertEqual('success', d.globalPingResults.ping_results['domestic'].message)
        self.assertIsNotNone(d.globalPingResults.ping_results['domestic'].statistics)
        self.assertEqual(1, d.globalPingResults.ping_results['eu'].code)
        self.assertIsNone(d.globalPingResults.ping_results['eu'].statistics)

    def test_domain_repository(self):
        create_dynamodb_table('domains', endpoint_url='http://localhost:8000')
        try:
            repository = DomainRepository('domains', endpoint_url='http://localhost:8000')
            repository.update_domain('google.com', int(time.time() * 1000))
            domain_names = repository.scan_domain_names(30)
            self.assertEqual(1, len(domain_names))
            self.assertTrue('google.com' in domain_names)
            repository.update_domestic('google.com', PingResult(2, 'not available', None))
            s = PingStatistics()
            s.transmitted = 10
            s.received = 10
            s.avg = Decimal('5.12')
            repository.update_auto('google.com', PingResult(0, 'success', s))
            s = PingStatistics()
            s.transmitted = 10
            s.received = 8
            s.avg = Decimal('10.56')
            repository.update_continent('google.com', 'eu', PingResult(0, 'success', s))
            domain = repository.scan(30)[0]
            self.assertEqual('google.com', domain.domainName)
            self.assertFalse(domain.globalPingResults.available_from_domestic())
            self.assertIsNone(domain.globalPingResults.select_fast_proxy())

        finally:
            delete_dynamodb_table('domains', endpoint_url='http://localhost:8000')


if __name__ == '__main__':
    unittest.main()
