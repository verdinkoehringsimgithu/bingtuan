#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    public sealed class SupportRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+60;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Support scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int count,bool left,bool sword)
        {
            var result=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                string identity=left?(sword?(i<2?"剑士":"学生"):(i==1?"学者":"学生")):"学生";
                var member=new BattleMember {characterName="Probe"+i,baseBP=100000,speed=left?1000:10,traits=new CharacterTraits {identity=identity}};
                var skill=BattleSkill.CreateDefaultMelee();
                skill.combat=new CombatSkill {chance=left?(sword?(i==0?100:0):(i<2?100:0)):100,mainParam=left?10:0,pierce=1,limit=!sword&&left&&i==0?1:999};
                if(left&&sword&&i==1){skill.combat.mainType="Heal";skill.combat.subParam=.1;skill.combat.limit=2;skill.animationId=1001;}
                member.skills.Add(skill);result.Add(member);
            }
            return result;
        }
        private static int ChainSeed(List<BattleMember> left,List<BattleMember> right,CombatSupportRules rules,int capacity)
        {
            for(int seed=0;seed<512;seed++)
            {
                var a=new BattleTroop(1,"A") {supportBonds=rules,memberCapacity=capacity};a.InitializeFromMembers(left);
                var b=new BattleTroop(2,"B") {memberCapacity=capacity};b.InitializeFromMembers(right);
                var engine=new BattleEngine();engine.InitBattle(a,b,seed);engine.Runtime.teams[0].bp*=.5;
                bool valid=true;
                for(int depth=0;depth<4;depth++)
                {var r=engine.ExecuteNextTurn();if(r.actingTroopId!=1||r.chainDepth!=depth||r.isDodge||r.hasContinuation!=(depth<3)){valid=false;break;}}
                if(valid)return seed;
            }
            throw new Exception("No deterministic four-skill test fixture found");
        }
        private IEnumerator Advance(BattleSceneSession session,BattleInspectionManager presentation)
        {session.Advance();yield return Wait(()=>!presentation.IsPlaybackBusy);}
        private IEnumerator Run()
        {
            Time.timeScale=4;var caller=SceneManager.GetActiveScene();
            for(int stage=1;stage<=6;stage++)
            {
                var left=Roster(stage*5,true,true);var right=Roster(stage*5,false,false);
                var rules=new CombatSupportRules {sword=true,swordChance=3};int seed=ChainSeed(left,right,rules,stage*5);
                var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,leftSupportBonds=rules,autoPlay=false,useSeed=true,seed=seed});
                rules.swordExtras=0;yield return Wait(()=>session.IsReady||session.IsClosed);Check(session.IsReady,"Stage "+stage+" sword scene entered");
                var p=FindObjectOfType<BattleSceneController>().presentation;var runtime=p.battleEngine.Runtime;runtime.teams[0].bp*=.5;p.leftTroop.Synchronize(runtime.teams[0]);
                var reports=new List<BattleTurnReport>();var times=new List<float>();bool busy=true;
                session.TurnResolved+=r=>{reports.Add(r);times.Add(Time.time);busy&=p.IsPlaybackBusy;};
                yield return Advance(session,p);
                Check(reports.Count==4,"Stage "+stage+" one manual action plays all four skills");
                for(int depth=0;depth<4;depth++)
                {
                    Check(reports[depth].chainDepth==depth&&reports[depth].casterMemberIndex==depth%2,"Stage "+stage+" owner/depth "+depth);
                    Check(reports[depth].actingTroopId==1&&reports[depth].round==1,"Stage "+stage+" no enemy interleave "+depth);
                    if(depth>0)Check(times[depth]>times[depth-1],"Stage "+stage+" distinct visual cue "+depth);
                }
                Check(busy,"Stage "+stage+" playback remains busy during all callbacks");
                Check(reports[1].healDone>0&&reports[3].healDone>0,"Stage "+stage+" recursive skills publish their own recovery cues");
                Check(runtime.teams[0].uses[0]==2&&runtime.teams[0].uses[1]==2,"Stage "+stage+" each owner's actual uses consumed");
                Check(runtime.teams[0].SupportBonds.Snapshot().swordExtras==3,"Stage "+stage+" actual extra count");
                var events=reports.Count;yield return Advance(session,p);
                Check(reports.Count==events+1&&reports[events].actingTroopId==2,"Stage "+stage+" enemy acts after the entire chain");
                session.Leave();yield return Wait(()=>session.IsClosed);
                Check(session.Result.leftSupportBonds.swordExtras==3,"Stage "+stage+" result summary");
                Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller navigation preserved");

                var scholar=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(stage*5,true,false),right=Roster(stage*5,false,false),
                    leftSupportBonds=new CombatSupportRules {scholar=true,scholarChance=100},autoPlay=false,useSeed=true,seed=23});
                yield return Wait(()=>scholar.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;runtime=p.battleEngine.Runtime;
                BattleTurnReport last=null;int count=0;scholar.TurnResolved+=r=>{last=r;count++;};
                yield return Advance(scholar,p);yield return Advance(scholar,p);yield return Advance(scholar,p);
                Check(last.casterMemberIndex==1&&last.scholarTarget==0&&last.scholarRestored==1,"Stage "+stage+" scholar restores the exhausted leading skill");
                Check(runtime.teams[0].uses[0]==0&&runtime.teams[0].casts[0]==1,"Stage "+stage+" restoration keeps cast history");
                Check(count==3&&!last.hasContinuation,"Stage "+stage+" restoration does not itself trigger an extra attack");
                yield return Advance(scholar,p);yield return Advance(scholar,p);
                Check(last.actingTroopId==1&&last.casterMemberIndex==0&&runtime.teams[0].casts[0]==2,"Stage "+stage+" restored skill resumes in original order");
                scholar.Leave();yield return Wait(()=>scholar.IsClosed);
                Check(scholar.Result.leftSupportBonds.scholarRestored==1,"Stage "+stage+" scholar result summary");
            }
            var l=Roster(5,true,true);var e=Roster(5,false,false);var chain=new CombatSupportRules {sword=true,swordChance=3};
            var cancel=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=l,right=e,leftSupportBonds=chain,autoPlay=false,useSeed=true,seed=ChainSeed(l,e,chain,5)});
            yield return Wait(()=>cancel.IsReady);var presentation=FindObjectOfType<BattleSceneController>().presentation;int callbacks=0;
            cancel.TurnResolved+=r=>{callbacks++;cancel.Leave();};cancel.Advance();yield return Wait(()=>cancel.IsClosed);
            Check(callbacks==1&&cancel.Result.outcome==BattleSceneOutcome.Interrupted,"Leaving during first cue cancels remaining recursive playback");
            Check(cancel.Result.leftSupportBonds.swordExtras==0&&cancel.Result.leftCasts[1]==0,"Queued recipient is not counted or consumed as an executed attack");
            var fresh=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=l,right=e,leftSupportBonds=chain,autoPlay=false});
            yield return Wait(()=>fresh.IsReady);var state=FindObjectOfType<BattleSceneController>().presentation.battleEngine.Runtime.teams[0];
            Check(state.SupportBonds.Snapshot().swordExtras==0&&state.uses[0]==0,"New scene does not inherit queued recursion or use counters");
            fresh.Leave();yield return Wait(()=>fresh.IsClosed);Time.timeScale=1;
        }
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
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_SUPPORT_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("SUPPORT_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
