// Explicit local qualification fixture. No network/provider/OAuth operations.
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Web.Script.Serialization;

class S14LocalFakeRclone {
    static string root;
    static string Arg(string[] args, string flag) {
        int index=Array.IndexOf(args,flag);
        if(index<0 || index+1>=args.Length) throw new Exception("FIXTURE_ARG_REQUIRED");
        return args[index+1];
    }
    static string Remote(string value) {
        if(!value.StartsWith("fixture-r7:")) throw new Exception("FIXTURE_REMOTE_REQUIRED");
        string path=Path.GetFullPath(Path.Combine(root,value.Substring(11).Replace('/',Path.DirectorySeparatorChar)));
        if(path!=root && !path.StartsWith(root+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)) throw new Exception("FIXTURE_PATH_DENIED");
        return path;
    }
    static string Hex(byte[] raw) { return BitConverter.ToString(raw).Replace("-","").ToLowerInvariant(); }
    static int Main(string[] args) {
        try {
            Console.OutputEncoding=new UTF8Encoding(false);
            string[] config=File.ReadAllLines(Arg(args,"--config"),Encoding.UTF8);
            if(config.Length!=2 || config[0]!="SYNTHETIC_LOCAL_FAKE_TRANSPORT") throw new Exception("FIXTURE_CONFIG_REQUIRED");
            root=Path.GetFullPath(config[1]);
            if(Arg(args,"--drive-root-folder-id")!="synthetic_drive_root_0001" || !Directory.Exists(root)) throw new Exception("FIXTURE_ROOT_REQUIRED");
            if(args[0]=="lsjson") {
                if(Remote(args[1])!=root) throw new Exception("FIXTURE_LIST_ROOT_REQUIRED");
                var rows=new List<object>();
                foreach(string path in Directory.GetDirectories(root,"*",SearchOption.AllDirectories).OrderBy(p=>p)) {
                    string relative=path.Substring(root.Length+1).Replace('\\','/');
                    rows.Add(new {Path=relative,Name=Path.GetFileName(path),IsDir=true,ID="synthetic-dir-"+relative});
                }
                foreach(string path in Directory.GetFiles(root,"*",SearchOption.AllDirectories).OrderBy(p=>p)) {
                    string relative=path.Substring(root.Length+1).Replace('\\','/');
                    string md5;using(var stream=File.OpenRead(path)) using(var digest=MD5.Create()) md5=Hex(digest.ComputeHash(stream));
                    rows.Add(new {Path=relative,Name=Path.GetFileName(path),Size=new FileInfo(path).Length,IsDir=false,
                        ID="synthetic-file-"+relative,Hashes=new Dictionary<string,string>{{"MD5",md5}}});
                }
                Console.Write(new JavaScriptSerializer().Serialize(rows));
            } else if(args[0]=="cat") {
                byte[] raw=File.ReadAllBytes(Remote(args[1]));
                int bound=Int32.Parse(Arg(args,"--head"));
                using(var output=Console.OpenStandardOutput()) output.Write(raw,0,Math.Min(raw.Length,bound));
            } else if(args[0]=="copyto") {
                string source=args[1].StartsWith("fixture-r7:")?Remote(args[1]):Path.GetFullPath(args[1]);
                string destination=args[2].StartsWith("fixture-r7:")?Remote(args[2]):Path.GetFullPath(args[2]);
                int maxIndex=Array.IndexOf(args,"--max-size");
                if(maxIndex>=0 && new FileInfo(source).Length>Int64.Parse(args[maxIndex+1].TrimEnd('B'))) return 3;
                byte[] raw=File.ReadAllBytes(source);
                if(File.Exists(destination) && !raw.SequenceEqual(File.ReadAllBytes(destination))) return 9;
                Directory.CreateDirectory(Path.GetDirectoryName(destination));
                if(!File.Exists(destination)) File.WriteAllBytes(destination,raw);
            } else return 2;
            return 0;
        } catch { return 3; }
    }
}
