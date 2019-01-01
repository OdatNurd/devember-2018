using System;
using System.Text;
using MiscUtil.Conversion;


public class BuildCompleteMessage : IProtocolMessage
{
    public UInt16 ExitCode { get ; private set; }

    public MessageType MsgID { get ; private set; } = MessageType.BuildComplete;
    public bool CloseAfterSending { get ; set; } = false;

    public BuildCompleteMessage(UInt16 exit_code)
    {
        ExitCode = exit_code;
    }

    public BuildCompleteMessage(byte[] data)
    {
        if (data.Length != 2 + 2)
            throw new ArgumentException("Message data length is invalid");

        ExitCode = ProtocolMessageFactory.Converter.ToUInt16(data, 2);
    }

    public byte[] Encode()
    {
        byte[] msg = new byte[4 + 2 + 2];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.BuildComplete), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) ExitCode), 0, msg, 6, 2);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<BuildComplete exit_code={0}>",
            ExitCode);
    }
}
