using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatSupportRules
    {
        public bool scholar,sword;
        public double countK=4,gain=1,scholarChance=.30,swordChance=.50,swordDecay=.50;
        public int scholarRestore=1,swordExtras=3;
        public CombatSupportRules Clone()
        {
            Validate();return new CombatSupportRules {scholar=scholar,sword=sword,countK=countK,gain=gain,scholarChance=scholarChance,
                scholarRestore=scholarRestore,swordChance=swordChance,swordDecay=swordDecay,swordExtras=swordExtras};
        }
        public void Validate()
        {
            foreach(double value in new[] {countK,gain,scholarChance,swordChance,swordDecay})
                if(double.IsNaN(value)||double.IsInfinity(value)||value<0)throw new ArgumentException("Invalid support bond coefficient");
            if(scholarRestore<1||swordExtras<0||swordExtras>3||swordDecay>=1)
                throw new ArgumentException("Support rules require positive restoration, 0..3 extras and decay in [0,1)");
        }
    }
    [Serializable] public sealed class CombatSupportSummary
    {
        public int scholars,swords,scholarChecks,scholarProcs,scholarRestored,swordProcs,swordExtras,maxChain;
    }
    public sealed class CombatSupportState
    {
        private readonly CombatSupportRules rules;
        private readonly string[] identities;
        private readonly int scholars,swords;
        private int scholarChecks,scholarProcs,scholarRestored,swordProcs,swordExtras,maxChain;
        public CombatSupportState(List<CombatMember> roster,CombatSupportRules rules)
        {
            this.rules=(rules??new CombatSupportRules()).Clone();identities=new string[roster.Count];
            for(int i=0;i<roster.Count;i++)
            {
                identities[i]=roster[i].traits==null?null:roster[i].traits.identity;
                if(identities[i]=="学者")scholars++;if(identities[i]=="剑士")swords++;
            }
        }
        private double Value(double coefficient,int count){return coefficient*(count/(count+rules.countK))*rules.gain;}
        internal void AfterAction(CombatTeam team,CombatTeam enemy,int round,CombatAction report,Func<double> random)
        {
            if(report.chainDepth>0&&!report.normal){swordExtras++;maxChain=Math.Max(maxChain,report.chainDepth);}
            if(report.owner<0||!rules.scholar||rules.gain<=0||identities[report.owner]!="学者")return;
            scholarChecks++;
            if(random()>=Math.Min(1,Value(rules.scholarChance,scholars)))return;
            int target=-1,bestRank=int.MaxValue;
            for(int pos=0;pos<team.members.Count;pos++)
            {
                if(pos==report.owner)continue;var skill=team.members[pos].skill;
                if(skill==null||skill.limit<=0||skill.limit>=999||team.uses[pos]<=0||(skill.turnUpper>0&&round>=skill.turnUpper))continue;
                int extra=team.members[pos].item.kind=="extra_use"?(int)team.members[pos].item.value:0;
                bool ready=skill.Eligible(round,team.Percent,enemy.Percent,0,extra);
                bool exhausted=team.uses[pos]>=skill.limit+extra;
                int rank=(ready?0:2)+(exhausted?0:1);
                if(rank<bestRank){bestRank=rank;target=pos;}
            }
            if(target<0)return;
            int amount=Math.Min(rules.scholarRestore,team.uses[target]);team.uses[target]-=amount;
            report.scholarTarget=target;report.scholarRestored=amount;scholarProcs++;scholarRestored+=amount;
        }
        internal int NextSword(CombatTeam team,CombatTeam enemy,int round,CombatAction report,Func<double> random)
        {
            if(!rules.sword||rules.gain<=0||report.normal||report.owner<0||identities[report.owner]!="剑士"||report.chainDepth>=rules.swordExtras)return -1;
            var candidates=new List<int>();
            for(int pos=0;pos<team.members.Count;pos++)
            {
                if(pos==report.owner||identities[pos]!="剑士")continue;
                var skill=team.members[pos].skill;if(skill==null)continue;
                int extra=team.members[pos].item.kind=="extra_use"?(int)team.members[pos].item.value:0;
                if(skill.Eligible(round,team.Percent,enemy.Percent,team.uses[pos],extra))candidates.Add(pos);
            }
            if(candidates.Count==0||random()>=Math.Min(1,Value(rules.swordChance,swords))*Math.Pow(rules.swordDecay,report.chainDepth))return -1;
            int chosen=candidates[Math.Min(candidates.Count-1,(int)(random()*candidates.Count))];swordProcs++;return chosen;
        }
        public CombatSupportSummary Snapshot()
        {
            return new CombatSupportSummary {scholars=scholars,swords=swords,scholarChecks=scholarChecks,scholarProcs=scholarProcs,
                scholarRestored=scholarRestored,swordProcs=swordProcs,swordExtras=swordExtras,maxChain=maxChain};
        }
    }
}
