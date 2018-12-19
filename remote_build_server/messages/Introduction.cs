using System;
using System.Text;
using MiscUtil.Conversion;


public class IntroductionMessage : IProtocolMessage
{
    /// <summary>
    /// The protocol version
    /// </summary>
    public byte ProtocolVersion { get ; private set; } = 1;

    public string User { get ; private set; }
    public string Password { get; private set; }
    public string Hostname { get; private set; }
    public string Platform { get; private set; }

    public MessageType MsgID { get ; private set; } = MessageType.Introduction;
    public bool CloseAfterSending { get ; set; } = false;

    public IntroductionMessage(string user, string password, string hostname, string platform)
    {
        User = user;
        Password = password;
        Hostname = hostname;
        Platform = platform;
    }

    public IntroductionMessage(byte[] data)
    {
        if (data.Length != 2 + 1 + 64 + 64 + 64 + 8)
            throw new ArgumentException("Message data length is invalid");

        ProtocolVersion = data[2];

        User = Encoding.UTF8.GetString(data, 3, 64);
        Password = Encoding.UTF8.GetString(data, 67, 64);
        Hostname = Encoding.UTF8.GetString(data, 131, 64);
        Platform = Encoding.UTF8.GetString(data, 195, 8);
    }

    public byte[] Encode()
    {
        byte[] msg = new byte[4 + 2 + 1 + 64 + 64 + 64 + 8];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.Introduction), 0, msg, 4, 2);
        msg[6] = ProtocolVersion;

        Buffer.BlockCopy(User.PaddedByteArray(64), 0, msg, 7, 64);
        Buffer.BlockCopy(Password.PaddedByteArray(64), 0, msg, 71, 64);
        Buffer.BlockCopy(Hostname.PaddedByteArray(64), 0, msg, 135, 64);
        Buffer.BlockCopy(Platform.PaddedByteArray(8), 0, msg, 199, 8);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Introduction user={0} host={1} platform={2} version={3}>",
            User, Hostname, Platform, ProtocolVersion);
    }
}
