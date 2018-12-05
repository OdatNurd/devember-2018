import sublime
import sublime_plugin

from threading import Thread, Event, Lock
import inspect
import struct
import time

from .messages import ProtocolMessage, IntroductionMessage, ErrorMessage
from .test_client import log


class ConnectionManager():
    """
    A class that manages all of our connections. There should be a single
    global instance of this class created, and it's what connects all of the
    parts of the system together.

    Underlyiung this would be a threadsafe list of all connections. Connections
    can be added and found from here. All read/write/close operations happen
    in the connection.

    The network thread introspects the client list here for use in select()
    calls to delegate network activity to the appropriate client.
    """
    def __init__(self):
        self.thr_event = Event()
        self.net_thread = NetworkThread(self.thr_event)
        self.connections = list()
        self.conn_lock = Lock()

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
        closes them and tells the network thread to terminuate itself.

        Called from plugin_unloaded() to break all of our connections if we get
        unloaded.
        """
        log("== Connection Manager Shutting Down")
        self.thr_event.set()
        self.net_thread.join(0.25)

    def connect(self, host, port):
        """
        Return: Connection

        Attempt to create a connection to the given host and port. A new
        Connection object is returned, which is not yet connected.

        This connection is added to our internal list.
        """
        with self.conn_lock:
            new_connection = Connection(host, port)
            self.connections.append(new_connection)

        return new_connection

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


class Connection():
    """
    This class wraps a connection to the remote server. They are handed out by
    the connection manager in response to opening a connection.
    """

    # The first queue is for messages that we've been told to deliver to the
    # other end of the connection while the second queue is for holding
    # messages that have been received.
    send_queue = None
    recv_queue = None

    # The client socket for this connection. This would be a non-blocking
    sock = None

    # Variables to store the message currently being sent and received, until
    # we get enough data would also be here.

    def __init__(self, host, port):
        """
        Create a new connection to the provided host and port combination.
        This should only be called by the connection manager, which will hold
        onto the connection.
        """
        self.host = host;
        self.port = port

    def __str__(self):
        return "<Connection host='{0}:{1}'>".format(self.host, self.port)

    def __repr__(self):
        return str(self)

    def send(self, protocolMsgInstance):
        """
        Queue the provided protocol message up for sending to the other end of
        the connection.

        This would go into the input queue.
        """
        pass

    def receive(self):
        """
        For getting received messages. This would return None if there are no
        pending messages, or a ProtocolMessage from the queue if any are
        available.
        """
        pass

    def register(self, callback):
        """
        For registering an interest in incomuing messages. Every time a message
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
        pass

    def fileno(self):
        """
        For allowing us to use this client in a call to select(); this should
        return the socket handle for the select() call to select on. It comes
        from our socket.
        """
        pass

    def _is_writeable(self):
        """
        Returns True if this connection is writeable; that is, that it has
        something to write.

        Thuis would return True if the input queue has items in it or if we
        are currently sending a message and didn't send it all in one shot.

        The network thread uses this to know if this client cares to know if
        it is writeable or not.
        """
        pass

    def _send(self):
        """
        Called by the network thread in response to a select() call if this
        connection selected as writeable.

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


class NetworkThread(Thread):
    """
    The background thread for doing all of our socket I/O. This ensures that
    we keep doing sends and receives no matter what else is happening.
    """
    def __init__(self, event):
        super().__init__()
        self.event = event
        log("== Creating network thread")

    def __del__(self):
        log("== Destroying network thread")

    def run(self):
        """
        The main loop needs to loop until a semaphore tells it that it's time
        to quit, at which point it will drop out of the loop and gracefullly
        exit, perhaps telling all connections to close in response.

        This needs to select all connections for reading, only those that have
        data pending send for writing, and needs to safely busy loop when there
        are no connections.
        """
        log("== Launching network thread")
        while not self.event.is_set():
            time.sleep(0.25)

        log("== Network thread is gracefullly ending")


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
