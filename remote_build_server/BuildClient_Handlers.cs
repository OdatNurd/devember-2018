using System;

// The state object for reading client data.
public partial class BuildClient
{
    // Has the client transmitted an introduction message to us yet?
    // We require one or anything that the client does is otherwise considered
    // to be an error.
    private bool hasIntroduced = false;

    // Transmit an error message to the user and then optionally close the
    // connection; the connection will be closed once we finish transmitting
    // this error.
    void SendError(UInt32 code, string errorMsg, bool closeAfter=true)
    {
        var error = new ErrorMessage(code, errorMsg);
        error.CloseAfterSending = closeAfter;
        Send(error);
    }

    void SendMessage(string msg)
    {
        Send(new MessageMessage(msg));
    }

    void HandleIntroduction(IntroductionMessage message)
    {
        if (hasIntroduced)
        {
            SendError(1000, "Introduction message has already been received");
            return;
        }

        if (message.ProtocolVersion != 1)
        {
            SendError(1001, "Invalid protocol; only version 1 is supported");
            return;
        }

        // No matter what, we've been introduced now.
        hasIntroduced = true;

        // Use the information from the introduction message to log in the user
        user = config.LoginUser(message.User, message.Password);

        if (user == null)
            SendError(1, "Invalid username/password");
        else
            SendMessage(String.Format("Hello, {0}", message.User));
    }

    void HandleMessage(MessageMessage message)
    {
        Send(message);
    }

    void HandleError(ErrorMessage message)
    {
        Send(message);
    }

    private void Dispatch(IProtocolMessage message)
    {
        // If we have not been introduced to the other end of the connection yet
        // then trigger an error unless this message is the introduction message
        // itself.
        if (hasIntroduced == false && message.MsgID != MessageType.Introduction)
        {
            SendError(1002, "Invalid communications; no Introduction received");
            return;
        }

        switch (message.MsgID)
        {
            case MessageType.Introduction:
                HandleIntroduction(message as IntroductionMessage);
                break;

            case MessageType.Message:
                HandleMessage(message as MessageMessage);
                break;

            case MessageType.Error:
                HandleError(message as ErrorMessage);
                break;

            default:
                throw new Exception("Unknown message type");
        }
    }
}