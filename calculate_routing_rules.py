import os
import boto3
from domains import Domain, DomainRepository

Rules = dict[str, list[str]]


def to_yaml_payload(domains):
    if domains:
        return 'payload:' + ''.join([f'\n  - {d}' for d in domains])
    else:
        return 'payload: []'


def save_bucket(rules: Rules) -> None:
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(os.environ['BUCKET'])
    for key in rules:
        bucket.put_object(
            ACL='public-read',
            Body=to_yaml_payload(rules[key]).encode(),
            ContentType='text/plain',
            Key=f"{os.environ['CONFIG_ROOT_PATH']}/domains_{key}.yaml"
        )


def routing_rules(items: list[Domain], continents: list[str]) -> Rules:
    rules = {'domestic': []}
    for c in continents:
        rules[c] = []
    for item in items:
        if item.globalPingResults.available_from_domestic():
            rules['domestic'].append(item.domainName)
            continue
        fast_continent = item.globalPingResults.select_fast_proxy()
        if fast_continent:
            rules[fast_continent].append(item.domainName)
    return rules


def handler(event, context):
    repository = DomainRepository(os.environ['DYNAMODB_TABLE'])
    continents = os.environ['CONTINENTS'].split(',')
    rules = routing_rules(repository.scan(
        int(os.environ['DAYS_TO_SCAN'])), continents)
    save_bucket(rules)
