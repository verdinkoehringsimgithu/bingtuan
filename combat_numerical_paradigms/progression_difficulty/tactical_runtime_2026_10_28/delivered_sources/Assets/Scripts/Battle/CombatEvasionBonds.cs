using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatEvasionRules
    {
        public bool military,ninja;
        public double countK=4,gain=1,militaryHit=.75,ninjaBase=.12,ninjaCast=.025,ninjaCap=.65;
        public CombatEvasionRules Clone()
        {
            Validate();
            return new CombatEvasionRules {military=military,ninja=ninja,countK=countK,gain=gain,
                militaryHit=militaryHit,ninjaBase=ninjaBase,ninjaCast=ninjaCast,ninjaCap=ninjaCap};
        }
        public void Validate()
        {
            foreach(double value in new[] {countK,gain,militaryHit,ninjaBase,ninjaCast,ninjaCap})
                if(double.IsNaN(value)||double.IsInfinity(value)||value<0)throw new ArgumentException("Invalid evasion bond coefficient");
            if(ninjaCap>1)throw new ArgumentException("Absolute evasion cap must be in [0,1]");
        }
    }
    [Serializable] public sealed class CombatEvasionSummary
    {
        public int capacity,military,ninjas,militarySkillChecks,forcedHits,absoluteDodges,ninjaSkillCasts;
        public double militaryRatio,ninjaGrowth,pendingNinja,ninjaProbability;
    }
    public sealed class CombatEvasionState
    {
        private readonly CombatEvasionRules rules;
        private readonly string[] identities;
        private readonly int capacity,military,ninjas;
        private int militarySkillChecks,forcedHits,absoluteDodges,ninjaSkillCasts;
        private double growth,pending;
        public CombatEvasionState(List<CombatMember> roster,int capacity,CombatEvasionRules rules)
        {
            if(capacity<roster.Count||capacity>30)throw new ArgumentException("Member capacity must cover the roster and be at most 30");
            this.capacity=capacity;this.rules=(rules??new CombatEvasionRules()).Clone();
            identities=new string[roster.Count];
            for(int i=0;i<roster.Count;i++)
            {
                identities[i]=roster[i].traits==null?null:roster[i].traits.identity;
                if(identities[i]=="军人")military++;
                if(identities[i]=="忍者")ninjas++;
            }
        }
        private bool NinjaActive {get{return rules.ninja&&ninjas>0&&rules.gain>0;}}
        public double NinjaProbability {get{return NinjaActive?Math.Min(rules.ninjaCap,rules.ninjaBase*(ninjas/(ninjas+rules.countK))*rules.gain+growth):0;}}
        internal bool ForceHit(int owner,Func<double> random)
        {
            if(!rules.military||rules.gain<=0||identities[owner]!="军人"||military/(double)capacity<.5)return false;
            militarySkillChecks++;
            double ratio=military/(double)capacity;
            bool forced=random()<Math.Min(1,rules.militaryHit*(.25+.75*(2*ratio-1))*rules.gain);
            if(forced)forcedHits++;
            return forced;
        }
        internal bool AbsoluteMiss(Func<double> random)
        {
            if(!NinjaActive)return false;
            bool missed=random()<NinjaProbability;
            if(missed)absoluteDodges++;
            return missed;
        }
        internal void AfterAction(int owner,bool skill)
        {
            if(!skill||owner<0||!NinjaActive||identities[owner]!="忍者")return;
            ninjaSkillCasts++;
            pending+=rules.ninjaCast*(ninjas/(ninjas+rules.countK))*rules.gain;
        }
        internal void EndRound(){growth+=pending;pending=0;}
        public CombatEvasionSummary Snapshot()
        {
            return new CombatEvasionSummary {capacity=capacity,military=military,ninjas=ninjas,militaryRatio=military/(double)capacity,
                militarySkillChecks=militarySkillChecks,forcedHits=forcedHits,absoluteDodges=absoluteDodges,ninjaSkillCasts=ninjaSkillCasts,
                ninjaGrowth=growth,pendingNinja=pending,ninjaProbability=NinjaProbability};
        }
    }
}
