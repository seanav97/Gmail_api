from __future__ import print_function
import pickle
import os.path
import threading
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from datetime import datetime
import json
import logging
import requests

####### global variables ########
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
creds = None
service = None
with open('credentials.json') as file:
    blacklist = json.load(file)['blacklist']

logging.basicConfig(filename="logger.log", level=logging.DEBUG)
logger = logging.getLogger()


def main():
    try:
        connect_go_gmail()
    except:
        logger.error("Failed connecting to the Gmail API")
        exit()

    check_5_minutes()


def connect_go_gmail():
    """connects to the Gmail API service
    :return:
    """
    global creds
    global service
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    service = build('gmail', 'v1', credentials=creds)
    logger.info("connected to Gmail API")


def check_5_minutes():
    """ The method checks the messages every 5 minutes
    :return:
    """
    threading.Timer(30.0, check_5_minutes).start()
    messages = get_messages_30_days()
    send_webhook(messages)


def send_webhook(messages):
    """ The method sends a post request to the webhook service
    :param messages: a JSON object representing an array of messages
    """
    try:
        url = "https://webhook.site/38703b0d-ba51-49b8-9e8a-f9aaa82c4152"
        requests.post(url, json=messages)
    except:
        logger.error("Failed to connect to webhook")


def get_messages_30_days():
    """ extract all the messages in the INBOX folder within the last 30 days
    :return:
            a list of JSON objects
    """
    global service
    messages_list = []

    # receive all messages in inbox
    results = service.users().messages().list(userId='me', labelIds=['INBOX']).execute()
    messages = results.get('messages', [])

    if not messages:
        return messages_list
    else:
        for message in messages:
            # for each message extract subject and date
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = msg['payload']['headers']
            subject = "NO_SUBJECT"
            date_str = "NO_DATE"
            for header in headers:
                if header["name"] == "Subject":
                    subject = header["value"]
                if header["name"] == "Date":
                    date_str = header["value"]
            try:
                message_date = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
            except:
                pass
            message_date = message_date.replace(tzinfo=None)
            curr_date = datetime.now()
            days_passed = (curr_date - message_date).days

            # add messages to list if they are not blacklisted and with in the time period
            if days_passed <= 30 and subject not in blacklist:
                messages_list.append({"Subject": subject, "Date": str(message_date)})
        return messages_list


if __name__ == '__main__':
    main()
