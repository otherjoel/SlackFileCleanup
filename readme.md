# SlackFileCleanup

Archives and deletes Slack files older than a specified age limit. Helps you stay under the 5GB limit for free Slack accounts.

This project is a fork of <https://gitlab.com/tomleo/SlackFileCleanup/>. The original code simply allowed you to delete files of a certain age. I’ve added some more capabilities:

* Download files for archiving before deleting them
* Exclude certain channels from archiving (i.e., make them delete-only)
* Compress archived files into multiple standalone zip files
* Includes an example script for doing the cleanup and adding a post to Slack with links to the zip files (suitable for running on a web server with `cron`)
* Uses Python 3 instead of 2
* Only acts on images and videos by default

## Setup

The script uses Python 3. No special packages are needed.

You do need an API token from Slack. You can generate a token at <https://api.slack.com/custom-integrations/legacy-tokens>.

## Usage

There are two scripts you can use:

* The original script, `slack_file_cleanup.py`, will simply download and delete files. 
* If you want to do some extra stuff like announce that the archiving has happened, putting the downloaded files into zip files, and/or making those zip files available for others to download, you should use (and perhaps customize) `slack_cleanup_cron.py`.

The second option is mainly useful if you want to let other people on your team participate in the archiving in some way.

### Using the core script by itself

```shell
python slack_file_cleanup.py --token <your-secret-token> [--n_days_ago <days>] [--do_actions]
```

This will log all actions to `files_to_act_on.csv`, download old files to an `archive/` subfolder (in the same path as the script itself) and then delete them from Slack. 

**Files other than images and videos will be ignored;** to change this, edit the `assign_file_actions` function.

`-d` or `--do_actions`
: If this flag is passed, files will be downloaded and deleted from Slack. Omit this flag to do a dry run, then you can examine the `files_to_act_on.csv` file to see what actions the script would have taken. 

`-l` or `--logging_off`
: Turn off logging to the CSV file.

`-n <days>` or `--n_days_ago <days>`
: Specify the minimum age of files to be archived and deleted. The default is 30 days.

`-s <bytes>` or `--min_file_size <bytes>`
: Skip deleting smaller files (that count less towards your quota)

`-c <channels>` or `--channels_noarchive <channels>`
: Comma-separated list of channels (without the `#` sign) to exclude from the archiving step. Files that have been shared in these channels will be deleted only without being downloaded first.

### Using the example `cron` script

```shell
python slack_cleanup_cron -t <token> --folder <folder> --url_folder <url> --notify_channel <channel> [--do_actions]
```

This script itself calls the `slack_file_cleanup.py` script above to download and delete old files, so all of the behavior described above applies here as well. It then takes the additional steps of compressing the downloaded files into zip files, moving those files into the specified `--folder`, then generating an announcement and posting it to the specified channel.

To cut down on the number of command line arguments needed, I plopped some values into constants near the top: `AGE_LIMIT_DAYS` and `NON_ARCHIVE_CHANNELS`. These values are used for the `n_days_ago` and `channels_noarchive` arguments when calling `main()` in `slack_file_cleanup.py`. At a minimum you should edit these constants to match your needs.

In addition to the required `-t` with your Slack API token, it takes the following arguments:

`-d` or `--do_actions`
: Same as above; if omitted, no files will be downloaded or deleted, and no messages will be posted to Slack.

`-f folder` or `--folder <folder>`
: Specify where to move the zip files containing the downloaded Slack files. The idea here is that you could put them into the public folder of a web server so they can be downloaded by others.

`-u <url>` or `--url_folder <url>`
: This should be the web-accessible URL of the folder specified in the `--folder` option above. It is used in generating download links to the zip files to be included in the announcement.

`-n <channel>` or `--notify_channel <channel>`
: The channel (either the ID or the `#name`) to post the announcement and download links.