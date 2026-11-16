#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace LegionBattle.Battle
{
    public sealed class CompoundRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double a,double b,string name){Check(Math.Abs(a-b)<1e-9*Math.Max(1,Math.Abs(b)),name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Compound scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int n,string identity,bool left,double power=0)
        {
            var list=new List<BattleMember>();
            for(int i=0;i<n;i++)
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
                int n=stage*5;double q=n/(n+4.0);var left=Roster(n,"女仆",true,99999);left[0].skills[0].combat.chance=0;left[0].skills[0].combat.limit=1;left[0].skills[0].combat.turnLower=100;left[0].skills[0].combat.selfUpper=1;
                var rules=new CombatCompoundRules {maid=true,maidBudget=.5};
                var s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(n,"学生",false),leftCompoundBonds=rules,autoPlay=false,useSeed=true,seed=83});
                rules.maidHeal=100;rules.maidUnlocks[0]=1;yield return Wait(()=>s.IsReady);var p=FindObjectOfType<BattleSceneController>().presentation;var a=p.battleEngine.Runtime.teams[0];
                a.bp=.5*a.maxBP;double initial=a.stats[2];BattleTurnReport last=null;s.TurnResolved+=r=>last=r;yield return Step(s,p);
                Check(last.maidCast&&!last.isNormalAttack&&last.casterMemberIndex==0,"Stage "+stage+" maid leader bypasses original gates");
                Near(last.healDone,Math.Round(a.maxBP*.08*q*.5),"Stage "+stage+" maid recovery live report");Near(a.stats[2],initial*(1+.025*q*.5),"Stage "+stage+" maid post-cast growth");
                int level=n<10?3:n<16?4:5;Check(a.CompoundBonds.Snapshot().maidLevel==level,"Stage "+stage+" maid component unlock snapshot");
                Check(a.members[0].skill.mainParam==99999&&a.uses[0]==1,"Stage "+stage+" replacement preserves source skill and real cast use");
                if(level==5)Check(a.CompoundBonds.Snapshot().maidTrueRequested>0,"Stage "+stage+" maid unlocked additional true component");
                s.Leave();yield return Wait(()=>s.IsClosed);Check(s.Result.leftCompoundBonds.maidCasts==1,"Stage "+stage+" maid result summary");
                s.Result.leftCompoundBonds.openingStats[2]=999;Near(a.CompoundBonds.Snapshot().openingStats[2],initial,"Stage "+stage+" compound result arrays copied");

                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(n,"农民",true),right=Roster(n,"学生",false),leftCompoundBonds=new CombatCompoundRules {farmer=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];a.bp=.25*a.maxBP;last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Check(last.fruitEvent=="planted"&&a.CompoundBonds.Snapshot().fruitReady==6,"Stage "+stage+" shared fruit starts at round six");
                yield return Step(s,p);yield return Step(s,p);Check(last.fruitEvent=="accelerated"&&a.CompoundBonds.Snapshot().fruitReady==5,"Stage "+stage+" immature attack accelerates fruit");
                yield return Step(s,p);yield return Step(s,p);yield return Step(s,p);yield return Step(s,p);
                Check(last.fruitEvent=="harvested"&&a.CompoundBonds.Snapshot().fruitHarvests==1,"Stage "+stage+" fruit matures and harvests through actual turns");
                Near(last.healDone,Math.Round(a.maxBP*.12*q),"Stage "+stage+" fruit recovery live cue");
                int kinds=q>=.8?4:q>=.6?3:2;Check(a.CompoundBonds.Snapshot().fruitKinds==kinds,"Stage "+stage+" fruit attribute kinds scale with strength");
                Near(a.stats[0],n/4.0*.1*q,"Stage "+stage+" fruit fixed opening mean grows lowest axis");
                s.Leave();yield return Wait(()=>s.IsClosed);Check(s.Result.leftCompoundBonds.fruitReady==-1,"Stage "+stage+" harvested fruit slot is clear in result");

                var right=Roster(n,"学生",false);right[0].equipment=new CombatItem {kind="death_lock",value=1};
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(n,"冒险者",true,100000),right=right,leftCompoundBonds=new CombatCompoundRules {adventurer=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];var b=p.battleEngine.Runtime.teams[1];last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Check(b.bp==b.maxBP&&a.CompoundBonds.Snapshot().adventureCompleted==4,"Stage "+stage+" all crossed bloodlines recorded before death lock");
                Near(last.bondDirectMultiplier,1,"Stage "+stage+" current skill does not use newly completed goals");
                yield return Step(s,p);yield return Step(s,p);Near(last.bondDirectMultiplier,1+4*.06*q,"Stage "+stage+" later adventurer skill uses completed goals");
                s.Leave();yield return Wait(()=>s.IsClosed);Check(s.Result.leftCompoundBonds.adventureCompleted==4,"Stage "+stage+" adventure nodes complete only once");
                Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller navigation retained");
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
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_COMPOUND_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("COMPOUND_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
