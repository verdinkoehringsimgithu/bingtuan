#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    public sealed class EvasionRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-10,name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Evasion scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int count,string identity,bool first)
        {
            var roster=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                var member=new BattleMember {characterName="Probe"+i,baseBP=100000, speed=first?1000:10,
                    traits=new CharacterTraits {personId="probe:"+i,identity=identity}};
                var skill=BattleSkill.CreateDefaultMelee();skill.combat=new CombatSkill {chance=100,mainParam=100,pierce=1};
                member.skills.Add(skill);roster.Add(member);
            }
            return roster;
        }
        private IEnumerator Run()
        {
            var caller=SceneManager.GetActiveScene();
            for(int stage=1;stage<=6;stage++)
            {
                for(int sparse=0;sparse<=1;sparse++)
                {
                    int cap=stage*5,count=sparse==0?cap:(cap-1)/2;
                    var left=Roster(count,"军人",true);
                    var military=new CombatEvasionRules {military=true,militaryHit=10};
                    var ninja=new CombatEvasionRules {ninja=true,ninjaBase=100,ninjaCap=1};
                    var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(cap,"忍者",false),
                        leftEvasionBonds=military,rightEvasionBonds=ninja,autoPlay=false,useSeed=true,seed=stage});
                    military.militaryHit=0;ninja.ninjaBase=0;left[0].traits.identity="probe-mutation";
                    yield return Wait(()=>session.IsReady||session.IsClosed);Check(session.IsReady,"Stage "+stage+" sparse "+sparse+" entered");
                    var presentation=FindObjectOfType<BattleSceneController>().presentation;BattleTurnReport report=null;
                    session.TurnResolved+=r=>report=r;session.Advance();
                    yield return Wait(()=>report!=null&&!presentation.IsPlaybackBusy);
                    var runtime=presentation.battleEngine.Runtime;
                    Check(report.actingTroopId==1,"Stage "+stage+" sparse "+sparse+" expected attacker");
                    Check(runtime.teams[0].EvasionBonds.Snapshot().capacity==cap,"Stage "+stage+" sparse "+sparse+" stage capacity reaches runtime");
                    if(sparse==0)
                    {
                        Check(report.isForcedHit&&!report.isDodge&&!report.isAbsoluteDodge,"Stage "+stage+" forced hit reaches presentation report");
                        Check(report.damageDealt>0&&runtime.teams[1].bp<runtime.teams[1].maxBP,"Stage "+stage+" forced hit delivers actual damage");
                        Check(runtime.teams[1].EvasionBonds.Snapshot().absoluteDodges==0,"Stage "+stage+" forced hit skips absolute evasion");
                    }
                    else
                    {
                        Check(report.isDodge&&report.isAbsoluteDodge&&!report.isForcedHit,"Stage "+stage+" sparse roster cannot bypass half-cap threshold");
                        Check(report.damageDealt==0&&report.healDone==0&&runtime.teams[1].bp==runtime.teams[1].maxBP,"Stage "+stage+" absolute miss delivers no direct damage or healing");
                        Check(runtime.teams[0].uses[0]==1,"Stage "+stage+" absolute miss still spends selected skill use");
                    }
                    session.Leave();yield return Wait(()=>session.IsClosed);
                    Check(session.Result.leftEvasionBonds.capacity==cap,"Stage "+stage+" sparse "+sparse+" result preserves stage capacity");
                    Check(session.Result.leftEvasionBonds.forcedHits==(sparse==0?1:0),"Stage "+stage+" sparse "+sparse+" result event counters");
                    Check(session.Result.rightEvasionBonds.absoluteDodges==sparse,"Stage "+stage+" sparse "+sparse+" result absolute evasion counters");
                    session.Result.leftEvasionBonds.forcedHits=999;
                    Check(runtime.teams[0].EvasionBonds.Snapshot().forcedHits!=999,"Stage "+stage+" sparse "+sparse+" result is independent");
                    Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" sparse "+sparse+" caller retains navigation");
                }
            }
            var grow=new CombatEvasionRules {ninja=true,ninjaBase=0,ninjaCast=.5,ninjaCap=1,countK=0};
            for(int run=0;run<2;run++)
            {
                var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=Roster(5,"忍者",true),right=Roster(5,"学生",false),
                    leftEvasionBonds=grow,autoPlay=false,useSeed=true,seed=23});
                yield return Wait(()=>session.IsReady);var presentation=FindObjectOfType<BattleSceneController>().presentation;
                var state=presentation.battleEngine.Runtime.teams[0].EvasionBonds;
                Near(state.NinjaProbability,0,"Run "+run+" starts without inherited ninja growth");
                session.Advance();yield return Wait(()=>!presentation.IsPlaybackBusy);
                Near(state.NinjaProbability,0,"Run "+run+" cast does not change current-round evasion");
                Near(state.Snapshot().pendingNinja,.5,"Run "+run+" growth is pending after first action");
                session.Advance();yield return Wait(()=>!presentation.IsPlaybackBusy);
                Near(state.NinjaProbability,.5,"Run "+run+" both actions completed before growth becomes active");
                Near(state.Snapshot().pendingNinja,0,"Run "+run+" pending growth committed once");
                session.Leave();yield return Wait(()=>session.IsClosed);
            }
        }
        private IEnumerator Start()
        {
            var stack=new Stack<IEnumerator>();stack.Push(Run());
            while(stack.Count>0)
            {
                bool more=false;object value=null;Exception failure=null;
                try{more=stack.Peek().MoveNext();if(more)value=stack.Peek().Current;}catch(Exception ex){failure=ex;}
                if(failure!=null){Debug.LogException(failure);UnityEditor.EditorApplication.Exit(1);yield break;}
                if(!more){stack.Pop();continue;}if(value is IEnumerator nested){stack.Push(nested);continue;}yield return value;
            }
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_EVASION_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("EVASION_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
