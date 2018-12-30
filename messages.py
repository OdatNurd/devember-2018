import sublime

import inspect
import struct
import socket
import hashlib

from os.path import dirname, basename


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
    This message is used to indicate to the remote server that we are preparing
    to execute a build. This gives the folders that are taking part in the
    build as well as a unique build ID value (sha1 hash) that uniquely
    represents the build.
    """
    def __init__(self, build_id, folders):
        self.folders = folders
        self.build_id = build_id

    def __str__(self):
        return "<SetBuild build_id='{0}' folders={1}>".format(
            self.build_id,
            self.folders)

    @classmethod
    def msg_id(cls):
        return 3

    @classmethod
    def make_build_id(cls, folders):
        folders = sorted(folders, key=lambda fn: (dirname(fn), basename(fn)))
        sha1 = hashlib.sha1()
        for folder in folders:
            sha1.update(folder.encode('utf-8'))

        return sha1.hexdigest()

    @classmethod
    def decode(cls, data):
        pre_len = struct.calcsize(">HI")
        _, msg_len = struct.unpack(">HI", data[:pre_len])

        folder_data, = struct.unpack_from(">%ds" % msg_len, data, pre_len)
        folders = folder_data.decode("utf-8").split("\x00")

        build_id = folders[0]
        del folders[0]

        return SetBuildMessage(build_id, folders)

    def encode(self):
        data = "\x00".join([
            f for sub in [[self.build_id], self.folders] for f in sub
            ]).encode("utf-8")
        return struct.pack(">IHI%ds" % len(data),
            2 + 4 + len(data),
            SetBuildMessage.msg_id(),
            len(data),
            data)

ProtocolMessage.register(SetBuildMessage)


class AcknowledgeMessage(ProtocolMessage):
    """
    This message is used by the server to signal the acknowledgment of a
    message transmitted by the client. This is generally paired with a textual
    Message, allowing the code to know the result of the message  without
    having to try and parse or otherwise understand the return text.
    """
    def __init__(self, message_id, positive=True):
        self.message_id = message_id
        self.positive = positive

    def __str__(self):
        return "<Acknowledge message_id={0} positive={1}>".format(
            self.message_id, self.positive)

    @classmethod
    def msg_id(cls):
        return 4

    @classmethod
    def decode(cls, data):
        _, message_id, positive = struct.unpack(">HH?", data)

        return AcknowledgeMessage(message_id, positive)

    def encode(self):
        return struct.pack(">IHH?",
            2 + 2 + 1,
            AcknowledgeMessage.msg_id(),
            self.message_id,
            self.positive)

ProtocolMessage.register(AcknowledgeMessage)
