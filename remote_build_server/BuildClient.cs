using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Collections.Concurrent;

// The state object for reading client data.
public partial class BuildClient
{
    // The socket that represents the client.
    public Socket socket = null;

    // The receive buffer for this client; we track both an array as well as
    // the size of that array.
    public const int ReadBufferSize = 1024;
    public byte[] readBuffer = new byte[ReadBufferSize];

    // The send buffer for this client. This gets assigned when we receive a
    // complete message, and tracks the bytes to send. The bytesSent value is
    // used to indicate how many bytes were actually transmitted so far.
    public byte[] sendBuffer;
    public int bytesSent;

    // The queue of messages that should be transmitted to the remote end of the
    // connection.
    public ConcurrentQueue<IProtocolMessage> outQueue = new ConcurrentQueue<IProtocolMessage>();

    // The data for the message that we're currently reading.
    public PartialMessage inMsg = new PartialMessage();

    /// <summary>
    /// Create a new client object that's set up to talk over the provided
    /// socket connection.
    /// </summary>
    public BuildClient(Socket clientSocket)
    {
        socket = clientSocket;
    }

    /// <summary>
    /// Queue up the given message for sending to the remote end of this
    /// client connection.
    /// </summary>
    public void Send(IProtocolMessage msg)
    {
        outQueue.Enqueue(msg);
        if (sendBuffer == null)
            BeginSending();
    }

    /// <summary>
    /// Launches an asynchronous receive operation for this client, pulling as
    /// much data as is possible into the client's receive buffer starting at
    /// the start of the buffer.
    /// </summary>
    public void BeginReading()
    {
        // Start an asynchronous receive operation for this client. This tells
        // the underlying API to read data into the buffer for this client
        // starting at position 0, reading as much as the size of the actual
        // buffer for the client, with no additional flags provided.
        //
        // The callback we provide will get invoked when the receive happens.
        // Here the state provided is an actual object that wraps all of the
        // information about the client (whereas above the state was just the
        // listener directly).
        socket.BeginReceive(readBuffer, 0, BuildClient.ReadBufferSize,
                            SocketFlags.None, new AsyncCallback(ReadCallback),
                            this);
    }

    /// <summary>
    /// Launches an asynchronous send operation for this client, attempting to
    /// send as much data as possible from the internal send buffer to the other
    /// end starting with the first unsent byte.
    /// </summary>
    /// <remarks>
    /// This requires that the send buffer and the number of bytes sent be
    /// previously set up by external code.
    /// </remarks>
    public void BeginSending()
    {
        // If we're not sending anything yet, then pull a message to send; this
        // will silently do nothing if there are no more messages to transmit.
        if (sendBuffer == null)
        {
            // Pull out a message to send. If there are no more to send, then
            // this does nothing and returns.
            IProtocolMessage msg;
            if (outQueue.TryDequeue(out msg) == false)
                return;

            sendBuffer = msg.Encode();
            bytesSent = 0;
        }

        // Start an asynchronous send operaion for this client. This works in
        // the same way as the read code, and the code here assumes that our
        // internal state for what we're sending and how much has been
        // transmitted is set up correctly before this is called.
        socket.BeginSend(sendBuffer, bytesSent,
                         sendBuffer.Length - bytesSent,
                         SocketFlags.None,
                         new AsyncCallback(SendCallback), this);
    }

    // This handles a receive event on a particular client socket that has
    // connected. We read data from them and collect it into a string builder
    // for use later.
    public void ReadCallback(IAsyncResult ar)
    {
        // From the state of the event, get our the state object that wraps all
        // of the information for this client, and then get the socket out of
        // it.
        BuildClient client = (BuildClient) ar.AsyncState;
        Socket socket = client.socket;

        // Perform the actual receive now; the result is the number of bytes
        // read, which can conceivably be 0; we only need to worry about doing
        // something if we actually got some data.
        int bytesRead = socket.EndReceive(ar);
        if (bytesRead == 0)
        {
            Console.WriteLine("Client closed connection");
            return;
        }

        Console.WriteLine("==> Read {0} bytes", bytesRead);

        int bytesUsed = 0;
        while (bytesUsed != bytesRead)
        {
            // Give some bytes to the current partial message so it can
            // reconstruct itself.
            bytesUsed += inMsg.GiveBytes(client.readBuffer, bytesRead, bytesUsed);

            // If this message is complete, then echo it back to the other end
            // and get ready for another received message.
            if (inMsg.IsComplete())
            {
                var msg = inMsg.getMessage();
                inMsg = new PartialMessage();
                client.Dispatch(msg);
            }
        }

        // End by getting ready to read more data.
        client.BeginReading();
    }

    // This handles a send event on a particular client socket that has
    // connected. We transmit back to them the data that we originally read, as
    // a sort of echo.
    private void SendCallback(IAsyncResult ar)
    {
        try
        {
            BuildClient client = (BuildClient) ar.AsyncState;
            Socket socket = client.socket;

            // Complete the transmission of the data to the remote end and
            // indicate that we did so.
            int bytesSent = socket.EndSend(ar);
            Console.WriteLine("Sent {0} bytes to client.", bytesSent);
            client.bytesSent += bytesSent;

            if (client.bytesSent == client.sendBuffer.Length)
            {
                Console.WriteLine("Finished message transmission");
                client.sendBuffer = null;
                client.bytesSent = 0;
            }

            // Trigger another send; if this send was complete, then this will
            // check and see if there's another message that we can send, but
            // if this send was not complete, then we'll try to finish the job.
            client.BeginSending();
        }

        catch (SocketException se)
        {
            Console.WriteLine("Socket Error: {0}", se.Message);
            Console.WriteLine("Closing connection");
        }

        catch (Exception e)
        {
            Console.WriteLine(e.ToString());
        }
    }
}