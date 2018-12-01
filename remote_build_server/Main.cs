using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

// The state object for reading client data.
public class StateObject
{
    // The socket that represents the client.
    public Socket workSocket = null;

    // The size of the receive buffer for this client, as well as an array of
    // bytes exactly that big.
    public const int BufferSize = 1024;
    public byte[] buffer = new byte[BufferSize];

    // The data string that has been received so far.
    public StringBuilder sb = new StringBuilder();
}


public class AsynchronousSocketListener
{
    // The thread signal object; this is used to allow the various threads of
    // execution to syncronize.
    public static ManualResetEvent allDone = new ManualResetEvent(false);

    // Contructor: empty
    public AsynchronousSocketListener() {}

    // Start listening for incoming connections on this host.
    public static void StartListening()
    {
        // Look up the IP address of our local socket by figuring out what our
        // DNS name is and then resolving it to an IP. For expediency we use
        // the first resolved result (which as pointed out in the sample client
        // code may possibly be nondeterministic if it happens that the DNS
        // returns an IPv6 here and an IPv4 later for the client or something).
        IPHostEntry ipHostInfo = Dns.GetHostEntry(Dns.GetHostName());
        IPAddress ipAddress = ipHostInfo.AddressList[0];

        // Create the address of the endpoint that we're going to listen on.
        IPEndPoint localEndPoint = new IPEndPoint(ipAddress, 50000);

        // Create our streaming TCP socket, using the address family appropriate
        // for whatever IP address we came up with.
        Socket listener = new Socket(ipAddress.AddressFamily, SocketType.Stream, ProtocolType.Tcp);

        try
        {
            // Bind our listening socket to the endpoint that we created and
            // then listen there for incoming connections. The default backlog
            // here is what was in the original sample; is there a reason it
            // seems unreasonably large?
            listener.Bind(localEndPoint);
            listener.Listen(100);

            Console.WriteLine("Listening for connections at: {0}", localEndPoint);

            // Drop into an infinite loop waiting for connections.
            while (true)
            {
                // Reset our event.
                allDone.Reset();

                // Start up an asynchronous accept operation; we need to pass
                // a callback that knows how to handle an accept and the socket
                // that is doing the listening.
                listener.BeginAccept(
                    new AsyncCallback(AcceptCallback),
                    listener);

                // The above line starts an async operation to listen for a
                // connection on the listening socket; this call pauses this
                // thread until a connection is successfully accepted, allowing
                // us to cycle around and get the next one.
                allDone.WaitOne();
            }
        }
        catch (Exception e)
        {
            Console.WriteLine(e.ToString());
        }
    }

    // This handles an accepted connection when an asynchronous accept
    // finishes.
    public static void AcceptCallback(IAsyncResult ar)
    {
        // Start by telling the main thread that it's OK for it to continue
        // now.
        allDone.Set();

        // The state of this event contains the socket that was listening, so
        // pull that our and then call it's EndAccept() method to get us our
        // socket.
        Socket listener = (Socket) ar.AsyncState;
        Socket handler = listener.EndAccept(ar);

        Console.WriteLine("New incoming connection");

        // Create a new state object to wrap this particular client and set the
        // new socket handle in.
        StateObject state = new StateObject();
        state.workSocket = handler;

        // Start an asynchronous receive operation for this client. This tells
        // the underlying API to read data into the buffer for this client
        // starting at position 0, reading as much as the size of the actual
        // buffer for the client, with no additional flags provided.
        //
        // The callback we provide will get invoked when the receive happens.
        // Here the state provided is an actual object that wraps all of the
        // information about the client (whereas above the state was just the
        // listener directly).
        handler.BeginReceive (state.buffer, 0, StateObject.BufferSize, 0,
                             new AsyncCallback(ReadCallback), state);
    }

    // This handles a receive event on a particular client socket that has
    // connected. We read data from them and collect it into a string builder
    // for use later.
    public static void ReadCallback(IAsyncResult ar)
    {
        String content = String.Empty;

        // From the state of the event, get our the state object that wraps all
        // of the information for this client, and then get the socket out of
        // it.
        StateObject state = (StateObject) ar.AsyncState;
        Socket handler = state.workSocket;

        // Perform the actual receive now; the result is the number of bytes
        // read, which can conceivably be 0; we only need to worry about
        // doing something if we actually got some data.
        int bytesRead = handler.EndReceive(ar);
        if (bytesRead > 0)
        {
            Console.WriteLine("Read {0} bytes", bytesRead);
            // Convert the data from the buffer into a UTF-8 String and append
            // it to the string builder as accumulated data for this client.
            //
            // NOTE: The original example use ASCII but the client command uses
            // UTF-8 so that has been changed here. There may or may not be a
            // particularly bad idea if there is a split receive; I don't know
            // if dotNET can handle partial encoding, but since this is a one
            // time call I'm assuming not.
            state.sb.Append(Encoding.UTF8.GetString(state.buffer, 0, bytesRead));

            // See if the special terminator value is in the string; if it is,
            // then we can echo it back all accumulated data to the client now.
            content = state.sb.ToString();
            if (content.IndexOf("<EOF>") > -1)
            {
                // Display the content, then transmit it to the other end.
                Console.WriteLine("Read {0} total bytes from client.\n Data : {1}",
                    content.Length, content);
                Send(handler, content);
            }
            else
            {
                // We haven't received the terminator yet, so start up a new
                // receive operation to get more data.
                handler.BeginReceive(state.buffer, 0, StateObject.BufferSize, 0,
                                     new AsyncCallback(ReadCallback), state);
            }
        }
    }

    // This handles a send to a particular client socket that has connected.
    // The string of data provided will be transmitted to the remote end of
    // the connection.
    private static void Send(Socket handler, String data)
    {
        // Convert the string into bytes for the trip back.
        byte[] byteData = Encoding.UTF8.GetBytes(data);

        // Start the transmission. As in the accept and receive, we need to
        // tell the socket to start sending data from the given buffer, starting
        // at the beginning of the buffer and writing all of the data, with
        // no socket options.
        //
        // We again need to provide a handler for when the send completes.
        handler.BeginSend(byteData, 0, byteData.Length, 0,
                         new AsyncCallback(SendCallback), handler);
    }

    // This handles a send event on a particular client socket that has
    // connected. We transmit back to them the data that we originally read,
    // as a sort of echo.
    private static void SendCallback(IAsyncResult ar)
    {
        try
        {
            // Get the socket out of the state object that was given to us.
            Socket handler = (Socket) ar.AsyncState;

            // Complete the transmission of the data to the remote end and
            // indicate that we did so.
            int bytesSent = handler.EndSend(ar);
            Console.WriteLine("Sent {0} bytes to client.", bytesSent);

            // Shut down the socket and close it. It's nice to see that this
            // library includes the proper notion of shutting things down.
            handler.Shutdown(SocketShutdown.Both);
            handler.Close();
            Console.WriteLine("Closing connection");
        }
        catch (Exception e)
        {
            Console.WriteLine(e.ToString());
        }
    }

    // Our entry point; this just starts us listening.
    public static int Main(String[] args)
    {
        StartListening();
        return 0;
    }
}