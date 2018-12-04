from threading import Thread
import inspect
import struct


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
    def startup(self):
        """
        Return: None

        Start up the system; initializes the client list, spins up the network
        thread. (maybe the thread only starts at the first connection made?)

        Called from plugin_loaded() to get things ready for connections when
        the package loads.
        """
        pass

    def shutdown(self):
        """
        Return: None

        Shut down the system; tells all open connections to shut down, then
        closes them and tells the network thread to terminuate itself.

        Called from plugin_unloaded() to break all of our connections if we get
        unloaded.
        """
        pass

    def connect(self, host, port):
        """
        Return: Connection

        Attempt to create a connection to the given host and port. A new
        Connection object is returned, which is not yet connected.

        This connection is added to our internal list.
        """
        pass

    def find_connection(self, host, port):
        """
        Return: [Connection]

        Find and return all connections matching the provided criteria; can
        find all connections to a host, all connections to a port, or just all
        connections.

        The returned list may be empty.
        """


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
        pass

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
    def run(self):
        """
        The main loop needs to loop until a semaphore tells it that it's time
        to quit, at which point it will drop out of the loop and gracefullly
        exit, perhaps telling all connections to close in response.

        This needs to select all connections for reading, only those that have
        data pending send for writing, and needs to safely busy loop when there
        are no connections.
        """
        pass


class ProtocolMessage():
    """
    A base class for all of our protocol messages.

    The methods flagged as base only are just that; implemented in the base
    class and then called there.

    The abstract methods are to be implemented by the subclasses to provide
    message specific behaviors. In particular the versions implemented here
    will throw an exception if you call them, to remind the developer that they
    forgot to implement something.
    """
    _registry = {}

    @classmethod
    def register(cls, classObj):
        """
        Called one or more times at startup to associate instances of all of
        the subclasses of this class with their ID values.

        This allows from_data() to determine what kind of message a block of
        data is so that it can call the appropriate decode() method.
        """
        if not inspect.isclass(classObj):
            raise ValueError('Need to provide a subclass of ProtocolMessage')

        if not issubclass(classObj, ProtocolMessage):
            raise ValueError('Can only register Protocol Messages (got %s)' % classObj.__name__)

        msg_id = classObj.msg_id()
        if msg_id in cls._registry:
            raise ValueError('Duplicate message type detected (%d, %s)' % (msg_id, classObj.__name__))

        cls._registry[msg_id] = classObj

    @classmethod
    def from_data(cls, data):
        """
        Takes a block of data (bytes) that contains a protocol message. This
        will examine the ID value of the message to determine what kind of
        message it is, and then if that type is known, it will invoke the
        decode() method on that class and return what it returns.

        This is the single endpoint for taking a block of data and turning it
        back into a message.
        """
        msg_id, = struct.unpack_from(">H", data)
        msg_class = cls._registry.get(msg_id)
        if msg_class is None:
            raise ValueError('Unknown message type (%d)' % msg_id)

        return msg_class.decode(data)

    @classmethod
    def msg_id(cls): #abstract
        """
        Provide a unique numeric id that represents this message. This needs to
        be implemented by subclasses; this version will throw an exception.
        """
        raise NotImplementedError('abstract base method should be overridden')

    @classmethod
    def decode(cls, data): # abstract
        """
        Takes a byte object and return back an instance of this class based on
        that data. The bytes provided will still contain the prefix id bytes.

        Unlike from_data(), this needs to be implemented by subclasses; this
        version will throw an exception.
        """
        raise NotImplementedError('abstract base method should be overridden')

    def encode(self): # abstract
        """
        Return a bytes object that represents this message in a way that the
        from_data() method can use to restore this object state.

        This needs to be implemented by subclasses; this version will throw
        an exception.
        """
        raise NotImplementedError('abstract base method should be overridden')


class IntroductionMessage(ProtocolMessage):
    """
    This message is used to introduce ourselves to the build server and declare
    what version of the protocol we speak, so that the server knows what to
    expect from us.
    """
    protocol_version = 1

    @classmethod
    def msg_id(cls):
        return 0

    @classmethod
    def decode(cls, data):
        msg = IntroductionMessage()
        _, msg.protocol_version  = struct.unpack(">HB", data)

        return msg

    def encode(self):
        return struct.pack(">HB",
            IntroductionMessage.msg_id(),
            self.protocol_version)


class ErrorMessage(ProtocolMessage):
    """
    This message is used to report an error to the remote end of the
    connection.
    """
    def __init__(self, error_code, error_msg):
        self.error_code = error_code
        self.error_msg = error_msg

    @classmethod
    def msg_id(cls):
        return 1

    @classmethod
    def decode(cls, data):
        pre_len = struct.calcsize(">HII")
        _, code, msg_len = struct.unpack(">HII", data[:pre_len])

        msg_str, = struct.unpack_from(">%ds" % msg_len, data, pre_len)

        return ErrorMessage(code, msg_str.decode('utf-8'))

    def encode(self):
        msg_data = self.error_msg.encode("utf-8")
        return struct.pack(">HII%ds" % len(msg_data),
            ErrorMessage.msg_id(),
            self.error_code,
            len(msg_data),
            msg_data)

ProtocolMessage.register(IntroductionMessage)
ProtocolMessage.register(ErrorMessage)

block1 = IntroductionMessage().encode()
block2 = ErrorMessage(1234, "An error of numerical run proportions has occured").encode()

msg1 = ProtocolMessage.from_data(block1)
msg2 = ProtocolMessage.from_data(block2)

print("Introduction with protocol version %d" % msg1.protocol_version)
print("Error(%d): '%s'" % (other.error_code, other.error_msg))




def test_simple_encode(string_val):
    """
    A simple encode example; all data that is of a fixed size. Of particular
    interest, the string is a fixed size to make it easier to grab data from
    the other end.
    """
    msg_id = 13
    val_1 = 18
    val_2 = 22
    val_3 = string_val.encode("utf-8")
    val_4 = True
    val_5 = 14.78

    return struct.pack(">Hii32s?d",
        msg_id, # Integer
        val_1,  # Integer
        val_2,  # Integer
        val_3,  # String
        val_4,  # Bool
        val_5)  # Double


def test_simple_decode(data):
    """
    Decoding the simple example.
    """
    msg_id, val_1, val_2, val_3, val_4, val_5 = struct.unpack(
        ">Hii32s?d", data)

    # Not sure what the best way to remove the null padding is.
    val_3 = val_3.decode("utf-8").rstrip('\x00')

    print("msg_id: {0}".format(msg_id))
    print("val_1 : {0}".format(val_1))
    print("val_2 : {0}".format(val_2))
    print("val_3 : '{0}'".format(val_3))
    print("val_4 : {0}".format(val_4))
    print("val_5 : {0}".format(val_5))


def test_complex_encode(string_val):
    """
    This is similar to the simple test, but now the string encodes as a
    variable length, which requires us to inject the original length into
    the bytes. The lesson here might be to put variable length strings at
    the end.
    """
    msg_id = 13
    val_1 = 18
    val_2 = 22
    val_3 = string_val.encode("utf-8")
    val_4 = True
    val_5 = 14.78

    return struct.pack(">HiiI%ds?d" % len(val_3),
        msg_id,            # Message ID
        val_1,             # Integer
        val_2,             # Integer
        len(val_3), val_3, # String
        val_4,             # Bool
        val_5)             # Double


def test_complex_decode(data):
    """
    Here in order to decode the data, we need to do it in pieces because the
    string is a dynamic length.
    """
    # Get everything up to and including the length of the variable length
    # string. We also need to pre-determine the length of this section for
    # later.
    prefix_len = struct.calcsize(">HiiI")
    msg_id, val_1, val_2, val_3_len = struct.unpack(">HiiI", data[:prefix_len])

    # Now we can extract the bytes for the string out, along with the
    # last couple of values.
    val_3, val_4, val_5 = struct.unpack_from(">%ds?d" % val_3_len,
                                             data, prefix_len)

    # Convert the bytes into a string. Here we don't need to strip the trailing
    # null padding because there isn't any.
    val_3 = val_3.decode("utf-8")

    print("msg_id: {0}".format(msg_id))
    print("val_1 : {0}".format(val_1))
    print("val_2 : {0}".format(val_2))
    print("val_3 : '{0}'".format(val_3))
    print("val_4 : {0}".format(val_4))
    print("val_5 : {0}".format(val_5))


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


def block_msg_id(data):
    """
    Get the message ID associated with the data in the given binary block.
    """
    return struct.unpack_from(">H", data)


# print("=== Simple ===")
# test_simple_decode(test_simple_encode("This string ends here. ->"))

# print("=== Complex ===")
# test_complex_decode(test_complex_encode("This string is longer, variable length, and ends here. ->"))

# print("=== Msg Lookup ===")
# msg_id = block_msg_id(test_simple_encode("This is a string"))
# print("Message has id %d" % msg_id)
