using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public static class EvasionInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-10,name);}
    private static CombatTeam Team(string[] identities,int capacity,CombatEvasionRules rules=null,double initiative=10000,CombatSkill skill=null)
    {
        var roster=new List<CombatMember>();
        foreach(string identity in identities)roster.Add(new CombatMember {bp=10000000,traits=new CharacterTraits {identity=identity},
            stats=new double[] {0,0,initiative/identities.Length,0},skill=skill??new CombatSkill {chance=100,mainParam=0}});
        return new CombatTeam(roster,null,null,rules,capacity);
    }
    private static string[] Ids(int count,string identity){var ids=new string[count];for(int i=0;i<count;i++)ids[i]=identity;return ids;}
    private static CombatEvasionRules Ninja(){return new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1};}
    private static CombatAction Attack(CombatTeam a,CombatTeam b){return new CombatRuntime(a,b,()=>0).Next();}
    public static void Main(string[] args)
    {
        try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" evasion invariant checks passed");}
        catch(Exception ex){Console.Error.WriteLine(ex.Message);Environment.Exit(1);}
    }
    private static void Run()
    {
        for(int cap=5;cap<=30;cap+=5)
        {
            int below=(cap-1)/2;var a=Team(Ids(below,"军人"),cap,new CombatEvasionRules {military=true});
            var b=Team(new[] {"忍者"},cap,Ninja(),1000);var result=Attack(a,b);
            Check(!result.forcedHit&&result.absoluteEvaded,"Stage cap "+cap+" under-half cannot force hit despite all occupied slots being military");
            Check(a.EvasionBonds.Snapshot().militarySkillChecks==0,"Stage cap "+cap+" under-half does not roll military");
            int enough=(cap+1)/2;a=Team(Ids(enough,"军人"),cap,new CombatEvasionRules {military=true});b=Team(new[] {"忍者"},cap,Ninja(),1000);
            result=Attack(a,b);Check(result.forcedHit&&!result.missed&&!result.critical,"Stage cap "+cap+" sufficient military bypasses both evasion types without requiring a crit");
            Check(b.EvasionBonds.Snapshot().absoluteDodges==0,"Stage cap "+cap+" forced hit bypasses absolute evasion roll");
        }
        var attackSkill=new CombatSkill {chance=100,baseCrit=1,limit=1,initiativeBonus=10,mainType="Heal",subParam=.2};
        var attacker=Team(new[] {"学生"},5,null,10000,attackSkill);attacker.bp=attacker.maxBP*.5;
        var defender=Team(new[] {"忍者"},5,Ninja(),1000);var report=Attack(attacker,defender);
        Check(report.absoluteEvaded&&report.missed&&!report.critical,"Absolute evasion runs before and can prevent guaranteed critical attacks");
        Check(attacker.uses[0]==1&&attacker.casts[0]==1,"Absolute miss consumes the selected skill use");
        Near(attacker.bp,attacker.maxBP*.5,"Absolute miss prevents the skill recovery");
        Near(attacker.stats[2],10010,"Pre-hit initiative growth remains on an absolute miss");
        var fallback=Team(new[] {"军人"},1,new CombatEvasionRules {military=true},10000,new CombatSkill {chance=0});
        report=Attack(fallback,Team(new[] {"忍者"},1,Ninja(),1000));
        Check(report.normal&&!report.forcedHit&&report.absoluteEvaded,"Military normal fallback receives no forced hit");
        Check(fallback.EvasionBonds.Snapshot().militarySkillChecks==0,"Military fallback does not roll the skill bond");
        var growthRules=new CombatEvasionRules {ninja=true,countK=0,ninjaBase=0,ninjaCast=.5,ninjaCap=1};
        var ninja=Team(new[] {"忍者"},5,growthRules);var enemy=Team(new[] {"学生"},5,null,1000);
        var battle=new CombatRuntime(ninja,enemy,()=>.1);battle.Next();
        Near(ninja.EvasionBonds.NinjaProbability,0,"Ninja cast does not improve evasion during its current round");
        Near(ninja.EvasionBonds.Snapshot().pendingNinja,.5,"Ninja growth is queued");
        report=battle.Next();Check(!report.absoluteEvaded,"Current-round counterattack sees old ninja chance");
        Near(ninja.EvasionBonds.NinjaProbability,.5,"Ninja growth commits after both actions");
        Near(ninja.EvasionBonds.Snapshot().pendingNinja,0,"Committed ninja growth is not left pending");
        battle.Next();report=battle.Next();Check(report.absoluteEvaded,"Next round uses committed ninja growth");
        Near(ninja.EvasionBonds.NinjaProbability,1,"Ninja chance respects configured cap");
        for(int i=0;i<8;i++)battle.Next();Near(ninja.EvasionBonds.NinjaProbability,1,"Further casts cannot exceed the cap");
        ninja=Team(new[] {"忍者"},5,growthRules);enemy=Team(new[] {"忍者"},5,Ninja(),1000);
        battle=new CombatRuntime(ninja,enemy,()=>.1);report=battle.Next();
        Check(report.absoluteEvaded&&ninja.EvasionBonds.Snapshot().ninjaSkillCasts==1,"Missed ninja skill still queues growth after activation");
        Near(ninja.EvasionBonds.NinjaProbability,0,"Missed skill growth is deferred too");
        var basicNinja=Team(new[] {"忍者"},5,growthRules,10000,new CombatSkill {chance=0});
        battle=new CombatRuntime(basicNinja,Team(new[] {"学生"},5,null,1000),()=>.99);battle.Next();battle.Next();
        Check(basicNinja.EvasionBonds.Snapshot().ninjaSkillCasts==0,"Ninja normal attacks do not grow the bond");
        Near(basicNinja.EvasionBonds.NinjaProbability,0,"No skill activation means no growth");
        var dots=Team(new[] {"忍者"},5,Ninja(),1000);var source=Team(new[] {"学生"},5);
        dots.statuses.Add(new CombatStatus {kind="max",value=.1,turns=1,source=source});
        report=Attack(source,dots);Check(report.preDamage>0&&dots.bp<dots.maxBP,"Absolute evasion does not erase scheduled loss damage");
        var mixed=Team(new[] {"学生","军人","军人","军人"},5,new CombatEvasionRules {military=true});
        report=Attack(mixed,Team(new[] {"忍者"},5,Ninja(),1000));
        Check(!report.forcedHit,"Non-military owner's skill receives no military forced hit");
        var oldRules=new CombatEvasionRules {ninja=true,ninjaBase=.3,countK=0};
        var isolated=Team(new[] {"忍者"},5,oldRules);oldRules.ninjaBase=100;
        Near(isolated.EvasionBonds.NinjaProbability,.3,"Rules are snapshotted on runtime construction");
        var snapshot=isolated.EvasionBonds.Snapshot();snapshot.ninjaGrowth=100;
        Near(isolated.EvasionBonds.NinjaProbability,.3,"Summary is independent of runtime state");
        var fresh=Team(new[] {"忍者"},5,growthRules);Near(fresh.EvasionBonds.NinjaProbability,0,"New battle does not inherit ninja growth");
        foreach(int capacity in new[] {-1,31})
        {bool rejected=false;try{Team(new[] {"学生"},capacity);}catch(ArgumentException){rejected=true;}Check(rejected,"Reject invalid capacity "+capacity);}
        bool shortCap=false;try{Team(new[] {"学生","学生"},1);}catch(ArgumentException){shortCap=true;}Check(shortCap,"Capacity cannot be below actual roster size");
        foreach(double value in new[] {-1,double.NaN,double.PositiveInfinity,1.1})
        {bool rejected=false;try{new CombatEvasionRules {ninjaCap=value}.Clone();}catch(ArgumentException){rejected=true;}Check(rejected,"Reject invalid ninja cap "+value);}
    }
}
