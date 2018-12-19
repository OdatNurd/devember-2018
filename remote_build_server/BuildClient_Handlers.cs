using System;

// The state object for reading client data.
public partial class BuildClient
{
    void HandleIntroduction(IntroductionMessage message)
    {
        Send(message);
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