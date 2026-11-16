using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public sealed class CombatAmplificationRules
    {
        public bool academy,cult,fighter,heroine,lady;
        public double countK=4,gain=1,teacherExperience=.12,teacherDamage=.0015,cultDamage=.035,fighterPerRound=.025,heroinePerLayer=.035,ladyDamage=.25;
        public int ladyMembersPerSlot=3;
        public CombatAmplificationRules Clone()
        {
            Validate();return new CombatAmplificationRules {academy=academy,cult=cult,fighter=fighter,heroine=heroine,lady=lady,countK=countK,gain=gain,
                teacherExperience=teacherExperience,teacherDamage=teacherDamage,cultDamage=cultDamage,fighterPerRound=fighterPerRound,
                heroinePerLayer=heroinePerLayer,ladyDamage=ladyDamage,ladyMembersPerSlot=ladyMembersPerSlot};
        }
        public void Validate()
        {
            foreach(double value in new[] {countK,gain,teacherExperience,teacherDamage,cultDamage,fighterPerRound,heroinePerLayer,ladyDamage})
                if(double.IsNaN(value)||double.IsInfinity(value)||value<0)throw new ArgumentException("Invalid amplification bond coefficient");
            if(ladyMembersPerSlot<1)throw new ArgumentException("Lady position divisor must be positive");
        }
    }
    [Serializable] public sealed class CombatAmplificationSummary
    {
        public int students,teachers,studentLevels,cultists,fighters,heroines,ladies,coveredPositions,heroineLayers,round;
        public double fighterMultiplier=1,studentExperienceMultiplier=1;
    }
    public sealed class CombatAmplificationState
    {
        private readonly CombatAmplificationRules rules;
        private readonly string[] identities;
        private readonly int[] tiers;
        private readonly bool[] heroineUsed;
        private readonly int students,teachers,studentLevels,cultists,fighters,heroines,ladies,coveredPositions;
        private int heroineLayers,round=1;
        public CombatAmplificationState(List<CombatMember> roster,CombatAmplificationRules rules)
        {
            this.rules=(rules??new CombatAmplificationRules()).Clone();identities=new string[roster.Count];tiers=new int[roster.Count];heroineUsed=new bool[roster.Count];
            for(int i=0;i<roster.Count;i++)
            {
                var member=roster[i];identities[i]=member.traits==null?null:member.traits.identity;tiers[i]=member.skill==null?0:member.skill.tier;
                switch(identities[i])
                {
                    case "学生":
                        if(this.rules.academy&&(member.level<1||member.level>30))throw new ArgumentException("Student level must be in 1..30");
                        students++;studentLevels+=member.level;break;
                    case "老师":teachers++;break;
                    case "拜火教":cultists++;break;
                    case "格斗家":fighters++;break;
                    case "侠女":heroines++;break;
                    case "淑女":ladies++;break;
                }
            }
            coveredPositions=ladies==0?0:Math.Min(roster.Count,Math.Max(1,(int)Math.Ceiling(ladies/(double)this.rules.ladyMembersPerSlot)));
        }
        private double Value(double coefficient,int count){return coefficient*(count/(count+rules.countK))*rules.gain;}
        internal void BeginRound(int value){round=value;}
        public double FighterMultiplier {get{return rules.fighter&&fighters>0&&rules.gain>0?1+Value(rules.fighterPerRound,fighters)*Math.Max(0,round-1):1;}}
        internal double ModifyDirect(double direct,int owner)
        {
            if(rules.gain<=0)return direct;
            if(rules.academy&&identities[owner]=="老师")direct*=1+rules.teacherDamage*studentLevels*rules.gain;
            if(rules.cult&&identities[owner]=="拜火教")
            {
                int lower=0;for(int i=0;i<tiers.Length;i++)if(identities[i]=="拜火教"&&tiers[i]>0&&tiers[i]<tiers[owner])lower++;
                direct*=1+rules.cultDamage*lower*rules.gain;
            }
            if(rules.heroine&&identities[owner]=="侠女")direct*=1+heroineLayers*Value(rules.heroinePerLayer,heroines);
            if(rules.lady&&ladies>0&&owner<coveredPositions)direct*=1+Value(rules.ladyDamage,ladies);
            return direct;
        }
        internal bool AfterAction(int owner,bool skill)
        {
            if(owner<0||!skill||!rules.heroine||rules.gain<=0||identities[owner]!="侠女"||heroineUsed[owner])return false;
            heroineUsed[owner]=true;heroineLayers++;return true;
        }
        public CombatAmplificationSummary Snapshot()
        {
            return new CombatAmplificationSummary {students=students,teachers=teachers,studentLevels=studentLevels,cultists=cultists,fighters=fighters,
                heroines=heroines,ladies=ladies,coveredPositions=rules.lady?coveredPositions:0,heroineLayers=heroineLayers,round=round,
                fighterMultiplier=FighterMultiplier,studentExperienceMultiplier=rules.academy?1+rules.teacherExperience*teachers*rules.gain:1};
        }
    }
}
