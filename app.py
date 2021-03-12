import os
import logging
import json
from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter
from leave_me_alone import LeaveMeAlone

# Initialize a Flask app to host the events adapter
APP = Flask(__name__)

LOGGER = None
CONFIG = {}
with open("config.json") as config:
    CONFIG = json.load(config)

# Create an events adapter and register it to an endpoint in the slack app for event injestion.
SLACK_EVENTS_ADAPTER = SlackEventAdapter(CONFIG["slack"].get("events_token"), CONFIG["slack"].get("events_route"), APP)

# Initialize a Web API client
SLACK_WEB_CLIENT = WebClient(token=CONFIG["slack"].get("token"))

def update_leave_status(channel):
    """Craft the LeaveMeAlone Bot, and send message to the channel
    """
    # Create a new Bot
    bot = LeaveMeAlone(channel)

    # Get the onboarding message payload
    message = bot.get_message_payload()

    # Post the onboarding message in Slack
    SLACK_WEB_CLIENT.chat_postMessage(**message)


# When a 'message' event is detected by the events adapter, forward that payload
# to this function.
@SLACK_EVENTS_ADAPTER.on("message")
def message(payload):
    """Parse the message event, and if the activation string is in the text,
    simulate a coin flip and send the result.
    """

    print(payload)

    # Get the event data from the payload
    event = payload.get("event", {})

    # Get the text from the event that came through
    text = event.get("text")

    # Check and see if the activation phrase was in the text of the message.
    # If so, execute the code to flip a coin.
    if "on leave today" in text.lower():
        # Since the activation phrase was met, get the channel ID that the event
        # was executed on
        channel_id = event.get("channel")

        # Execute the flip_coin function and send the results of
        # flipping a coin to the channel
        return update_leave_status(channel_id)

if __name__ == "__main__":
    # Create the logging object
    LOGGER = logging.getLogger()

    # Set the log level to DEBUG. This will increase verbosity of logging messages
    LOGGER.setLevel(logging.DEBUG)

    # Add the StreamHandler as a logging handler
    LOGGER.addHandler(logging.StreamHandler())

    # Run our app on our externally facing IP address on port 3000 instead of
    # running it on localhost, which is traditional for development.
    APP.run(host='0.0.0.0', port=CONFIG.get("port"))
