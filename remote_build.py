import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys

from .messages import ProtocolMessage, IntroductionMessage
from .messages import MessageMessage, ErrorMessage

from .network import ConnectionManager, Notification, log


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

    if netManager is not None:
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
            self.connection = netManager.connect(host, port)
            self.connection.register(lambda c,n: self.result(c,n))
            self.connection.send(IntroductionMessage("tmartin", "password"))

        self.connection.send(MessageMessage(msg))

    def result(self, connection, notification):
        log("==> Callback: {0}:{1} = {3}, {2}",
            connection.host, connection.port,
            "connected" if connection.connected else "disconnected",
            notification,
            panel=True)

        if notification == Notification.MESSAGE:
            msg = connection.receive()
            if msg is None:
                log(" -> Error: Notification says message, queue says no")
            else:
                log("Received: '{0}'", msg, panel=True)


### ---------------------------------------------------------------------------
