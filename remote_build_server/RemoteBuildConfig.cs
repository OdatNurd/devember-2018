using System;
using System.IO;
using System.Text;
using System.Collections.Generic;
using Newtonsoft.Json;

public class RemoteBuildConfig
{
    // The base cache path; all remote builds take place somewhere under here.
    // This is the configured version, which can be either absolute or relative
    // as desired.
    public string base_cache;

    // This is the fully expanded version of the base_cache, which may be the
    // same or may be different, depending on whether the base_cache is a
    // relative or absolute path.
    [JsonIgnore]
    public string full_cache_path = null;

    // Should we listen on localhost instead of the "normal" host name?
    public bool use_localhost = false;

    // The list of users that have access to remote builds.
    public List<RemoteBuildUser> users;

    // A record of each individual user that has access to remote builds and all
    // of their custom settings.
    public class RemoteBuildUser
    {
        public string username;
        public string password;
    }

    // Load the configuration file with the given file name
    public static RemoteBuildConfig Load(string filename)
    {
        var json = File.ReadAllText(filename, Encoding.UTF8);
        return JsonConvert.DeserializeObject<RemoteBuildConfig>(json);
    }

    // Given a username and password, return back the record for that
    // user, or null if there is no match (such as when there is no
    // such user or the password is wrong).
    public RemoteBuildUser LoginUser(string username, string password)
    {
        foreach (var user in users)
        {
            if (user.username == username && user.password == password)
                return user;
        }

        return null;
    }
}