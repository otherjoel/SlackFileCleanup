import csv
import time
import calendar
import datetime
from urllib2 import Request, urlopen
from collections import namedtuple

import requests
import os.path

DEBUG = True
MIN = 60
SLACK_FILE_ATTRIBUTES = ['id',       'name',     'permalink', 
                         'created',  'user',     'size', 
                         'channels', 'filetype', 'action']
SlackFile = namedtuple('SlackFile', SLACK_FILE_ATTRIBUTES)

def filename_string(file):
    datestring = file.created.strftime("%Y-%m-%d")
    file_ext = os.path.splitext(file.name)[1]
    
    # e.g. 2017-07-04-joel_general+random_f633m1hfa.jpg
    return "%s-%s_%s_%s%s" % (datestring, 
                            file.user,
                            file.channels,
                            file.id.lower(),
                            file_ext)

def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)

def get_slack_file(f, channels, users):
    filename = f[u'name'].encode('utf-8')
    url = f[u'url_private']
    created = datetime.datetime.fromtimestamp(float(f[u'created']))
    user = users[f[u'user']].encode('utf-8')
    slack_id = f[u'id']
    size = f[u'size'] # filesize in bytes
    file_channels = '+'.join([channels[fc] for fc in f[u'channels']])
    filetype = f[u'filetype']
    return SlackFile(id=slack_id,
                     name=filename,
                     permalink=url,
                     created=created,
                     user=user,
                     size=size,
                     filetype=filetype,
                     action='',
                     channels=file_channels)

def get_slack_files(files, channel_list, user_list):
    return [get_slack_file(f, channel_list, user_list) for f in files]


def handle_logging(log_name, files_to_act_on):
    with open(log_name, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=SLACK_FILE_ATTRIBUTES)
        writer.writeheader()
        for slackfile in files_to_act_on:
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
        'page': page
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

def other_list_request(token,type):
    # See https://api.slack.com/methods/channels.list
    # and https://api.slack.com/methods/users.list
    if not type in ['channels', 'users']:
        return None
        
    list_url = "https://slack.com/api/%s.list" % type

    data = {
        'token': token
    }
    resp = requests.post(list_url, data=data)

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

def get_files_to_act_on(token, n_days_ago, min_file_size=None):
    upperbound = datetime.datetime.now() - datetime.timedelta(days=n_days_ago)
    resp = list_request(token, upperbound)
    if not resp:
        return []
        
    channel_resp = other_list_request(token, 'channels')
    if not channel_resp:
        return []
    
    user_resp = other_list_request(token, 'users')
    if not user_resp:
        return[]
    
    # Construct dictionaries mapping user and channel IDs to their names
    channels = { c[u'id'] : c[u'name'] for c in channel_resp['channels'] }
    users = { user[u'id'] : user[u'name'] for user in user_resp['members'] }

    slack_files = get_slack_files(resp['files'], channels, users)  # asdf
    if resp['paging']['pages'] > 1:
        for page in range(resp['paging']['page']+1, resp['paging']['pages']+1):
            _resp = list_request(token, upperbound, page=page)
            slack_files.extend(get_slack_files(_resp['files'], channels, users))

    if DEBUG:
        print "Total files to delete %s" % len(slack_files)
    if min_file_size:
        slack_files = filter_slack_files(slack_files, min_file_size)
    
    if DEBUG:
        print "Filtered files to delete %s" % len(slack_files)

    return slack_files

# For debug only
def print_channel_list(token):
    resp = other_list_request(token,'channels')
    if not resp:
        print "No response!?"
    
    slack_channels = { c[u'id'] : c[u'name'] for c in resp['channels'] }
    # print "Next cursor: %s" % resp['response_metadata']['next_cursor']
    
    for channel_id in slack_channels.keys():
        print "[%s] %s" % (channel_id, slack_channels[channel_id])

def assign_file_actions(files, channels_noarchive):
    actionable_types = ['jpg', 'jpeg', 'png', 'mov', 'mp4']
    
    channels_not_to_archive = channels_noarchive.split(',') if channels_noarchive else []
    examined_files = []
    
    for file in files:
        file_channels = file.channels.split('+')
        dont_archive = set(file_channels).issubset(channels_not_to_archive)
        
        if file.filetype in actionable_types:
            if not file.channels:
                # file was shared in a private channel/DM
                # you may want this to be 'delete', but probably not 'archive'
                file = file._replace(action='ignore')
            elif dont_archive:
                file = file._replace(action='delete')
            else:
                file = file._replace(action='archive,delete')
        else:
            file = file._replace(action='ignore')
        
        examined_files.append(file)
        
    return examined_files

def count_action(files, action):
    return len([f for f in files if action in f.action])

def download_slack_file(file, token):
    filename = filename_string(file)
    
    with open(filename, 'wb') as handle:
        download_request = Request(file.permalink)
        download_request.add_header('Authorization', 'Bearer %s' % token)
        
        download_response = urlopen(download_request)
        handle.write(download_response.read())
    
    return True

def main(token, do_actions=False, n_days_ago=30, logging_off=False, \
         min_file_size=None, channels_noarchive=""):
    """
    Deletes lack files older than `n_days_ago`

    By default files to be deleted are written to `files_to_act_on.csv`, if the delete
    flag is passed, then the files will also be deleted from slack.
    """

    if DEBUG:
        print "do_actions %s" % do_actions
        print "n_days_ago %s" % n_days_ago
        print "logging_off %s" % logging_off
        print "min_file_size %s" % min_file_size
        print "channels_noarchive %s" % channels_noarchive

    print_channel_list(token)
    
    files_to_act_on = get_files_to_act_on(token, n_days_ago, min_file_size)
    files_to_act_on = assign_file_actions(files_to_act_on, channels_noarchive)

    if DEBUG:
        for file in files_to_act_on:
            print filename_string(file)
        
        print "File to archive: %s" % count_action(files_to_act_on, 'archive')
        print "Files to delete: %s" % count_action(files_to_act_on, 'delete')
        print "Files to ignore: %s" % count_action(files_to_act_on, 'ignore')
        
    if not logging_off:
        handle_logging('files_to_act_on.csv', files_to_act_on)

    if do_actions:
        for slackfile in files_to_act_on:
            if 'archive' in file.action:
                download_slack_file(file, token)
            if 'delete' in file.action:
                delete_request(token, slackfile)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser("Bulk archive/delete files older than 30 days")
    parser.add_argument('-t', '--token', type=str, help="Oauth token for Slack RESTfull API")
    parser.add_argument('-d', '--do_actions', action='store_true', help="Confirm file archive/deletion (this cannot be undone)")
    parser.add_argument('-n', '--n_days_ago', type=int, help="Delete files older than n days ago (default = 30)", default=30)
    parser.add_argument('-l', '--logging_off', action='store_true', help="Turn off CSV logging of deleted files")
    parser.add_argument('-s', '--min_file_size', type=int, help="Min filesize (in bytes) a file must be to get deleted")
    parser.add_argument('-c', '--channels_noarchive', type=str, help="Channels to skip archiving (delete only)")
    main(**vars(parser.parse_args()))


