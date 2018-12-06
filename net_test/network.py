from threading import Thread, Event, Lock
import queue
import inspect
import struct
import socket
import time
import textwrap

from messages import ProtocolMessage, IntroductionMessage, ErrorMessage


### ---------------------------------------------------------------------------


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
        log("== Connection Manager Initializing")
        self.net_thread.start()

    def shutdown(self):
        """
        Return: None

        Shut down the system; tells all open connections to shut down, then
        closes them and tells the network thread to terminate itself.

        Called from plugin_unloaded() to break all of our connections if we get
        unloaded.
        """
        log("== Connection Manager Shutting Down")
        self.thr_event.set()
        self.net_thread.join(0.25)

        with self.conn_lock:
            for connection in self.connections:
                self._close_connection(connection)

    def connect(self, host, port):
        """
        Return: Connection

        Attempt to create a connection to the given host and port. A new
        Connection object is returned, which is not yet connected.

        This connection is added to our internal list.
        """
        with self.conn_lock:
            connection = self._open_connection(host, port)
            self.connections.append(connection)

        return connection

    def _open_connection(self, host, port):
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

        return Connection(self, sock, host, port)

    def _close_connection(self, connection):
        """
        Given a connection object, attempt to gracefully close it.
        """
        log("** Gracefully closing {0}".format(connection))
        if connection.socket:
            try:
                connection.socket.shutdown(socket.SHUT_RDWR)
                connection.socket.close()
            except:
                pass

            connection.socket = None

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
    def __init__(self, mgr, socket, host, port):
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

        log("  -- Creating connection: {0}".format(self))

    def __del__(self):
        log("  -- Destroying connection: {0}".format(self))
        # don't close here; assume the manager will close us before it goes
        # away.
        # self.close()

    def __str__(self):
        return "<Connection host='{0}:{1}' socket={2} out={3} in={4}>".format(
            self.host, self.port, self.socket.fileno() if self.socket else None,
            self.send_queue.qsize(),
            self.recv_queue.qsize())

    def __repr__(self):
        return str(self)

    def send(self, protocolMsgInstance):
        """
        Queue the provided protocol message up for sending to the other end of
        the connection.

        This would go into the input queue.
        """
        self.send_queue.put(protocolMsgInstance)

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

    def register(self, callback):
        """
        For registering an interest in incoming messages. Every time a message
        arrives, or the connection breaks, the callback is invoked to tell the
        caller.

        Could be enhanced in the future to also provide notifications on
        delivery of messages perhaps, or allow for registering specific types
        of message replies only.

        The return is some value for use in the unregister() call, in case you
        want to cancel registrations.

        Notifications will be raised by using set_timeout() (or the async
        variant) so that the calling code gets handled in the main thread.

        Notifications fire last, so you only get one notification for reception
        no matter how many are read, lets say.
        """
        pass

    def unregister(self, key):
        """
        Using the key, which was provided by call to register(), cancel all
        notifications from this connection.

        If the register() method gets smart enough to filter, this should also
        be enhanced.
        """
        pass

    def close(self):
        """
        For closing this particular connection; the socket will be shut down
        and the connection will be removed from the connection list.

        Perhaps we keep the connection until we know it fully closes, to allow
        it to send any partial sends. We may also want to make it transmit a
        graceful goodbye message or something.
        """
        self.manager._remove(self)


    def fileno(self):
        """
        For allowing us to use this client in a call to select(); this should
        return the socket handle for the select() call to select on. It comes
        from our socket.
        """
        if self.socket:
            return socket.fileno()

        return None

    def _is_writeable(self):
        """
        Returns True if this connection is write-able; that is, that it has
        something to write.

        This would return True if the input queue has items in it or if we
        are currently sending a message and didn't send it all in one shot.

        The network thread uses this to know if this client cares to know if
        it is write-able or not.
        """
        return self.send_queue.qsize() > 0

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
        pass

    def _receive(self):
        """
        Called by the network thread in response to a select() call if this
        connection selected as readable.

        Here we would try to receive as many messages as we can from the
        socket call, queuing any that we fully read and tracking partial
        reads for later.
        """
        pass


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
        log("== Launching network thread")
        while not self.event.is_set():
            time.sleep(0.25)

        log("== Network thread is gracefully ending")


### ---------------------------------------------------------------------------


def message_to_block(data):
    """
    Given an encoded message block, create and return a block that wraps it as
    a block to be transmitted to the remote end.

    The theory here is that writing a message to the opposite end is easier if
    we can write just a single blob of data in one operation; on the receive
    end this is not possible because we need to read the length first and then
    the block.
    """
    block = bytearray(len(data) + 4)
    struct.pack_into(">I", block, 0, len(data))
    block[4:] = data

    return block

def test():
    mgr = ConnectionManager()
    mgr.startup()

    time.sleep(2)

    mgr.shutdown()
    print("Run complete")

# sublime.set_timeout_async(lambda: test())

mgr = ConnectionManager()
mgr.startup()

mgr.connect("localhost", 50000)
mgr.connect("dart", 7)
conn1 = mgr.connect("dart", 7)

conn1.close()
conn1 = None
time.sleep(1)

# print(mgr.find_connection(host="localhost", port=50000))
mgr.shutdown()
print("Run complete")