import boto3
import time
from datetime import timedelta
from boto3.dynamodb.conditions import Attr

class Domains:
    def __init__(self, name):
        dynamodb = boto3.resource('dynamodb')
        self.table = dynamodb.Table(name)

    def _cut_time(days_to_scan):
        return (time.time() - timedelta(days=days_to_scan).total_seconds()) * 1000

    def scanDomainNames(self, days_to_scan):
        fe = Attr('lastAccessEpoch').gte(self._cut_time(days_to_scan))
        items = []
        response = self.table.scan(FilterExpression = fe, ProjectionExpression = 'domainName')
        items.extend(response['Items'])
        while response['LastEvaluatedKey']:
            response = self.table.scan(FilterExpression = fe, ExclusiveStartKey = response['LastEvaluatedKey'])
            items.extend(response['Items'])
        return [e['domainName'] for e in items]
    
    def scanStatistics(self, days_to_scan):
        fe = Attr('lastAccessEpoch').gte(self._cut_time(days_to_scan))
        items = []
        response = self.table.scan(FilterExpression = fe)
        items.extend(response['Items'])
        while response['LastEvaluatedKey']:
            response = self.table.scan(FilterExpression = fe)
            items.extend(response['Items'])
        return items


    def batch_update_ping_statistics(self, continent, items):
        with self.table.batch_writer() as batch:
            for item in items:
                batch.update_item(
                    Key = {'domainName': item['domainName']},
                    UpdateExpression = f'SET ping_{continent} = :v',
                    ExpressionAttributeValues = {':v': item['statistics']})
                
    
    def update_domain(self, domain, access_epoch_ms):
        self.table.update_item(
            Key = {'domainName': domain},
            UpdateExpression = 'SET lastAccessEpoch = :v',
            ExpressionAttributeValues = {':v': access_epoch_ms})
