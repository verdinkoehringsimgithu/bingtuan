using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public class ParityCase
{
    public string name;
    public List<CombatMember> left, right;
    public double[] random;
    public double[] macro;
    public int rounds;
    public double hp, enemy_hp;
    public int turns, win, censored, draw;
}
public class RuntimeParityHarness
{
    public static void Main(string[] args)
    {
        var json=new JavaScriptSerializer { MaxJsonLength=int.MaxValue, RecursionLimit=1000 };
        var cases=json.Deserialize<List<ParityCase>>(File.ReadAllText(args[0]));
        int count=0, tapeCount=0;
        foreach(var c in cases)
        {
            var left=new CombatTeam(c.left); var right=new CombatTeam(c.right);
            if(c.macro!=null) right.Macro(c.macro[0],c.macro[1],c.macro[2],c.macro[3],c.macro[4],c.macro[5]);
            int tape=0;
            var battle=new CombatRuntime(left,right,()=>{if(tape>=c.random.Length)throw new Exception("Tape exhausted: "+c.name);return c.random[tape++];},c.rounds);
            while(!battle.Ended) battle.Next();
            double hp=Math.Max(0,left.bp)/left.maxBP, enemy=Math.Max(0,right.bp)/right.maxBP;
            bool draw=left.Dead&&right.Dead;
            if(Math.Abs(hp-c.hp)>1e-10 || Math.Abs(enemy-c.enemy_hp)>1e-10 || battle.Round!=c.turns || (battle.Winner==0?1:0)!=c.win || (battle.Censored?1:0)!=c.censored || (draw?1:0)!=c.draw)
                throw new Exception(c.name+": actual hp="+hp+", enemy="+enemy+", round="+battle.Round+"; expected hp="+c.hp+", enemy="+c.enemy_hp+", round="+c.turns+"; draws="+tape+"/"+c.random.Length);
            count++;tapeCount+=tape;
        }
        File.WriteAllText(args[1],json.Serialize(new { cases=count,random_draws=tapeCount,passed=true,tolerance=1e-10 }));
        Console.WriteLine(count+" C#/Python battle parity cases passed.");
    }
}
