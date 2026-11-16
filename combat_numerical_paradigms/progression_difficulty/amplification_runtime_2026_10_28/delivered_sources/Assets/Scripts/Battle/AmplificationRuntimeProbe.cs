#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    public sealed class AmplificationRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Amplification scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int count,bool left,bool cult=false)
        {
            var list=new List<BattleMember>();var roles=new[] {"老师","学生","拜火教","格斗家","侠女"};
            for(int i=0;i<count;i++)
            {
                var member=new BattleMember {characterName="Probe"+i,level=i+1,baseBP=100000,speed=left?1000:10,
                    traits=new CharacterTraits {identity=!left?"学生":cult?(i<2?"拜火教":"淑女"):i<5?roles[i]:"淑女"}};
                var skill=BattleSkill.CreateDefaultMelee();skill.combat=new CombatSkill {chance=100,mainParam=left?10:0,pierce=1,
                    limit=left?(cult?1:i<4?1:999):999,tier=cult?(i==0?5:1):1};
                member.skills.Add(skill);list.Add(member);
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
                var left=Roster(stage*5,true);var rules=new CombatAmplificationRules {academy=true,cult=true,fighter=true,heroine=true,lady=true};
                var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=Roster(stage*5,false),leftAmplificationBonds=rules,autoPlay=false,useSeed=true,seed=31});
                rules.teacherDamage=100;left[1].level=30;
                yield return Wait(()=>session.IsReady);var p=FindObjectOfType<BattleSceneController>().presentation;var team=p.battleEngine.Runtime.teams[0];
                Check(team.members[1].level==2&&team.AmplificationBonds.Snapshot().studentLevels==2,"Stage "+stage+" actual levels are snapshotted");
                BattleTurnReport last=null;session.TurnResolved+=r=>last=r;
                yield return Step(session,p);
                int ladies=stage*5-5,coverage=ladies==0?0:(int)Math.Ceiling(ladies/3.0);
                double ladyFactor=ladies==0?1:1+.25*ladies/(ladies+4.0);
                Near(last.bondDirectMultiplier,1.003*ladyFactor,"Stage "+stage+" teacher/lady factors reach live report");
                Near(last.bondOutputMultiplier,1,"Stage "+stage+" first round fighter factor");
                Near(team.AmplificationBonds.Snapshot().studentExperienceMultiplier,1.12,"Stage "+stage+" student experience multiplier");
                for(int owner=1;owner<=4;owner++)
                {
                    yield return Step(session,p);yield return Step(session,p);
                    Check(last.actingTroopId==1&&last.casterMemberIndex==owner,"Stage "+stage+" original owner order "+owner);
                    Near(last.bondOutputMultiplier,1+.005*owner,"Stage "+stage+" fighter grows by round "+owner);
                }
                Check(last.heroineFirst&&team.AmplificationBonds.Snapshot().heroineLayers==1,"Stage "+stage+" heroine first layer is recorded");
                double firstHeroine=4<coverage?ladyFactor:1;
                Near(last.bondDirectMultiplier,firstHeroine,"Stage "+stage+" first heroine does not use its new layer immediately");
                yield return Step(session,p);yield return Step(session,p);
                Check(!last.heroineFirst&&last.casterMemberIndex==4,"Stage "+stage+" repeat heroine does not add a second first layer");
                Near(last.bondDirectMultiplier,firstHeroine*1.007,"Stage "+stage+" later heroine skill benefits from accumulated first layer");
                session.Leave();yield return Wait(()=>session.IsClosed);
                Check(session.Result.leftAmplificationBonds.studentLevels==2&&session.Result.leftAmplificationBonds.heroineLayers==1,"Stage "+stage+" result attribution snapshot");
                session.Result.leftAmplificationBonds.studentLevels=999;Check(team.AmplificationBonds.Snapshot().studentLevels==2,"Stage "+stage+" result does not alias runtime");

                var c=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(stage*5,true,true),right=Roster(stage*5,false),
                    leftAmplificationBonds=new CombatAmplificationRules {cult=true,lady=true},autoPlay=false,useSeed=true,seed=19});
                yield return Wait(()=>c.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;last=null;c.TurnResolved+=r=>last=r;
                yield return Step(c,p);ladies=stage*5-2;ladyFactor=1+.25*ladies/(ladies+4.0);
                Near(last.bondDirectMultiplier,1.035*ladyFactor,"Stage "+stage+" lower cult tier and lady multiply in canonical order");
                var state=p.battleEngine.Runtime.teams[0].AmplificationBonds;
                Check(state.Snapshot().coveredPositions==(int)Math.Ceiling(ladies/3.0),"Stage "+stage+" lady coverage count");
                Check(state.Snapshot().heroineLayers==0,"Stage "+stage+" new fight clears previous heroine state");
                c.Leave();yield return Wait(()=>c.IsClosed);Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller navigation preserved");
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
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_AMPLIFICATION_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("AMPLIFICATION_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
