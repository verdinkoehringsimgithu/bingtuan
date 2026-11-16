using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Web.Script.Serialization;
using LegionBattle.Generator;

public static class GeneratorBridge
{
    public static void Main(string[] args)
    {
        string destination = args[0];
        int count = args.Length > 1 ? int.Parse(args[1]) : 128;
        int offset = args.Length > 2 ? int.Parse(args[2]) : 0;
        var flags = BindingFlags.Static | BindingFlags.NonPublic;
        var genRandom = typeof(GeneratorEngine).GetField("_rand", flags);
        var affixRandom = typeof(AffixManager).GetField("_rand", flags);
        var records = new List<object>();
        string[] genres = { "勇气", "坚韧", "先机", "魔力" };
        for (int tier = 1; tier <= 6; tier++)
            for (int g = 0; g < genres.Length; g++)
                for (int j = offset; j < offset + count; j++)
                {
                    int sid = tier * 100000 + g * 10000 + j;
                    genRandom.SetValue(null, new Random(20261012 + sid));
                    affixRandom.SetValue(null, new Random(20261012 + sid));
                    SkillRecord r = GeneratorEngine.Generate(tier, genres[g], sid);
                    records.Add(new Dictionary<string, object> {
                        { "tier", tier }, { "genre", genres[g] }, { "sample", j },
                        { "detail", r.DetailText }, { "csv", r.CsvData }
                    });
                }
        var json = new JavaScriptSerializer { MaxJsonLength = int.MaxValue };
        File.WriteAllText(destination, json.Serialize(records), new System.Text.UTF8Encoding(false));
        Console.WriteLine("Generated " + records.Count + " current-source skill records");
    }
}
