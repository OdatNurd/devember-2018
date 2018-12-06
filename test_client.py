import sublime
import sublime_plugin

from threading import Thread
from queue import Queue

import textwrap
import socket
import sys

# related:
#     https://docs.python.org/3.3/howto/sockets.html
#     https://realpython.com/python-sockets/#echo-client
#     https://docs.python.org/3.3/library/socket.html


## ---------------------------------------------------------------------------


_jobQueue = None
_jobThread = None


## ---------------------------------------------------------------------------


def plugin_loaded():
    global _jobQueue, _jobThread

    _jobQueue = Queue()
    _jobThread = NetworkThread()
    _jobThread.start()


def plugin_unloaded():
    if _jobThread is not None:
        _jobQueue.put((None, None, None))
        _jobThread.join(0.25)


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


class NetworkThread(Thread):
    """
    Spawns a background thread that will perform our socket IO.
    """
    def __init__(self):
        super().__init__()
        log("Creating NetworkThread{0}", self)

    def __del__(self):
        log("Destroing NetworkThread{0}", self)

    def run(self):
        running = True
        while running:
            host, port, msg = _jobQueue.get()
            if host is None:
                running = False
            else:
                self.run_query(host, port, msg)

    def run_query(self, host, port, msg):
        msg =  msg + "<EOF>"

        try:
            # Create a socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Make the socket non-blocking; requires calls to select, so
                # lets skip that for now. Could maybe also use settimeout()
                # in combination with a select() to verify that an operation
                # may work and then use a blocking read.
                # sock.setblocking(0)

                # Connect; anecdotally instead of a host this should be a
                # resolved IP address -- the first resolved address is used,
                # which may be either IPv4 or IPv6.
                sock.connect((host, port))

                # Sends may be short; send returns the number of bytes sent (I
                # assume buffered at the socket level). Apparently there is a
                # sendall(), but from looking at it we probably don't want it
                # because if a send is interrupted by a signal it errors out
                # and you can't tell how much was sent.
                #
                # Sends need to be bytes.
                sock.send(msg.encode('utf-8'))

                # Blocking receive of the data;
                #
                # Read data is bytes
                data = sock.recv(1024).decode('utf-8')

                # If we got a whole read, throw the trailer off.
                pos = data.index("<EOF>")
                data = data[:pos] if pos > 0 else data

                # Display it.
                sublime.set_timeout(lambda:
                    log("Received\n{0}", data, dialog=True))

        except Exception as error:
            err = error
            sublime.set_timeout(lambda:
                log("Socket Error:\n{0}", err, error=True))


class ProtocolMessage():
    """
    The base class for all protocol messages sent to and received from the
    remote end. The constructor can take any number of keyword arguments, but
    the _data argument is special and tells the constructor that it should
    construct based on the bytes in the data instead.
    """
    def __init__(self, _data=None, **kwargs):
        if _data:
            self.decode(_data)

    def msg_id(self):
        """
        The unique protocol message id for messages of this type. This is used
        to associated protocol messages classes with the id values they
        represent.
        """
        pass

    def encode(self):
        """
        Given the state of this object, return back a protocol formatted bytes
        object that can be used to reconstruct the object later. The first
        bytes in the encoded data must be the msg_id() of this message type
        so that the received knows what message type it is.
        """
        pass

    def decode(self, data):
        """
        Given a piece of data, set up this object by decoding that data back
        into the appropriate parts. The length of the data can be queried or
        verified to ensure that things work as we expect.
        """
        pass


### ---------------------------------------------------------------------------


# Crude blocking socket example; should be threaded, non-blocking, check
# errors better, etc.
#
# If our protocol is binary, use struct.pack() to prepare data.
class SocketTestCommand(sublime_plugin.ApplicationCommand):
    last_msg = "Hello, World!"

    def run(self, host, port):
        sublime.active_window().show_input_panel(
            "Message:",
            self.last_msg or "",
            lambda msg: self.test(host, port, msg), None, None)

    def test(self, host, port, msg):
        self.last_msg = msg
        _jobQueue.put((host, port, msg))


### ---------------------------------------------------------------------------

