using System;
using System.IO;
using System.Collections.Generic;
using LegionBattle.Battle;

public static class RuntimeInvariantHarness
{
    private static int checks;
    private static void Check(bool condition,string name){if(!condition)throw new Exception(name);checks++;}
    private static CombatMember Member(CombatSkill skill=null,CombatItem item=null,double magic=0,double initiative=100)
    {
        return new CombatMember { bp=10000000, stats=new double[] {0,0,initiative,magic},skill=skill,item=item??new CombatItem() };
    }
    private static CombatTeam Team(params CombatMember[] members){return new CombatTeam(new List<CombatMember>(members));}
    private static CombatRuntime Battle(CombatTeam a,CombatTeam b,int rounds=120){b.attack=.001;return new CombatRuntime(a,b,()=>.99,rounds);}
    public static void Main(string[] args)
    {
        var zero=new CombatSkill {chance=0};var once=new CombatSkill {chance=100,limit=1};
        var a=Team(Member(zero),Member(once));var b=Team(Member(initiative:0));var battle=Battle(a,b);
        var first=battle.Next();Check(first.owner==1&&!first.normal&&a.uses[1]==1,"First eligible owner activates once");
        battle.Next();var next=battle.Next();Check(next.normal&&a.uses[1]==1,"Exhausted skill falls back to normal attack");
        var shared=new CombatSkill {chance=100,limit=1};a=Team(Member(shared),Member(shared));b=Team(Member(initiative:0));battle=Battle(a,b);
        battle.Next();battle.Next();next=battle.Next();Check(next.owner==1&&a.uses[0]==1&&a.uses[1]==1,"Shared template has independent owner limits");
        a=Team(Member(new CombatSkill {chance=100}),Member(new CombatSkill {chance=100},new CombatItem {kind="skill_damage",value=3}));b=Team(Member(initiative:0));double baseline=Battle(a,b).Next().damage;
        a=Team(Member(new CombatSkill {chance=100}),Member(new CombatSkill {chance=100}));b=Team(Member(initiative:0));Check(Math.Abs(Battle(a,b).Next().damage-baseline)<1e-8,"Unselected owner's equipment does not amplify another skill");
        bool rejected=false;try{var roster=new List<CombatMember>();for(int i=0;i<5;i++)roster.Add(Member(item:new CombatItem {top=true}));new CombatTeam(roster);}catch(ArgumentException){rejected=true;}Check(rejected,"Five top items rejected");
        double[] heals=new double[2];for(int i=0;i<2;i++){a=Team(Member(new CombatSkill {chance=100,mainType="Heal",subParam=.1},magic:i*1000));a.bp=a.maxBP*.5;b=Team(Member(initiative:0));heals[i]=Battle(a,b).Next().healing;}
        Check(Math.Abs(heals[0]-heals[1])<1e-8,"Self healing is independent of magic");
        a=Team(Member(new CombatSkill {chance=100,mainType="Heal",subParam=.2},new CombatItem {kind="overheal_shield",value=.5}));b=Team(Member(initiative:0));Battle(a,b).Next();Check(Math.Abs(a.shield-a.maxBP*.1)<1e-8,"Overheal shield uses the selected owner");
        a=Team(Member(new CombatSkill {chance=100,subEffect="虚弱压制",subParam=30,duration=2,limit=1}));b=Team(Member(initiative:0));battle=Battle(a,b);battle.Next();battle.Next();Check(Math.Abs(b.Output()-.7)<1e-12,"Two-round weakness remains after first round");battle.Next();battle.Next();Check(Math.Abs(b.Output()-1)<1e-12,"Weakness expires after full rounds");
        a=Team(Member(new CombatSkill {chance=100,subEffect="最大流失",subParam=.1,duration=2,limit=1}));b=Team(Member(initiative:0));battle=Battle(a,b);battle.Next();battle.Next();next=battle.Next();Check(Math.Abs(next.preDamage-b.maxBP*.1*.75)<1e-8,"Max loss occurs at next round start with resilience reduction");
        a=Team(Member(new CombatSkill {chance=100,mainParam=0}));b=Team(Member(initiative:0));battle=Battle(a,b,1);battle.Next();next=battle.Next();Check(next.censored&&next.winner==-1,"Round cap preserves an unresolved result");
        File.WriteAllText(args[0],"{\"passed\":true,\"invariant_checks\":"+checks+"}");Console.WriteLine(checks+" runtime invariant checks passed.");
    }
}
