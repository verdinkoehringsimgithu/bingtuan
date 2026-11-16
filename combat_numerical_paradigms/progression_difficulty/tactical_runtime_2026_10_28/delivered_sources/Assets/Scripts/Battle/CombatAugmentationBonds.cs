using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatAugmentationRules
    {
        public bool engineer,sage,thief,killer;
        public double countK=4,gain=1,engineerBase=.25,engineerCast=.035,sageOut=.25,sageIn=.25,thiefRate=.015,killerReduction=.60;
        public CombatAugmentationRules Clone()
        {
            Validate();return new CombatAugmentationRules {engineer=engineer,sage=sage,thief=thief,killer=killer,countK=countK,gain=gain,
                engineerBase=engineerBase,engineerCast=engineerCast,sageOut=sageOut,sageIn=sageIn,thiefRate=thiefRate,killerReduction=killerReduction};
        }
        public void Validate()
        {
            foreach(double value in new[] {countK,gain,engineerBase,engineerCast,sageOut,sageIn,thiefRate,killerReduction})
                if(double.IsNaN(value)||double.IsInfinity(value)||value<0)throw new ArgumentException("Invalid augmentation coefficient");
        }
    }
    [Serializable] public sealed class CombatAugmentationSummary
    {
        public int engineers,sages,thieves,killers,engineerSkillCasts,thiefAttacks,killerMarks;
        public double engineerMultiplier=1,engineerGrowth,pendingEngineer,pendingHealPenalty,healingPrevented;
        public double[] gearStats,stolenStats;
    }
    public sealed class CombatAugmentationState
    {
        private readonly CombatAugmentationRules rules;
        private readonly string[] identities;
        private readonly int engineers,sages,thieves,killers;
        private readonly double[] gearStats=new double[4],stolen=new double[4];
        private int engineerSkillCasts,thiefAttacks,killerMarks;
        private double growth,pending,nextHealPenalty,activeRecovery=1,healingPrevented;
        private bool inSkill;
        public CombatAugmentationState(List<CombatMember> roster,CombatAugmentationRules rules)
        {
            this.rules=(rules??new CombatAugmentationRules()).Clone();identities=new string[roster.Count];
            for(int i=0;i<roster.Count;i++)
            {
                identities[i]=roster[i].traits==null?null:roster[i].traits.identity;
                switch(identities[i]){case "工程师":engineers++;break;case "贤者":sages++;break;case "盗贼":thieves++;break;case "杀手":killers++;break;}
            }
            for(int k=0;k<4;k++)
            {
                double explicitStats=0,ownerStats=0;
                foreach(var member in roster)
                {
                    explicitStats+=member.item.stats[k];
                    if(member.item.kind=="owner_stats")ownerStats+=member.stats[k]*member.item.value;
                }
                gearStats[k]=explicitStats+ownerStats;
            }
        }
        private double Value(double coefficient,int count){return coefficient*(count/(count+rules.countK))*rules.gain;}
        private bool EngineerActive {get{return rules.engineer&&engineers>0&&rules.gain>0;}}
        private double EngineerBase {get{return EngineerActive?Value(rules.engineerBase,engineers):0;}}
        public double HealingPrevented {get{return healingPrevented;}}
        internal void ApplyOpening(double[] stats){double factor=EngineerBase;for(int k=0;k<4;k++)stats[k]+=gearStats[k]*factor;}
        internal double ModifyNegative(double sub,CombatAugmentationState enemy)
        {
            double outgoing=rules.sage&&sages>0&&rules.gain>0?Value(rules.sageOut,sages):0;
            double incoming=enemy.rules.sage&&enemy.sages>0&&enemy.rules.gain>0?enemy.Value(enemy.rules.sageIn,enemy.sages):0;
            return sub*(1+outgoing)*Math.Max(0,1-incoming);
        }
        internal void BeginAction(){inSkill=false;activeRecovery=1;}
        internal double BeginSkill(){inSkill=true;double penalty=nextHealPenalty;nextHealPenalty=0;activeRecovery=1-penalty;return penalty;}
        internal void EndAction(){inSkill=false;activeRecovery=1;}
        internal double FilterHealing(double amount)
        {
            if(!inSkill||activeRecovery>=1)return amount;
            healingPrevented+=amount*(1-activeRecovery);return amount*activeRecovery;
        }
        internal void AfterAction(CombatTeam actor,CombatTeam enemy,CombatAction report)
        {
            int owner=report.owner;if(owner<0||rules.gain<=0)return;
            if(EngineerActive&&!report.normal&&identities[owner]=="工程师")
            {double amount=Value(rules.engineerCast,engineers);pending+=amount;engineerSkillCasts++;report.engineerQueued=amount;}
            if(rules.thief&&identities[owner]=="盗贼")
            {
                thiefAttacks++;double rate=Math.Min(1,Value(rules.thiefRate,thieves));report.stolenStats=new double[4];
                for(int k=0;k<4;k++)
                {
                    double amount=Math.Min(enemy.stats[k],Math.Max(0,enemy.Effective(k))*rate);
                    enemy.stats[k]-=amount;actor.stats[k]+=amount;stolen[k]+=amount;report.stolenStats[k]=amount;
                }
            }
            if(rules.killer&&!report.normal&&actor.hit&&identities[owner]=="杀手")
            {
                double reduction=Math.Min(1,Value(rules.killerReduction,killers));
                enemy.AugmentationBonds.nextHealPenalty=Math.Max(enemy.AugmentationBonds.nextHealPenalty,reduction);
                killerMarks++;report.killerMarked=true;
            }
        }
        internal void EndRound(double[] stats)
        {
            if(pending==0)return;
            for(int k=0;k<4;k++)stats[k]+=gearStats[k]*pending;
            growth+=pending;pending=0;
        }
        public CombatAugmentationSummary Snapshot()
        {
            return new CombatAugmentationSummary {engineers=engineers,sages=sages,thieves=thieves,killers=killers,engineerSkillCasts=engineerSkillCasts,
                thiefAttacks=thiefAttacks,killerMarks=killerMarks,engineerMultiplier=1+EngineerBase+growth,engineerGrowth=growth,pendingEngineer=pending,
                pendingHealPenalty=nextHealPenalty,healingPrevented=healingPrevented,gearStats=(double[])gearStats.Clone(),stolenStats=(double[])stolen.Clone()};
        }
    }
}
