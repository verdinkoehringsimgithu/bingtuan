using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;

public static class AugmentationInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name+": "+value+" / "+expected);}
    private static CombatMember M(string id,double chance=100)
    {return new CombatMember {bp=10000000,stats=new double[] {0,0,10000,0},traits=new CharacterTraits {identity=id},skill=new CombatSkill {chance=chance,mainParam=0,pierce=1}};}
    private static CombatTeam T(CombatAugmentationRules rules,params CombatMember[] roster)
    {return new CombatTeam(new List<CombatMember>(roster),null,null,null,Math.Max(5,roster.Length),null,null,rules);}
    private static CombatTeam E(){var m=M("学生");m.stats[2]=0;return T(null,m);}
    private static CombatRuntime B(CombatTeam a,CombatTeam b=null){return new CombatRuntime(a,b??E(),()=>.99);}
    public static void Main(string[] args)
    {try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" augmentation invariant checks passed");}catch(Exception ex){Console.Error.WriteLine(ex.Message);Environment.Exit(1);}}
    private static void Run()
    {
        var engineer=M("工程师");engineer.stats=new double[] {100,200,300,400};
        engineer.item=new CombatItem {kind="owner_stats",value=.5,stats=new double[] {10,20,30,40}};
        var ally=M("学生");ally.stats=new double[] {10,20,30,40};ally.item=new CombatItem {stats=new double[] {2,4,6,8}};
        var a=T(new CombatAugmentationRules {engineer=true},engineer,ally);
        Near(a.AugmentationBonds.Snapshot().gearStats[0],62,"Engineer base includes explicit equipment and owner_stats actual contribution");
        Near(a.stats[0],175.1,"Engineer opening adds only the equipment fraction");
        var battle=B(a);var r=battle.Next();Near(a.stats[0],175.1,"Engineer skill does not apply growth in current round");
        Near(r.engineerQueued,.007,"Engineer queues the candidate growth coefficient");
        battle.Next();Near(a.stats[0],175.534,"Engineer growth commits after both actions");
        Near(a.AugmentationBonds.Snapshot().pendingEngineer,0,"Engineer pending growth commits once");
        Near(engineer.stats[0],100,"Engineer never rewrites character budget");
        var noStats=M("工程师",0);noStats.item=new CombatItem {kind="skill_damage",value=10,bp=1000};a=T(new CombatAugmentationRules {engineer=true},noStats);
        Near(a.maxBP,10001000,"Engineer does not amplify equipment BP");Near(a.stats[2],10000,"Engineer does not reinterpret skill mechanism as attributes");
        r=B(a).Next();Check(r.normal&&a.AugmentationBonds.Snapshot().engineerSkillCasts==0,"Engineer normal fallback has no growth trigger");
        var sage=M("贤者");sage.skill.subEffect="四维削弱";sage.skill.subParam=20;sage.skill.duration=3;
        var target=M("贤者");target.stats[2]=0;
        a=T(new CombatAugmentationRules {sage=true},sage);var e=T(new CombatAugmentationRules {sage=true},target);r=B(a,e).Next();
        Near(e.statuses[0].value,.1995,"Sage outgoing and incoming factors compose before native caps");Check(e.statuses[0].turns==3,"Sage does not silently change duration");
        sage=M("贤者");sage.skill.mainType="Heal";sage.skill.subEffect="当前战力自愈";sage.skill.subParam=.1;
        a=T(new CombatAugmentationRules {sage=true},sage);a.bp=a.maxBP*.5;r=B(a).Next();Near(r.healing,a.maxBP*.05,"Sage does not modify positive self-healing");
        var thief=M("盗贼");target=M("学生");target.stats=new double[] {100,200,300,400};
        e=new CombatTeam(new List<CombatMember>{target},new CombatPersistentLimits {courage=.5,resilience=.25,initiative=.75});
        e.statuses.Add(new CombatStatus {kind="stats",value=.2,turns=5});a=T(new CombatAugmentationRules {thief=true,thiefRate=1,countK=0},thief);
        r=new CombatRuntime(a,e,()=>0).Next();Check(r.missed,"Thief test exercises an attack that missed");
        double[] stolen={40,40,180,320};
        for(int k=0;k<4;k++)Near(r.stolenStats[k],stolen[k],"Thief uses target effective stat channel "+k);
        Near(e.stats[0],60,"Thief subtracts raw target stat by actual transferred amount");Near(a.stats[0],40,"Thief gains exactly the removed raw stat");
        Near(target.stats[0],100,"Thief leaves persistent member budget unchanged");
        var killer=M("杀手");var heal=M("学生");heal.stats[2]=0;heal.skill.mainType="Heal";heal.skill.subParam=.2;
        a=T(new CombatAugmentationRules {killer=true,countK=0},killer);e=T(null,heal);e.bp=e.maxBP*.5;e.regen=.1;battle=B(a,e);
        r=battle.Next();Check(r.killerMarked,"Killer hit queues the next-skill penalty");Near(e.AugmentationBonds.Snapshot().pendingHealPenalty,.6,"Killer candidate reduction queued");
        r=battle.Next();Near(r.appliedHealPenalty,.6,"Next actual skill consumes the queued penalty");
        Near(r.healing,e.maxBP*.08,"Killer reduces skill healing request before its cap");Near(r.healingPrevented,e.maxBP*.12,"Prevented metric is the blocked recovery request");
        Near(e.bp,e.maxBP*.68,"Round macro regeneration remains outside the skill penalty");Near(e.AugmentationBonds.Snapshot().pendingHealPenalty,0,"Consumed penalty is cleared");
        heal=M("学生");heal.stats[2]=0;heal.skill.mainType="Heal";heal.skill.subEffect="当前战力自愈";heal.skill.subParam=.2;
        a=T(new CombatAugmentationRules {killer=true,countK=0},M("杀手"));e=T(null,heal);e.bp=e.maxBP*.5;battle=B(a,e);battle.Next();r=battle.Next();
        Near(r.healing,e.maxBP*.04,"Current-BP healing retains its own basis under killer");Near(r.healingPrevented,e.maxBP*.06,"Current-BP prevented request uses current BP, not max BP");
        target=M("学生",0);target.stats[2]=0;a=T(new CombatAugmentationRules {killer=true,countK=0},M("杀手"));e=T(null,target);battle=B(a,e);battle.Next();r=battle.Next();
        Check(r.normal,"Penalty preservation test uses a fallback normal attack");Near(e.AugmentationBonds.Snapshot().pendingHealPenalty,.6,"Normal attacks do not consume next-skill penalty");
        battle.Next();Near(e.AugmentationBonds.Snapshot().pendingHealPenalty,.6,"Repeated killer marks use maximum, not additive stacking");
        target=M("学生");target.stats[2]=0;a=T(new CombatAugmentationRules {killer=true,countK=0},M("杀手"));e=T(null,target);battle=B(a,e);battle.Next();r=battle.Next();
        Near(r.appliedHealPenalty,.6,"Non-healing skill also consumes next-skill mark");Near(r.healingPrevented,0,"Non-healing skill does not invent prevented recovery");
        target=M("忍者");target.stats[2]=0;e=new CombatTeam(new List<CombatMember>{target},null,null,new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1});
        a=T(new CombatAugmentationRules {killer=true},M("杀手"));r=B(a,e).Next();Check(r.absoluteEvaded&&!r.killerMarked,"Missed killer skill cannot apply its mark");
        var summary=a.AugmentationBonds.Snapshot();summary.stolenStats[0]=999;Check(a.AugmentationBonds.Snapshot().stolenStats[0]==0,"Augmentation result arrays are independent");
        bool rejected=false;try{new CombatAugmentationRules {engineerCast=-1}.Clone();}catch(ArgumentException){rejected=true;}Check(rejected,"Invalid augmentation coefficients rejected");
    }
}
