using System;
using System.Text;
using MiscUtil.Conversion;

public class FileContentMessage : IProtocolMessage
{
    public string RootPath { get ; private set; } = null;
    public string RelativeName { get ; private set; } = null;
    public string FileContent { get ; private set; } = null;

    public MessageType MsgID { get ; private set; } = MessageType.FileContent;
    public bool CloseAfterSending { get ; set; } = false;


    // TODO: This doesn't actually load any file content; it just stubs out the
    // content to be an empty string. The server sending files back is a stage
    // two kind of thing.
    public FileContentMessage(string root, string name)
    {
        RootPath = root;
        RelativeName = name;
        FileContent = "";
    }

    public FileContentMessage(byte[] data)
    {
        if (data.Length < 2 + 256 + 256 + 4)
            throw new ArgumentException("Message data length is invalid");

        RootPath = Extensions.GetFixedWidthString(data, 2, 256);
        RelativeName = Extensions.GetFixedWidthString(data, 258, 256);
        UInt32 fileLength = ProtocolMessageFactory.Converter.ToUInt32(data, 514);

        if (data.Length < 2 + 256 + 256 + 4 + fileLength)
            throw new ArgumentException("Message data length is invalid");

        FileContent = Encoding.UTF8.GetString(data, 518, (int) fileLength);
    }

    public byte[] Encode()
    {
        byte[] file_data = Encoding.UTF8.GetBytes(FileContent);
        byte[] msg = new byte[4 + 2 + 256 + 256 + 4 + file_data.Length];

        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) msg.Length - 4), 0, msg, 0, 4);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt16) MessageType.FileContent), 0, msg, 4, 2);

        Buffer.BlockCopy(RootPath.PaddedByteArray(256),     0 , msg,   6, 256);
        Buffer.BlockCopy(RelativeName.PaddedByteArray(256), 0 , msg, 262, 256);
        Buffer.BlockCopy(ProtocolMessageFactory.Converter.GetBytes((UInt32) file_data.Length), 0, msg, 518, 4);
        Buffer.BlockCopy(file_data, 0, msg, 522, file_data.Length);

        return msg;
    }

    public override string ToString()
    {
        return String.Format("<FileContent root='{0}' name='{1}' size={2}>",
            RootPath, RelativeName, FileContent.Length);
    }
}