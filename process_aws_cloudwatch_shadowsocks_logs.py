import base64
import json
import os
import gzip
import re
import logging
from domains import Domains

DOMAIN_PATTERN = r'<-> ([\w.-]+\.[\w]+):\d+ '

def decode_events(event):
    compressed_event_data = base64.standard_b64decode(event['awslogs']['data'])
    cloudwatch_logs_message = json.loads(gzip.decompress(compressed_event_data).decode())
    return cloudwatch_logs_message['logEvents']


def extract_domain(message):
    match = re.search(DOMAIN_PATTERN, message)
    if match:
        return match.group(1)
    

def handler(event, context):
    domains = Domains(os.environ['DYNAMODB_TABLE'])
    for log_event in decode_events(event):
        log_message = log_event['message']
        domain = extract_domain(log_message)
        if domain:
            logging.info('process domain: ' + domain)
            domains.update_domain(domain, log_event['timestamp'])
