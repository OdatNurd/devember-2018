using System;

// The state object for reading client data.
public partial class BuildClient
{
    /// <summary>
    /// Used to indicate whether the other side has transmitted an introduction
    /// message yet.
    /// </summary>
    /// An introduction message must be the first message transmitted upon a new
    /// incoming connection, which is used by the client to tell us who they are
    /// as well as their credentials.
    private bool hasIntroduced = false;

    /// <summary>
    /// If we have been introduced successfully, this stores the hostname that
    /// the client is currently connecting from.
    /// </summary>
    private string remote_host;

    /// <summary>
    /// If we have been introduced successfully, this stores the platform that
    /// the client is currently connecting from.
    /// </summary>
    private string remote_platform;

    /// <summary>
    /// Transmit an error message to the user, optionally closing the connection
    /// once the message has been transmitted.
    /// </summary>
    void SendError(UInt32 code, string errorMsg, bool closeAfter=true)
    {
        var error = new ErrorMessage(code, errorMsg);
        error.CloseAfterSending = closeAfter;
        Send(error);
    }

    /// <summary>
    /// Transmit an informational or warning message to the user; this is used
    /// for all textual communications which are not considered an out and out
    /// error.
    /// </summary>
    void SendMessage(string msg)
    {
        Send(new MessageMessage(msg));
    }

    /// <summary>
    /// Handle an incoming protocol message by sending back an error message
    /// indicating that a message of this type is not allowed at this point in
    /// the conversation.
    /// </summary>
    void ProtocolViolationMessage(IProtocolMessage message, string reason=null)
    {
        SendError(9999, String.Format(
            "Received unexpected message with id={0}; protocol violation",
            message.MsgID), reason == null);

        if (reason != null)
            SendError(9999, reason);
    }

    /// <summary>
    /// Handle an incoming protocol message by echoing it back to the remote
    /// client exactly as received. This is a useful test that both ends can
    /// successfully encode and decode the message.
    /// </summary>
    void EchoMessage(IProtocolMessage message)
    {
        Send(message);
    }

    /// <summary>
    /// Invoked every time a message is received from the client. This does all
    /// of the protocol handling work on our end, handling messages as
    /// appropriate.
    /// </summary>
    private void Dispatch(IProtocolMessage message)
    {
        // If we have not been introduced to the other end of the connection yet
        // then trigger an error unless this message is the introduction message
        // itself.
        if (hasIntroduced == false && message.MsgID != MessageType.Introduction)
        {
            ProtocolViolationMessage(message, "First message must be an introduction");
            return;
        }

        switch (message.MsgID)
        {
            // These messages are only valid when transmitted from the server to
            // the client; if the client sends them to us, issue a protocol
            // violation.
            case MessageType.Message:
            case MessageType.Error:
                ProtocolViolationMessage(message, "These messages are for server use only");
                break;

            // This should always be the first message received on a connection
            // (and is only valid as the first message). It has specific
            // handling associated with it.
            case MessageType.Introduction:
                HandleIntroduction(message as IntroductionMessage);
                break;

            // The client is indicating that it's time to set up a new build.
            // This message tells us what paths are being built so that we can
            // set things up on our end.
            case MessageType.SetBuild:
                HandleSetBuild(message as SetBuildMessage);
                break;

            default:
                throw new Exception("Unknown message type");
        }
    }

    /// <summary>
    /// Handle the incoming Introduction message from the remote end of the
    /// connection, validating the information. The response to this message is
    /// either to set up our object and send a text message back, or to respond
    /// with an error.
    /// </summary>
    void HandleIntroduction(IntroductionMessage message)
    {
        // It is an error to receive an introduction message after the client
        // has already introduced themselves.
        if (hasIntroduced)
        {
            ProtocolViolationMessage(message, "An introduction message has already been received");
            return;
        }

        // If the client is not using the correct protocol version, then error
        // out the connection; a more robust implementation would try to tailor
        // to the age of the client and fall back to an older protocol.
        if (message.ProtocolVersion != 1)
        {
            SendError(1000, "Invalid protocol; only version 1 is supported");
            return;
        }

        // Consider ourselves introduced now.
        hasIntroduced = true;

        // Using the information from the message, validate that the user is
        // allowed to connect and has provided the appropriate credentials.
        //
        // This grabs the appropriate record out of the configuration, if there
        // is one.
        user = config.LoginUser(message.User, message.Password);

        // If we didn't find an appropriate user, then return an error message
        // back and we're done.
        if (user == null)
        {
            SendError(1001, "Invalid username/password; login denied");
            return;
        }

        // Save the hostname and platform.
        remote_host = message.Hostname;
        remote_platform = message.Platform;

        // Welcome the user
        SendMessage(String.Format("Hello, {0} from {1} {2}",
            user.username,
            remote_platform,
            remote_host));
    }

    void HandleSetBuild(SetBuildMessage message)
    {
        Send(message);
    }
}
