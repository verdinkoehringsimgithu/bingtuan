using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public sealed class LimitedCase
{
    public string name;
    public List<CombatMember> left,right;
    public CombatPersistentLimits limits;
    public double[] macro,random,left_stats,right_stats;
    public int[] left_uses,right_uses;
    public int rounds,turns,win,censored,draw;
    public double hp,enemy_hp,left_received,right_received,left_min,right_min;
}
public static class LimitedParityHarness
{
    private static double maximumError;
    private static void Near(double actual,double expected,string name)
    {
        double error=Math.Abs(actual-expected)/Math.Max(1,Math.Abs(expected));
        maximumError=Math.Max(maximumError,error);
        if(error>1e-9)throw new Exception(name+": "+actual+" != "+expected);
    }
    public static void Main(string[] args)
    {
        try { Run(args); }
        catch(Exception ex) { Console.Error.WriteLine(ex.GetType().Name+": "+ex.Message);Environment.Exit(1); }
    }
    private static void Run(string[] args)
    {
        var json=new JavaScriptSerializer {MaxJsonLength=int.MaxValue,RecursionLimit=1000};
        var cases=json.Deserialize<List<LimitedCase>>(File.ReadAllText(args[0]));
        int draws=0;
        foreach(var c in cases)
        {
            if(args.Length>2&&c.name!=args[2])continue;
            var a=new CombatTeam(c.left,c.limits);var b=new CombatTeam(c.right);
            if(c.macro!=null)b.Macro(c.macro[0],c.macro[1],c.macro[2],c.macro[3],c.macro[4],c.macro[5]);
            int index=0;
            var battle=new CombatRuntime(a,b,()=>{if(index>=c.random.Length)throw new Exception(c.name+" tape exhausted");return c.random[index++];},c.rounds);
            var trace=new List<object>();
            while(!battle.Ended)
            {
                var report=battle.Next();
                if(args.Length>2)trace.Add(new {report,index,a_bp=a.bp,b_bp=b.bp,a_stats=new[] {a.Effective(0),a.Effective(1),a.Effective(2),a.Effective(3)},b_stats=new[] {b.Effective(0),b.Effective(1),b.Effective(2),b.Effective(3)},a_output=a.Output(),b_output=b.Output()});
            }
            if(args.Length>2){File.WriteAllText(args[1],json.Serialize(trace));return;}
            if(index!=c.random.Length||battle.Round!=c.turns||(battle.Winner==0?1:0)!=c.win||
                (battle.Censored?1:0)!=c.censored||(a.Dead&&b.Dead?1:0)!=c.draw)throw new Exception(c.name+" outcome/tape mismatch: draws "+index+"/"+c.random.Length+", round "+battle.Round+"/"+c.turns);
            Near(Math.Max(0,a.bp)/a.maxBP,c.hp,c.name+" HP");Near(Math.Max(0,b.bp)/b.maxBP,c.enemy_hp,c.name+" enemy HP");
            Near(a.DamageReceived,c.left_received,c.name+" damage received");Near(b.DamageReceived,c.right_received,c.name+" enemy damage received");
            Near(a.MinimumBPRatio,c.left_min,c.name+" BP minimum");Near(b.MinimumBPRatio,c.right_min,c.name+" enemy BP minimum");
            for(int i=0;i<4;i++){Near(a.Effective(i),c.left_stats[i],c.name+" stats");Near(b.Effective(i),c.right_stats[i],c.name+" enemy stats");}
            for(int i=0;i<a.uses.Length;i++)if(a.uses[i]!=c.left_uses[i])throw new Exception(c.name+" owner uses");
            for(int i=0;i<b.uses.Length;i++)if(b.uses[i]!=c.right_uses[i])throw new Exception(c.name+" enemy owner uses");
            draws+=index;
        }
        File.WriteAllText(args[1],json.Serialize(new {passed=true,cases=cases.Count,random_draws=draws,relative_tolerance=1e-9,maximum_relative_error=maximumError}));
        Console.WriteLine(cases.Count+" limited C#/Python cases passed; max error "+maximumError);
    }
}
