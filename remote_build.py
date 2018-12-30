import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys

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
        if self.connection is None or self.connection.connected == False:
            if all (k in kwargs for k in ("host", "port", "username", "password")):
                return self.make_connection(kwargs["host"], kwargs["port"],
                                            kwargs["username"], kwargs["password"])
            else:
                return self.window.run_command("remote_build_select_connection", kwargs)

        self.start_build()

    def make_connection(self, host, port, username, password):
        self.connection = netManager.connect(host, port)
        self.connection.register(lambda c,n: self.result(c,n))
        self.connection.send(IntroductionMessage(username, password))

        self.start_build()

    def start_build(self):
        project_files = find_project_files(self.window)
        project_folders = list(project_files.keys())
        project_id = SetBuildMessage.make_build_id(project_folders)
        self.connection.send(SetBuildMessage(project_id, project_folders))

        msg = FileContentMessage(project_folders[0], "LICENSE")
        print(msg)
        self.connection.send(msg)

    def result(self, connection, notification):
        # log("==> Callback: {0}:{1} = {3}, {2}",
        #     connection.host, connection.port,
        #     "connected" if connection.connected else "disconnected",
        #     notification,
        #     panel=True)

        if connection.connected == False:
            self.connection = None

        if notification == Notification.MESSAGE:
            msg = connection.receive()
            while msg is not None:
                if isinstance(msg, MessageMessage):
                    log("Message: {0}", msg.msg, panel=True)
                elif isinstance(msg, ErrorMessage):
                    log("Error: [{0}] => {1}", msg.error_code, msg.error_msg, panel=True)
                elif isinstance(msg, FileContentMessage):
                    log("{0}/{1}", msg.root_path, msg.relative_name, panel=True)
                    log("{0}", msg.file_content, panel=True)
                else:
                    log("Unhandled: {0}", msg, panel=True)

                msg = connection.receive()


### ---------------------------------------------------------------------------
