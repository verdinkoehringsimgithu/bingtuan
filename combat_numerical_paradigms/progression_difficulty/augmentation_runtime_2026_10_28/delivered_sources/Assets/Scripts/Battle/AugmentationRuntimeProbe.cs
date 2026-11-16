#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace LegionBattle.Battle
{
    public sealed class AugmentationRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks=new List<string>();
        private void Check(bool value,string name){if(!value)throw new Exception(name);checks.Add(name);}
        private void Near(double value,double expected,string name){Check(Math.Abs(value-expected)<1e-9*Math.Max(1,Math.Abs(expected)),name);}
        private IEnumerator Wait(Func<bool> ready)
        {
            double end=Time.realtimeSinceStartupAsDouble+45;
            while(!ready()){if(Time.realtimeSinceStartupAsDouble>end)throw new TimeoutException("Augmentation scene timeout");yield return null;}
        }
        private static List<BattleMember> Roster(int count,string identity,bool left)
        {
            var list=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                var m=new BattleMember {characterName="Probe"+i,level=30,baseBP=10000000,speed=left?1:0,
                    traits=new CharacterTraits {identity=identity},equipment=new CombatItem {stats=new double[] {0,10,0,0}}};
                var skill=BattleSkill.CreateDefaultMelee();skill.combat=new CombatSkill {chance=100,mainParam=0,pierce=1};m.skills.Add(skill);list.Add(m);
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
                int count=stage*5;double q=count/(count+4.0);var left=Roster(count,"工程师",true);var right=Roster(count,"学生",false);
                var rules=new CombatAugmentationRules {engineer=true};
                var s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,leftAugmentationBonds=rules,autoPlay=false,useSeed=true,seed=83});
                rules.engineerCast=100;left[0].equipment.stats[1]=999;
                yield return Wait(()=>s.IsReady);var p=FindObjectOfType<BattleSceneController>().presentation;var a=p.battleEngine.Runtime.teams[0];var b=p.battleEngine.Runtime.teams[1];
                BattleTurnReport last=null;s.TurnResolved+=r=>last=r;
                double opening=count*10*(1+.25*q);Near(a.stats[1],opening,"Stage "+stage+" engineer equipment and request copied");
                yield return Step(s,p);Near(last.engineerQueued,.035*q,"Stage "+stage+" engineer report pending growth");
                Near(a.stats[1],opening,"Stage "+stage+" engineer keeps current round unchanged");
                yield return Step(s,p);Near(a.stats[1],opening+count*10*.035*q,"Stage "+stage+" engineer end round commit");
                Near(a.AugmentationBonds.Snapshot().pendingEngineer,0,"Stage "+stage+" engineer pending clears once");
                s.Leave();yield return Wait(()=>s.IsClosed);
                Near(s.Result.leftAugmentationBonds.engineerGrowth,.035*q,"Stage "+stage+" engineer result growth");
                s.Result.leftAugmentationBonds.gearStats[1]=999;Near(a.AugmentationBonds.Snapshot().gearStats[1],count*10,"Stage "+stage+" result arrays isolated");

                left=Roster(count,"贤者",true);right=Roster(count,"贤者",false);
                left[0].skills[0].combat.subEffect="四维削弱";left[0].skills[0].combat.subParam=20;left[0].skills[0].combat.duration=3;
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,leftAugmentationBonds=new CombatAugmentationRules {sage=true},rightAugmentationBonds=new CombatAugmentationRules {sage=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;b=p.battleEngine.Runtime.teams[1];
                yield return Step(s,p);Near(b.statuses[0].value,.2*(1+.25*q)*(1-.25*q),"Stage "+stage+" sage outgoing and incoming compose");
                Check(b.statuses[0].turns==3,"Stage "+stage+" sage duration remains native");s.Leave();yield return Wait(()=>s.IsClosed);

                left=Roster(count,"盗贼",true);right=Roster(count,"学生",false);
                foreach(var m in right)m.defense=100;
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,leftAugmentationBonds=new CombatAugmentationRules {thief=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;a=p.battleEngine.Runtime.teams[0];b=p.battleEngine.Runtime.teams[1];last=null;s.TurnResolved+=r=>last=r;
                double target=b.stats[1],own=a.stats[1];yield return Step(s,p);double stolen=target*.015*q;
                Near(last.stolenStats[1],stolen,"Stage "+stage+" thief report actual effective transfer");Near(a.stats[1],own+stolen,"Stage "+stage+" thief receives removed stats");
                Near(b.stats[1],target-stolen,"Stage "+stage+" thief target loses transferred amount");Check(right[0].defense==100,"Stage "+stage+" thief preserves caller budget");
                s.Leave();yield return Wait(()=>s.IsClosed);Near(s.Result.leftAugmentationBonds.stolenStats[1],stolen,"Stage "+stage+" thief result attribution");

                left=Roster(count,"杀手",true);right=Roster(count,"学生",false);right[0].skills[0].combat.mainType="Heal";right[0].skills[0].combat.subParam=.2;
                s=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=left,right=right,leftAugmentationBonds=new CombatAugmentationRules {killer=true},autoPlay=false,useSeed=true,seed=83});
                yield return Wait(()=>s.IsReady);p=FindObjectOfType<BattleSceneController>().presentation;b=p.battleEngine.Runtime.teams[1];last=null;s.TurnResolved+=r=>last=r;
                yield return Step(s,p);Check(last.killerMarked,"Stage "+stage+" killer live hit marks");Near(b.AugmentationBonds.Snapshot().pendingHealPenalty,.6*q,"Stage "+stage+" killer pending next skill");
                b.bp=.5*b.maxBP;yield return Step(s,p);Near(last.appliedHealPenalty,.6*q,"Stage "+stage+" next skill consumes penalty");
                Near(last.healingPrevented,b.maxBP*.2*.6*q,"Stage "+stage+" killer actual recovery request prevented");Near(b.bp,b.maxBP*(.5+.2*(1-.6*q)),"Stage "+stage+" recovery cue final BP");
                Near(b.AugmentationBonds.Snapshot().pendingHealPenalty,0,"Stage "+stage+" consumed penalty clears");
                s.Leave();yield return Wait(()=>s.IsClosed);Near(s.Result.rightAugmentationBonds.healingPrevented,b.maxBP*.2*.6*q,"Stage "+stage+" killer result attributed to affected side");
                Check(SceneManager.GetActiveScene()==caller,"Stage "+stage+" caller retains navigation");
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
            File.WriteAllText(Environment.GetEnvironmentVariable("LEGION_AUGMENTATION_VALIDATION"),JsonUtility.ToJson(new Result {passed=true,checks=checks.ToArray()},true));
            Debug.Log("AUGMENTATION_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class Result {public bool passed;public string[] checks;}
    }
}
#endif
