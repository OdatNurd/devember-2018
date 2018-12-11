using System;
using System.Text;
using MiscUtil.Conversion;

public class Message : IProtocolMessage
{
    public string Msg { get ; private set; } = null;

    public Message(string msg)
    {
        Msg = msg;
    }

    public Message(byte[] data)
    {
        if (data.Length < 6)
            throw new ArgumentException("Message data length is invalid");

        UInt32 msgLength = ProtocolMessageFactory.Converter.ToUInt32(data, 2);

        if (data.Length < 6 + msgLength)
            throw new ArgumentException("Message data length is invalid");

        Msg = Encoding.UTF8.GetString(data, 6, (int) msgLength);
    }

    public byte[] encode()
    {
        byte[] msgBytes = Encoding.UTF8.GetBytes(Msg);
        UInt32 msgLength = (UInt32) msgBytes.Length;

        byte[] msg = new byte[4 + 2 + 4 + msgLength];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.Message), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(msgLength), 0, msg, 6, 4);
        Buffer.BlockCopy(msgBytes, 0, msg, 10, (int) msgLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Message msg='{1}'>", Msg);
    }
}