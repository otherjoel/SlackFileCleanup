import csv
import calendar
import datetime
from collections import namedtuple

import requests

SLACK_FILE_ATTRIBUTES = ['id', 'name', 'permalink', 'created', 'user', 'size']
SlackFile = namedtuple('SlackFile', SLACK_FILE_ATTRIBUTES)

def gen_files_to_delete(files):
    for f in files:
        filename = f[u'name'].encode('utf-8')
        url = f[u'permalink']
        created = datetime.datetime.fromtimestamp(float(f[u'created']))
        user = f[u'user'].encode('utf-8')
        slack_id = f[u'id']
        size = f[u'size'] # filesize in bytes
        yield SlackFile(
            id=slack_id,
            name=filename,
            permalink=url,
            created=created,
            user=user,
            size=size)

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
    # TODO: Look out for HTTP 429 Too Many Requests responses and sleep for Retry-After seconds with a fallback to 1 second
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

def list_request(token, n_days_ago):
    files_list_url = 'https://slack.com/api/files.list'
    files_until_n_days_ago = datetime.datetime.now() - datetime.timedelta(days=n_days_ago)
    ts_n_days_ago = str(calendar.timegm(files_until_n_days_ago.utctimetuple()))
    data = {
        'token': token,
        'ts_to': ts_n_days_ago
    }
    resp = requests.post(files_list_url, data=data)
    if resp.ok and resp.json()['ok']:
        return resp.json()['files']
    else:
        print "%s: %s" % (resp.status, resp.body)
    return []

def main(token, delete=False, n_days_ago=30, logging_off=False, min_file_size=None):
    """
    Deletes lack files older than `n_days_ago`

    By default files to be deleted are written to `files_to_delete.csv`, if the delete
    flag is passed, then the files will also be deleted from slack.
    """
    files_to_delete = [slackfile for slackfile in gen_files_to_delete(list_request(token, n_days_ago))]

    if min_file_size:
        files_to_delete = [slackfile for slackfile in files_to_delete if slackfile.size > min_file_size]

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



