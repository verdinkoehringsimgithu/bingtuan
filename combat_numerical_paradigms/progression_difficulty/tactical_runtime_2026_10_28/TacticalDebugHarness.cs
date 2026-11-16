using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;
public static class TacticalDebugHarness
{
    public static void Main(string[] args)
    {
        var json=new JavaScriptSerializer {MaxJsonLength=int.MaxValue,RecursionLimit=1000};
        var c=json.Deserialize<List<TacticalCase>>(File.ReadAllText(args[0])).First(x=>x.name==args[1]);
        var a=new CombatTeam(c.left,c.limits,c.leftOpening,c.leftEvasion,c.capacity,c.leftSupport,c.leftAmplification,c.leftAugmentation,c.leftTactical);
        var b=new CombatTeam(c.right,null,c.rightOpening,c.rightEvasion,c.capacity,c.rightSupport,c.rightAmplification,c.rightAugmentation,c.rightTactical);
        if(c.macro!=null)b.Macro(c.macro[0],c.macro[1],c.macro[2],c.macro[3],c.macro[4],c.macro[5]);
        int index=0,n=0;var battle=new CombatRuntime(a,b,()=>c.random[index++],c.rounds);
        Console.WriteLine(json.Serialize(new {c.name,c.macro,c.leftTactical,c.left,c.right,c.hp,c.enemy_hp,c.turns}));
        try{while(!battle.Ended)
        {
            var r=battle.Next();var e=n<c.actions.Length?c.actions[n]:null;
            Console.WriteLine(json.Serialize(new {n=n++,r,index,e,left=a.bp,right=b.bp,leftDots=a.trueLoss.Count,rightDots=b.trueLoss.Count}));
        }}catch(Exception ex){Console.WriteLine(ex.Message+" index="+index);}
    }
}
