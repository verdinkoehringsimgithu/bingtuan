using System;
using System.Collections.Generic;
namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatTacticalRules
    {
        public bool mage,hunter,gang,rich,worker;
        public double countK=4,gain=1,magePercent=.04,mageDamage=.04,hunterFraction=.35,gangDamage=.65,richCoin=1,richReduction=.025,richCap=.60,workerRecovery=.20;
        public int hunterRounds=3;
        public CombatTacticalRules Clone()
        {
            Validate();return new CombatTacticalRules {mage=mage,hunter=hunter,gang=gang,rich=rich,worker=worker,countK=countK,gain=gain,
                magePercent=magePercent,mageDamage=mageDamage,hunterFraction=hunterFraction,hunterRounds=hunterRounds,gangDamage=gangDamage,
                richCoin=richCoin,richReduction=richReduction,richCap=richCap,workerRecovery=workerRecovery};
        }
        public void Validate()
        {
            foreach(double x in new[] {countK,gain,magePercent,mageDamage,hunterFraction,gangDamage,richCoin,richReduction,richCap,workerRecovery})
                if(double.IsNaN(x)||double.IsInfinity(x)||x<0)throw new ArgumentException("Invalid tactical coefficient");
            if(hunterRounds<1||richCap>1)throw new ArgumentException("Invalid tactical duration or reduction cap");
        }
    }
    [Serializable] public sealed class CombatTacticalSummary
    {
        public int mages,hunters,gangs,richMembers,workers,mageSame,mageSwitches,gangAttacks,richAttacks,workerProcs;
        public string lastAxis;
        public string[] axes;
        public int[] percentLayers;
        public double hunterScheduled,coins,richSaved;
    }
    public sealed class CombatTrueLoss
    {
        internal double amount;internal int remaining,start,owner;internal CombatTeam source;
    }
    public sealed class CombatTacticalState
    {
        private readonly CombatTacticalRules rules;
        private readonly string[] identities;
        private readonly int mages,hunters,gangs,richMembers,workers;
        private readonly SortedDictionary<string,int> layers=new SortedDictionary<string,int>(StringComparer.Ordinal);
        private string lastAxis;
        private int same,switches,gangAttacks,richAttacks,workerProcs;
        private double scheduled,coins,saved;
        public CombatTacticalState(List<CombatMember> roster,CombatTacticalRules config)
        {
            rules=(config??new CombatTacticalRules()).Clone();identities=new string[roster.Count];
            for(int k=0;k<roster.Count;k++)
            {
                identities[k]=roster[k].traits==null?null:roster[k].traits.identity;
                switch(identities[k]){case "魔法师":mages++;break;case "猎手":hunters++;break;case "帮派":gangs++;break;case "富翁":richMembers++;break;case "社畜":workers++;break;}
            }
        }
        private double Value(double coefficient,int count){return coefficient*count/(count+rules.countK)*rules.gain;}
        internal bool HunterActive {get{return rules.hunter&&hunters>0&&rules.gain>0;}}
        internal bool IsGang(int owner){return rules.gang&&rules.gain>0&&identities[owner]=="帮派";}
        internal double GangAttack(){gangAttacks++;return 1+Value(rules.gangDamage,gangs);}
        internal double ModifySkill(string axis,ref double pierce,ref double critical,ref double sub)
        {
            if(!rules.mage||mages==0||rules.gain<=0)return 1;
            axis=axis??"";int count;layers.TryGetValue(axis,out count);layers[axis]=count;
            if(lastAxis==axis){layers[axis]=++count;same++;}else if(lastAxis!=null)switches++;
            lastAxis=axis;double factor=1+count*Value(rules.magePercent,mages);
            pierce*=factor;critical*=factor;sub*=factor;return 1+switches*Value(rules.mageDamage,mages);
        }
        internal double Convert(CombatTeam actor,CombatTeam enemy,double raw,int round,int owner)
        {
            if(!rules.hunter||hunters==0||rules.gain<=0)return raw;
            double amount=raw*Math.Min(1,Value(rules.hunterFraction,hunters));scheduled+=amount;
            enemy.trueLoss.Add(new CombatTrueLoss {amount=amount/rules.hunterRounds,remaining=rules.hunterRounds,start=round+1,source=actor,owner=owner});
            return raw-amount;
        }
        internal double FilterDamage(double amount)
        {
            if(!rules.rich||richMembers==0||rules.gain<=0)return amount;
            double reduction=Math.Min(rules.richCap,coins*rules.richReduction*rules.gain);saved+=amount*reduction;return amount*(1-reduction);
        }
        internal void Rescue(CombatTeam team)
        {
            if(team.bp>0||!rules.worker||workers==0||rules.gain<=0||workerProcs>0)return;
            workerProcs++;team.bp=1;team.Heal(team.maxBP*Math.Min(1,Value(rules.workerRecovery,workers)),false);
        }
        internal void AfterAction(CombatAction report)
        {
            if(report.owner<0||!rules.rich||rules.gain<=0||identities[report.owner]!="富翁")return;
            double amount=rules.richCoin*rules.gain;coins+=amount;richAttacks++;report.coinsEarned=amount;
        }
        public CombatTacticalSummary Snapshot()
        {
            var axes=new List<string>();var counts=new List<int>();foreach(var pair in layers){axes.Add(pair.Key);counts.Add(pair.Value);}
            return new CombatTacticalSummary {mages=mages,hunters=hunters,gangs=gangs,richMembers=richMembers,workers=workers,mageSame=same,mageSwitches=switches,
                gangAttacks=gangAttacks,richAttacks=richAttacks,workerProcs=workerProcs,lastAxis=lastAxis,axes=axes.ToArray(),percentLayers=counts.ToArray(),hunterScheduled=scheduled,coins=coins,richSaved=saved};
        }
    }
}
