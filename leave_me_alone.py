# import the random library to help us generate the random numbers
import random

# Create the LeaveMeAlone Bot Class
class LeaveMeAlone:
    # The constructor for the class. It takes the channel name as the a
    # parameter and then sets it as an instance variable
    def __init__(self, channel):
        self.channel = channel

    # Craft and return the entire message payload as a dictionary.
    def get_default_payload(self, name):
        # Create a constant that contains the default text for the message
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Hey! *"+name+"*, I've updated your leave status."
                    ),
                },
            }
        ]
        return {
            "channel": self.channel,
            "blocks": blocks,
        }

    def get_leave_payload(self, uid, name, avatar):
        blocks = [
		    {
			    "type": "context",
	    	    "elements": [
	    	    	{
	    	    		"type": "image",
	    	    		"image_url": avatar,
	    	    		"alt_text": "avatar"
	    	    	},
	    	    	{
	    	    		"type": "mrkdwn",
	    	    		"text": "*<@"+uid+"|"+name+">* is on leave today."
	    	    	}
	    	    ]
	    	}
	    ]

        return {
            "channel": self.channel,
            "blocks": blocks,
        }

    def get_attachments_payload(self, text, color):
        return [
		    {
                "color": color,
			    "blocks": [
                    {
			    		"type": "section",
			    		"text": {
			    			"type": "mrkdwn",
			    			"text": "*Message*"
			    		}
			    	},
			    	{
			    		"type": "section",
			    		"text": {
			    			"type": "mrkdwn",
			    			"text": text
			    		}
			    	}
			    ]
		    }
	    ]
        