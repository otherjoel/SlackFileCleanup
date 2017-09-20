from datetime import date, datetime, timedelta
import os

# Modules from this project
from slack_utils import markdown_post_request, chat_post_request
import slack_file_cleanup
import zipfolder

AGE_LIMIT_DAYS = 180

def make_markdown_message(file_list, url_prefix):
    message_markdown = """To save space, files older than {age} days have been deleted from this Slack account. 
    These old files have been saved in zip file{plural} which you can download using the link{plural}
    below.\n\n"""
    plural_suffix = 's' if len(file_list) > 1 else ''
    
    for f in file_list:
        file_name = os.path.basename(f)
        size_mb = round(os.path.getsize(f) / 1000000, 1)
        file_url = os.path.join(url_prefix, file_name)
        message_markdown += "* [`{url}`]({url}) ({size} MB)\n".format(url=file_url,size=size_mb)
    
    return message_markdown.format(age=AGE_LIMIT_DAYS, plural=plural_suffix)

def main(token, folder, url_folder, notify_channel, do_actions=False):
    
    #slack_file_cleanup.main(token, do_actions,
    #                        n_days_ago=180,
    #                        channels_noarchive="food,techsupport")
    
    today = datetime.now()
    last_month = date(today.year, today.month, 1) - timedelta(days=1)
    date_string = "{:%Y-%m}".format(today)
    post_title = "{:%B} Archives".format(last_month)
    
    if do_actions:
        zip_list = zipfolder.zip_folder(slack_file_cleanup.DOWNLOAD_DIR,
                                        zipfile_prefix=date_string,
                                        rough_size_limit_mb=500)
        # zip_list = ['2017-09_001.zip', '2017-09_002.zip', '2017-09_003.zip']
        
        for index, zfile in enumerate(zip_list):
            new_name = os.path.join(folder, os.path.basename(zfile))
            os.rename(zfile, new_name)
            zip_list[index] = new_name
            
        # TODO : delete files in slack_file_cleanup.DOWNLOAD_DIR
        
        msg = make_markdown_message(zip_list, url_prefix=url_folder)
        markdown_post_request(token, channels=notify_channel, title=post_title, content=msg)
        chat_post_request(token, channel=notify_channel, message='@channel: Latest archives are ready!')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser("Slack cleanup cron script")
    parser.add_argument('-t', '--token', type=str, help="Oauth token for Slack API")
    parser.add_argument('-d', '--do_actions', action='store_true', help="Confirm file archive/deletion (this cannot be undone)")
    parser.add_argument('-f', '--folder', type=str, help="Folder to store zip files")
    parser.add_argument('-u', '--url_folder', type=str, help="Public directory URL where files can be downloaded")
    parser.add_argument('-n', '--notify_channel', type=str, help="Channel to post notification and download links")
    main(**vars(parser.parse_args()))