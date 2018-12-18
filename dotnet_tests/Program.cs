using System;
using System.Collections.Generic;
using Newtonsoft.Json;

namespace dotnet_tests
{
    // A file delta entry
    public class FileEntry
    {
        public FileEntry (string name, string sha1, double last_modified)
        {
            this.name = name;
            this.sha1 = sha1;
            this.last_modified = last_modified;
        }

        public string name { get; set; }
        public string sha1 { get; set; }
        public double last_modified { get; set; }
    }

    // A list of deltas that represent a particular path
    public class DeltaList
    {
        public List<FileEntry> add { get; set; } = new List<FileEntry>();
        public List<FileEntry> modify { get; set; } = new List<FileEntry>();
        public List<FileEntry> remove { get; set; } = new List<FileEntry>();
    }

    public class FileDelta : Dictionary<string, DeltaList>
    {
        public FileDelta() : base()
        {

        }

        public DeltaList AddPath(string path)
        {
            var delta = new DeltaList();
            this[path] =delta;

            return delta;
        }
    }

    class Program
    {
        static FileDelta MakeDeltaTest()
        {
            FileDelta file_delta = new FileDelta();
            var delta = file_delta.AddPath("/home/tmartin/local/src/devember-2018/remote_build_server");

            delta.add.Add(new FileEntry("BuildClient.cs", "201b43d4ddb4dc395c09b10e83305227b643db50", 1544504473.2212374));
            delta.remove.Add(new FileEntry("BuildClient1.cs", "201b43d4ddb4dc395c09b10e83305227b643db50", 1544504473.2212374));
            delta.modify.Add(new FileEntry("Extensions.cs", "3e137214ffd6dfdd52b8ff3bb46e9fdab96fab7c", 1544416126.3528106));
            delta.modify.Add(new FileEntry("Main.cs", "e596ccd55c6b253f14f09a7b68826e22fbb59f8e", 1544502070.7733796));

            return file_delta;
        }

        static void Main(string[] args)
        {
            var json = JsonConvert.SerializeObject(MakeDeltaTest(), Formatting.Indented);
            Console.WriteLine("JSON: {0}", json);

            var delta = JsonConvert.DeserializeObject<FileDelta>(json);
            Console.WriteLine("Delta: {0}", delta);

            if (json == JsonConvert.SerializeObject(delta, Formatting.Indented))
                Console.WriteLine("PASS");
            else
                Console.WriteLine("FAIL");
        }
    }
}
