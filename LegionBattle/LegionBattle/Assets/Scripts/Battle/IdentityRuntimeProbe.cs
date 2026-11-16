#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    public sealed class IdentityRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name);}
        private List<CombatMember> Members()
        {
            var roster=new List<CombatMember>();
            foreach(string identity in new[] {"水手","水手","行商","学生","老师"})
                roster.Add(new CombatMember {bp=10000,stats=new double[] {100,20,40,10},traits=new CharacterTraits {identity=identity}});
            return roster;
        }
        private void Numeric()
        {
            var rules=new OpeningBondRules {sailor=true,merchant=true};
            var roster=Members();
            roster[0].item=new CombatItem {kind="owner_stats",value=.5,stats=new double[] {2,4,6,8}};
            var baseline=new CombatTeam(roster);
            var enabled=new CombatTeam(roster,new CombatPersistentLimits {magic=.5},rules);
            double water=170.0*4*.006*2/6;
            double merchant=(552+water)*.3/5;
            Near(enabled.OpeningBonds.sailorPerStat,water,"Sailor basis excludes equipment and counts distinct identities");
            Near(enabled.stats[0],552+water,"Sailor added after equipment and owner_stats");
            Near(enabled.stats[3],63+water+merchant,"Merchant uses highest stat after sailor");
            Near(enabled.Effective(3),(63+water+merchant)*.5,"Travel limit applies after opening bonuses");
            Check(enabled.OpeningBonds.merchantAxis==3,"Merchant selects lowest axis before travel limits");
            Near(baseline.stats[3],63,"Existing behavior unchanged with no explicit rule");
            rules.sailorCoefficient=100;roster[0].traits.identity="probe-mutation";
            Near(enabled.stats[0],552+water,"Opening result independent of later config and label edits");
            var tieRoster=new List<CombatMember> {new CombatMember {bp=10000,stats=new double[] {20,20,20,20},traits=new CharacterTraits {identity="行商"}}};
            var tie=new CombatTeam(tieRoster,null,new OpeningBondRules {merchant=true});
            Check(tie.OpeningBonds.merchantAxis==0,"Lowest-stat ties use C/R/I/M stable order");
            var unknown=Members();unknown[2].traits=null;unknown[3].traits=new CharacterTraits();
            var partial=new CombatTeam(unknown,null,new OpeningBondRules {sailor=true});
            Check(partial.OpeningBonds.distinctIdentities==2,"Unmarked identity is not a new identity");
            foreach(var member in tieRoster)member.traits.identity="农民";
            var absent=new CombatTeam(tieRoster,null,new OpeningBondRules {merchant=true,sailor=true});
            Near(absent.stats[0],20,"Rule without corresponding members has no effect");
            bool rejected=false;try{new OpeningBondRules {gain=double.NaN}.Clone();}catch(ArgumentException){rejected=true;}
            Check(rejected,"Invalid coefficients rejected");
        }
        private static List<BattleMember> Roster(int count,bool player)
        {
            var result=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                var member=new BattleMember {characterName="Probe"+i,baseBP=player?20000:10000,dodge=50,defense=20,speed=player?100:1000,
                    traits=new CharacterTraits {personId="probe:"+i,identity=i%3==0?"水手":i%3==1?"行商":"学生",race="人类",gender="无"}};
                var skill=BattleSkill.CreateDefaultMelee();skill.combat=new CombatSkill {chance=100,mainParam=player?5000:30,pierce=1,baseCrit=1};
                member.skills.Add(skill);result.Add(member);
            }
            return result;
        }
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Identity scene timeout");yield return null;}
        }
        private IEnumerator Scenes()
        {
            var caller=SceneManager.GetActiveScene();
            for(int stage=1;stage<=6;stage++)
            {
                var left=Roster(stage*5,true);var rules=new OpeningBondRules {sailor=true,merchant=true};
                double budget=170,water=budget*3*.006*Math.Ceiling(stage*5/3.0)/(Math.Ceiling(stage*5/3.0)+4);
                var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(stage*5,false),autoPlay=false,useSeed=true,seed=stage,
                    playerLimits=new CombatPersistentLimits {bp=.6,magic=.5},leftOpeningBonds=rules});
                left[0].traits.identity="probe-mutation";rules.gain=100;
                yield return Wait(()=>session.IsReady||session.IsClosed);Check(session.IsReady,"Stage "+stage+" entered");
                var runtime=FindObjectOfType<BattleSceneController>().presentation.battleEngine.Runtime;
                var team=runtime.teams[0];
                Near(team.OpeningBonds.sailorPerStat,water,"Stage "+stage+" snapshots labels and config");
                Near(team.stats[0],stage*5*50+water,"Stage "+stage+" opening bonus applied once");
                Near(team.bp,stage*5*20000*.6,"Stage "+stage+" travel cap preserved");
                Near(runtime.teams[1].stats[0],stage*5*50,"Stage "+stage+" enemy rule remains independent");
                Check(session.Request.left[0].traits.identity=="水手","Stage "+stage+" input label snapshot");
                FindObjectOfType<BattleSceneController>().presentation.battleEngine.SimulateFullBattle();
                yield return Wait(()=>session.Result!=null);
                Near(team.stats[0],stage*5*50+water,"Stage "+stage+" no repeated opening growth during rounds");
                Near(session.Result.leftOpeningBonds.sailorPerStat,water,"Stage "+stage+" result reports opening attribution");
                session.Result.leftOpeningBonds.sailorPerStat=999;
                Near(team.OpeningBonds.sailorPerStat,water,"Stage "+stage+" result does not alias runtime report");
                session.Leave();yield return Wait(()=>session.IsClosed);
                Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller retains navigation");
            }
        }
        private IEnumerator Run(){Numeric();yield return Scenes();}
        private IEnumerator Start()
        {
            var stack=new Stack<IEnumerator>();stack.Push(Run());
            while(stack.Count>0)
            {
                bool more=false;object value=null;Exception error=null;
                try{more=stack.Peek().MoveNext();if(more)value=stack.Peek().Current;}catch(Exception ex){error=ex;}
                if(error!=null){Debug.LogException(error);UnityEditor.EditorApplication.Exit(1);yield break;}
                if(!more){stack.Pop();continue;}if(value is IEnumerator nested){stack.Push(nested);continue;}yield return value;
            }
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_IDENTITY_RUNTIME_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("IDENTITY_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
