using System;
using System.Text;
using MiscUtil.Conversion;

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

        Code = ProtocolMessageFactory.Converter.ToUInt32(data, 2);
        UInt32 msgLength = ProtocolMessageFactory.Converter.ToUInt32(data, 6);

        if (data.Length < 10 + msgLength)
            throw new ArgumentException("Message data length is invalid");

        Message = Encoding.UTF8.GetString(data, 10, (int) msgLength);
    }

    public byte[] Encode()
    {
        byte[] msgBytes = Encoding.UTF8.GetBytes(Message);
        UInt32 msgLength = (UInt32) msgBytes.Length;

        byte[] msg = new byte[4 + 2 + 4 + 4 + msgLength];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.Error), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(Code), 0, msg, 6, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(msgLength), 0, msg, 10, 4);
        Buffer.BlockCopy(msgBytes, 0, msg, 14, (int) msgLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Error code={0} msg='{1}'>",
            Code, Message);
    }
}