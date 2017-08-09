# SlackFileCleanup

Deletes lack files older than `n_days_ago`

By default files to be deleted are written to `files_to_delete.csv`, if the delete
flag is passed, then the files will also be deleted from slack.

## Usage

``` cmd
python slack_file_cleanup.py -t <your-secren-token> -d
```

You can do a dry run by omiting the `-d` flag.

Deleted files are logged to `files_to_delete.csv` by default, this can be turned off by adding the flag `--logging_off`.

By default files older than 30 days ago are deleted, this can be changed by passing a `--n_days_ago` argument.

You can skip deleting smaller files (that count less towards your quota) by passing a `--min_file_size` argument.

## Getting a token

You can generate a token via: https://api.slack.com/custom-integrations/legacy-tokens


