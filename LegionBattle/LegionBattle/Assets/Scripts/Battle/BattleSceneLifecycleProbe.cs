#if UNITY_EDITOR
using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    public sealed class BattleSceneLifecycleProbe : MonoBehaviour
    {
        private int checks;
        private Camera callerCamera;
        private Canvas callerCanvas;
        private Renderer callerRenderer;
        private Scene caller;
        private void Check(bool value,string message){if(!value)throw new Exception(message);checks++;}
        private string Signature(BattleSceneController controller)
        {
            string result="";
            foreach(var member in controller.presentation.leftTroop.members)
                result+=member.characterName+":"+member.level+":"+member.dodge+":"+member.defense+":"+member.speed+":"+member.authority+":"+JsonUtility.ToJson(member.skills[0].combat)+";";
            return result;
        }
        private IEnumerator Wait(Func<bool> condition)
        {
            double deadline=Time.realtimeSinceStartupAsDouble+45;
            while(!condition()){if(Time.realtimeSinceStartupAsDouble>deadline)throw new TimeoutException("Battle lifecycle timeout");yield return null;}
        }
        private IEnumerator Start()
        {
            caller=gameObject.scene;callerCamera=Camera.main;callerCanvas=FindObjectOfType<Canvas>();callerRenderer=GameObject.Find("CallerRenderer").GetComponent<Renderer>();
            var stack=new System.Collections.Generic.Stack<IEnumerator>();stack.Push(Run());
            while(stack.Count>0)
            {
                bool more=false;object current=null;Exception failure=null;
                try{more=stack.Peek().MoveNext();if(more)current=stack.Peek().Current;}catch(Exception ex){failure=ex;}
                if(failure!=null){Debug.LogException(failure);UnityEditor.EditorApplication.Exit(1);yield break;}
                if(!more){stack.Pop();continue;}
                if(current is IEnumerator nested){stack.Push(nested);continue;}yield return current;
            }
            string output=Environment.GetEnvironmentVariable("LEGION_SCENE_VALIDATION");
            File.WriteAllText(output,"{\"passed\":true,\"lifecycle_checks\":"+checks+",\"navigation_owner\":\"caller\"}");
            Debug.Log("BATTLE_SCENE_LIFECYCLE_PASSED "+checks);UnityEditor.EditorApplication.Exit(0);
        }
        private IEnumerator Run()
        {
            for(int stage=1;stage<=6;stage++)
            {
                int completed=0,closed=0;var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,autoPlay=false,useSeed=true,seed=stage,topEquipment=true});
                session.Completed+=r=>completed++;session.Closed+=r=>closed++;
                yield return Wait(()=>session.IsReady||session.IsClosed);
                Check(session.IsReady,"Scene entry failed: "+session.Result?.error);
                Check(!callerCamera.enabled&&!callerCanvas.enabled&&!callerRenderer.enabled,"Caller presentation was not isolated");
                var controller=FindObjectOfType<BattleSceneController>();
                Check(controller.presentation.leftTroop.members.Count==stage*5,"Stage roster mismatch");
                controller.presentation.battleEngine.SimulateFullBattle();yield return Wait(()=>session.Result!=null);
                Check(completed==1&&session.Result.rounds<=120,"Completion callback mismatch");session.Leave();session.Leave();
                yield return Wait(()=>session.IsClosed);
                Check(closed==1&&completed==1&&BattleSceneFlow.Active==null,"Duplicate or missing exit callback");
                Check(!SceneManager.GetSceneByName(BattleSceneFlow.SceneName).isLoaded,"Battle scene was not unloaded");
                Check(callerCamera.enabled&&callerCanvas.enabled&&callerRenderer.enabled,"Caller presentation was not restored");
            }
            var early=BattleSceneFlow.Enter(new BattleSceneRequest {autoPlay=false});early.Leave();yield return Wait(()=>early.IsClosed);
            Check(early.Result.outcome==BattleSceneOutcome.Interrupted&&BattleSceneFlow.Active==null,"Early leave leaked a session");
            Check(!early.Result.initialized,"Uninitialized cancellation incorrectly returned a battle snapshot");
            var mid=BattleSceneFlow.Enter(new BattleSceneRequest {autoPlay=false});yield return Wait(()=>mid.IsReady);
            bool duplicateRejected=false;try{BattleSceneFlow.Enter(new BattleSceneRequest());}catch(InvalidOperationException){duplicateRejected=true;}
            Check(duplicateRejected,"Concurrent entry was accepted");
            var active=FindObjectOfType<BattleSceneController>();active.presentation.battleEngine.ExecuteNextTurn();mid.Leave();yield return Wait(()=>mid.IsClosed);
            Check(mid.Result.outcome==BattleSceneOutcome.Interrupted&&mid.Result.leftCasts!=null,"Midbattle result snapshot missing");
            Time.timeScale=20;
            var animated=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,autoPlay=true,useSeed=true,seed=3});
            yield return Wait(()=>animated.Result!=null);Check(animated.Result.outcome!=BattleSceneOutcome.Interrupted,"Automatic battle did not complete");
            animated.Leave();yield return Wait(()=>animated.IsClosed);Time.timeScale=1;
            var database=UnityEditor.AssetDatabase.LoadAssetAtPath<CharacterDatabase>("Assets/Characters/CharacterDatabase.asset");
            var supplied=BattleRosterStrategy.BuildStrategyRoster(database,"输入",1,"C_I",false,false).selected30;
            var opponents=BattleRosterStrategy.BuildStrategyRoster(database,"输入",1,"M_R",false,false).selected30;
            int courage=supplied[0].dodge;double parameter=supplied[0].skills[0].combat.mainParam;
            var external=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=supplied,right=opponents,autoPlay=false,enemyMacro=new CombatMacro {alpha=10,beta=.01}});
            supplied[0].dodge+=5000;supplied[0].skills[0].combat.mainParam=9999;
            yield return Wait(()=>external.IsReady);
            active=FindObjectOfType<BattleSceneController>();Check(active.presentation.leftTroop.members[0].dodge==courage&&active.presentation.leftTroop.members[0].skills[0].combat.mainParam==parameter,"External input was not snapshotted");
            int turns=0;external.TurnResolved+=r=>turns++;external.Advance();yield return Wait(()=>!active.presentation.IsPlaybackBusy);
            Check(turns==1,"Manual action report callback missing");external.Leave();yield return Wait(()=>external.IsClosed);
            foreach(var member in supplied)member.equipment.top=true;
            var invalid=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=supplied,right=opponents,autoPlay=false});yield return Wait(()=>invalid.IsClosed);
            Check(invalid.Result.outcome==BattleSceneOutcome.Failed&&BattleSceneFlow.Active==null&&callerCamera.enabled,"Invalid input did not clean up scene state");
            var custom=SceneManager.CreateScene("CallerChosenDestination");
            var route=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,autoPlay=false});
            route.Closed+=r=>SceneManager.SetActiveScene(custom);yield return Wait(()=>route.IsReady);route.Leave();yield return Wait(()=>route.IsClosed);
            Check(SceneManager.GetActiveScene()==custom,"Battle scene overrode caller navigation");
            SceneManager.SetActiveScene(caller);yield return SceneManager.UnloadSceneAsync(custom);
            Time.timeScale=20;
            yield return SceneManager.LoadSceneAsync(BattleSceneFlow.SceneName,LoadSceneMode.Additive);
            yield return Wait(()=>BattleSceneFlow.Active!=null&&BattleSceneFlow.Active.IsReady);
            var direct=BattleSceneFlow.Active;Check(direct.IsReady,"Direct scene Play did not initialize");
            direct.Leave();yield return Wait(()=>direct.IsClosed);Time.timeScale=1;
            Check(!SceneManager.GetSceneByName(BattleSceneFlow.SceneName).isLoaded,"Direct scene cleanup leaked loaded content");
            var click=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,autoPlay=false});yield return Wait(()=>click.IsReady);
            FindObjectOfType<BattleSceneController>().leaveButton.onClick.Invoke();yield return Wait(()=>click.IsClosed);
            Check(click.Result.outcome==BattleSceneOutcome.Interrupted,"Scene leave button did not close the session");
            string signature=null;
            for(int run=0;run<2;run++)
            {
                var seeded=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,autoPlay=false,useSeed=true,seed=987});yield return Wait(()=>seeded.IsReady);
                string value=Signature(FindObjectOfType<BattleSceneController>());
                if(signature==null)signature=value;else Check(signature==value,"Seed did not reproduce reference roster generation");
                seeded.Leave();yield return Wait(()=>seeded.IsClosed);
            }
            var liveLeft=BattleRosterStrategy.BuildStrategyRoster(database,"输入",1,"C_I",false,false).selected30;
            var liveRight=BattleRosterStrategy.BuildStrategyRoster(database,"输入",1,"M_R",false,false).selected30;
            foreach(var member in liveLeft){member.skills[0].animationId=1001;member.skills[0].combat=new CombatSkill {name=member.skills[0].name,chance=100};}
            foreach(var member in liveRight){member.skills[0].animationId=1001;member.skills[0].combat=new CombatSkill {name=member.skills[0].name,chance=100};}
            var timing=EffectTimingConfig.For(1001);string oldTiming=UnityEngine.JsonUtility.ToJson(timing);
            timing.playOnCaster=false;timing.fps=1;timing.effectStartFrame=0;timing.damageFrame=timing.physicsFrame=0;timing.reactionType=1;
            timing.advanceDuration=.45f;timing.holdDuration=.65f;timing.retreatDuration=.55f;
            var longEffect=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=liveLeft,right=liveRight,autoPlay=false,enemyMacro=new CombatMacro {alpha=10,beta=.01}});
            yield return Wait(()=>longEffect.IsReady);
            active=FindObjectOfType<BattleSceneController>();BattleTurnReport action=null;
            float advanceStarted=Time.time,liveContact=-1;
            longEffect.TurnResolved+=r=>{action=r;liveContact=Time.time;};longEffect.Advance();yield return Wait(()=>action!=null);
            Check(liveContact-advanceStarted>=timing.advanceDuration-.06f&&liveContact-advanceStarted<=timing.advanceDuration+.20f,"Live contact follows configured forward duration");
            var returned=action.actingTroopId==1?active.presentation.LeftSlots:active.presentation.RightSlots;
            var hit=action.actingTroopId==1?active.presentation.RightSlots:active.presentation.LeftSlots;
            Check(action.damageDealt>0&&!action.isDodge,"Live damage synchronization test requires a hit");
            Check(hit[0].DisplayColor!=Color.white,"Live damage cue starts the hit color");
            yield return new WaitForSeconds(.20f);
            Check(active.presentation.IsPlaybackBusy,"Long effect stopped before the hold test");
            Check(Mathf.Abs(Vector3.Distance(returned[0].transform.position,returned[0].BasePosition)-BattlePresentationTimeline.ChargeDistance)<.0001f,"Live attacker does not skip the normal attack hold");
            yield return new WaitForSeconds(timing.holdDuration+timing.retreatDuration*.5f-.20f);
            float halfway=Vector3.Distance(returned[0].transform.position,returned[0].BasePosition);
            Check(halfway>.4f&&halfway<1.2f,"Live return follows the configured duration");
            yield return new WaitForSeconds(timing.retreatDuration*.5f+.10f);
            Check(active.presentation.IsPlaybackBusy,"Long effect stopped before the return test");
            foreach(var member in returned)if(member!=null&&member.CharacterData!=null)
                Check(Vector3.Distance(member.transform.position,member.BasePosition)<.0001f,"Live scene attacker waited for the effect before returning");
            longEffect.Leave();yield return Wait(()=>longEffect.IsClosed);
            timing.fps=4;timing.damageFrame=2;timing.physicsFrame=0;
            timing.advanceDuration=.30f;timing.holdDuration=.50f;timing.retreatDuration=.40f;
            var delayedHit=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=liveLeft,right=liveRight,autoPlay=false,enemyMacro=new CombatMacro {alpha=10,beta=.01}});
            yield return Wait(()=>delayedHit.IsReady);active=FindObjectOfType<BattleSceneController>();action=null;
            var battleCamera=Camera.main;var originalCameraPosition=battleCamera.transform.localPosition;
            delayedHit.TurnResolved+=r=>action=r;delayedHit.Advance();yield return new WaitForSeconds(.45f);
            Check(action==null,"Delayed damage is not published at the earlier physics cue");
            bool allWhite=true;foreach(var member in active.presentation.LeftSlots)if(member!=null&&member.DisplayColor!=Color.white)allWhite=false;
            foreach(var member in active.presentation.RightSlots)if(member!=null&&member.DisplayColor!=Color.white)allWhite=false;
            Check(allWhite,"Earlier physics does not start live hit coloring");
            Check(Vector3.Distance(battleCamera.transform.localPosition,originalCameraPosition)<.0001f,"Earlier physics does not start live shake");
            yield return Wait(()=>action!=null);hit=action.actingTroopId==1?active.presentation.RightSlots:active.presentation.LeftSlots;
            Check(action.damageDealt>0&&!action.isDodge&&hit[0].DisplayColor!=Color.white,"Delayed live damage starts hit coloring after physics");
            Check(Vector3.Distance(battleCamera.transform.localPosition,originalCameraPosition)>.00001f,"Delayed live damage starts camera shake");
            yield return new WaitForSeconds(.45f);
            Check(hit[0].DisplayColor==Color.white&&Vector3.Distance(battleCamera.transform.localPosition,originalCameraPosition)<.0001f,"Live damage coloring and shake return to normal");
            delayedHit.Leave();yield return Wait(()=>delayedHit.IsClosed);UnityEngine.JsonUtility.FromJsonOverwrite(oldTiming,timing);
        }
    }
}
#endif
