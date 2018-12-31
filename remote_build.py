import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys
import os

from .messages import ProtocolMessage, IntroductionMessage
from .messages import MessageMessage, ErrorMessage
from .messages import SetBuildMessage, AcknowledgeMessage
from .messages import FileContentMessage

from .network import ConnectionManager, Notification, log

from .file_gather import find_project_files


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


class RemoteBuildSelectConnectionCommand(sublime_plugin.WindowCommand):
    """
    Prompt the user with a quick panel to select one of the connections from
    the connection list.

    Upon selection, this forwards all arguments that the command receives,
    plus a user, host, port and password to the build command to actually use
    the build.

    If the selected connection has no password, the command sends all arguments
    to the command to select a password instead.
    """
    def run(self, **kwargs):
        hosts = rb_setting("build_hosts")

        items = []
        for server in hosts:
            if server.get("password") is None:
                format_string = "rb://{username}@{host}:{port}"
            else:
                format_string = "rb://{username}:********@{host}:{port}"

            items.append([server["name"], format_string.format(**server)])

        self.window.show_quick_panel(
            items=items,
            on_select=lambda idx: self.select_item(idx, hosts, kwargs))

    def select_item(self, index, hosts, args):
        if index >= 0:
            server = hosts[index]
            del server["name"]
            args.update(server)

            if args.get("password") is None:
                cmd = "remote_build_server_enter_password"
            else:
                cmd = "remote_build"

            self.window.run_command(cmd, args)


class RemoteBuildServerEnterPasswordCommand(sublime_plugin.WindowCommand):
    """
    Prompt the user with an input panel to enter the password for a given
    user@host combination.

    Once the password is entered, all arguments to the command, plus the newly
    entered password, are sent to the build command to actually execute the
    build.
    """
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
    def __init__(self, window):
        super().__init__(window)
        self.connection = None

    def run(self, **kwargs):
        self.build_args = kwargs

        # If there is no connection, or there is but it's not connected, then
        # either create a new connection or prompt the user for connection
        # details, depending on the arguments we got.
        if self.connection is None or self.connection.connected == False:
            if all (k in kwargs for k in ("host", "port", "username", "password")):
                self.connection = netManager.connect(kwargs["host"], kwargs["port"], lambda c,n: self.result(c,n))
                self.connection.send(IntroductionMessage(kwargs["username"], kwargs["password"]))
                return

            else:
                return self.window.run_command("remote_build_select_connection", kwargs)

        # Must have a connection, so start the build now.
        self.start_build()

    def start_build(self):
        """
        Kick off a build by capturing the list of project folders and files
        and announcing it to the server.
        """
        self.proj_info = find_project_files(self.window)
        self.proj_roots = list(self.proj_info.keys())
        self.proj_id = SetBuildMessage.make_build_id(self.proj_roots)

        # Make a big list of all files that need to be transferred. This is
        # a list of lists that contains the root and the relative name. As
        # we transmit files to the server, they're removed from this list.
        # We know the build is ready to execute when the last file is done.
        self.proj_files = []
        for root in self.proj_roots:
            for file in self.proj_info[root]:
                self.proj_files.append([root, file])

        # Send off the message to start the build now.
        self.connection.send(SetBuildMessage(self.proj_id, self.proj_roots))

    def acknowledge(self, msg_id, ack):
        # For now, we don't do anything in response to a NACK message; only
        # ACK.
        if not ack:
            return

        # On ack of the introduction message, start the build; we logged in
        if msg_id == IntroductionMessage.msg_id() :
            return self.start_build()

        # When the build message or a file transmission is acknowledged, we
        # can send the first (or next) file.
        if msg_id in (SetBuildMessage.msg_id(), FileContentMessage.msg_id()):
            self.send_next_file()

    def send_next_file(self):
        if self.proj_files:
            file_info = self.proj_files.pop()
            return self.connection.send(FileContentMessage(file_info[0], file_info[1]))

        log("Receive: All files transmitted", panel=True)

    def result(self, connection, notification):
        if notification == Notification.CLOSED:
            if connection == self.connection:
                self.connection = None
                log("Connection: Closed", panel=True)

        elif notification == Notification.CONNECTING:
            log("Connection: Connecting to {0}:{1}", connection.host, connection.port, panel=True)

        elif notification == Notification.CONNECTED:
            log("Connection: Connected", panel=True)

        elif notification == Notification.CONNECTION_FAILED:
            log("Connection: Failed", panel=True)

        elif notification == Notification.SEND_ERROR:
            log("Network: Send error", panel=True)

        elif notification == Notification.RECV_ERROR:
            log("Network: Receive error", panel=True)

        elif notification == Notification.MESSAGE:
            msg = connection.receive()
            if msg is None:
                return

            if isinstance(msg, MessageMessage):
                log("Message: {0}", msg.msg, panel=True)

            elif isinstance(msg, ErrorMessage):
                log("Error: [{0}] => {1}", msg.error_code, msg.error_msg, panel=True)

            elif isinstance(msg, AcknowledgeMessage):
                self.acknowledge(msg.message_id, msg.positive)

            elif isinstance(msg, FileContentMessage):
                log("Receive: {0}/{1} ({2} bytes)",
                    os.path.basename(os.path.normpath(msg.root_path)),
                    msg.relative_name,
                    len(msg.file_content),
                    panel=True)
                # log("=== Received File ===", panel=True)
                # log("{0}/{1}", msg.root_path, msg.relative_name, panel=True)
                # log("======================", panel=True)
                # log("{0}", msg.file_content, panel=True)
                # log("======================", panel=True)

            else:
                log("Unhandled: {0}", msg, panel=True)


### ---------------------------------------------------------------------------
