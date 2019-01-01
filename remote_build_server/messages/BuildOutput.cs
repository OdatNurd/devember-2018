using System;
using System.Text;
using MiscUtil.Conversion;

public class BuildOutputMessage : IProtocolMessage
{
    public string Msg { get ; private set; } = null;
    public bool Stdout { get ; private set; } = false;

    public MessageType MsgID { get ; private set; } = MessageType.BuildOutput;
    public bool CloseAfterSending { get ; set; } = false;


    public BuildOutputMessage(string msg, bool stdout)
    {
        Msg = msg;
        Stdout = stdout;
    }

    public BuildOutputMessage(byte[] data)
    {
        if (data.Length < 7)
            throw new ArgumentException("Message data length is invalid");

        Stdout = Convert.ToBoolean(data[2]);
        UInt32 msgLength = ProtocolMessageFactory.Converter.ToUInt32(data, 3);

        if (data.Length < 7 + msgLength)
            throw new ArgumentException("Message data length is invalid");

        Msg = Encoding.UTF8.GetString(data, 7, (int) msgLength);
    }

    public byte[] Encode()
    {
        byte[] msgBytes = Encoding.UTF8.GetBytes(Msg);
        UInt32 msgLength = (UInt32) msgBytes.Length;

        byte[] msg = new byte[4 + 2 + 1 + 4 + msgLength];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.BuildOutput), 0, msg, 4, 2);
        msg[6] = Convert.ToByte(Stdout);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(msgLength), 0, msg, 7, 4);
        Buffer.BlockCopy(msgBytes, 0, msg, 11, (int) msgLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<BuildOutput msg='{0}' is_stdout={1}>", Msg, Stdout);
    }
}