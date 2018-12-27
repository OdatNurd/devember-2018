import sublime

import inspect
import struct
import socket


class ProtocolMessage():
    """
    This class represents the base class for all protocol messages to be sent
    between the client and the build host. It also acts as an intermediate
    that knows how to contruct a message of the appropriate type based on an
    encoded data object.
    """
    _registry = {}

    @classmethod
    def register(cls, classObj):
        """
        Register the provided class object with the system so that messages
        of that type can be decoded. The provided object needs to be a class
        that is a subclass of this class, which has implemented all of the
        abstract methods and ensures that it has a unique message ID.
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
        Takes a block of data (bytes) that contains an encoded protocol
        message. If the block is for a known protocol message (based on the
        encoded type ID), an instance of that message will be returned
        containing the decoded data. Otherwise a ValueError exception will be
        raised.
        """
        msg_id, = struct.unpack_from(">H", data)
        msg_class = cls._registry.get(msg_id)
        if msg_class is None:
            raise ValueError('Unknown message type (%d)' % msg_id)

        return msg_class.decode(data)

    @classmethod
    def msg_id(cls):
        """
        Provide a unique numeric id that represents this message. This needs to
        be implemented by subclasses; this version will throw an exception.
        """
        raise NotImplementedError('abstract base method should be overridden')

    @classmethod
    def decode(cls, data):
        """
        Takes a byte object and return back an instance of this class based on
        that data. The data provided will be exactly the data that was returned
        from a prior call to encode().
        """
        raise NotImplementedError('abstract base method should be overridden')

    def encode(self):
        """
        Return a bytes object that represents this message in a way that the
        decode() method can use to restore this object state. The first field
        in the encoded message needs to be the message type code.
        """
        raise NotImplementedError('abstract base method should be overridden')


class IntroductionMessage(ProtocolMessage):
    """
    This message is used to introduce ourselves to the build server and declare
    what version of the protocol we speak, so that the server knows what to
    expect from us.
    """
    protocol_version = 1

    def __init__(self, user, password, hostname=None, platform=None):
        self.user = user
        self.password = password
        self.hostname = hostname or socket.getfqdn()
        self.platform = platform or sublime.platform()

    def __str__(self):
        return "<Introduction user={0} host={1} platform={2} version={3}>".format(
            self.user, self.hostname, self.platform, self.protocol_version)

    @classmethod
    def msg_id(cls):
        return 0

    @classmethod
    def decode(cls, data):
        _, version, user, password, hostname, platform = struct.unpack(">HB64s64s64s8s", data)

        msg = IntroductionMessage(
            user.decode("utf-8").rstrip("\000"),
            password.decode("utf-8").rstrip("\000"),
            hostname.decode("utf-8").rstrip("\000"),
            platform.decode("utf-8").rstrip("\000"))
        msg.protocol_version = version

        return msg

    def encode(self):
        return struct.pack(">IHB64s64s64s8s",
            2 + 1 + 64 + 64 + 64 + 8,
            IntroductionMessage.msg_id(),
            self.protocol_version,
            self.user.encode("utf-8"),
            self.password.encode("utf-8"),
            self.hostname.encode("utf-8"),
            self.platform.encode("utf-8"))

ProtocolMessage.register(IntroductionMessage)


class MessageMessage(ProtocolMessage):
    """
    This message is used to report generic message information to the remote
    end of the connection.
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return "<Message msg='{0}'>".format(self.msg)

    @classmethod
    def msg_id(cls):
        return 1

    @classmethod
    def decode(cls, data):
        pre_len = struct.calcsize(">HI")
        _, msg_len = struct.unpack(">HI", data[:pre_len])

        msg_str, = struct.unpack_from(">%ds" % msg_len, data, pre_len)

        return MessageMessage(msg_str.decode('utf-8'))

    def encode(self):
        msg_data = self.msg.encode("utf-8")
        return struct.pack(">IHI%ds" % len(msg_data),
            2 + 4 + len(msg_data),
            MessageMessage.msg_id(),
            len(msg_data),
            msg_data)

ProtocolMessage.register(MessageMessage)


class ErrorMessage(ProtocolMessage):
    """
    This message is used to report an error to the remote end of the
    connection.
    """
    def __init__(self, error_code, error_msg):
        self.error_code = error_code
        self.error_msg = error_msg

    def __str__(self):
        return "<Error code={0} msg='{1}'>".format(
            self.error_code, self.error_msg)

    @classmethod
    def msg_id(cls):
        return 2

    @classmethod
    def decode(cls, data):
        pre_len = struct.calcsize(">HII")
        _, code, msg_len = struct.unpack(">HII", data[:pre_len])

        msg_str, = struct.unpack_from(">%ds" % msg_len, data, pre_len)

        return ErrorMessage(code, msg_str.decode('utf-8'))

    def encode(self):
        msg_data = self.error_msg.encode("utf-8")
        return struct.pack(">IHII%ds" % len(msg_data),
            2 + 4 + 4 + len(msg_data),
            ErrorMessage.msg_id(),
            self.error_code,
            len(msg_data),
            msg_data)

ProtocolMessage.register(ErrorMessage)


class SetBuildMessage(ProtocolMessage):
    """
    This message is used to report generic message information to the remote
    end of the connection.
    """
    def __init__(self, folders):
        self.folders = folders

    def __str__(self):
        return "<SetBuild folders={0}>".format(self.folders)

    @classmethod
    def msg_id(cls):
        return 3

    @classmethod
    def decode(cls, data):
        pre_len = struct.calcsize(">HI")
        _, msg_len = struct.unpack(">HI", data[:pre_len])

        folder_data, = struct.unpack_from(">%ds" % msg_len, data, pre_len)
        folders = folder_data.decode("utf-8").split("\x00")

        return SetBuildMessage(folders)

    def encode(self):
        folder_data = "\x00".join(self.folders).encode("utf-8")
        print("encoded folder data is %d bytes" % len(folder_data))
        return struct.pack(">IHI%ds" % len(folder_data),
            2 + 4 + len(folder_data),
            SetBuildMessage.msg_id(),
            len(folder_data),
            folder_data)

ProtocolMessage.register(SetBuildMessage)
