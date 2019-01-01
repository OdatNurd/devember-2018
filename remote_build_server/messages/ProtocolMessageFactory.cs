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
    SetBuild = 3,
    Acknowledge = 4,
    FileContent = 5,
    ExecuteBuild = 6,
    BuildOutput = 7,
    BuildComplete = 8,
}

// An interface that represents a protocol message;
public interface IProtocolMessage
{
    MessageType MsgID { get; }
    bool CloseAfterSending { get ; set; }

    byte[] Encode();
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
                return new MessageMessage(data);

            case MessageType.Error:
                return new ErrorMessage(data);

            case MessageType.SetBuild:
                return new SetBuildMessage(data);

            case MessageType.Acknowledge:
                return new AcknowledgeMessage(data);

            case MessageType.FileContent:
                return new FileContentMessage(data);

            case MessageType.ExecuteBuild:
                return new ExecuteBuildMessage(data);

            case MessageType.BuildOutput:
                return new BuildOutputMessage(data);

            case MessageType.BuildComplete:
                return new BuildCompleteMessage(data);

            default:
                throw new ArgumentOutOfRangeException("Unrecognized message type");
        }
    }
}
