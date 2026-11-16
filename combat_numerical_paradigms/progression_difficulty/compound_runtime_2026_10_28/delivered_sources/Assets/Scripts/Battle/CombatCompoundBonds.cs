using System;
using System.Collections.Generic;
namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatCompoundRules
    {
        public bool maid,farmer,adventurer,maidAdditionalTrue=true;
        public double countK=4,gain=1,maidBudget=1,maidAttack=1.8,maidHeal=.08,maidStats=.025,maidDebuff=12,maidCrit=.20,maidTrue=.35;
        public int maidDebuffRounds=2,fruitRipen=5,fruitAccelerate=1;
        public double fruitWait=.15,fruitHeal=.12,fruitStats=.10,adventureDamage=.06;
        public double[] maidUnlocks={.2,.4,.55,.7,.8},fruitUnlocks={0,.4,.6,.8};
        public string[] goals={"enemy_below_100","enemy_below_75","enemy_below_50","enemy_below_25","first_crit","first_dodge"};
        public CombatCompoundRules Clone()
        {
            Validate();return new CombatCompoundRules {maid=maid,farmer=farmer,adventurer=adventurer,maidAdditionalTrue=maidAdditionalTrue,countK=countK,gain=gain,
                maidBudget=maidBudget,maidAttack=maidAttack,maidHeal=maidHeal,maidStats=maidStats,maidDebuff=maidDebuff,maidCrit=maidCrit,maidTrue=maidTrue,
                maidDebuffRounds=maidDebuffRounds,fruitRipen=fruitRipen,fruitAccelerate=fruitAccelerate,fruitWait=fruitWait,fruitHeal=fruitHeal,fruitStats=fruitStats,
                adventureDamage=adventureDamage,maidUnlocks=(double[])maidUnlocks.Clone(),fruitUnlocks=(double[])fruitUnlocks.Clone(),goals=(string[])goals.Clone()};
        }
        public void Validate()
        {
            foreach(double x in new[] {countK,gain,maidBudget,maidAttack,maidHeal,maidStats,maidDebuff,maidCrit,maidTrue,fruitWait,fruitHeal,fruitStats,adventureDamage})
                if(double.IsNaN(x)||double.IsInfinity(x)||x<0)throw new ArgumentException("Invalid compound coefficient");
            if(maidDebuffRounds<1||fruitRipen<1||fruitAccelerate<0||maidUnlocks==null||maidUnlocks.Length!=5||fruitUnlocks==null||fruitUnlocks.Length!=4||goals==null)
                throw new ArgumentException("Invalid compound duration or definition");
            foreach(var array in new[] {maidUnlocks,fruitUnlocks})
                for(int k=0;k<array.Length;k++)if(double.IsNaN(array[k])||double.IsInfinity(array[k])||array[k]<0||array[k]>1||(k>0&&array[k]<array[k-1]))throw new ArgumentException("Invalid compound unlock curve");
            var seen=new HashSet<string>();foreach(string goal in goals)if(!CombatCompoundState.IsEvent(goal)||!seen.Add(goal))throw new ArgumentException("Invalid adventure goal");
        }
    }
    [Serializable] public sealed class CombatFirstEvent {public string key,phase;public int round;}
    [Serializable] public sealed class CombatCompoundSummary
    {
        public int maids,farmers,adventurers,maidOwner=-1,maidLevel,maidCasts,fruitReady=-1,fruitPlanted,fruitAccelerated,fruitHarvests,fruitWait,fruitKinds,adventureCompleted,adventureBoostedCasts;
        public double maidHealRequested,maidStatsTotal,maidTrueRequested,fruitHealRequested;
        public double[] openingStats,fruitStats;
        public CombatFirstEvent[] events;
    }
    public sealed class CombatCompoundState
    {
        private readonly CombatCompoundRules rules;
        private readonly string[] identities;
        private readonly int maids,farmers,adventurers,maidOwner=-1,level;
        private readonly double[] opening,fruitStats=new double[4];
        private readonly int[] axes={0,1,2,3};
        private readonly SortedDictionary<string,CombatFirstEvent> events=new SortedDictionary<string,CombatFirstEvent>(StringComparer.Ordinal);
        private readonly HashSet<string> goals;
        private int round=1,maidCasts,ready=-1,planted,accelerated,harvests,waitTotal,kindsTotal,completed,boosted;
        private double healRequested,statsTotal,trueRequested,fruitRequested;
        public CombatCompoundState(List<CombatMember> roster,double[] stats,CombatCompoundRules config)
        {
            rules=(config??new CombatCompoundRules()).Clone();goals=new HashSet<string>(rules.goals);opening=(double[])stats.Clone();identities=new string[roster.Count];
            for(int k=0;k<roster.Count;k++)
            {
                identities[k]=roster[k].traits==null?null:roster[k].traits.identity;
                if(identities[k]=="女仆"){maids++;if(maidOwner<0)maidOwner=k;}if(identities[k]=="农民")farmers++;if(identities[k]=="冒险者")adventurers++;
            }
            double q=Q(maids);foreach(double unlock in rules.maidUnlocks)if(q>=unlock-1e-12)level++;
            Array.Sort(axes,(a,b)=>opening[a]==opening[b]?a.CompareTo(b):opening[a].CompareTo(opening[b]));
        }
        private double Q(int count){return count==0?0:count/(count+rules.countK);}
        internal static bool IsEvent(string key)
        {
            switch(key){case "enemy_below_100":case "enemy_below_75":case "enemy_below_50":case "enemy_below_25":case "first_crit":case "first_dodge":case "first_hit":case "first_heal":case "first_dot":case "first_debuff":case "first_absolute_dodge":return true;default:return false;}
        }
        internal void BeginRound(int value){round=value;}
        internal bool IsMaidLeader(int owner){return rules.maid&&rules.gain>0&&owner==maidOwner;}
        internal CombatSkill Replace(int owner,CombatSkill original)
        {
            if(!IsMaidLeader(owner))return original;maidCasts++;double strength=Q(maids)*rules.gain*rules.maidBudget;
            return new CombatSkill {name=original.name,axis=original.axis,tier=original.tier,chance=100,mainParam=100*(1+rules.maidAttack*strength),
                subEffect=level>=3?"四维削弱":"",subParam=level>=3?rules.maidDebuff*strength:0,duration=level>=3?rules.maidDebuffRounds:0,
                baseCrit=level>=4?rules.maidCrit*strength:0,pierce=level>=5&&!rules.maidAdditionalTrue?1:0};
        }
        internal void CastRecovery(CombatTeam actor,int owner,CombatAction report)
        {
            if(!IsMaidLeader(owner))return;double amount=actor.maxBP*rules.maidHeal*Q(maids)*rules.gain*rules.maidBudget;
            if(actor.members[owner].item.kind=="skill_heal")amount*=1+actor.members[owner].item.value;
            healRequested+=amount;report.healing+=actor.Heal(amount,true,"maid_heal");report.maidCast=true;
        }
        internal double AdditionalTrue(int owner,double raw)
        {
            if(!IsMaidLeader(owner)||level<5||!rules.maidAdditionalTrue)return 0;
            double amount=raw*rules.maidTrue*Q(maids)*rules.gain*rules.maidBudget;trueRequested+=amount;return amount;
        }
        internal double AdventureMultiplier(int owner)
        {
            if(!rules.adventurer||rules.gain<=0||identities[owner]!="冒险者")return 1;
            if(completed>0)boosted++;return 1+completed*rules.adventureDamage*Q(adventurers)*rules.gain;
        }
        internal void Event(string key,string phase)
        {
            if(events.ContainsKey(key))return;events[key]=new CombatFirstEvent {key=key,round=round,phase=phase};
            if(rules.adventurer&&adventurers>0&&rules.gain>0&&goals.Contains(key))completed++;
        }
        internal void DamageCrossing(double before,double removed,double maximum,string phase)
        {
            double low=Math.Max(0,before-removed);
            foreach(int pct in new[] {100,75,50,25})if(before>=maximum*pct/100&&low<maximum*pct/100)Event("enemy_below_"+pct,phase);
        }
        internal void AfterAction(CombatTeam actor,CombatAction report)
        {
            int owner=report.owner;if(owner<0)return;
            if(rules.farmer&&farmers>0&&rules.gain>0&&identities[owner]=="农民")
            {
                if(ready<0){ready=round+rules.fruitRipen;planted++;report.fruitEvent="planted";}
                else if(round<ready){ready=Math.Max(round,ready-rules.fruitAccelerate);accelerated++;report.fruitEvent="accelerated";}
                else
                {
                    int wait=round-ready;double strength=Q(farmers)*rules.gain*(1+wait*rules.fruitWait),amount=actor.maxBP*rules.fruitHeal*strength;
                    fruitRequested+=amount;report.healing+=actor.Heal(amount,false,"fruit_heal");int kinds=0;foreach(double unlock in rules.fruitUnlocks)if(Q(farmers)>=unlock-1e-12)kinds++;
                    double basis=0;foreach(double stat in opening)basis+=stat;double per=basis/4*rules.fruitStats*strength;
                    for(int k=0;k<kinds;k++){int axis=axes[k];actor.stats[axis]+=per;fruitStats[axis]+=per;}
                    harvests++;waitTotal+=wait;kindsTotal+=kinds;ready=-1;report.fruitEvent="harvested";
                }
            }
            if(!report.normal&&IsMaidLeader(owner)&&level>=2)
                for(int k=0;k<4;k++){double amount=opening[k]*rules.maidStats*Q(maids)*rules.gain*rules.maidBudget;actor.stats[k]+=amount;statsTotal+=amount;}
        }
        public CombatCompoundSummary Snapshot()
        {
            var first=new List<CombatFirstEvent>();foreach(var pair in events)first.Add(new CombatFirstEvent {key=pair.Value.key,round=pair.Value.round,phase=pair.Value.phase});
            return new CombatCompoundSummary {maids=maids,farmers=farmers,adventurers=adventurers,maidOwner=maidOwner,maidLevel=rules.maid&&maids>0&&rules.gain>0?level:0,
                maidCasts=maidCasts,fruitReady=ready,fruitPlanted=planted,fruitAccelerated=accelerated,fruitHarvests=harvests,fruitWait=waitTotal,fruitKinds=kindsTotal,
                adventureCompleted=completed,adventureBoostedCasts=boosted,maidHealRequested=healRequested,maidStatsTotal=statsTotal,maidTrueRequested=trueRequested,
                fruitHealRequested=fruitRequested,openingStats=(double[])opening.Clone(),fruitStats=(double[])fruitStats.Clone(),events=first.ToArray()};
        }
    }
}
