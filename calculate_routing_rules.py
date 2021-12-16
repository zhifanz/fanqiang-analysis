import os
import boto3
from domains import Domains

MAX_PING_MS = 10000

def to_yaml_payload(domains):
    if domains:
        return 'payload:' + ''.join([f'\n  - {d}' for d in domains])
    else:
        return 'payload: []'

def is_ping_success(ping):
    return ping and ping['code'] == 0 and ping['statistics']['transmitted'] == ping['statistics']['received']

def ping_key(candidate):
    ping = candidate['ping']
    if not ping or ping['code'] > 0:
        return MAX_PING_MS
    return ping['statistics']['avg']

def save_bucket(rules):
    s3 = boto3.client('s3')
    bucket = s3.Bucket(os.environ['BUCKET'])
    for r in rules:
        bucket.put_object(
            ACL = 'public-read',
            Body = to_yaml_payload(r['domains']).encode(),
            ContentType = 'text/plain',
            Key = f"{os.environ['CONFIG_ROOT_PATH']}/domains_{r['name']}.yaml"
        )

def routing_rules(items):
    cn = []
    ap = []
    eu = []
    for item in items:
        if is_ping_success(item.get('ping_cn')):
            cn.append(item['domainName'])
            continue
        
        candidates = [
            {'name': 'na', 'ping': item.get('ping_na')},
            {'name': 'ap', 'ping': item.get('ping_ap')},
            {'name': 'eu', 'ping': item.get('ping_eu')}
        ]
        candidates.sort(key=ping_key)
        if candidates[0]['name'] == 'ap':
            ap.append(item['domainName'])
        elif candidates[0]['name'] == 'eu':
            eu.append(item['domainName'])
    return [
        {'name': 'domestic', 'domains': cn},
        {'name': 'ap', 'domains': ap},
        {'name': 'eu', 'domains': eu}
    ]


def handler(event, context):
    domains = Domains(os.environ['DYNAMODB_TABLE'])
    save_bucket(routing_rules(domains.scanStatistics(int(os.environ['DAYS_TO_SCAN']))))
