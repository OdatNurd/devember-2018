using System;
using System.IO;
using System.Text.RegularExpressions;
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

    class Exclusions
    {
        List<string> include_folders { get; set; } = new List<string>();
        List<string> exclude_folders { get; set; } = new List<string>();

        List<Regex> include_files { get; set; } = new List<Regex>();
        List<Regex> exclude_files { get; set; } = new List<Regex>();

        public void AddFolderInclude(string dir)
        {
            include_folders.Add(dir);
        }

        public void AddFolderExclude(string dir)
        {
            exclude_folders.Add(dir);
        }

        public void AddFileInclude(string file)
        {
            include_files.Add(MakeRegex(file));
        }

        public void AddFileExclude(string file)
        {
            exclude_files.Add(MakeRegex(file));
        }

        public bool UseDir(string dir)
        {
            if (include_folders.Count == 0 || include_folders.Contains(dir))
            {
                if (exclude_folders.Contains(dir) == false)
                {
                    Console.WriteLine("Including Dir: {0}", dir);
                    return true;
                }
            }

            Console.WriteLine("Excluding Dir: {0}", dir);
            return false;
        }

        public bool UseFile(string file)
        {
            var result =
             ListMatches(file, include_files, true) == true &&
                   ListMatches(file, exclude_files, false) == false;

            // if (result)
            //     Console.WriteLine("Including File: {0}", file);
            // else
            //     Console.WriteLine("Excluding File: {0}", file);
            return result;
        }

        bool ListMatches(string file, List<Regex> patterns, bool default_if_empty)
        {
            if (patterns.Count == 0)
                return default_if_empty;

            foreach (var pattern in patterns)
            {
                if (pattern.IsMatch(file))
                    return true;
            }

            return false;
        }

        Regex MakeRegex(string glob)
        {
            var regex = Regex.Escape(glob).Replace(@"\*", ".*").Replace(@"\?", ".");

            return new Regex(String.Format("^{0}$", regex));

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

        static void PathSearch(string rootPath, Exclusions exclusions, string dir=null)
        {
            rootPath = Path.GetFullPath(rootPath);
            if (rootPath.EndsWith(Path.DirectorySeparatorChar.ToString()) == false)
                rootPath += Path.DirectorySeparatorChar;

            if (dir == null)
                dir = rootPath;

            if (dir.EndsWith(Path.DirectorySeparatorChar.ToString()) == false)
                dir += Path.DirectorySeparatorChar;

            foreach (var thisDir in Directory.GetDirectories(dir))
            {
                var subDir = thisDir.Substring(dir.Length);
                // Console.WriteLine("rootDir = {0}", rootPath);
                // Console.WriteLine("thisDir = {0}", thisDir);
                // Console.WriteLine("xxxDir = {0}", dir);
                // Console.WriteLine("==> {0}", subDir);
                if (exclusions.UseDir(subDir))
                    PathSearch(rootPath, exclusions, thisDir);
            }

            foreach (var thisFile in Directory.GetFiles(dir))
            {
                if (exclusions.UseFile(thisFile.Substring(dir.Length)))
                    Console.WriteLine("-> {0}", thisFile.Substring(rootPath.Length));
                // Console.WriteLine("{0} ({1})",
                //     thisFile.Substring(rootPath.Length),
                //     thisFile.Substring(dir.Length));
            }
        }

        static void Main(string[] args)
        {
            Exclusions exclusions = new Exclusions();

            exclusions.AddFolderExclude("bin");
            exclusions.AddFolderExclude("obj");
            // exclusions.AddFileInclude("*.cs");

            PathSearch("C:/Users/micro/AppData/Roaming/Sublime Text 3/Packages/devember_2018/remote_build_server", exclusions);
            // var json = JsonConvert.SerializeObject(MakeDeltaTest(), Formatting.Indented);
            // Console.WriteLine("JSON: {0}", json);

            // var delta = JsonConvert.DeserializeObject<FileDelta>(json);
            // Console.WriteLine("Delta: {0}", delta);

            // if (json == JsonConvert.SerializeObject(delta, Formatting.Indented))
            //     Console.WriteLine("PASS");
            // else
            //     Console.WriteLine("FAIL");
        }
    }
}
