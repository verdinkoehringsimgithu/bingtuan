using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public static class AmplificationInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name);}
    private static CombatMember M(string id,int tier=1,int level=30,double chance=100,int limit=999)
    {return new CombatMember {level=level,bp=10000000,stats=new double[] {0,0,5000,0},traits=new CharacterTraits {identity=id},skill=new CombatSkill {chance=chance,limit=limit,tier=tier,mainParam=0}};}
    private static CombatTeam T(CombatAmplificationRules rules,params CombatMember[] roster)
    {return new CombatTeam(new List<CombatMember>(roster),null,null,null,Math.Max(5,roster.Length),null,rules);}
    private static CombatTeam E(){var m=M("学生");m.stats[2]=0;return T(null,m);}
    private static CombatRuntime B(CombatTeam a,CombatTeam b=null){return new CombatRuntime(a,b??E(),()=>0);}
    public static void Main(string[] args)
    {try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" amplification invariant checks passed");}catch(Exception ex){Console.Error.WriteLine(ex.Message);Environment.Exit(1);}}
    private static void Run()
    {
        var a=T(new CombatAmplificationRules {academy=true},M("老师"),M("学生",level:10),M("学生",level:20));
        var r=B(a).Next();Near(r.bondDirectMultiplier,1.045,"Teacher damage uses actual student level total");
        Near(a.AmplificationBonds.Snapshot().studentExperienceMultiplier,1.12,"Teacher provides explicit student experience multiplier");
        Check(a.AmplificationBonds.Snapshot().studentLevels==30,"Student levels are preserved separately from four-stat budget");
        a=T(new CombatAmplificationRules {academy=true},M("老师"),M("老师"),M("学生",level:10));
        Near(a.AmplificationBonds.Snapshot().studentExperienceMultiplier,1.24,"More teachers increase student experience multiplier");
        a=T(new CombatAmplificationRules {academy=true},M("老师"));Near(B(a).Next().bondDirectMultiplier,1,"No students means no teacher combat bonus");
        var heal=M("老师");heal.skill.mainType="Heal";heal.skill.subParam=.1;
        a=T(new CombatAmplificationRules {academy=true},heal,M("学生"));a.bp=a.maxBP*.5;r=B(a).Next();
        Near(r.healing,a.maxBP*.1,"Teacher direct-damage bonus does not multiply recovery");Near(r.bondDirectMultiplier,1.045,"Teacher healing skill still strengthens its native direct attack");
        a=T(new CombatAmplificationRules {cult=true},M("拜火教",tier:5),M("拜火教",tier:1),M("拜火教",tier:3),M("拜火教",tier:5),M("学生",tier:1));
        Near(B(a).Next().bondDirectMultiplier,1.07,"Cult counts only lower-tier cult skill owners");
        a=T(new CombatAmplificationRules {cult=true},M("拜火教",tier:1),M("拜火教",tier:5));Near(B(a).Next().bondDirectMultiplier,1,"Low-tier cultist receives no bonus from higher-tier ally");
        a=T(new CombatAmplificationRules {fighter=true},M("格斗家"));var e=E();var b=B(a,e);
        r=b.Next();Near(r.bondOutputMultiplier,1,"Fighter starts without round growth");b.Next();r=b.Next();Near(r.bondOutputMultiplier,1.005,"Fighter grows on the next round");
        Near(a.AmplificationBonds.Snapshot().fighterMultiplier,1.005,"Fighter growth is exposed in result state");
        var source=T(new CombatAmplificationRules {fighter=true},M("格斗家"));e=E();b=B(source,e);b.Next();b.Next();
        e.statuses.Add(new CombatStatus {kind="max",value=.01,turns=1,source=source});r=b.Next();
        Near(r.preDamage,e.maxBP*.01*.75*1.005,"Fighter output growth also affects existing source-owned loss on the new round");
        a=T(new CombatAmplificationRules {heroine=true},M("侠女",limit:1),M("侠女"));b=B(a);
        r=b.Next();Check(r.heroineFirst,"First heroine skill records one first-cast layer");Near(r.bondDirectMultiplier,1,"First heroine does not receive its own new layer during that cast");
        b.Next();r=b.Next();Near(r.bondDirectMultiplier,1+.035*2/6,"Next heroine receives the preceding first-cast layer");
        Check(r.heroineFirst&&a.AmplificationBonds.Snapshot().heroineLayers==2,"Each heroine contributes at most one layer");
        b.Next();r=b.Next();Check(!r.heroineFirst&&a.AmplificationBonds.Snapshot().heroineLayers==2,"Repeat heroine skill cannot add another first-cast layer");
        a=T(new CombatAmplificationRules {heroine=true},M("侠女",chance:0));r=B(a).Next();Check(r.normal&&!r.heroineFirst,"Normal fallback is not a heroine first skill");
        a=T(new CombatAmplificationRules {lady=true},M("学生"),M("淑女"),M("淑女"),M("淑女"));
        Near(B(a).Next().bondDirectMultiplier,1+.25*3/7,"Ladies strengthen the first covered position regardless of its identity");
        Check(a.AmplificationBonds.Snapshot().coveredPositions==1,"Three ladies cover one leading position");
        var roster=new List<CombatMember>();for(int i=0;i<7;i++)roster.Add(M("淑女"));
        a=T(new CombatAmplificationRules {lady=true},roster.ToArray());Check(a.AmplificationBonds.Snapshot().coveredPositions==3,"Lady coverage grows with count");
        var expired=M("学生",chance:100);expired.skill.turnLower=1;
        a=T(new CombatAmplificationRules {lady=true},expired,M("学生"),M("淑女"));Near(B(a).Next().bondDirectMultiplier,1,"Uncovered later position is not buffed");
        a=T(new CombatAmplificationRules {lady=true},M("淑女",chance:0));r=B(a).Next();Near(r.bondDirectMultiplier,1,"Lady candidate strengthens skills, not fallback attacks");
        var rules=new CombatAmplificationRules {academy=true};a=T(rules,M("老师"),M("学生",level:20));rules.teacherDamage=100;
        Near(B(a).Next().bondDirectMultiplier,1.03,"Amplification input is snapshotted");
        var summary=a.AmplificationBonds.Snapshot();summary.studentLevels=999;Check(a.AmplificationBonds.Snapshot().studentLevels==20,"Amplification summary is independent");
        foreach(var invalid in new[] {new CombatAmplificationRules {gain=double.NaN},new CombatAmplificationRules {ladyMembersPerSlot=0}})
        {bool rejected=false;try{invalid.Clone();}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid amplification rule rejected "+checks.Count);}
        bool badLevel=false;try{T(new CombatAmplificationRules {academy=true},M("学生",level:31));}catch(ArgumentException){badLevel=true;}
        Check(badLevel,"Academy rejects student levels beyond 30");
    }
}
