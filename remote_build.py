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
    """
    Initialize plugin state.
    """
    global netManager

    netManager = ConnectionManager()
    netManager.startup()

    rb_setting.obj = sublime.load_settings("RemoteBuild.sublime-settings")
    rb_setting.default = {
        "build_hosts": []
    }



def plugin_unloaded():
    global netManager

    if netManager is not None:
        netManager.shutdown()
        netManager = None


### ---------------------------------------------------------------------------


def rb_setting(key):
    """
    Get a RemoteBuild setting from a cached settings object.
    """
    default = rb_setting.default.get(key, None)
    return rb_setting.obj.get(key, default)


### ---------------------------------------------------------------------------


class RemoteBuildServerEnterPasswordCommand(sublime_plugin.WindowCommand):
    def run(self, **kwargs):
        prompt = "{username}@{host} password:".format(
            username=kwargs["username"],
            host=kwargs["host"])

        self.window.show_input_panel(
            prompt, "", lambda passwd: self.enter(passwd, kwargs), None, None)

    def enter(self, passwd, args):
        args["password"] = passwd
        self.window.run_command("remote_build", args)


class RemoteBuildCommand(sublime_plugin.WindowCommand):
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
