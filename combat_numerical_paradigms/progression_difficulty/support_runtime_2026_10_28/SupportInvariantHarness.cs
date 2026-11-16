using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public static class SupportInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static CombatMember Member(string id,double chance=100,int limit=999)
    {return new CombatMember {bp=10000000,stats=new double[] {0,0,5000,0},traits=new CharacterTraits {identity=id},skill=new CombatSkill {chance=chance,limit=limit,mainParam=0}};}
    private static CombatTeam Team(CombatSupportRules rules,params CombatMember[] members){return new CombatTeam(new List<CombatMember>(members),null,null,null,Math.Max(5,members.Length),rules);}
    private static CombatTeam Enemy(){var m=Member("学生");m.stats[2]=0;return Team(null,m);}
    private static CombatSupportRules Scholar(){return new CombatSupportRules {scholar=true,scholarChance=100};}
    private static CombatSupportRules Sword(){return new CombatSupportRules {sword=true,swordChance=100,countK=0};}
    private static CombatRuntime Battle(CombatTeam a,CombatTeam b=null,Func<double> rng=null){return new CombatRuntime(a,b??Enemy(),rng??(()=>0));}
    private static CombatTeam ScholarTeam()
    {
        var t=Team(Scholar(),Member("学者"),Member("学生",100,3),Member("剑士",100,1));
        t.uses[1]=t.uses[2]=1;t.casts[2]=7;t.failed[2]=6;return t;
    }
    public static void Main(string[] args)
    {try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" support invariant checks passed");}catch(Exception ex){Console.Error.WriteLine(ex.Message);Environment.Exit(1);}}
    private static void Run()
    {
        var t=ScholarTeam();var r=Battle(t).Next();
        Check(r.scholarTarget==2&&r.scholarRestored==1,"Smart scholar prioritizes an eligible exhausted skill over an earlier partial skill");
        Check(t.uses[2]==0&&t.casts[2]==7&&t.failed[2]==6,"Restoration changes remaining uses, preserving cast history and failed-roll counters");
        t=ScholarTeam();t.members[2].skill.selfUpper=50;r=Battle(t).Next();
        Check(r.scholarTarget==1,"Currently eligible partial skill precedes a gated exhausted skill");
        t=ScholarTeam();t.members[2].item=new CombatItem {kind="extra_use",value=2};r=Battle(t).Next();
        Check(r.scholarTarget==1,"Extra-use equipment participates in exhaustion ranking");
        t=ScholarTeam();t.members[1].skill.limit=999;t.members[2].skill.turnUpper=1;r=Battle(t).Next();
        Check(r.scholarTarget==-1&&r.scholarRestored==0,"Scholar skips unlimited and permanently expired skills");
        t=Team(Scholar(),Member("学者",0),Member("学生",100,1));t.uses[1]=1;r=Battle(t).Next();
        Check(r.normal&&r.scholarTarget==1,"Scholar normal attack can restore a teammate");
        t=ScholarTeam();var e=Enemy();e= new CombatTeam(e.members,null,null,new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1},5);
        e.members[0].traits.identity="忍者"; // Counts are snapshotted, construct again with the intended identity.
        e=new CombatTeam(e.members,null,null,new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1},5);
        r=Battle(t,e).Next();Check(r.absoluteEvaded&&r.scholarTarget==2,"Scholar attack does not require a hit to restore uses");
        t=Team(Scholar(),Member("学者",100,1));r=Battle(t).Next();Check(r.scholarTarget==-1,"Scholar cannot restore itself");
        var s0=Member("剑士");var s1=Member("剑士",0,3);t=Team(Sword(),s0,s1);var battle=Battle(t);
        for(int depth=0;depth<4;depth++)
        {
            r=battle.Next();Check(r.side==0&&r.round==1&&r.chainDepth==depth,"Sword link "+depth+" remains in the same team action and round");
            Check(r.owner==depth%2&&!r.normal,"Sword link "+depth+" selects another sword and uses its complete skill");
            Check(r.hasContinuation==(depth<3),"Sword link "+depth+" continuation marker");
        }
        Check(t.uses[0]==2&&t.uses[1]==2,"Sword recursion consumes each owner's actual skill uses, including zero-chance recipients");
        Check(t.SupportBonds.Snapshot().swordExtras==3&&t.SupportBonds.Snapshot().maxChain==3,"Three extras produce four total skills");
        Check(battle.Next().side==1,"Enemy acts only after all sword links finish");
        t=Team(Sword(),Member("剑士",100,1),Member("剑士",0,1));battle=Battle(t);battle.Next();r=battle.Next();
        Check(!r.hasContinuation&&t.uses[0]==1&&t.uses[1]==1,"Exhausted recipients stop recursion before the global cap");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.members[1].skill.turnLower=1;r=Battle(t).Next();
        Check(!r.hasContinuation,"Sword respects recipient round gates");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.members[0].skill.mainParam=100;t.members[1].skill.enemyUpper=80;
        battle=Battle(t);r=battle.Next();Check(r.hasContinuation,"Recipient BP conditions are evaluated after the preceding hit");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.bp=t.maxBP*.5;t.members[1].skill.mainType="Heal";t.members[1].skill.subParam=.2;
        battle=Battle(t);battle.Next();r=battle.Next();Check(r.healing>0&&t.bp>t.maxBP*.5,"Forced sword skill executes its full healing effect");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.members[1].skill.mainParam=100;t.members[1].skill.subEffect="最大流失";t.members[1].skill.subParam=.01;t.members[1].skill.duration=2;
        t.members[1].item=new CombatItem {kind="cast_ramp",value=.5};e=Enemy();e.maxBP=e.bp=100000000;battle=Battle(t,e);
        battle.Next();var first=battle.Next();battle.Next();var second=battle.Next();
        Check(second.damage>first.damage,"Recursive owner's cast-ramp equipment counts each actual activation");
        Check(e.statuses.Count==2&&first.preDamage==0&&second.preDamage==0,"Each recursive skill applies its own loss effect without ticking it between links");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.members[0].item=new CombatItem {kind="cleanse",value=1};
        t.statuses.Add(new CombatStatus {kind="stats",value=.1,turns=5});t.statuses.Add(new CombatStatus {kind="weak",value=.1,turns=5});
        battle=Battle(t);for(int i=0;i<4;i++)battle.Next();Check(t.statuses.Count==2,"Cleanse keeps its original end-round timing during recursion");
        battle.Next();Check(t.statuses.Count==0,"Earlier recursive casts retain their own cleanse equipment activations");
        t=Team(Sword(),Member("剑士"),Member("剑士",0));t.members[0].skill.mainParam=10000;battle=Battle(t);r=battle.Next();
        Check(r.ended&&!r.hasContinuation&&t.uses[1]==0,"Lethal original skill stops recursion without spending another owner's use");
        var values=new Queue<double>(new[] {0.0,.99,.99,.4,0.0,0.0,.99,.99,.4});
        t=Team(new CombatSupportRules {sword=true,swordChance=.8,countK=0,swordDecay=.5},Member("剑士"),Member("剑士",0));
        battle=Battle(t,null,()=>values.Count>0?values.Dequeue():.99);r=battle.Next();Check(r.hasContinuation,"First sword chance uses the original probability");
        r=battle.Next();Check(!r.hasContinuation,"Next sword chance is reduced by decay");
        var rules=Sword();t=Team(rules,Member("剑士"),Member("剑士",0));rules.swordExtras=0;r=Battle(t).Next();
        Check(r.hasContinuation,"Support rule input is snapshotted");
        var snapshot=t.SupportBonds.Snapshot();snapshot.swordProcs=999;Check(t.SupportBonds.Snapshot().swordProcs!=999,"Support result snapshot is independent");
        foreach(var invalid in new[] {new CombatSupportRules {swordExtras=4},new CombatSupportRules {swordDecay=1},new CombatSupportRules {scholarRestore=0},new CombatSupportRules {gain=double.NaN}})
        {bool rejected=false;try{invalid.Clone();}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid support rules rejected "+checks.Count);}
    }
}
