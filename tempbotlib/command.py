import logging
log = logging.getLogger(__name__)


class CommandStatusError(Exception):
    pass


class Command:
    def __init__(self, command="", channel="",
                 message="", files=[], args={}):
        self.command = command
        self.channel = channel
        self.message = message
        self.files = files
        self.args = args
