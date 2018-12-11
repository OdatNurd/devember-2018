using System;
using System.Text;
using MiscUtil.Conversion;


public class IntroductionMessage : IProtocolMessage
{
    /// <summary>
    /// The protocol version
    /// </summary>
    public byte ProtocolVersion { get ; private set; } = 1;

    public IntroductionMessage()
    {

    }

    public IntroductionMessage(byte[] data)
    {
        if (data.Length != 3)
            throw new ArgumentException("Message data length is invalid");

        ProtocolVersion = data[2];
    }

    public byte[] encode()
    {
        byte[] msg = new byte[4 + 3];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) 3), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.Introduction), 0, msg, 4, 2);
        msg[6] = ProtocolVersion;

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Introduction version={0}>", ProtocolVersion);
    }
}
