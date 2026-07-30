"""Fetch an IBKR Activity Flex statement via the Flex Web Service (v3).

Credentials (never commit these; report/data/ is gitignored):
    report/data/flex_credentials with two lines:
        TOKEN=<your Flex Web Service token>
        QUERY_ID=<your Activity Flex Query id>
    or the environment variables IB_FLEX_TOKEN / IB_FLEX_QUERY_ID.

Writes ../data/flex_statement.xml and prints a per-account summary of
what the statement contains.
"""
import os
import sys
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPORT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CRED_PATH = os.path.join(REPORT, 'data', 'flex_credentials')
OUT_PATH = os.path.join(REPORT, 'data', 'flex_statement.xml')

SEND_URL = ('https://ndcdyn.interactivebrokers.com'
            '/AccountManagement/FlexWebService/SendRequest')


def load_credentials():
    creds = {}
    if os.path.exists(CRED_PATH):
        with open(CRED_PATH) as f:
            for line in f:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    creds[key] = value
    token = os.environ.get('IB_FLEX_TOKEN', creds.get('TOKEN'))
    query_id = os.environ.get('IB_FLEX_QUERY_ID', creds.get('QUERY_ID'))
    if not token or not query_id:
        sys.exit(
            'Missing Flex credentials.\n'
            'Create {} with:\n'
            '    TOKEN=<Flex Web Service token>\n'
            '    QUERY_ID=<Activity Flex Query id>\n'
            '(Client Portal: Performance & Reports -> Flex Queries to make '
            'the query; Reports -> Settings -> Flex Web Service for the '
            'token.)'.format(CRED_PATH))
    return token, query_id


def http_get(url, params):
    req = Request(url + '?' + urlencode(params),
                  headers={'User-Agent': 'pyfolio-report/1.0'})
    with urlopen(req, timeout=60) as resp:
        return resp.read().decode('utf-8', errors='replace')


def main():
    token, query_id = load_credentials()

    body = http_get(SEND_URL, {'t': token, 'q': query_id, 'v': '3'})
    root = ET.fromstring(body)
    if root.findtext('Status') != 'Success':
        sys.exit('Flex request failed: {} {}'.format(
            root.findtext('ErrorCode'), root.findtext('ErrorMessage')))

    reference = root.findtext('ReferenceCode')
    statement_url = root.findtext('Url')

    statement = None
    for _ in range(24):  # statements can take a minute to generate
        candidate = http_get(statement_url,
                             {'q': reference, 't': token, 'v': '3'})
        if '<FlexQueryResponse' in candidate:
            statement = candidate
            break
        time.sleep(5)
    if statement is None:
        sys.exit('Statement was not ready after 120s; re-run to retry.')

    with open(OUT_PATH, 'w') as f:
        f.write(statement)
    print('wrote', OUT_PATH, '\n')

    root = ET.fromstring(statement)
    for stmt in root.iter('FlexStatement'):
        print('account {}: {} -> {}'.format(
            stmt.get('accountId'), stmt.get('fromDate'), stmt.get('toDate')))
        sections = {}
        for child in stmt:
            sections[child.tag] = len(list(child))
        for tag, count in sorted(sections.items()):
            print('    {:<40}{:>6} rows'.format(tag, count))


if __name__ == '__main__':
    main()
