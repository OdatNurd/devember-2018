using System;
using System.Text;
using MiscUtil.Conversion;


public class AcknowledgeMessage : IProtocolMessage
{
    public MessageType AcknowledgeID { get ; private set; }
    public bool Ack { get ; private set; }

    public MessageType MsgID { get ; private set; } = MessageType.Acknowledge;
    public bool CloseAfterSending { get ; set; } = false;

    public AcknowledgeMessage(MessageType acknowledge_id, bool isAck)
    {
        AcknowledgeID = acknowledge_id;
        Ack = isAck;
    }

    public AcknowledgeMessage(byte[] data)
    {
        if (data.Length != 2 + 2 + 1)
            throw new ArgumentException("Message data length is invalid");

        AcknowledgeID = (MessageType) ProtocolMessageFactory.Converter.ToUInt16(data, 2);
        Ack = Convert.ToBoolean(data[4]);
    }

    public byte[] Encode()
    {
        byte[] msg = new byte[4 + 2 + 2 + 1];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.Acknowledge), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) AcknowledgeID), 0, msg, 6, 2);
        msg[8] = Convert.ToByte(Ack);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Acknowledge message_id={0} positive={1}>",
            AcknowledgeID, Ack);
    }
}
