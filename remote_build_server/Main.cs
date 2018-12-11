using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
// using MiscUtil.Conversion;

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
        // DNS name is and then resolving it to an IP. For expediency we use the
        // first resolved result (which as pointed out in the sample client code
        // may possibly be nondeterministic if it happens that the DNS returns
        // an IPv6 here and an IPv4 later for the client or something).
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

        // // A 32 bit test value, and what it appears as when you encode it as
        // // a big endian value; value here taken from using struct.pack() in
        // // Python.
        // UInt32 sample = 1234567890;
        // byte[] test = {73, 150, 2, 210};

        // // Our converters; we really only want the big endian one.
        // var lec = new LittleEndianBitConverter();
        // var bec = new BigEndianBitConverter();

        // Console.WriteLine("Input: {0}", sample);
        // Console.WriteLine("       {0}", test.ToByteString());
        // Console.WriteLine("");

        // // This shows that the internal BitConverter is little endian because
        // // the local machine is little endian, but using MiscUtils we can
        // // force the endian.
        // Console.WriteLine("======= Decoding the byte array ===============");
        // Console.WriteLine("BitConverter => {0}", BitConverter.ToUInt32(test, 0));
        // Console.WriteLine("LittleEndianBitConverter => {0}", lec.ToUInt32(test, 0));
        // Console.WriteLine("BigEndianBitConverter => {0}", bec.ToUInt32(test, 0));

        // // This tests going the other way; given our input value, convert it to
        // // a byte array and display it using the extension method. Again the
        // // internal converter is always little endian.
        // Console.WriteLine("");
        // Console.WriteLine("======= Encoding the byte array ===============");
        // Console.WriteLine("BitConverter => {0}", BitConverter.GetBytes(sample).ToByteString());
        // Console.WriteLine("LittleEndianBitConverter => {0}", lec.GetBytes(sample).ToByteString());
        // Console.WriteLine("BigEndianBitConverter => {0}", bec.GetBytes(sample).ToByteString());

        // // Allocate a byte array and put our data into it
        // byte[] myArray = new byte[8];

        // // Just as a test, this is the method for quickly copying data from one
        // // array to another, should that be needed.
        // Console.WriteLine("");
        // Console.WriteLine("======= Encoding the byte array ===============");
        // Console.WriteLine("Original: {0}", myArray.ToByteString());

        // Buffer.BlockCopy(test, 0, myArray, 2, 4);
        // Console.WriteLine("Copied: {0}", myArray.ToByteString());
        // Console.WriteLine("BigEndianBitConverter => {0}", bec.ToUInt32(myArray, 2));

        // // byte[] intro = new byte[] {0, 0, 1};
        // // byte[] error = new byte[] {0, 1, 73, 150, 2, 210, 0, 0, 0, 57, 73, 32, 97, 109,
        // //                 32, 116, 104, 101, 32, 101, 114, 114, 111, 114, 32, 109, 101,
        // //                 115, 115, 97, 103, 101, 44, 32, 97, 110, 100, 32, 73, 39, 109,
        // //                 32, 115, 111, 109, 101, 32, 110, 117, 109, 98, 101, 114, 32,
        // //                 111, 102, 32, 98, 121, 116, 101, 115, 32, 108, 111, 110, 103};

        // byte[] intro = new IntroductionMessage().encode();
        // byte[] error = new ErrorMessage(987654321, "Blast Off!").encode();

        // try
        // {
        //     Console.WriteLine("{0}", ProtocolMessageFactory.from_data(intro));
        //     Console.WriteLine("{0}", ProtocolMessageFactory.from_data(error));
        // }
        // catch (Exception e)
        // {
        //     Console.WriteLine("Error: {0}", e);
        // }

        // Console.WriteLine("Done");
        return 0;
    }
}
