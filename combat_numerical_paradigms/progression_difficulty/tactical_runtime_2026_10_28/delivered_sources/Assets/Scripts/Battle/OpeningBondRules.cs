using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    // First production batch. Coefficients are the existing research candidates, explicitly enabled by callers.
    [Serializable] public sealed class OpeningBondRules
    {
        public bool sailor, merchant;
        public double countK=4, gain=1, sailorCoefficient=.006, merchantCoefficient=.30;
        public OpeningBondRules Clone()
        {
            Validate();
            return new OpeningBondRules {sailor=sailor,merchant=merchant,countK=countK,gain=gain,
                sailorCoefficient=sailorCoefficient,merchantCoefficient=merchantCoefficient};
        }
        public void Validate()
        {
            foreach(double value in new[] {countK,gain,sailorCoefficient,merchantCoefficient})
                if(double.IsNaN(value)||double.IsInfinity(value)||value<0)throw new ArgumentException("Invalid opening bond coefficient");
        }
        internal OpeningBondReport Apply(List<CombatMember> roster, double[] stats)
        {
            Validate();
            var report=new OpeningBondReport();
            var identities=new HashSet<string>(StringComparer.Ordinal);
            int sailors=0,merchants=0;double memberBudget=0;
            foreach(var member in roster)
            {
                string identity=member.traits==null?null:member.traits.identity;
                if(!string.IsNullOrWhiteSpace(identity))identities.Add(identity);
                if(identity=="水手")sailors++;
                if(identity=="行商")merchants++;
                for(int k=0;k<4;k++)memberBudget+=member.stats[k];
            }
            report.distinctIdentities=identities.Count;report.sailors=sailors;report.merchants=merchants;
            if(sailor&&sailors>0&&gain>0)
            {
                double scale=sailorCoefficient*(sailors/(sailors+countK))*gain;
                report.sailorPerStat=memberBudget/roster.Count*identities.Count*scale;
                for(int k=0;k<4;k++)stats[k]+=report.sailorPerStat;
            }
            if(merchant&&merchants>0&&gain>0)
            {
                int low=0;double high=stats[0];
                for(int k=1;k<4;k++){if(stats[k]<stats[low])low=k;high=Math.Max(high,stats[k]);}
                report.merchantAxis=low;
                report.merchantGain=high*(merchantCoefficient*(merchants/(merchants+countK))*gain);
                stats[low]+=report.merchantGain;
            }
            return report;
        }
    }
    [Serializable] public sealed class OpeningBondReport
    {
        public int distinctIdentities,sailors,merchants,merchantAxis=-1;
        public double sailorPerStat,merchantGain;
    }
}
