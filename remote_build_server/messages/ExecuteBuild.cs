using System;
using System.Text;
using MiscUtil.Conversion;

public class ExecuteBuildMessage : IProtocolMessage
{
    public string ShellCmd { get ; private set; } = null;

    public MessageType MsgID { get ; private set; } = MessageType.ExecuteBuild;
    public bool CloseAfterSending { get ; set; } = false;


    public ExecuteBuildMessage(string shell_cmd)
    {
        ShellCmd = shell_cmd;
    }

    public ExecuteBuildMessage(byte[] data)
    {
        if (data.Length < 6)
            throw new ArgumentException("Message data length is invalid");

        UInt32 msgLength = ProtocolMessageFactory.Converter.ToUInt32(data, 2);

        if (data.Length < 6 + msgLength)
            throw new ArgumentException("Message data length is invalid");

        ShellCmd = Encoding.UTF8.GetString(data, 6, (int) msgLength);
    }

    public byte[] Encode()
    {
        byte[] msgBytes = Encoding.UTF8.GetBytes(ShellCmd);
        UInt32 msgLength = (UInt32) msgBytes.Length;

        byte[] msg = new byte[4 + 2 + 4 + msgLength];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.ExecuteBuild), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(msgLength), 0, msg, 6, 4);
        Buffer.BlockCopy(msgBytes, 0, msg, 10, (int) msgLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<ExecuteBuild shell_cmd='{0}'>", ShellCmd);
    }
}