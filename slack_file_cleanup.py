import csv
import time
import calendar
import datetime
from collections import namedtuple

import requests

DEBUG = True
MIN = 60
SLACK_FILE_ATTRIBUTES = ['id', 'name', 'permalink', 'created', 'user', 'size']
SlackFile = namedtuple('SlackFile', SLACK_FILE_ATTRIBUTES)

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def get_slack_file(f):
    filename = f[u'name'].encode('utf-8')
    url = f[u'permalink']
    created = datetime.datetime.fromtimestamp(float(f[u'created']))
    user = f[u'user'].encode('utf-8')
    slack_id = f[u'id']
    size = f[u'size'] # filesize in bytes
    return SlackFile(id=slack_id,
                     name=filename,
                     permalink=url,
                     created=created,
                     user=user,
                     size=size)

def get_slack_files(files):
    return [get_slack_file(f) for f in files]


def handle_logging(log_name, files_to_delete):
    with open(log_name, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SLACK_FILE_ATTRIBUTES)
        writer.writeheader()
        for slackfile in files_to_delete:
            writer.writerow(slackfile._asdict())

def delete_request(token, slackfile):
    delete_url = 'https://slack.com/api/files.delete'
    resp_delete = requests.post(delete_url, data={
        'token': token,
        'file': slackfile.id
    })

    if DEBUG:
        # TODO: Look out for HTTP 429 Too Many Requests responses and sleep for Retry-After seconds with a fallback to 1 second
        if resp_delete.status_code == 429:
            import pdb; pdb.set_trace()

    if resp_delete.ok and resp_delete.json()['ok']:
        print "Deleted: %s (%s) uploaded by %s on %s has been deleted" % (slackfile.name,
                                                                          slackfile.id,
                                                                          slackfile.user,
                                                                          slackfile.created)
    else:
        print "Failed: %s (%s) uploaded by %s on %s failed to delete" % (slackfile.name,
                                                                         slackfile.id,
                                                                         slackfile.user,
                                                                         slackfile.created)

def list_request(token, upperbound, page=1):
    # See https://api.slack.com/methods/files.list
    files_list_url = 'https://slack.com/api/files.list'
    lowerbound = upperbound - datetime.timedelta(days=31)
    ts_upperbound = str(calendar.timegm(upperbound.utctimetuple()))
    data = {
        'token': token,
        'ts_to': ts_upperbound,
        'page': 1
    }
    resp = requests.post(files_list_url, data=data)

    if DEBUG:
        # TODO: Look out for HTTP 429 Too Many Requests responses and sleep for Retry-After seconds with a fallback to 1 second
        if resp.status_code == 429:
            import pdb; pdb.set_trace()

    if resp.ok and resp.json()['ok']:
        return resp.json()
    print "%s: %s" % (resp.status_code, resp.body)
    return None  # TODO: raise error instead of handling None case?

def filter_slack_files(slack_files, min_file_size):
    if DEBUG:
        upload_total = 0
        for slackfile in slack_files:
            upload_total += slackfile.size
            print "Filesize %s" % sizeof_fmt(slackfile.size)
        print "Filesize %s" % sizeof_fmt(upload_total)
    return [slackfile for slackfile in slack_files if slackfile.size > min_file_size]

def get_files_to_delete(token, n_days_ago, min_file_size=None):
    upperbound = datetime.datetime.now() - datetime.timedelta(days=n_days_ago)
    resp = list_request(token, upperbound)
    if not resp:
        return []

    slack_files = get_slack_files(resp['files'])  # asdf
    if resp['paging']['pages'] > 1:
        for page in range(resp['paging']['page']+1, resp['paging']['pages']+1):
            _resp = list_request(token, upperbound, page=page)
            slack_files.extend(get_slack_files(_resp['files']))

    if DEBUG:
        print "Total files to delete %s" % len(slack_files)
    if min_file_size:
        slack_files = filter_slack_files(slack_files, min_file_size)
    
    if DEBUG:
        print "Filtered files to delete %s" % len(slack_files)

    return slack_files

def main(token, delete=False, n_days_ago=30, logging_off=False, min_file_size=None):
    """
    Deletes lack files older than `n_days_ago`

    By default files to be deleted are written to `files_to_delete.csv`, if the delete
    flag is passed, then the files will also be deleted from slack.
    """

    if DEBUG:
        print "delete %s" % delete
        print "n_days_ago %s" % n_days_ago
        print "logging_off %s" % logging_off
        print "min_file_size %s" % min_file_size

    files_to_delete = get_files_to_delete(token, n_days_ago, min_file_size)

    if not logging_off:
        handle_logging('files_to_delete.csv', files_to_delete)

    if delete:
        for slackfile in files_to_delete:
            delete_request(token, slackfile)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser("Bulk delete files older than 30 days")
    parser.add_argument('-t', '--token', type=str, help="Oauth token for Slack RESTfull API")
    parser.add_argument('-d', '--delete', action='store_true', help="Confirm file deletion (this cannot be undone)")
    parser.add_argument('-n', '--n_days_ago', type=int, help="Delete files older than n days ago (default = 30)", default=30)
    parser.add_argument('-l', '--logging_off', action='store_true', help="Turn off CSV logging of deleted files")
    parser.add_argument('-s', '--min_file_size', type=int, help="Min filesize (in bytes) a file must be to get deleted")
    main(**vars(parser.parse_args()))


