using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;
public static class TacticalInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static void Near(double a,double b,string name){Check(Math.Abs(a-b)<1e-9*Math.Max(1,Math.Abs(b)),name+": "+a+" / "+b);}
    private static CombatMember M(string identity,double power=0)
    {return new CombatMember {bp=10000000,stats=new double[] {0,0,1,0},traits=new CharacterTraits {identity=identity},skill=new CombatSkill {chance=100,mainParam=power,pierce=1}};}
    private static CombatTeam T(CombatTacticalRules rules,params CombatMember[] members)
    {return new CombatTeam(new List<CombatMember>(members),null,null,null,Math.Max(5,members.Length),null,null,null,rules);}
    private static CombatTeam E(){var m=M("学生");m.stats[2]=0;return T(null,m);}
    public static void Main(string[] args)
    {try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" tactical invariant checks passed");}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.Exit(1);}}
    private static void Run()
    {
        var m=M("魔法师");m.skill.axis="C";var a=T(new CombatTacticalRules {mage=true,countK=0},m);var b=E();var battle=new CombatRuntime(a,b,()=>.99);var r=battle.Next();
        Near(r.bondDirectMultiplier,1,"First skill does not invent a switch");battle.Next();r=battle.Next();
        Check(a.TacticalBonds.Snapshot().mageSame==1,"Same-axis skill advances percentage layer");
        Near(a.TacticalBonds.Snapshot().percentLayers[0],1,"Same-axis layer is retained");battle.Next();m.skill.axis="M";r=battle.Next();
        Near(r.bondDirectMultiplier,1.04,"Different-axis skill gains switch damage immediately");
        Check(a.TacticalBonds.Snapshot().mageSwitches==1&&a.TacticalBonds.Snapshot().lastAxis=="M","Mage stores actual last selected axis");
        var gang=M("帮派",100000);gang.skill.turnLower=100;gang.skill.limit=1;gang.skill.subEffect="四维削弱";gang.skill.subParam=100;
        gang.item=new CombatItem {kind="normal_damage",value=.5};a=T(new CombatTacticalRules {gang=true,countK=0},gang);a.uses[0]=7;b=E();battle=new CombatRuntime(a,b,()=>.99);r=battle.Next();
        Check(r.normal&&!a.skillSelected,"Gang substitutes normal attack before original skill execution");Near(a.uses[0],7,"Gang does not consume original skill uses");
        Near(a.casts[0],0,"Gang does not increment original skill cast count");Check(b.statuses.Count==0,"Gang never calls original added effect");
        Near(r.bondDirectMultiplier,1.65,"Gang multiplier stays separate from normal equipment");Near(a.TacticalBonds.Snapshot().gangAttacks,1,"Gang attack counted");
        gang=M("帮派");gang.skill.chance=0;a=T(new CombatTacticalRules {gang=true,countK=0},gang);r=new CombatRuntime(a,E(),()=>.99).Next();
        Near(r.bondDirectMultiplier,1,"Random fallback does not invent a selected gang proc");
        var hunter=M("猎手",100);a=T(new CombatTacticalRules {hunter=true,countK=0,hunterFraction=1,hunterRounds=3},hunter);b=E();battle=new CombatRuntime(a,b,()=>.99);
        r=battle.Next();Near(r.damage,0,"Full hunter conversion removes immediate direct damage");Check(b.trueLoss.Count==1,"Hunter creates one duration record");
        double scheduled=a.TacticalBonds.Snapshot().hunterScheduled;Check(scheduled>0,"Hunter records pre-defense scheduled amount");Near(b.bp,b.maxBP,"Hunter cannot tick in creation round");
        battle.Next();r=battle.Next();Near(r.preDamage,scheduled/3,"Hunter starts next round with one third");
        Check(b.trueLoss[0].remaining==2,"Hunter decrements duration exactly once per round");
        a=T(new CombatTacticalRules {rich=true,countK=0},M("富翁"));b=E();battle=new CombatRuntime(a,b,()=>.99);r=battle.Next();
        Near(r.coinsEarned,1,"Rich attack earns battle-local coins");Near(a.TacticalBonds.Snapshot().coins,1,"Rich coin state records this fight");
        Near(a.TacticalBonds.FilterDamage(100),97.5,"Rich coins reduce subsequent incoming damage");
        Near(a.TacticalBonds.Snapshot().richSaved,2.5,"Rich prevented amount is recorded");
        var fresh=T(new CombatTacticalRules {rich=true},M("富翁"));Near(fresh.TacticalBonds.Snapshot().coins,0,"New battle starts with no previous coins");
        a=T(new CombatTacticalRules {worker=true,countK=0},M("社畜"));a.bp=0;a.TacticalBonds.Rescue(a);
        Near(a.bp,1+a.maxBP*.2,"Worker keeps one BP then performs independent recovery");a.bp=0;a.TacticalBonds.Rescue(a);Near(a.bp,0,"Worker rescues only once");
        Check(a.TacticalBonds.Snapshot().workerProcs==1,"Worker proc count is battle-local");
        var attacker=M("学生",100000);attacker.stats[2]=100;var worker=M("社畜");worker.stats[2]=0;worker.item=new CombatItem {kind="death_lock",value=.1};
        a=T(null,attacker);b=T(new CombatTacticalRules {worker=true,countK=0},worker);battle=new CombatRuntime(a,b,()=>.99);battle.Next();
        Check(b.locks[0]&&b.TacticalBonds.Snapshot().workerProcs==0,"Equipment death lock precedes worker rescue");battle.Next();battle.Next();
        Check(b.TacticalBonds.Snapshot().workerProcs==1&&!b.Dead,"Worker remains available for a later lethal attack");
        a=E();b=E();b.trueLoss.Add(new CombatTrueLoss {amount=b.maxBP*2,start=1,remaining=1,source=a});
        r=new CombatRuntime(a,b,()=>{throw new Exception("Random draw after pre-action lethal loss");}).Next();
        Check(r.ended&&r.owner<0&&b.Dead,"Pre-action lethal true loss ends before initiative tie random draw");
        bool bad=false;try{new CombatTacticalRules {hunterRounds=0}.Clone();}catch(ArgumentException){bad=true;}Check(bad,"Hunter duration requires a positive number of rounds");
        bad=false;try{new CombatTacticalRules {richCap=2}.Clone();}catch(ArgumentException){bad=true;}Check(bad,"Rich reduction cap cannot exceed one");
    }
}
