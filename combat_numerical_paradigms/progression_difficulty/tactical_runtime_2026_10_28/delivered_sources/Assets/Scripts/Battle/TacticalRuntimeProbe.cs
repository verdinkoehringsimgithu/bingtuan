#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace LegionBattle.Battle
{
    public sealed class TacticalRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Tactical scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int count,string identity,bool left,double power=0)
        {
            var list=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                var m=new BattleMember {characterName="Probe"+i,level=30,baseBP=10000000,speed=left?1:0,traits=new CharacterTraits {identity=identity}};
                var skill=BattleSkill.CreateDefaultMelee();skill.combat=new CombatSkill {chance=100,mainParam=power,pierce=1};m.skills.Add(skill);list.Add(m);
            }
            return list;
        }
        private IEnumerator Step(BattleSceneSession session,BattleInspectionManager p)
        {session.Advance();yield return Wait(()=>!p.IsPlaybackBusy);}
        private IEnumerator Run()
        {
            Time.timeScale=8;var caller=SceneManager.GetActiveScene();
            for(int stage=1;stage<=6;stage++)
            {
                int n=stage*5;var left=Roster(n,"魔法师",true);left[0].skills[0].combat.limit=1;left[1].skills[0].combat.limit=1;left[2].skills[0].combat.axis="M";
                var rules=new CombatTacticalRules {mage=true};var s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(n,"学生",false),leftTacticalBonds=rules,autoPlay=false,useSeed=true,seed=83});
                rules.mageDamage=100;yield return Wait(()=>s.IsReady);var p=FindObjectOfType<BattleSceneController>().presentation;var a=p.battleEngine.Runtime.teams[0];BattleTurnReport last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Near(last.bondDirectMultiplier,1,"Stage "+stage+" mage starts without a switch");
                yield return Step(s,p);yield return Step(s,p);Check(a.TacticalBonds.Snapshot().mageSame==1,"Stage "+stage+" mage same axis layer");
                yield return Step(s,p);yield return Step(s,p);Near(last.bondDirectMultiplier,1+.04*n/(n+4.0),"Stage "+stage+" mage switch uses snapshotted rule");
                s.Leave();yield return Wait(()=>s.IsClosed);Check(s.Result.leftTacticalBonds.mageSwitches==1,"Stage "+stage+" mage result snapshot");

                left=Roster(n,"帮派",true,100000);left[0].skills[0].combat.turnLower=100;left[0].skills[0].combat.subEffect="四维削弱";left[0].skills[0].combat.subParam=100;
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(n,"学生",false),leftTacticalBonds=new CombatTacticalRules {gang=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];var b=p.battleEngine.Runtime.teams[1];last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Check(last.isNormalAttack&&last.casterMemberIndex==0,"Stage "+stage+" gang presents a normal attack from selected owner");
                Check(a.uses[0]==0&&a.casts[0]==0,"Stage "+stage+" gang preserves original uses and casts");Check(b.statuses.Count==0,"Stage "+stage+" gang strips original effect");
                Near(last.bondDirectMultiplier,1+.65*n/(n+4.0),"Stage "+stage+" gang direct attribution");s.Leave();yield return Wait(()=>s.IsClosed);

                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(n,"猎手",true,100),right=Roster(n,"学生",false),leftTacticalBonds=new CombatTacticalRules {hunter=true,countK=0,hunterFraction=1},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];b=p.battleEngine.Runtime.teams[1];
                yield return Step(s,p);Near(b.bp,b.maxBP,"Stage "+stage+" hunter conversion causes no immediate loss");double scheduled=a.TacticalBonds.Snapshot().hunterScheduled;
                Check(scheduled>0&&b.trueLoss.Count==1,"Stage "+stage+" hunter records deferred pre-defense damage");yield return Step(s,p);yield return Step(s,p);
                Near(b.bp,b.maxBP-scheduled/3,"Stage "+stage+" hunter true loss ticks at next round");s.Leave();yield return Wait(()=>s.IsClosed);

                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(n,"富翁",true),right=Roster(n,"学生",false,100),leftTacticalBonds=new CombatTacticalRules {rich=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Near(last.coinsEarned,1,"Stage "+stage+" rich coins in live report");yield return Step(s,p);Check(a.TacticalBonds.Snapshot().richSaved>0,"Stage "+stage+" rich coins reduce incoming damage");
                s.Leave();yield return Wait(()=>s.IsClosed);Near(s.Result.leftTacticalBonds.coins,1,"Stage "+stage+" rich exports battle-local coins");

                left=Roster(n,"学生",true,100000);var right=Roster(n,"社畜",false);right[0].equipment=new CombatItem {kind="death_lock",value=.1};
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,rightTacticalBonds=new CombatTacticalRules {worker=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;b=p.battleEngine.Runtime.teams[1];yield return Step(s,p);
                Check(b.locks[0]&&b.TacticalBonds.Snapshot().workerProcs==0,"Stage "+stage+" equipment rescue precedes worker");
                yield return Step(s,p);yield return Step(s,p);Check(b.TacticalBonds.Snapshot().workerProcs==1&&!b.Dead,"Stage "+stage+" worker rescues later lethal attack");
                yield return Step(s,p);yield return Step(s,p);Check(b.Dead&&b.TacticalBonds.Snapshot().workerProcs==1,"Stage "+stage+" worker cannot repeat rescue");
                s.Leave();yield return Wait(()=>s.IsClosed);Check(s.Result.rightTacticalBonds.workerProcs==1,"Stage "+stage+" worker result counter");Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller navigation retained");
            }
            Time.timeScale=1;
        }
        private IEnumerator Start()
        {
            var stack=new Stack<IEnumerator>();stack.Push(Run());
            while(stack.Count>0)
            {
                bool more=false;object current=null;Exception error=null;
                try{more=stack.Peek().MoveNext();if(more)current=stack.Peek().Current;}catch(Exception ex){error=ex;}
                if(error!=null){Debug.LogException(error);UnityEditor.EditorApplication.Exit(1);yield break;}
                if(!more){stack.Pop();continue;}if(current is IEnumerator nested){stack.Push(nested);continue;}yield return current;
            }
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_TACTICAL_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("TACTICAL_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
