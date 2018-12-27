using System;
using System.Text;
using System.Collections.Generic;
using MiscUtil.Conversion;

public class SetBuildMessage : IProtocolMessage
{
    public List<string> Folders { get ; private set; } = null;

    public MessageType MsgID { get ; private set; } = MessageType.SetBuild;
    public bool CloseAfterSending { get ; set; } = false;


    public SetBuildMessage(List<string> folders)
    {
        Folders = folders;
    }

    public SetBuildMessage(byte[] data)
    {
        if (data.Length < 6)
            throw new ArgumentException("Message data length is invalid");

        UInt32 folderLength = ProtocolMessageFactory.Converter.ToUInt32(data, 2);

        if (data.Length < 6 + folderLength)
            throw new ArgumentException("Folder data length is invalid");

        var folderStr = Encoding.UTF8.GetString(data, 6, (int) folderLength);
        Folders = new List<string>(folderStr.Split("\x00"));
    }

    public byte[] Encode()
    {
        byte[] folderBytes = Encoding.UTF8.GetBytes(string.Join("\x00", Folders));
        UInt32 folderLength = (UInt32) folderBytes.Length;

        byte[] msg = new byte[4 + 2 + 4 + folderLength];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.SetBuild), 0, msg, 4, 2);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes(folderLength), 0, msg, 6, 4);
        Buffer.BlockCopy(folderBytes, 0, msg, 10, (int) folderLength);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<Message folders={1}>", Folders);
    }
}