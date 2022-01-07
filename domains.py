import boto3
import time
import sys
from datetime import timedelta
from boto3.dynamodb.conditions import Attr


class PingStatistics:
    def __init__(self) -> None:
        self.destPublicIp = None
        self.transmitted = None
        self.received = None
        self.min = None
        self.avg = None
        self.max = None
        self.mdev = None


class PingResult:
    def __init__(self, code: int, message: str, statistics: PingStatistics) -> None:
        self.code = code
        self.message = message
        self.statistics = statistics

    def is_success(self):
        return self.code == 0 and self.statistics.transmitted == self.statistics.received

    def to_dict(self) -> dict:
        return {'code': self.code, 'message': self.message,
                'statistics': self.statistics.__dict__ if self.statistics else None}


class GlobalPingResults:
    def __init__(self, ping_results: dict[str, PingResult]) -> None:
        self.ping_results = ping_results

    def _available_from(self, key):
        return key in self.ping_results and self.ping_results[key].is_success()

    def available_from_domestic(self) -> bool:
        return self._available_from('domestic')

    def select_fast_proxy(self) -> str:
        if 'central' not in self.ping_results:
            return ''
        continent = 'central'
        min_avg = sys.float_info.max
        for k in self.ping_results:
            if k == 'domestic':
                continue
            if self.ping_results[k].code == 0 and self.ping_results[k].statistics.avg < min_avg:
                continent = k
                min_avg = self.ping_results[k].statistics.avg
        return None if continent == 'central' else continent


class Domain:
    def __init__(self, data) -> None:
        self.domainName = data['domainName']
        self.lastAccessEpoch = data['lastAccessEpoch']
        ping_results = {}
        for k in data['globalPingResults']:
            ping_result_dict = data['globalPingResults'][k]
            statistics = None
            if 'statistics' in ping_result_dict and ping_result_dict['statistics']:
                statistics = PingStatistics()
                statistics.__dict__.update(**ping_result_dict['statistics'])
            ping_results[k] = PingResult(ping_result_dict['code'], ping_result_dict['message'], statistics)
        self.globalPingResults = GlobalPingResults(ping_results)


class DomainRepository:
    def __init__(self, name, endpoint_url=None, region_name=None):
        dynamodb = boto3.resource('dynamodb', endpoint_url=endpoint_url, region_name=region_name)
        self.table = dynamodb.Table(name)

    def _cut_time(self, days_to_scan) -> int:
        return int(time.time() - timedelta(days=days_to_scan).total_seconds()) * 1000

    def scan_domain_names(self, days_to_scan) -> list[str]:
        fe = Attr('lastAccessEpoch').gte(self._cut_time(days_to_scan))
        items = []
        response = self.table.scan(
            FilterExpression=fe, ProjectionExpression='domainName')
        items.extend(response['Items'])
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(
                FilterExpression=fe, ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        return [e['domainName'] for e in items]

    def scan(self, days_to_scan) -> list[Domain]:
        fe = Attr('lastAccessEpoch').gte(self._cut_time(days_to_scan))
        items = []
        response = self.table.scan(FilterExpression=fe)
        items.extend(response['Items'])
        while 'LastEvaluatedKey' in response:
            response = self.table.scan(FilterExpression=fe, ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        return [Domain(e) for e in items]

    def _update(self, domain_name: str, key: str, ping_result: PingResult):
        self.table.update_item(
            Key={'domainName': domain_name},
            UpdateExpression=f'SET globalPingResults.{key} = :v',
            ExpressionAttributeValues={':v': ping_result.to_dict()})

    def update_domestic(self, domain_name: str, ping_result: PingResult):
        self._update(domain_name, 'domestic', ping_result)

    def update_auto(self, domain_name: str, ping_result: PingResult):
        self._update(domain_name, 'central', ping_result)

    def update_continent(self, domain_name: str, continent: str, ping_result: PingResult):
        self._update(domain_name, continent, ping_result)

    def update_domain(self, domain, access_epoch_ms):
        self.table.update_item(
            Key={'domainName': domain},
            UpdateExpression='SET lastAccessEpoch = :v1, globalPingResults = :v2',
            ExpressionAttributeValues={':v1': access_epoch_ms, ':v2': {}})
