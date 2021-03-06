using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using System.Diagnostics;


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
    /// If we are executing a build, this stores the build ID of the current
    /// build.
    /// </summary>
    private string current_build_id;

    /// <summary>
    /// If we are executing a build, this is a mapping that indicates what the
    /// remote folders are named, and what the local names for those same
    /// folders is.
    /// </summary>
    private Dictionary<string, string> current_build_folders;

    /// <summary>
    /// Transmit an error message to the user, optionally closing the connection
    /// once the message has been transmitted.
    /// </summary>
    void SendError(bool closeAfter, UInt32 code, string msg, params object[] args)
    {
        var error = new ErrorMessage(code, String.Format(msg, args));
        error.CloseAfterSending = closeAfter;

        Send(error);
    }

    /// <summary>
    /// Transmit an informational or warning message to the user; this is used
    /// for all textual communications which are not considered an out and out
    /// error.
    /// </summary>
    void SendMessage(string msg, params object[] args)
    {
        Send(new MessageMessage(String.Format(msg, args)));
    }

    /// <summary>
    /// Acknowledge (either positive or negative, depending on ack) the
    /// reception of the message of the provided type.
    /// </summary>
    void Acknowledge(MessageType msgType, bool ack=true)
    {
        Send(new AcknowledgeMessage(msgType, ack));
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
    /// Handle an incoming protocol message by sending back an error message
    /// indicating that a message of this type is not allowed at this point in
    /// the conversation.
    /// </summary>
    void ProtocolViolationMessage(IProtocolMessage message,
                                  string reason=null, params object[] args)
    {
        SendError(reason == null,
            9999,
            "Received unexpected message with id={0}; protocol violation",
            message.MsgID);

        if (reason != null)
            SendError(true, 9999, reason, args);
    }

    /// <summary>
    /// Invoked every time a message is received from the client. This does all
    /// of the protocol handling work on our end, handling messages as
    /// appropriate.
    /// </summary>
    private void Dispatch(PartialMessage inMsg)
    {
        try
        {
            // Convert the message from it's partial data format into a complete
            // message.
            IProtocolMessage message = inMsg.getMessage();
            Console.WriteLine("Recv: {0}", message);

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
                case MessageType.Acknowledge:
                case MessageType.BuildOutput:
                case MessageType.BuildComplete:
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

                // The client is sending us the contents of a file. We need to
                // persist it to disk so that it can take a part in the build.
                case MessageType.FileContent:
                    HandleFileContents(message as FileContentMessage);
                    break;

                // Handle the command to execute a build by running the given
                // command inside of the appropriate folder, dispatching all of
                // the output back to the other end.
                case MessageType.ExecuteBuild:
                    HandleExecuteBuild(message as ExecuteBuildMessage);
                    break;

                default:
                    throw new Exception("Unknown message type");
            }
        }
        catch (Exception err)
        {
            SendError(true, 9998, "Server Exception: {0}", err.Message);
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
            SendError(true, 1000, "Invalid protocol; only version 1 is supported");
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
            SendError(true, 1001, "Invalid username/password; login denied");
            return;
        }

        // Save the hostname and platform.
        remote_host = message.Hostname;
        remote_platform = message.Platform;

        // Welcome the user
        SendMessage("Hello, {0} from {1} {2}",
            user.username,
            remote_platform,
            remote_host);
        Acknowledge(MessageType.Introduction);
    }

    /// <summary>
    /// Handle setting up for a new build for this client.
    /// </summary>
    void HandleSetBuild(SetBuildMessage message)
    {
        // Store the build ID and build and get ready to map build folders
        current_build_id = message.BuildID;
        current_build_folders = new Dictionary<string, string>();

        // All of the folders that we want to use for the build will be based in
        // this root, which is based on the configured cache path with some path
        // elements that separate the items for different users on different
        // platforms and hosts.
        //
        // The last path component in the root is the build ID value, which will
        // remain the same for multiple builds from the same host OS for the
        // same folders, based on the uniqueness constraint of the build ID
        // value.
        var local_root_folder = Path.Combine(
            config.full_cache_path,
            user.username,
            remote_platform,
            remote_host,
            current_build_id);

        foreach (var remote_folder in message.Folders)
        {
            var local_folder = Path.Combine(local_root_folder, Path.GetFileName(remote_folder));

            current_build_folders[remote_folder] = local_folder;

            Directory.CreateDirectory(local_folder);
        }

        SendMessage("SetBuild OK: Using Build {0}", current_build_id);
        SendMessage("Build root: {0}", local_root_folder);
        Acknowledge(MessageType.SetBuild);
    }

    /// <summary>
    /// Handle a file transmission by writing the file to the appropriate
    /// location in the cache folder for the currently registered build.
    /// </summary>
    void HandleFileContents(FileContentMessage message)
    {
        // Map the root path on the client to the local cached version; if this
        // fails, the client is sending us files for a root it didn't tell us
        // about when it started the build, so trigger an error.
        string local_path;
        if (current_build_folders.TryGetValue(message.RootPath, out local_path) == false)
        {
            SendError(true, 2000, "Unrecognized root path {0}", message.RootPath);
            return;
        }

        // Now we can combine the relative path of the file in the root with our
        // locally mapped root in order to get an entire complete absolute file
        // name.
        //
        // Once we do that, ensure that the directory that contains the file
        // esists (since it may have never before seen relative parts) and then
        // write it there.
        var local_file = Path.Combine(local_path, message.RelativeName);

        Directory.CreateDirectory(Path.GetDirectoryName(local_file));
        File.WriteAllText(local_file, message.FileContent, Encoding.UTF8);

        // Now that we're done, tell the client that we have received the file
        // and handled it so they can send the next one or start the build.
        Acknowledge(MessageType.FileContent);
    }

    /// <summary>
    /// Handle the execution of the build by executing the command that exists
    /// in the first cached folder in the build.
    /// </summary>
    void HandleExecuteBuild(ExecuteBuildMessage message)
    {
        // Determine what the working directory should be; we want it to be
        // the first path given to us. For our purposes here since this is a
        // dictionary, we just select the first key. This is entirely not the
        // right thing, but we need to think more about how to convey the
        // appropriate working directory from the client to the server anyway.
        string working_dir;
        using (var enumerator = current_build_folders.GetEnumerator())
        {
            enumerator.MoveNext();
            working_dir = enumerator.Current.Value;
        }

        // Say what we're going to do, then do it.
        //
        // Here the working directory is shortened up for clarity.
        SendMessage("Executing '{0}' (working_dir: {1})", message.ShellCmd, Path.GetFileName(working_dir));
        ExecuteProcess(message.ShellCmd, working_dir);
    }

    /// <summary>
    /// Given a shell command and a working directory, return back an object
    /// that knows how to execute that command in that directory.
    /// </summary>
    /// <remarks>
    /// This tries to be smart so that the command will execute properly
    /// regardless of platform, but it has only been tested on Linux and Windows
    /// as the current time (and not extensitively by any stretch).
    /// </remarks>
    ProcessStartInfo GetProcessStartInfo(string shell_cmd, string working_dir)
    {
        ProcessStartInfo startInfo = new ProcessStartInfo();

        // Ensure that any double quotes in the input string are handled
        // properly.
        shell_cmd = shell_cmd.Replace("\"", "\\\"");

        // If there is a COMSPEC environemtn variable, we're on windows.
        // Use that to execute the command.
        var comspec = Environment.GetEnvironmentVariable("COMSPEC");
        if (comspec != null)
        {
            startInfo.FileName = comspec;
            startInfo.Arguments = String.Format(@"/C ""{0}""", shell_cmd);
        }
        else
        {
            // On Linux/MacOS, use bash to execute the shell command; we
            // will use env to determine where it is, in case it's not in a
            // standard location.
            startInfo.FileName = "/usr/bin/env";
            startInfo.Arguments = String.Format(@"bash -c ""{0}""", shell_cmd);
        }

        // We don't wait to create a window; the task should just run in the
        // background on the server.
        startInfo.CreateNoWindow = true;

        // Set the working directory up.
        startInfo.WorkingDirectory = working_dir;

        // Set up to capture standard output and standard error; this
        // requires that we don't let the shell execute the thing,
        // apparently.
        startInfo.UseShellExecute = false;
        startInfo.RedirectStandardOutput = true;
        startInfo.RedirectStandardError = true;

        return startInfo;
    }

    /// <summary>
    /// Execute the process specified in the given ProcessStartInfo structure.
    /// This happens in the background and (for the moment) can't be stopped
    /// once started.
    /// </summary>
    void ExecuteProcess(string shell_cmd, string working_dir)
    {
        try
        {
            // Create a process to run our build, and give it the process info
            // we were given.
            // Create a process
            var process = new Process();
            process.StartInfo = GetProcessStartInfo(shell_cmd, working_dir);

            // Set up event handlers to handle when output data is received
            // from the stdout and stderr. These both ensure that they don't
            // handle output when it's a null, because that is an indication
            // that the output is done now.
            process.OutputDataReceived += (sender, data) => {
                if (data.Data != null)
                    Send(new BuildOutputMessage(data.Data, true));
            };

            process.ErrorDataReceived += (sender, data) => {
                if (data.Data != null)
                    Send(new BuildOutputMessage(data.Data, false));
            };

            // Also ensure that we can detect when the process is going away
            // so that we can dispose it and such.
            process.EnableRaisingEvents = true;
            process.Exited += (sender, e) => {
                Process sendProc = sender as Process;

                Send(new BuildCompleteMessage((UInt16) sendProc.ExitCode));
                sendProc.Dispose();
            };

            // Launch it and start reading output in the background. We'll get
            // events when it exits or data arrives, so we can just leave now.
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
        }
        catch (Exception error)
        {
            SendError(false, 3000, "Error: {0}", error.Message);
        }
    }
}
