using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public sealed class ExpectedTacticalAction
{
    public int round,side,owner,index,chainDepth,scholarTarget,scholarRestored;
    public double leftBP,rightBP,bondDirectMultiplier,bondOutputMultiplier;
    public double coinsEarned;
    public bool heroineFirst,killerMarked;
    public double engineerQueued,appliedHealPenalty,healingPrevented;
    public double[] stolenStats;
    public bool normal,critical,missed,forcedHit,absoluteEvaded,hasContinuation;
}
public sealed class TacticalCase
{
    public string name;
    public List<CombatMember> left,right;
    public CombatPersistentLimits limits;
    public OpeningBondRules leftOpening,rightOpening;
    public CombatEvasionRules leftEvasion,rightEvasion;
    public CombatSupportRules leftSupport,rightSupport;
    public CombatAmplificationRules leftAmplification,rightAmplification;
    public CombatAugmentationRules leftAugmentation,rightAugmentation;
    public CombatTacticalRules leftTactical,rightTactical;
    public CombatTacticalSummary left_summary,right_summary;
    public ExpectedTacticalAction[] actions;
    public double[] macro,random,left_stats,right_stats;
    public int[] left_uses,right_uses;
    public int capacity,rounds,turns,win,censored,draw;
    public double hp,enemy_hp,left_received,right_received,left_min,right_min;
}
public static class TacticalParityHarness
{
    private static double maximumError;
    private static void Near(double value,double expected,string name)
    {
        double error=Math.Abs(value-expected)/Math.Max(1,Math.Abs(expected));maximumError=Math.Max(maximumError,error);
        if(error>1e-9)throw new Exception(name+": "+value+" != "+expected);
    }
    private static void Summary(CombatTacticalSummary a,CombatTacticalSummary b,string name)
    {
        if(a.mages!=b.mages||a.hunters!=b.hunters||a.gangs!=b.gangs||a.richMembers!=b.richMembers||a.workers!=b.workers||
            a.mageSame!=b.mageSame||a.mageSwitches!=b.mageSwitches||a.gangAttacks!=b.gangAttacks||a.richAttacks!=b.richAttacks||a.workerProcs!=b.workerProcs||a.lastAxis!=b.lastAxis)
            throw new Exception(name+" tactical counters");
        Near(a.hunterScheduled,b.hunterScheduled,name+" scheduled");Near(a.coins,b.coins,name+" coins");Near(a.richSaved,b.richSaved,name+" saved");
        if(a.axes.Length!=b.axes.Length)throw new Exception(name+" axes length");
        for(int k=0;k<a.axes.Length;k++)if(a.axes[k]!=b.axes[k]||a.percentLayers[k]!=b.percentLayers[k])throw new Exception(name+" axis layers");
    }
    public static void Main(string[] args)
    {
        try{Run(args);}catch(Exception ex){Console.Error.WriteLine(ex.GetType().Name+": "+ex.Message);Environment.Exit(1);}
    }
    private static void Run(string[] args)
    {
        var json=new JavaScriptSerializer {MaxJsonLength=int.MaxValue,RecursionLimit=1000};
        var cases=json.Deserialize<List<TacticalCase>>(File.ReadAllText(args[0]));int draws=0,actions=0;
        foreach(var c in cases)
        {
            if(args.Length>2&&args[2]!=c.name)continue;
            var a=new CombatTeam(c.left,c.limits,c.leftOpening,c.leftEvasion,c.capacity,c.leftSupport,c.leftAmplification,c.leftAugmentation,c.leftTactical);
            var b=new CombatTeam(c.right,null,c.rightOpening,c.rightEvasion,c.capacity,c.rightSupport,c.rightAmplification,c.rightAugmentation,c.rightTactical);
            if(c.macro!=null)b.Macro(c.macro[0],c.macro[1],c.macro[2],c.macro[3],c.macro[4],c.macro[5]);
            int index=0,actionIndex=0;
            var battle=new CombatRuntime(a,b,()=>{if(index>=c.random.Length)throw new Exception(c.name+" tape exhausted");return c.random[index++];},c.rounds);
            while(!battle.Ended)
            {
                var report=battle.Next();
                if(report.owner<0)continue; // A pre-action loss can end a round without an attack.
                if(actionIndex>=c.actions.Length)throw new Exception(c.name+" extra action");
                var expected=c.actions[actionIndex++];
                Near(report.bondDirectMultiplier,expected.bondDirectMultiplier,c.name+" direct attribution");Near(report.bondOutputMultiplier,expected.bondOutputMultiplier,c.name+" output attribution");
                Near(report.coinsEarned,expected.coinsEarned,c.name+" earned");
                Near(report.engineerQueued,expected.engineerQueued,c.name+" engineer queued");
                Near(report.appliedHealPenalty,expected.appliedHealPenalty,c.name+" applied penalty");
                Near(report.healingPrevented,expected.healingPrevented,c.name+" healing prevented");
                if((report.stolenStats==null)!=(expected.stolenStats==null))throw new Exception(c.name+" stolen array mismatch");
                if(report.stolenStats!=null)for(int k=0;k<4;k++)Near(report.stolenStats[k],expected.stolenStats[k],c.name+" stolen stat");
                if(report.hasContinuation){Near(a.bp,expected.leftBP,c.name+" chained left BP");Near(b.bp,expected.rightBP,c.name+" chained right BP");}
                if(report.round!=expected.round||report.side!=expected.side||report.owner!=expected.owner||report.normal!=expected.normal||
                    report.critical!=expected.critical||report.missed!=expected.missed||report.forcedHit!=expected.forcedHit||report.absoluteEvaded!=expected.absoluteEvaded||index!=expected.index||report.chainDepth!=expected.chainDepth||report.hasContinuation!=expected.hasContinuation||report.scholarTarget!=expected.scholarTarget||report.scholarRestored!=expected.scholarRestored||report.heroineFirst!=expected.heroineFirst||report.killerMarked!=expected.killerMarked)
                {
                    File.WriteAllText(args[1]+".failure.json",json.Serialize(new {name=c.name,actionIndex,actual=report,expected,index,leftUses=a.uses,rightUses=b.uses,left=a.TacticalBonds.Snapshot(),right=b.TacticalBonds.Snapshot()}));
                    throw new Exception(c.name+" action "+actionIndex+" mismatch: round "+report.round+", side "+report.side+", owner "+report.owner+", draws "+index+"/"+expected.index);
                }
            }
            if(actionIndex!=c.actions.Length||index!=c.random.Length||battle.Round!=c.turns||(battle.Winner==0?1:0)!=c.win||
                (battle.Censored?1:0)!=c.censored||(a.Dead&&b.Dead?1:0)!=c.draw)throw new Exception(c.name+" final outcome/tape mismatch");
            Near(Math.Max(0,a.bp)/a.maxBP,c.hp,c.name+" HP");Near(Math.Max(0,b.bp)/b.maxBP,c.enemy_hp,c.name+" enemy HP");
            Near(a.DamageReceived,c.left_received,c.name+" received");Near(b.DamageReceived,c.right_received,c.name+" enemy received");
            Near(a.MinimumBPRatio,c.left_min,c.name+" minimum");Near(b.MinimumBPRatio,c.right_min,c.name+" enemy minimum");
            for(int i=0;i<4;i++){Near(a.Effective(i),c.left_stats[i],c.name+" stat");Near(b.Effective(i),c.right_stats[i],c.name+" enemy stat");}
            for(int i=0;i<a.uses.Length;i++)if(a.uses[i]!=c.left_uses[i])throw new Exception(c.name+" owner usage");
            for(int i=0;i<b.uses.Length;i++)if(b.uses[i]!=c.right_uses[i])throw new Exception(c.name+" enemy usage");
            Summary(a.TacticalBonds.Snapshot(),c.left_summary,c.name);Summary(b.TacticalBonds.Snapshot(),c.right_summary,c.name+" enemy");
            draws+=index;actions+=actionIndex;
        }
        File.WriteAllText(args[1],json.Serialize(new {passed=true,cases=cases.Count,actions,random_draws=draws,maximum_relative_error=maximumError,tolerance=1e-9}));
        Console.WriteLine(cases.Count+" tactical cases and "+actions+" actions passed; max error "+maximumError);
    }
}
