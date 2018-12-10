using System;
using System.Net;
using System.Net.Sockets;
using System.Text;

// The state object for reading client data.
public class BuildClient
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

    // The data string that has been received so far.
    public StringBuilder stringBuff = new StringBuilder();

    /// <summary>
    /// Create a new client object that's set up to talk over the provided
    /// socket connection.
    /// </summary>
    public BuildClient(Socket socket)
    {
        this.socket = socket;
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
        socket.BeginReceive(this.readBuffer, 0, BuildClient.ReadBufferSize,
                            SocketFlags.None, new AsyncCallback(this.ReadCallback),
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
        // Start an asynchronous send operaion for this client. This works in
        // the same way as the read code, and the code here assumes that our
        // internal state for what we're sending and how much has been
        // transmitted is set up correctly before this is called.
        socket.BeginSend(this.sendBuffer, this.bytesSent,
                         this.sendBuffer.Length - this.bytesSent,
                         SocketFlags.None,
                         new AsyncCallback(this.SendCallback), this);
    }

    // This handles a receive event on a particular client socket that has
    // connected. We read data from them and collect it into a string builder
    // for use later.
    public void ReadCallback(IAsyncResult ar)
    {
        String content = String.Empty;

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

        Console.WriteLine("Read {0} bytes", bytesRead);

        // Convert the data from the buffer into a UTF-8 String and append
        // it to the string builder as accumulated data for this client.
        //
        // NOTE: The original example use ASCII but the client command uses
        // UTF-8 so that has been changed here. There may or may not be a
        // particularly bad idea if there is a split receive; I don't know
        // if dotNET can handle partial encoding, but since this is a one
        // time call I'm assuming not.
        client.stringBuff.Append(Encoding.UTF8.GetString(client.readBuffer, 0, bytesRead));

        // See if the special terminator value is in the string; if it is,
        // then we can echo it back all accumulated data to the client now.
        content = client.stringBuff.ToString();
        if (content.IndexOf("<EOF>") > -1)
        {
            // Display the content, then transmit it to the other end.
            Console.WriteLine("Read {0} total bytes from client.\n Data : {1}",
                content.Length, content);

            client.sendBuffer = Encoding.UTF8.GetBytes(content);
            client.bytesSent = 0;
            client.BeginSending();
        }
        else
            // We haven't received the terminator yet, so start up a new
            // receive operation to get more data.
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
                // Shut down the socket and close it. It's nice to see that this
                // library includes the proper notion of shutting things down.
                socket.Shutdown(SocketShutdown.Both);
                socket.Close();
                Console.WriteLine("Closing connection");
            }
            else
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