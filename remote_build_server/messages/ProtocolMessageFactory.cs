using System;
using System.Text;
using MiscUtil.Conversion;


// An enumeration that determiens what the ID value of a particular message
// is.
public enum MessageType
{
    Introduction = 0,
    Message = 1,
    Error = 2,
}

// An interface that represents a protocol message;
public interface IProtocolMessage
{
    byte[] encode();
}

public class ProtocolMessageFactory
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

            case MessageType.Message:
                return new Message(data);

            case MessageType.Error:
                return new ErrorMessage(data);

            default:
                throw new ArgumentOutOfRangeException("Unrecognized message type");
        }
    }
}

