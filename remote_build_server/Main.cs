using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;


public class RemoteBuildServer
{
    // The thread signal object; this is used to allow the various threads of
    // execution to syncronize.
    public static ManualResetEvent allDone = new ManualResetEvent(false);

    // Contructor: empty
    public RemoteBuildServer() {}

    // Start listening for incoming connections on this host.
    public static void StartListening()
    {
        // Look up the IP address of our local socket by figuring out what our
        // DNS name is and then resolving it to an IP. For expediency we use the
        // first resolved result (which as pointed out in the sample client code
        // may possibly be nondeterministic if it happens that the DNS returns
        // an IPv6 here and an IPv4 later for the client or something).
        IPHostEntry ipHostInfo = Dns.GetHostEntry(Dns.GetHostName());
        IPAddress ipAddress = null;

        foreach (var ip in ipHostInfo.AddressList)
        {
            if (ip.AddressFamily == AddressFamily.InterNetwork)
            {
                ipAddress = ip;
                break;
            }
        }

        if (ipAddress == null)
        {
            Console.WriteLine("No IPv4 address found to listen on");
            return;
        }

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

                // Start up an asynchronous accept operation; we need to pass a
                // callback that knows how to handle an accept and the socket
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

    // This handles an accepted connection when an asynchronous accept finishes.
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

        // Create a new client object to wrap this new client socket, and tell
        // it to start reading now.
        new BuildClient(handler).BeginReading();
    }

    // Our entry point; this just starts us listening.
    public static int Main(String[] args)
    {
        StartListening();

        return 0;
    }
}
