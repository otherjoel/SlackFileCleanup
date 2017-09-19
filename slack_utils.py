import requests
import sys

def chat_post_request(token, channel, message):
    """Post a message to a Slack channel"""
    
    # See https://api.slack.com/methods/chat.postMessage
    chat_api_url = 'https://slack.com/api/chat.postMessage'
    
    data = {
        'token': token,
        'channel': channel,
        'as_user': True,
        'parse': 'full',
        'text': message
    }
    resp = requests.post(chat_api_url, data=data)
    
    if resp.ok and resp.json()['ok']:
        return resp.json()
    print("[chat.postMessage] %s: %s" % (resp.status_code, resp.text), file=sys.stderr)
    return None  # TODO: raise error instead of handling None case?

def markdown_post_request(token, channels, title, content, filetype='post'):
    """Create a ‘Post’ in a Slack channel using Markdown formatting."""
    
    # See https://api.slack.com/methods/files.upload
    file_upload_api_url = 'https://slack.com/api/files.upload'
    
    data = {
        'token': token,
        'channels': channels,
        'content': content,
        'title': title,
        'filetype': filetype
    }
    
    resp = requests.post(file_upload_api_url, data=data)
    
    if resp.ok and resp.json()['ok']:
        return resp.json()
    print("[files.upload] %s: %s" % (resp.status_code, resp.text), file=sys.stderr)
    return None  # TODO: raise error instead of handling None case?