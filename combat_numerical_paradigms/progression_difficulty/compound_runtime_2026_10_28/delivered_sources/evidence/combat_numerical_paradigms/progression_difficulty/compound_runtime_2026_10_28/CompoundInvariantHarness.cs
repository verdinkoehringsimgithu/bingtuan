using System;
using System.IO;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using LegionBattle.Battle;
public static class CompoundInvariantHarness
{
    private static readonly List<string> checks=new List<string>();
    private static void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
    private static void Near(double a,double b,string name){Check(Math.Abs(a-b)<1e-9*Math.Max(1,Math.Abs(b)),name+": "+a+" / "+b);}
    private static CombatMember M(string identity)
    {return new CombatMember {bp=10000000,stats=new double[] {0,0,1,0},traits=new CharacterTraits {identity=identity},skill=new CombatSkill {chance=100,mainParam=0,pierce=1}};}
    private static CombatTeam T(CombatCompoundRules rules,params CombatMember[] members)
    {return new CombatTeam(new List<CombatMember>(members),null,null,null,Math.Max(5,members.Length),null,null,null,null,rules);}
    private static CombatTeam E(){var m=M("学生");m.stats[2]=0;return T(null,m);}
    public static void Main(string[] args)
    {try{Run();File.WriteAllText(args[0],new JavaScriptSerializer().Serialize(new {passed=true,checks}));Console.WriteLine(checks.Count+" compound invariant checks passed");}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.Exit(1);}}
    private static void Run()
    {
        var maid=M("女仆");maid.skill.chance=0;maid.skill.limit=1;maid.skill.turnLower=100;maid.skill.selfUpper=1;maid.skill.mainParam=99999;
        var a=T(new CombatCompoundRules {maid=true},maid);a.uses[0]=99;a.bp=.5*a.maxBP;var battle=new CombatRuntime(a,E(),()=>.99);var r=battle.Next();
        Check(r.maidCast&&!r.normal,"Maid leader bypasses probability, uses, turn and percentage gates");Near(a.uses[0],100,"Unlimited maid keeps real cast accounting");
        Near(r.healing,a.maxBP*.08*.2,"First maid component provides recovery");Near(maid.skill.mainParam,99999,"Maid replacement does not rewrite original skill");
        Check(a.CompoundBonds.Snapshot().maidOwner==0&&a.CompoundBonds.Snapshot().maidLevel==1,"Earliest maid becomes leader at first component");
        foreach(int n in new[] {3,5,10,16})
        {
            var roster=new List<CombatMember>();for(int k=0;k<n;k++)roster.Add(M("女仆"));
            a=new CombatTeam(roster,null,null,null,n,null,null,null,null,new CombatCompoundRules {maid=true});
            Check(a.CompoundBonds.Snapshot().maidLevel==(n==3?2:n==5?3:n==10?4:5),"Maid component candidate unlock count "+n);
        }
        maid=M("女仆");maid.item=new CombatItem {kind="skill_heal",value=.5};a=T(new CombatCompoundRules {maid=true},maid);a.bp=a.maxBP*.5;
        r=new CombatRuntime(a,E(),()=>.99).Next();Near(r.healing,a.maxBP*.08*.2*1.5,"Maid recovery uses its owner's healing equipment");
        var ninja=M("忍者");ninja.stats[2]=0;var enemy=new CombatTeam(new List<CombatMember>{ninja},null,null,new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1});
        var roster3=new List<CombatMember>{M("女仆"),M("女仆"),M("女仆")};a=new CombatTeam(roster3,null,null,null,5,null,null,null,null,new CombatCompoundRules {maid=true});a.bp=.5*a.maxBP;
        double opening=a.stats[2];r=new CombatRuntime(a,enemy,()=>.99).Next();Check(r.absoluteEvaded&&r.healing>0,"Maid cast recovery survives later absolute dodge");
        Near(a.stats[2],opening*(1+.025*3/7.0),"Maid post-cast attributes grow even after missed cast");
        bool observedDodge=false;foreach(var e in enemy.CompoundBonds.Snapshot().events)if(e.key=="first_dodge")observedDodge=true;
        Check(observedDodge,"Defending absolute dodge records the ordinary first-dodge node as well");
        Check(a.CompoundBonds.Snapshot().events.Length>0,"Effective recovery is an observable first event");
        var f0=M("农民");f0.stats=new double[] {40,10,30,20};var f1=M("农民");f1.stats=new double[4];
        a=T(new CombatCompoundRules {farmer=true},f0,f1);a.bp=.1*a.maxBP;var state=a.CompoundBonds;
        state.BeginRound(1);r=new CombatAction {owner=0};state.AfterAction(a,r);Check(r.fruitEvent=="planted"&&state.Snapshot().fruitReady==6,"First farmer attack plants shared five-round fruit");
        state.BeginRound(2);r=new CombatAction {owner=1};state.AfterAction(a,r);Check(r.fruitEvent=="accelerated"&&state.Snapshot().fruitReady==5,"Second farmer accelerates the same shared fruit");
        state.BeginRound(3);state.AfterAction(a,r);state.BeginRound(4);r=new CombatAction {owner=0};state.AfterAction(a,r);
        Check(r.fruitEvent=="harvested"&&state.Snapshot().fruitHarvests==1&&state.Snapshot().fruitReady==-1,"Mature fruit harvest clears shared slot");
        Near(r.healing,a.maxBP*.12/3,"Fruit provides effective recovery");Near(a.stats[1],10+25*.1/3,"Fruit grows the lowest opening attribute");Near(a.stats[0],40,"Locked fruit attribute channels remain unchanged");
        state.BeginRound(5);state.AfterAction(a,new CombatAction {owner=0});state.BeginRound(12);r=new CombatAction {owner=0};state.AfterAction(a,r);
        Near(r.healing,a.maxBP*.12/3*1.3,"Waiting after maturity increases fruit recovery");Near(state.Snapshot().fruitStats[1],25*.1/3*2.3,"Fruit attribute gains use fixed opening basis");
        a=T(new CombatCompoundRules {adventurer=true},M("冒险者"));state=a.CompoundBonds;state.BeginRound(2);state.DamageCrossing(100,80,100,"direct");
        Check(state.Snapshot().adventureCompleted==4,"Single hit can complete all four strictly crossed bloodlines");state.DamageCrossing(100,80,100,"direct");
        Check(state.Snapshot().adventureCompleted==4,"Healing and recrossing cannot repeat completed goals");Near(state.AdventureMultiplier(0),1+4*.06*.2,"Completed goals strengthen later adventurer skills");
        a=T(new CombatCompoundRules {adventurer=true,goals=new[] {"enemy_below_75"}},M("冒险者"));state=a.CompoundBonds;state.DamageCrossing(100,25,100,"direct");
        Check(state.Snapshot().adventureCompleted==0,"Exactly touching a bloodline does not complete strict-below goal");state.Event("first_crit","direct");
        Check(state.Snapshot().adventureCompleted==0,"Observed events outside selected goal packet grant no completion");
        var source=M("冒险者");source.skill.mainParam=100000;var target=M("学生");target.stats[2]=0;target.item=new CombatItem {kind="death_lock",value=1};
        a=T(new CombatCompoundRules {adventurer=true},source);enemy=T(null,target);r=new CombatRuntime(a,enemy,()=>.99).Next();
        Check(enemy.bp==enemy.maxBP&&a.CompoundBonds.Snapshot().adventureCompleted==4,"Bloodline goals record damage before full equipment rescue");
        var snapshot=a.CompoundBonds.Snapshot();snapshot.events[0].round=999;snapshot.openingStats[0]=999;
        Check(a.CompoundBonds.Snapshot().events[0].round==1&&a.CompoundBonds.Snapshot().openingStats[0]==0,"Compound result arrays and event records are copied");
        var input=new CombatCompoundRules {adventurer=true};var cloned=input.Clone();input.goals[0]="first_hit";Check(cloned.goals[0]=="enemy_below_100","Rule goal arrays are cloned");
        var scholar=M("学者");var finite=M("学生");finite.skill.limit=1;maid=M("女仆");maid.skill.limit=1;
        a=new CombatTeam(new List<CombatMember>{maid,scholar,finite},null,null,null,5,new CombatSupportRules {scholar=true,countK=0,scholarChance=1},null,null,null,new CombatCompoundRules {maid=true});
        a.uses[0]=9;a.uses[2]=1;r=new CombatAction {owner=1};a.SupportBonds.AfterAction(a,E(),1,r,()=>0);
        Check(r.scholarTarget==2&&a.uses[0]==9&&a.uses[2]==0,"Smart scholar skips unlimited maid leader and restores finite teammate");
        var killer=M("杀手");killer.stats[2]=100;a=new CombatTeam(new List<CombatMember>{killer},null,null,null,5,null,null,new CombatAugmentationRules {killer=true,countK=0});
        maid=M("女仆");maid.stats[2]=0;enemy=T(new CombatCompoundRules {maid=true},maid);enemy.bp=.5*enemy.maxBP;
        battle=new CombatRuntime(a,enemy,()=>.99);battle.Next();r=battle.Next();
        Near(r.healing,enemy.maxBP*.08*.2*.4,"Killer next-skill penalty applies to maid's independent cast recovery");
        Near(r.healingPrevented,enemy.maxBP*.08*.2*.6,"Maid blocked recovery is recorded exactly once");
        bool bad=false;try{new CombatCompoundRules {goals=new[] {"first_crit","first_crit"}}.Clone();}catch(ArgumentException){bad=true;}Check(bad,"Duplicate adventure goals rejected");
        bad=false;try{new CombatCompoundRules {maidUnlocks=new[] {.2,.1,.5,.7,.8}}.Clone();}catch(ArgumentException){bad=true;}Check(bad,"Unordered compound unlocks rejected");
    }
}
