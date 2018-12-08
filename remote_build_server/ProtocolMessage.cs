using System;
using System.Text;
using MiscUtil.Conversion;

// An enumeration that determiens what the ID value of a particular message
// is.
public enum MessageType
{
    Introduction = 0,
    Error = 1,
}

// An interface that represents a protocol message;
public interface IProtocolMessage
{
    byte[] encode();
}


public class MessageFactory
{
    public static BigEndianBitConverter Converter = new BigEndianBitConverter();

    public static IProtocolMessage from_data(byte[] data)
    {
        if (data.Length < 2)
            throw new ArgumentException("Message data length is invalid");

        // Console.WriteLine("BigEndianBitConverter => {0}", bec.ToUInt32(test, 0));
        MessageType msgType = (MessageType) Converter.ToUInt16(data, 0);

        switch (msgType)
        {
            case MessageType.Introduction:
                return new IntroductionMessage(data);

            case MessageType.Error:
                return new ErrorMessage(data);

            default:
                throw new ArgumentOutOfRangeException("Unrecognized message type");
        }
    }
}

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
        byte[] msg = new byte[3];

        Buffer.BlockCopy(MessageFactory.Converter.GetBytes((UInt16) MessageType.Introduction), 0, msg, 0, 2);
        msg[2] = ProtocolVersion;

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<IntroductionMessage version={0}>", ProtocolVersion);
    }
}

public class ErrorMessage : IProtocolMessage
{
    public UInt32 Code { get; private set; } = 0;
    public string Message { get ; private set; } = null;

    public ErrorMessage(UInt32 errCode, string errMsg)
    {
        Code = errCode;
        Message = errMsg;
    }

    public ErrorMessage(byte[] data)
    {

        if (data.Length < 10)
            throw new ArgumentException("Message data length is invalid");

        Code = MessageFactory.Converter.ToUInt32(data, 2);
        UInt32 msgLength = MessageFactory.Converter.ToUInt32(data, 6);

        if (data.Length < 10 + msgLength)
            throw new ArgumentException("Message data length is invalid");

        Message = Encoding.UTF8.GetString(data, 10, (int) msgLength);
    }

    public byte[] encode()
    {
        byte[] msgBytes = Encoding.UTF8.GetBytes(Message);
        UInt32 msgLength = (UInt32) msgBytes.Length;

        byte[] msg = new byte[2 + 4 + 4  + msgLength];

        Buffer.BlockCopy(MessageFactory.Converter.GetBytes((UInt16) MessageType.Error), 0, msg, 0, 2);
        Buffer.BlockCopy(MessageFactory.Converter.GetBytes(Code), 0, msg, 2, 4);
        Buffer.BlockCopy(MessageFactory.Converter.GetBytes(msgLength), 0, msg, 6, 4);
        Buffer.BlockCopy(msgBytes, 0, msg, 10, (int) msgLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<ErrorMessage code={0} msg='{1}'>",
            Code, Message);
    }
}