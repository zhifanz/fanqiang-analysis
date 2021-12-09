import base64
import json
import os
import gzip
import re
import logging
import boto3
from boto3.dynamodb.conditions import Key

DOMAIN_PATTERN = r'<-> ([\w.-]+\.[\w]+):\d+ '

def decode_events(event):
    compressed_event_data = base64.standard_b64decode(event['awslogs']['data'])
    cloudwatch_logs_message = json.loads(gzip.decompress(compressed_event_data).decode())
    return cloudwatch_logs_message['logEvents']

def extract_domain(message):
    match = re.search(DOMAIN_PATTERN, message)
    if match:
        return match.group(1)


def process_domain(domain):
    logging.info('process domain: ' + domain)
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])
    response = table.query(Select='COUNT', KeyConditionExpression=Key('domainName').eq(domain))
    if response['Count'] > 0:
        return
    table.put_item(Item={'domainName': domain})
    

def handler(event, context):
    for log_event in decode_events(event):
        log_message = log_event['message']
        domain = extract_domain(log_message)
        if domain:
            process_domain(domain)
