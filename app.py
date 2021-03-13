import os
import logging
import json
import random
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

# Initialize a Web API client
SLACK_WEB_CLIENT = WebClient(token=CONFIG["slack"].get("token"))

def load_members():
    members = []
    filepath = CONFIG["path"]["members"]
    try:
        with open(filepath) as file:
            members = json.load(file)
    except Exception as ex:
        pass
    return members

def load_channels():
    channels_map = {}
    filepath = CONFIG["path"]["channels"]
    try:    
        with open(filepath) as file:
            channels_map = json.load(file)
    except Exception as ex:
        pass
    return channels_map

def get_channels():
    channels_map = {}
    filepath = CONFIG["path"]["channels"]
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

def create_new_member(members, user_profile, channels=[]):
    filepath = CONFIG["path"]["members"]
    try:
        user = {
            "email": user_profile.get("email"),
            "nickname": user_profile.get("display_name"),
            "name": user_profile.get("real_name"),
            "channels": channels,
            "team": "",
            "project": "",
            "mailingList": []
        }
        members.append(user)
        with open(filepath, 'w') as file:
            json.dump(members, file)
    except Exception as ex:
        pass

def update_members_channels(members):
    filepath = CONFIG["path"]["members"]
    try:
        with open(filepath, 'w') as file:
            json.dump(members, file)
    except Exception as ex:
        pass

def add_user_channels(user_profile, text):
    user_email = user_profile.get("email")
    new_channels = text.split(",")
    if not new_channels:
        return "Please, specify one or more public or private channels separated by comma (,)"

    team_members = load_members()
    team_channels = load_channels()
    
    channels = {"invalid": [], "valid": []}
    for channel in new_channels:
        channel = channel.lower().strip()
        if channel not in team_channels:
            channels["invalid"].append(channel)
        else:
            channels["valid"].append(channel)

    user_found = False
    new_channels_added = False
    for member in team_members:
        if user_email.lower() == member.get("email", "").lower():
            user_found = True
            for channel in channels["valid"]:
                if channel not in member.get("channels"):    
                    member["channels"].append(channel)
                    new_channels_added = True
            break

    if new_channels_added:
        update_members_channels(team_members)
    
    if not user_found:
        create_new_member(team_members, user_profile, channels["valid"])

    if channels["invalid"]:
        return "These channels doesn't exists or the app doesn't have permission to access them\n\n*"+", ".join(channels["invalid"])+"*"
    
    return None
        
def remove_user_channels(user_profile, text):
    user_email = user_profile.get("email")
    new_channels = text.split(",")
    if not new_channels:
        return "Please, specify one or more public or private channels separated by comma (,)"

    team_members = load_members()
    team_channels = load_channels()
    
    channels = {"invalid": [], "valid": []}
    for channel in new_channels:
        channel = channel.lower().strip()
        if channel not in team_channels:
            channels["invalid"].append(channel)
        else:
            channels["valid"].append(channel)

    channels_removed = False
    for member in team_members:
        if user_email.lower() == member.get("email", "").lower():
            for channel in channels["valid"]:
                if channel in member.get("channels"):    
                    member["channels"].remove(channel)
                    channels_removed = True
            break

    if channels_removed:
        update_members_channels(team_members)
    
    if channels["invalid"]:
        return "These channels doesn't exists or the app doesn't have permission to access them\n\n*"+", ".join(channels["invalid"])+"*"
    
    return None

def get_user_channels(user_profile, list_channels=False):
    user_email = user_profile.get("email")
    
    team_members = load_members()
    team_channels = load_channels()
    user_channels = []
    user_found = False
    for member in team_members:
        if user_email.lower() == member.get("email", "").lower():
            user_channels =  member.get("channels")
            user_found = True
            break
    
    if list_channels:
        return user_channels

    if not user_found:
        create_new_member(team_members, user_profile)

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

@APP.route(CONFIG["slack"]["commands_route"]["leave"], methods=['POST'])
def handle_leaves():
    curr_channel = request.form["channel_id"]
    text = request.form["text"]
    uid = request.form["user_id"]
    user_profile = get_user_profile(uid)
    username = user_profile.get("display_name")
    avatar = user_profile.get("image_32")
    user_channels = get_user_channels(user_profile)

    for channel in user_channels:
        if channel == curr_channel:
            continue
        bot = LeaveMeAlone(channel)
        message = bot.get_leave_payload(uid, username, avatar)
        attachments = bot.get_attachments_payload(text, CONFIG["slack"].get("app_color"))
        SLACK_WEB_CLIENT.chat_postMessage(**message, attachments=attachments)
    
    bot = LeaveMeAlone(curr_channel)
    message = bot.get_default_payload("Hey! *"+username+"*, I've updated your leave status...")
    return jsonify({"blocks": message.get("blocks")})

@APP.route(CONFIG["slack"]["commands_route"]["channels"], methods=['POST'])
def handle_list_channels():
    curr_channel = request.form["channel_id"]
    uid = request.form["user_id"]
    user_profile = get_user_profile(uid)
    user_channels = get_user_channels(user_profile, True)

    bot = LeaveMeAlone(curr_channel)
    if not user_channels:
        message = bot.get_default_payload("You haven't added any channels yet.")
        return jsonify({"blocks": message.get("blocks")})
    
    message = bot.get_default_payload("App can post leave messages to these channels")
    attachments = bot.get_attachments_payload(", ".join(user_channels), CONFIG["slack"].get("app_color"), "Channels")
    return jsonify({"blocks": message.get("blocks"), "attachments": attachments})

@APP.route(CONFIG["slack"]["commands_route"]["add"], methods=['POST'])
def handle_add_channels():
    curr_channel = request.form["channel_id"]
    text = request.form["text"]
    uid = request.form["user_id"]
    user_profile = get_user_profile(uid)
    error = add_user_channels(user_profile, text)

    bot = LeaveMeAlone(curr_channel)
    if not error:
        greetings = random.choice(["Voila", "Awesome", "Bravo", "Great"])
        emoji = random.choice(["clap", "ok_hand", "white_check_mark", "thumbsup"])
        message = bot.get_default_payload(greetings+"! :"+emoji+":, all the channels added successfully...")
        return jsonify({"blocks": message.get("blocks")})
    
    expression = random.choice(["Aw Snap", "Not Good", "Oh No", "That's Weird"])
    emoji = random.choice(["exclamation", "thinking_face", "cold_sweat", "eyes"])
    message = bot.get_default_payload(expression+"! :"+emoji+":, not able to add all channels...")
    attachments = bot.get_attachments_payload(error, CONFIG["slack"].get("app_color"), "This seems to be the problem")
    return jsonify({"blocks": message.get("blocks"), "attachments": attachments})

@APP.route(CONFIG["slack"]["commands_route"]["remove"], methods=['POST'])
def handle_remove_channels():
    curr_channel = request.form["channel_id"]
    text = request.form["text"]
    uid = request.form["user_id"]
    user_profile = get_user_profile(uid)
    error = remove_user_channels(user_profile, text)

    bot = LeaveMeAlone(curr_channel)
    if not error:
        greetings = random.choice(["Voila", "Awesome", "Bravo", "Great"])
        emoji = random.choice(["clap", "ok_hand", "white_check_mark", "thumbsup"])
        message = bot.get_default_payload(greetings+"! :"+emoji+":, all the channels removed successfully...")
        return jsonify({"blocks": message.get("blocks")})
    
    expression = random.choice(["Aw Snap", "Not Good", "Oh No", "That's Weird"])
    emoji = random.choice(["exclamation", "thinking_face", "cold_sweat", "eyes"])
    message = bot.get_default_payload(expression+"! :"+emoji+":, not able to remove all channels...")
    attachments = bot.get_attachments_payload(error, CONFIG["slack"].get("app_color"), "This seems to be the problem")
    return jsonify({"blocks": message.get("blocks"), "attachments": attachments})

# get all public and private channels that app has access to
get_channels()

if __name__ == "__main__":
    # Run our app on our externally facing IP address on port 3000 instead of
    # running it on localhost, which is traditional for development.
    APP.run(host='0.0.0.0', port=CONFIG.get("port"))
