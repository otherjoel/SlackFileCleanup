import csv
import calendar
import datetime
from collections import namedtuple

import requests

SlackFile = namedtuple('SlackFile', ['id', 'name', 'permalink', 'created', 'user'])

def gen_files_to_delete(files):
    for f in files:
        filename = f[u'name'].encode('utf-8')
        url = f[u'permalink']
        created = datetime.datetime.fromtimestamp(float(f[u'created']))
        user = f[u'user'].encode('utf-8')
        slack_id = f[u'id']
        yield SlackFile(
            id=slack_id,
            name=filename,
            permalink=url,
            created=created,
            user=user)

def handle_logging(log_name):
    with open(log_name, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=['id', 'name', 'permalink', 'created', 'user'])
        writer.writeheader()
        for slackfile in files_to_delete:
            writer.writerow(slackfile._asdict())

def delete_request(token, slackfile):
    delete_url = 'https://slack.com/api/files.delete'
    resp_delete = requests.post(delete_url, data={
        'token': token,
        'file': slackfile.id
    })
    if resp_delete.ok and resp_delete.json()['ok']:
        print "Deleted: %s (%s) uploaded by %s on %s has been deleted" % (slackfile.filename,
                                                                          slackfile.id,
                                                                          slackfile.user,
                                                                          slackfile.created)
        print "Failed: %s (%s) uploaded by %s on %s failed to delete" % (slackfile.filename,
                                                                         slackfile.id,
                                                                         slackfile.user,
                                                                         slackfile.created)

def list_request(token, n_days_ago):
    files_list_url = 'https://slack.com/api/files.list'
    files_until_n_days_ago = datetime.datetime.now() - datetime.timedelta(days=n_days_ago)
    ts_n_days_ago = str(calendar.timegm(files_until_n_days_ago.utctimetuple()))
    data = {
        'token': _token,
        'ts_to': ts_n_days_ago
    }
    resp = requests.post(files_list_url, data=data)
    if resp.ok and resp.json()['ok']:
        return resp.json()['files']
    return []

def main(token, delete=False, n_days_ago=30):
    """
    Deletes lack files older than `n_days_ago`

    By default files to be deleted are written to `files_to_delete.csv`, if the delete
    flag is passed, then the files will also be deleted from slack.
    """
    files_to_delete = map(gen_files_to_delete, list_request(token, n_days_ago))

    if not logging_off:
        handle_logging('files_to_delete.csv')

    if delete:
        for slackfile in files_to_delete:
            delete_request(token, slackfile)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser("Bulk delete files older than 30 days")
    parser.add_argument('-t', '--token', type=str, help="Oauth token for Slack RESTfull API")
    parser.add_argument('-d', '--delete', action='store_true', help="Confirm file deletion (this cannot be undone)")
    parser.add_argument('-n', '--n_days_ago', type=int, help="Delete files older than n days ago (default = 30)")
    parser.add_argument('-l', '--logging_off', action='store_false', help="Turn off CSV logging of deleted files")
    main(**vars(parser.parse_args()))



