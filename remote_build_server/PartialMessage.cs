using System;
using System.Text;
using MiscUtil.Conversion;


public class PartialMessage
{
    // The bytes that we are reading so that we can determine how big the
    // message payload is. The array is allocated at init time, and decoded as
    // a big endian value once all four of them are consumed.
    private byte[] msgLenBytes = new byte[4];

    // The bytes that make up the actual data in this message. This is null when
    // we don't know how many bytes we need, and an allocated array once we have
    // determined the length.
    private byte[] msgData = null;

    // In either the msgLenBytes or msgData arrays, this tracks how many bytes
    // of the bytes that CAN be stored in the array HAVE been stored in the
    // array.
    private int bytesUsed = 0;

    // Constructor; Empty.
    public PartialMessage() {}

    /// <summary>
    /// Give some bytes from the provided data at the given offset to this
    /// message. The returned value is the number of bytes that have been
    /// consumed from the data array, which may be 0 or may be the entire
    /// contents of the data array that still remain at the given offset.
    /// </summary>
    public int GiveBytes(byte[] data, int bufferLen, int offset)
    {
        int remain = bufferLen - offset;
        int taken = 0;

        // If msgData is null, we don't have all of the bytes needed in
        // msgLenBytes to know how long the message is, so try to grab that
        // many.
        if (msgData == null)
        {
            // Figure out how many bytes we want, which is either the number of
            // bytes needed to fill out put msgLenBytes array, or the amount of
            // remaining data, whichever is smaller.
            taken = Math.Min(remain, msgLenBytes.Length - bytesUsed);

            // Copy the number of bytes we're taking out of the data array at
            // the given offset, then update the offset and the number of
            // remaining bytes.
            Buffer.BlockCopy(data, offset, msgLenBytes, bytesUsed, taken);
            bytesUsed += taken;
            offset += taken;
            remain -= taken;

            // If the bytes used is the entire length of the message bytes
            // length array, then we have all of the bytes we need, so decode
            // and get the msg length ready.
            //
            // If that's not the case, we don't have enough bytes yet, so just
            // return back.
            if (bytesUsed == msgLenBytes.Length)
            {
                var msgLength = MessageFactory.Converter.ToUInt32(msgLenBytes, 0);

                msgData = new byte[msgLength];
                bytesUsed = 0;
            }
            else
                return taken;
        }

        // Try to consume bytes from the message. We know how many bytes we need
        // and how many bytes we've actually used so far; determine how many
        // bytes we can actually grab, which may be all we need or only a
        // smaller set.
        var msgBytesTaken = Math.Min(remain, msgData.Length - bytesUsed);

        // Copy the data over and update our values.
        Buffer.BlockCopy(data, offset, msgData, bytesUsed, msgBytesTaken);
        bytesUsed += msgBytesTaken;

        return taken + msgBytesTaken;
    }

    /// <summary>
    /// Determine if this partial message is complete or not. A message that is
    /// comlete can be decoded, while a message that's not needs to have
    /// GiveBytes called at least one more time.
    /// </summary>
    public bool IsComplete()
    {
        return (msgData != null && bytesUsed == msgData.Length);
    }

    /// <summary>
    /// Convert the internal message data into a decoded message. This will
    /// throw an exception if the message is not yet complete.
    /// </summary>
    public IProtocolMessage getMessage()
    {
        if (IsComplete() == false)
            throw new InvalidOperationException("Message is not complete yet");

        return MessageFactory.from_data(msgData);
    }
}
