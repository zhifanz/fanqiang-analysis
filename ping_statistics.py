import subprocess
import re
import argparse
from subprocess import TimeoutExpired, CalledProcessError, SubprocessError

from domains import Domains

IP_PATTERN = r'PING.+ \(([\d.]+)\) '
COUNT_PATTERN = r'(\d+).+transmitted,.+(\d+).+received'
LATENCY_PATTERN = r'min/avg/max/mdev = ([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+) ms'

MAX_ALLOW_SCAN_DAYS = 90

def parse_statistics(stdout):
    statistics = {}
    for line in stdout.split('\n'):
        match = re.search(IP_PATTERN, line)
        if match:
            statistics['public_ip'] = match.group(1)
            continue
        match = re.search(COUNT_PATTERN, line)
        if match:
            statistics['transmitted'] = int(match.group(1))
            statistics['received'] = int(match.group(2))
            continue
        match = re.search(LATENCY_PATTERN, line)
        if match:
            statistics['min'] = float(match.group(1))
            statistics['avg'] = float(match.group(2))
            statistics['max'] = float(match.group(3))
            statistics['mdev'] = float(match.group(4))
    return statistics


def ping(domain, count):
    try:
        cp = subprocess.run(['ping', f'-c{count}', '-q', domain], capture_output=True, text=True, check=True)
        return {'code': 0, 'message': 'success', 'statistics': parse_statistics(cp.stdout)} if cp.returncode == 0 else {'code': 1, 'message': 'failed'}
    except (TimeoutExpired, CalledProcessError) as err:
        return {'code': 2, 'message': err.stderr}


def arg_parser():
    parser = argparse.ArgumentParser(description='Test network latency and save statistics to dynamodb.')
    parser.add_argument('--days', help='domains within last days to scan for ping statistics', type=int, default=30)
    parser.add_argument('--pingcount', help='-c option for ping command', type=int, default=10)
    parser.add_argument('table', help='dynamodb table name')
    parser.add_argument('continent', help='continent where this program is run from')
    return parser

def main():
    args = arg_parser().parse_args()
    if args.days > MAX_ALLOW_SCAN_DAYS:
        raise RuntimeError(f'Scan days must less than {MAX_ALLOW_SCAN_DAYS}')
    domains = Domains(args.table)
    domainNames = domains.scanDomainNames(args.days)
    domains.batch_update_ping_statistics(args.continent, [{'domainName': dn, 'statistics': ping(dn, args.pingcount)} for dn in domainNames])


if __name__ == '__main__':
    main()
