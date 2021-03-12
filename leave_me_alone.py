# import the random library to help us generate the random numbers
import random

# Create the LeaveMeAlone Bot Class
class LeaveMeAlone:

    # Create a constant that contains the default text for the message
    DEFAULT_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": (
                "Sure! I'll update your leave status....\n\n"
            ),
        },
    }

    # The constructor for the class. It takes the channel name as the a
    # parameter and then sets it as an instance variable
    def __init__(self, channel):
        self.channel = channel

    # Craft and return the entire message payload as a dictionary.
    def get_message_payload(self):
        return {
            "channel": self.channel,
            "blocks": [
                self.DEFAULT_BLOCK
            ],
        }