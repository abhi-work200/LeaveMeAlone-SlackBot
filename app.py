import os
import logging
import json
from flask import Flask, jsonify, request
import requests
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from leave_me_alone import LeaveMeAlone

# Initialize a Flask app to host the events adapter
APP = Flask(__name__)

# Create the logging object
LOGGER = logging.getLogger()
# Set the log level to DEBUG. This will increase verbosity of logging messages
LOGGER.setLevel(logging.DEBUG)
# Add the StreamHandler as a logging handler
LOGGER.addHandler(logging.StreamHandler())

CONFIG = {}
with open("config.json") as config:
    CONFIG = json.load(config)

# Create an events adapter and register it to an endpoint in the slack app for event injestion.
# SLACK_EVENTS_ADAPTER = SlackEventAdapter(CONFIG["slack"].get("events_token"), CONFIG["slack"].get("events_route"), APP)

# Initialize a Web API client
SLACK_WEB_CLIENT = WebClient(token=CONFIG["slack"].get("token"))

def load_members():
    members = []
    filepath = "private/members.json"
    try:
        with open(filepath) as file:
            members = json.load(file)
    except Exception as ex:
        pass
    return members

def load_channels():
    channels_map = {}
    filepath = "private/channels.json"
    try:    
        with open(filepath) as file:
            channels_map = json.load(file)
    except Exception as ex:
        pass
    return channels_map

def get_channels():
    channels_map = {}
    filepath = "private/channels.json"
    try:    
        url = "https://slack.com/api/conversations.list"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer {}".format(CONFIG["slack"].get("token"))
        }
        params = {
            "limit": 500,
            "types": "public_channel,private_channel",
        }
        while True:
            response = requests.get(url, headers=headers, params=params)
            assert response.status_code == 200, response
            data = response.json()
            next_cursor = data["response_metadata"].get("next_cursor") if data.get("response_metadata") else None
            for channel in data.get("channels", []):
                ch_name = channel.get("name")
                ch_id = channel.get("id")
                if ch_name not in channels_map:
                    channels_map[ch_name] = ch_id

            if not next_cursor:
                break
            else:
                params["cursor"] = next_cursor

        with open(filepath, "w") as file:
            json.dump(channels_map, file)
    except Exception as ex:
        print(ex)
    return channels_map

def get_user_channels(user_email):
    team_members = load_members()
    team_channels = load_channels()
    user_channels = []
    for member in team_members:
        if user_email.lower() == member.get("email", "").lower():
            user_channels =  member.get("channels")
            break
    
    channels_id = []
    for channel in user_channels:
        channel = channel.lower()
        if channel in team_channels:
            channels_id.append(team_channels[channel])

    return channels_id

def get_user_profile(uid):
    try:    
        url = "https://slack.com/api/users.profile.get"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": "Bearer {}".format(CONFIG["slack"].get("user_token"))
        }
        params = {
            "user": uid
        }
        response = requests.get(url, headers=headers, params=params)
        assert response.status_code == 200, response
        return response.json().get("profile", {})
    except Exception as ex:
        print(ex)
        return {}

# def update_leave_status(event):
#     """Craft the LeaveMeAlone Bot, and send message to the channel
#     """

#     # Check and see if the activation phrase was in the text of the message.
#     # If so, execute the code to flip a coin.
#     if "on leave today" not in event.get("text", "").lower():
#         return

#     curr_channel = event.get("channel")
#     uid = event.get("user")
#     user_profile = get_user_profile(uid)
#     username = user_profile.get("display_name")
#     avatar = user_profile.get("image_24")
#     user_channels = get_user_channels(user_profile.get("email"))

#     # Create a new Bot
#     bot = LeaveMeAlone(curr_channel)
#     # Get the default message payload
#     message = bot.get_default_payload(username)
#     # Post leave status message to current channels
#     SLACK_WEB_CLIENT.chat_postMessage(**message)

#     # Post leave message to all specified channels
#     for channel in user_channels:
#         if channel == curr_channel:
#             continue
#         bot = LeaveMeAlone(channel)
#         blocks = bot.get_leave_payload(uid, username, avatar)
#         SLACK_WEB_CLIENT.chat_postMessage(**message)


# When a 'message' event is detected by the events adapter, forward that payload
# to this function.
# @SLACK_EVENTS_ADAPTER.on("message")
# def message(payload):
#     """Parse the message event, and if the activation string is in the text,
#     simulate a coin flip and send the result.
#     """
#     # Execute the flip_coin function and send the results of
#     # flipping a coin to the channel
#     return update_leave_status(payload.get("event", {}))

@APP.route(CONFIG["slack"].get("commands_route"), methods=['POST'])
def handle_commands():
    curr_channel = request.form["channel_id"]
    text = request.form["text"]
    uid = request.form["user_id"]
    user_profile = get_user_profile(uid)
    username = user_profile.get("display_name")
    avatar = user_profile.get("image_32")
    user_channels = get_user_channels(user_profile.get("email"))

    # Post leave message to all specified channels
    for channel in user_channels:
        if channel == curr_channel:
            continue
        bot = LeaveMeAlone(channel)
        message = bot.get_leave_payload(uid, username, avatar)
        attachments = bot.get_attachments_payload(text, CONFIG["slack"].get("app_color"))
        SLACK_WEB_CLIENT.chat_postMessage(**message, attachments=attachments)
    
    # Create a new Bot
    bot = LeaveMeAlone(curr_channel)
    # Get the default message payload
    message = bot.get_default_payload(username)
    # Post leave status message to current channels
    return jsonify({"blocks": message.get("blocks")})


# get all public and private channels that app has access to
get_channels()

if __name__ == "__main__":
    # Run our app on our externally facing IP address on port 3000 instead of
    # running it on localhost, which is traditional for development.
    APP.run(host='0.0.0.0', port=CONFIG.get("port"))
