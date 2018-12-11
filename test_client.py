import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys

from .messages import ProtocolMessage, IntroductionMessage
from .messages import MessageMessage, ErrorMessage

from .network import mgr


## ---------------------------------------------------------------------------


def log(msg, *args, dialog=False, error=False, **kwargs):
    """
    Generate a message to the console and optionally as either a message or
    error dialog. The message will be formatted and dedented before being
    displayed, and will be prefixed with its origin.
    """
    msg = textwrap.dedent(msg.format(*args, **kwargs)).strip()

    if error:
        print("remote_build:")
        return sublime.error_message(msg)

    for line in msg.splitlines():
        print("remote_build: {msg}".format(msg=line))

    if dialog:
        sublime.message_dialog(msg)


### ---------------------------------------------------------------------------


class SocketTestCommand(sublime_plugin.WindowCommand):
    last_msg = "Hello, World!"

    def __init__(self, window):
        super().__init__(window)
        self.connection = None

    def run(self, host, port):
        sublime.active_window().show_input_panel(
            "Message:",
            self.last_msg or "",
            lambda msg: self.test(host, port, msg), None, None)

    def test(self, host, port, msg):
        self.last_msg = msg
        if self.connection is None:
            self.connection = mgr.connect("dart", 50000)

        self.connection.send(MessageMessage(msg))
        sublime.set_timeout(lambda: self.result(), 500)

    def result(self):
        msg = self.connection.receive()
        if msg is not None:
            log("Received:\n{0}", msg.msg, dialog=True)


### ---------------------------------------------------------------------------
