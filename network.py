import sublime
import sublime_plugin

from threading import Thread, Event, Lock
import queue
import inspect
import struct
import socket
import select
import os
import time
import textwrap

from .messages import ProtocolMessage


### ---------------------------------------------------------------------------


def log(msg, *args, dialog=False, error=False, panel=False, **kwargs):
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

    if panel:
        window = sublime.active_window()
        if "output.remote_build" not in window.panels():
            view = window.create_output_panel("remote_build")
            view.set_read_only(True)
            view.settings().set("_rb_net_window", True)
            view.settings().set("gutter", False)
            view.settings().set("rulers", [])
            view.settings().set("word_wrap", False)
            view.settings().set("syntax", "Packages/devember_2018/RemoteBuildPanel.sublime-syntax")
            # view.assign_syntax("Packages/devember_2018/RemoteBuildPanel.sublime-syntax")

        view = window.find_output_panel("remote_build")
        view.run_command("append", {
            "characters": msg + "\n",
            "force": True,
            "scroll_to_end": True})

        window.run_command("show_panel", {"panel": "output.remote_build"})


### ---------------------------------------------------------------------------


class Notification():
    """
    An enumeration for that various connection notifications that a Connection
    instance may raise.
    """
    # The connection was closed (either gracefully or due to an error).
    CLOSED=0

    # A new connection attempt is being made on the connection
    CONNECTING=1

    # The connection has successfully connected
    CONNECTED=2

    # The connection attempt to the remote host failed.
    CONNECTION_FAILED=3

    # An error occured while sending data to the server
    SEND_ERROR=4

    # An error occured while receiving data from the server
    RECV_ERROR=5

    # A message has been received
    MESSAGE=6


### ---------------------------------------------------------------------------


class ConnectionManager():
    """
    A class that manages all of our connections. There should be a single
    global instance of this class created, and it's what connects all of the
    parts of the system together.

    Underlying this would be a thread safe list of all connections. Connections
    can be added and found from here. All read/write/close operations happen
    in the connection.

    The network thread introspects the client list here for use in select()
    calls to delegate network activity to the appropriate client.
    """
    def __init__(self):
        self.conn_lock = Lock()
        self.connections = list()
        self.thr_event = Event()
        self.net_thread = NetworkThread(self.conn_lock, self.connections,
                                        self.thr_event)

    def startup(self):
        """
        Return: None

        Start up the system; initializes the client list, spins up the network
        thread. (maybe the thread only starts at the first connection made?)

        Called from plugin_loaded() to get things ready for connections when
        the package loads.
        """
        log("=> Connection Manager Initializing")
        self.net_thread.start()

    def shutdown(self):
        """
        Return: None

        Shut down the system; tells all open connections to shut down, then
        closes them and tells the network thread to terminate itself.

        Called from plugin_unloaded() to break all of our connections if we get
        unloaded.
        """
        log("=> Connection Manager Shutting Down")
        self.thr_event.set()
        self.net_thread.join(0.25)

        with self.conn_lock:
            for connection in self.connections:
                self._close_connection(connection)

    def connect(self, host, port, callback):
        """
        Return: Connection

        Attempt to create a connection to the given host and port. A new
        Connection object is returned, which is not yet connected.

        If a callback is required, it will be registered directly as soon as
        the connection is created.

        This connection is added to our internal list.
        """
        with self.conn_lock:
            connection = self._open_connection(host, port, callback)
            self.connections.append(connection)

        return connection

    def _open_connection(self, host, port, callback):
        """
        Do the underlying work of actually opening up a brand new connection
        to the provided host and port.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)
            sock.connect((host, port))
        except BlockingIOError:
            pass

        connection = Connection(self, sock, host, port, callback)
        # log("Connecting to: {0}:{1}", host, port, panel=True)

        return connection


    def _close_connection(self, connection):
        """
        Given a connection object, attempt to gracefully close it.
        """
        # log("Closing Connection: {0}:{1}",
        #     connection.host, connection.port, panel=True)

        if connection.socket:
            try:
                connection.socket.shutdown(socket.SHUT_RDWR)
                connection.socket.close()

            except:
                pass

            finally:
                connection.socket = None
                connection.connected = False

    def find_connection(self, host=None, port=None):
        """
        Return: [Connection]

        Find and return all connections matching the provided criteria; can
        find all connections to a host, all connections to a port, or just all
        connections.

        The returned list may be empty.
        """
        retcons = list()
        with self.conn_lock:
            for connection in self.connections:
                if host is not None and host != connection.host:
                    continue

                if port is not None and port != connection.port:
                    continue

                retcons.append(connection)

        return retcons

    def _remove(self, connection):
        """
        Remove the provided connection from the list of connections that we
        are currently storing.
        """
        with self.conn_lock:
            self._close_connection(connection)
            self.connections[:] = [conn for conn in self.connections
                                        if conn is not connection]


### ---------------------------------------------------------------------------


class Connection():
    """
    This class wraps a connection to the remote server. They are handed out by
    the connection manager in response to opening a connection.
    """
    def __init__(self, mgr, socket, host, port, callback):
        """
        Create a new connection to the provided host and port combination.
        This should only be called by the connection manager, which will hold
        onto the connection.
        """
        self.manager = mgr
        self.send_queue = queue.Queue()
        self.recv_queue = queue.Queue()

        self.host = host;
        self.port = port

        self.socket = socket
        self.connected = False

        self.send_data = None
        self.receive_data = bytearray()
        self.expected_length = None

        self.callback = callback

        # We get created in response to a connect call, so trigger a connecting
        # notification right now.
        self._raise(Notification.CONNECTING)

        # log("  -- Creating connection: {0}".format(self))

    def __del__(self):
        # don't close here; assume the manager will close us before it goes
        # away.
        # self.close()
        # log("  -- Destroying connection: {0}".format(self))
        pass

    def __str__(self):
        return "<Connection host='{0}:{1}' socket={2} out={3} in={4}{5}>".format(
            self.host, self.port, self.socket.fileno() if self.socket else None,
            self.send_queue.qsize(),
            self.recv_queue.qsize(),
            " CONNECTED" if self.connected else "")

    def __repr__(self):
        return str(self)

    def send(self, protocolMsgInstance):
        """
        Queue the provided protocol message up for sending to the other end of
        the connection.

        This would go into the input queue.
        """
        self.send_queue.put(protocolMsgInstance.encode())

    def receive(self):
        """
        For getting received messages. This would return None if there are no
        pending messages, or a ProtocolMessage from the queue if any are
        available.
        """
        try:
            return self.recv_queue.get_nowait()
        except queue.Empty:
            return None

    def close(self):
        """
        For closing this particular connection; the socket will be shut down
        and the connection will be removed from the connection list.

        Perhaps we keep the connection until we know it fully closes, to allow
        it to send any partial sends. We may also want to make it transmit a
        graceful goodbye message or something.
        """
        self.manager._remove(self)
        self._raise(Notification.CLOSED)



    def fileno(self):
        """
        For allowing us to use this client in a call to select(); this should
        return the socket handle for the select() call to select on. It comes
        from our socket.
        """
        if self.socket:
            return self.socket.fileno()

        return None

    def _raise(self, notification):
        """
        If there is a registered listener, trigger a callback to let the other
        end know that there is a change in state for us. The callback is
        triggered in the main thread in Sublime.
        """
        if self.callback:
            sublime.set_timeout(lambda: self.callback(self, notification))

    def _is_writeable(self):
        """
        Returns True if this connection is write-able; that is, that it has
        something to write.

        This would return True if the input queue has items in it or if we
        are currently sending a message and didn't send it all in one shot.

        The network thread uses this to know if this client cares to know if
        it is write-able or not.
        """
        if self.socket:
            return (not self.connected or
                    self.send_queue.qsize() > 0 or
                    self.send_data is not None)

        return False

    def _send(self):
        """
        Called by the network thread in response to a select() call if this
        connection selected as write-able.

        Here we would try to send as many messages from the queue as possible,
        with possibly a sanity check to ensure that we don't get into an I/O
        starvation situation.

        If we can't send a whole message, track what we didn't send for later
        calls.
        """
        # Since sends happen after receives, it's possible that the connection
        # broke during the receive, in which case we should do nothing here.
        if self.socket is None:
            return

        if not self.connected:
            code = self.socket.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if code == 0:
                self.connected = True
                # log("Connection established: {0}:{1}",
                #     self.host, self.port, panel=True)
                self._raise(Notification.CONNECTED)
            else:
                # log("Connection failed: {0}:{1}: {2}",
                #     self.host, self.port, os.strerror(code), panel=True)
                self._raise(Notification.CONNECTION_FAILED)
                self.close()
                return

        try:
            for _ in range(10):
                if self.send_data is None:
                    self.send_data = self.send_queue.get_nowait()

                sent = self.socket.send(self.send_data)
                # sent = self.socket.send(self.send_data[:1])
                self.send_data = self.send_data[sent:]
                if not self.send_data:
                    self.send_data = None
                else:
                    break

        except queue.Empty:
            pass

        except BlockingIOError:
            pass

        except Exception as e:
            self._raise(Notification.SEND_ERROR)
            log("Send Error: {0}:{1}: {2}",
                self.host, self.port, e)
            self.close()

    def _receive(self):
        """
        Called by the network thread in response to a select() call if this
        connection selected as readable.

        Here we would try to receive as many messages as we can from the
        socket call, queuing any that we fully read and tracking partial
        reads for later.
        """
        try:
            new_data = self.socket.recv(4096)
            if not new_data:
                return self.close()

            self.receive_data.extend(new_data)

            while True:
                if self.expected_length is None:
                    if len(self.receive_data) >= 4:
                        self.expected_length, = struct.unpack_from(">I", self.receive_data)
                        self.receive_data = self.receive_data[4:]
                    else:
                        break

                if len(self.receive_data) >= self.expected_length:
                    msg_data = self.receive_data[:self.expected_length]
                    self.receive_data = self.receive_data[self.expected_length:]
                    self.expected_length = None

                    self.recv_queue.put(ProtocolMessage.from_data(msg_data))
                    self._raise(Notification.MESSAGE)

                else:
                    break

        except BlockingIOError:
            pass

        except Exception as e:
            self._raise(Notification.RECV_ERROR)
            log("Receive Error: {0}:{1}: {2}",
                self.host, self.port, e)
            self.close()
            return


### ---------------------------------------------------------------------------


class NetworkThread(Thread):
    """
    The background thread for doing all of our socket I/O. This ensures that
    we keep doing sends and receives no matter what else is happening.
    """
    def __init__(self, lock, connections, event):
        log("== Creating network thread")
        super().__init__()
        self.conn_lock = lock
        self.connections = connections
        self.event = event

    def __del__(self):
        log("== Destroying network thread")

    def run(self):
        """
        The main loop needs to loop until a semaphore tells it that it's time
        to quit, at which point it will drop out of the loop and gracefully
        exit, perhaps telling all connections to close in response.

        This needs to select all connections for reading, only those that have
        data pending send for writing, and needs to safely busy loop when there
        are no connections.
        """
        log("== Entering network loop")
        while not self.event.is_set():
            with self.conn_lock:
                readable = [c for c in self.connections if c.connected]
                writable = [c for c in self.connections if c._is_writeable()]

            if not readable and not writable:
                # log("*** Network thread has no connections to service")
                time.sleep(0.25)
                continue

            rset, wset, _ = select.select(readable, writable, [], 0.25)

            for conn in rset:
                conn._receive()

            for conn in wset:
                conn._send()

        log("== Network thread is gracefully ending")


### ---------------------------------------------------------------------------
