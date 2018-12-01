import sublime
import sublime_plugin

import socket
import sys

# related:
#     https://docs.python.org/3.3/howto/sockets.html
#     https://realpython.com/python-sockets/#echo-client
#     https://docs.python.org/3.3/library/socket.html

# Crude blocking socket example; should be threaded, non-blocking, check
# errors better, etc.
#
# If our protocol is binary, use struct.pack() to prepare data.
class SocketTestCommand(sublime_plugin.ApplicationCommand):
    def run(self, host, port):
        try:
            # Create a socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Make the socket non-blocking; requires calls to select, so
                # lets skip that for now. Could maybe also use settimeout()
                # in combination with a select() to verify that an operation
                # may work and then use a blocking read.
                # sock.setblocking(0)

                # Connect; anecdotally instead of a host this should be a
                # resolved IP address -- the first resolved address is used,
                # which may  be either IPv4 or IPv6.
                sock.connect((host, port))

                # Sends may be short; send returns the number of bytes sent (I
                # assume buffered at the socket level). Apparently there is a
                # sendall(), but from looking at it we probably don't want it
                # because if a send is interrupted by a signal it errors out
                # and you can't tell how much was sent.
                #
                # Sends need to be bytes.
                sock.send('Hello, world!<EOF>'.encode('utf-8'))

                # Blocking receive of the data;
                #
                # Read data is bytes
                data = sock.recv(1024).decode('utf-8')

                # If we got a whole read, throw the trailer off.
                pos = data.index("<EOF>")
                data = data[:pos] if pos > 0 else data

                # Display it.
                sublime.message_dialog('Received:\n' + data)

        except Exception as error:
            sublime.error_message("Socket Error:\n%s" % error)
