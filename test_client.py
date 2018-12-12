import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys

from .messages import ProtocolMessage, IntroductionMessage
from .messages import MessageMessage, ErrorMessage

from .network import ConnectionManager, log


### ---------------------------------------------------------------------------


# Our global connection manager object
netManager = None


### ---------------------------------------------------------------------------


def plugin_loaded():
    global netManager

    netManager = ConnectionManager()
    netManager.startup()


def plugin_unloaded():
    global netManager

    netManager.shutdown()
    netManager = None


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
        if self.connection is None or self.connection.socket is None:
            self.connection = netManager.connect("dart", 50000)

        self.connection.send(MessageMessage(msg))
        sublime.set_timeout(lambda: self.result(), 500)

    def result(self):
        msg = self.connection.receive()
        if msg is not None:
            log("Received:\n{0}", msg.msg, dialog=True)


### ---------------------------------------------------------------------------
