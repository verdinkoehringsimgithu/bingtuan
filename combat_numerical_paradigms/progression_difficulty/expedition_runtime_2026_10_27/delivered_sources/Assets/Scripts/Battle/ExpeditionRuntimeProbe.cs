#if UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace LegionBattle.Battle
{
    // Batch validation only; not included in players or attached to a saved scene.
    public sealed class ExpeditionRuntimeProbe : MonoBehaviour
    {
        private readonly List<string> checks = new List<string>();
        private void Check(bool condition, string name)
        {
            if (!condition) throw new Exception(name);
            checks.Add(name);
        }
        private void Near(double actual, double expected, string name)
        { Check(Math.Abs(actual-expected) <= 1e-9*Math.Max(1,Math.Abs(expected)), name); }
        private void Reject(Action action, string name)
        {
            bool rejected=false;
            try { action(); } catch (ArgumentException) { rejected=true; }
            Check(rejected,name);
        }
        private static CombatTeam Team(CombatPersistentLimits limits=null, CombatItem item=null)
        {
            return new CombatTeam(new List<CombatMember> { new CombatMember { bp=10000,
                stats=new double[] {100,200,300,400}, item=item??new CombatItem() } },limits);
        }
        private void Numeric()
        {
            var limits=new CombatPersistentLimits {bp=.6,courage=.7,resilience=.8,initiative=.5,magic=.9};
            var team=Team(limits,new CombatItem {bp=2000,stats=new double[] {10,20,30,40}});
            Near(team.UnrestrictedMaxBP,12000,"Unrestricted budget includes equipment");
            Near(team.maxBP,7200,"BP limit applies after equipment");
            Near(team.bp,team.maxBP,"Start full at the reduced cap");
            double[] expected={77,176,165,396};
            for(int i=0;i<4;i++) Near(team.Effective(i),expected[i],"Equipment and persistent stat channel "+i);
            limits.bp=.1;limits.initiative=.1;
            Near(team.maxBP,7200,"Runtime isolates limit input mutation");
            team.stats[2]+=100;
            Near(team.Effective(2),215,"Initiative growth stays subject to persistent limit");
            team.statuses.Add(new CombatStatus {kind="stats",value=.2});
            Near(team.Effective(2),172,"Combat debuff compounds with persistent limit");
            team.statuses.Clear();
            Near(team.Effective(2),215,"Cleanse leaves persistent limit intact");
            Near(team.Heal(99999),0,"Healing cannot exceed the reduced cap");
            team.Macro(2,1);
            Near(team.maxBP,14400,"Encounter macro composes with cap");
            Near(team.UnrestrictedMaxBP,24000,"Unrestricted budget tracks macro separately");
            var fractionalRoster=new List<CombatMember>();
            for(int i=0;i<20;i++)fractionalRoster.Add(new CombatMember {bp=10000,stats=new double[] {0,0,301.0/20,0}});
            var tied=new CombatTeam(fractionalRoster,new CombatPersistentLimits {initiative=.25});
            tied.stats[2]+=3;
            Check(tied.Effective(2)==76,"Fractional equipment aggregation preserves a true initiative tie after growth");
            foreach(double bad in new[] {0,-.1,1.1,double.NaN,double.PositiveInfinity})
                Reject(()=>Team(new CombatPersistentLimits {bp=bad}),"Reject invalid cap "+bad);

            var deal=typeof(CombatRuntime).GetMethod("Deal",BindingFlags.Instance|BindingFlags.NonPublic);
            var victim=Team();victim.absorption=.25;victim.shield=100;
            var runtime=new CombatRuntime(Team(),victim,()=>.99);
            deal.Invoke(runtime,new object[] {victim,1000.0,true});
            Near(victim.DamageReceived,650,"Telemetry excludes absorption and shields");
            victim.Heal(10000);
            deal.Invoke(runtime,new object[] {victim,1000.0,true});
            Near(victim.DamageReceived,1400,"Healing does not erase accumulated damage");
            Near(victim.MinimumBPRatio,.925,"Minimum BP ratio ignores later recovery");
            var locked=Team(item:new CombatItem {kind="death_lock",value=.2});
            runtime=new CombatRuntime(Team(),locked,()=>.99);
            deal.Invoke(runtime,new object[] {locked,20000.0,true});
            Near(locked.bp,2000,"Telemetry preserves lethal recovery behavior");
            Near(locked.DamageReceived,10000,"Telemetry clips overkill before lethal recovery");
            Near(locked.MinimumBPRatio,0,"Lethal recovery cannot hide zero BP trough");
            deal.Invoke(runtime,new object[] {locked,1000.0,false});
            Near(locked.DamageReceived,11000,"Unclamped loss uses the same actual-damage accounting");
            Near(locked.DamageExposure,1,"Exposure saturates while accumulated damage remains exact");
            var negative=Team();runtime=new CombatRuntime(Team(),negative,()=>.99);
            deal.Invoke(runtime,new object[] {negative,20000.0,false});
            deal.Invoke(runtime,new object[] {negative,5000.0,false});
            Near(negative.DamageReceived,10000,"Negative BP never counts additional overkill");

            var state=new ExpeditionState {troopId="probe"};
            var win=new BattleSceneResult {initialized=true,outcome=BattleSceneOutcome.LeftWon};
            Check(state.SettleBattle("battle-1",win,new double[] {.4,.2,0,.5,0}),"First battle settlement accepted");
            Near(state.BattleLimits().bp,.6,"Log wear converts to multiplicative cap");
            Check(!state.SettleBattle("battle-1",win,new double[] {.4,.2,0,.5,0}),"Repeated callback cannot settle twice");
            Check(state.victoriesSinceRest==1,"Duplicate callback cannot advance journey count");
            var before=JsonUtility.ToJson(state);
            Reject(()=>state.SettleBattle("invalid",win,new double[] {.1,0,0,double.NaN,0}),"Invalid loss rejected atomically");
            Check(before==JsonUtility.ToJson(state),"Rejected loss leaves all channels and ledger intact");
            foreach(var outcome in new[] {BattleSceneOutcome.Interrupted,BattleSceneOutcome.Failed,BattleSceneOutcome.Unresolved})
                Check(!state.SettleBattle("ignored",new BattleSceneResult {initialized=true,outcome=outcome},new double[5]),"Ignore unsettled outcome "+outcome);
            Check(!state.SettleBattle("uninitialized",new BattleSceneResult {outcome=BattleSceneOutcome.LeftWon},new double[5]),"Uninitialized result cannot settle");
            state.SettleBattle("battle-2",win,new double[] {.5,0,0,0,0});
            Near(state.BattleLimits().bp,.3,"Successive losses multiply remaining caps");
            Check(state.RestoreMissingCaps("supply-1",new double[] {.5,1,0,0,0}),"Explicit partial supply accepted");
            Near(state.BattleLimits().bp,.65,"Supply restores half of missing cap");
            Near(state.BattleLimits().courage,1,"Targeted supply clears selected stat loss");
            Near(state.BattleLimits().initiative,.5,"Targeted supply leaves other channels intact");
            Check(state.victoriesSinceRest==2,"Supply does not reset journey count");
            var loaded=JsonUtility.FromJson<ExpeditionState>(JsonUtility.ToJson(state));loaded.Validate();
            Check(!loaded.RestoreMissingCaps("supply-1",new double[] {1,1,1,1,1}),"Save and reload preserves idempotency");
            Near(loaded.BattleLimits().bp,.65,"Save and reload preserves cap");
            Check(loaded.Rest("rest-1"),"Explicit rest accepted");
            Check(loaded.victoriesSinceRest==0&&loaded.BattleLimits().bp==1&&loaded.BattleLimits().initiative==1,"Full rest restores caps and journey count");
            Check(!loaded.SettleBattle("battle-1",win,new double[5]),"Rest preserves duplicate protection for old results");
            Check(loaded.ApplyEventLoss("event-1",new double[] {.2,0,.3,0,0}),"Travel event loss accepted");
            Near(loaded.BattleLimits().bp,.8,"Travel event applies BP loss");
            Near(loaded.BattleLimits().resilience,.7,"Travel event applies targeted stat loss");
            Check(loaded.victoriesSinceRest==0&&!loaded.ApplyEventLoss("event-1",new double[5]),"Travel event neither advances victories nor settles twice");
            var lost=new ExpeditionState {troopId="defeat-probe"};
            Check(lost.SettleBattle("lost-battle",new BattleSceneResult {initialized=true,outcome=BattleSceneOutcome.RightWon},new double[5]),"Resolved defeat accepts explicit zero loss");
            Check(lost.victoriesSinceRest==0&&lost.BattleLimits().bp==1,"Defeat invents no loss or victory");
            loaded.settledOperations.Add("battle-1");
            Reject(loaded.Validate,"Corrupt duplicate persisted IDs rejected");
        }
        private IEnumerator Wait(Func<bool> condition)
        {
            double deadline=Time.realtimeSinceStartupAsDouble+45;
            while(!condition())
            { if(Time.realtimeSinceStartupAsDouble>deadline)throw new TimeoutException("Expedition integration timeout"); yield return null; }
        }
        private static List<BattleMember> Roster(int count, bool player)
        {
            var roster=new List<BattleMember>();
            for(int i=0;i<count;i++)
            {
                var member=new BattleMember {characterName="Probe"+i,baseBP=player?20000:10000,
                    speed=player?100:1000,dodge=player?50:0,defense=20,authority=0};
                var skill=BattleSkill.CreateDefaultMelee();
                skill.combat=new CombatSkill {chance=100,mainParam=player?5000:30,pierce=1,baseCrit=1};
                member.skills.Add(skill);roster.Add(member);
            }
            return roster;
        }
        private IEnumerator Scenes()
        {
            var caller=SceneManager.GetActiveScene();
            var state=new ExpeditionState {troopId="scene-probe"};
            for(int stage=1;stage<=6;stage++)
            {
                var limits=new CombatPersistentLimits {bp=.6,courage=.7,resilience=.8,initiative=.5,magic=.9};
                var session=BattleSceneFlow.Enter(new BattleSceneRequest {stage=stage,left=Roster(stage*5,true),right=Roster(stage*5,false),
                    playerLimits=limits,autoPlay=false,useSeed=true,seed=stage});
                limits.bp=.1;limits.initiative=.1;
                yield return Wait(()=>session.IsReady||session.IsClosed);
                Check(session.IsReady,"Stage "+stage+" limited scene entered");
                var engine=FindObjectOfType<BattleSceneController>().presentation.battleEngine;
                Near(engine.Runtime.teams[0].bp,stage*5*20000*.6,"Stage "+stage+" starts full reduced BP");
                Near(engine.Runtime.teams[0].Effective(2),stage*5*100*.5,"Stage "+stage+" snapshots stat limit");
                Near(engine.Runtime.teams[1].maxBP,stage*5*10000,"Stage "+stage+" enemy cap unaffected");
                int settlements=0;
                Action<BattleSceneResult> settle=r=>{if(state.SettleBattle("scene-"+stage,r,new double[] {.1,0,0,0,0}))settlements++;};
                session.Completed+=settle;session.Closed+=settle;
                engine.SimulateFullBattle();yield return Wait(()=>session.Result!=null);
                var result=session.Result;
                Check(result.outcome==BattleSceneOutcome.LeftWon,"Stage "+stage+" probe victory");
                Near(result.leftUnrestrictedMaxBP,stage*5*20000,"Stage "+stage+" result keeps original budget");
                Near(result.leftDamageReceived,engine.Runtime.teams[0].DamageReceived,"Stage "+stage+" result exact cumulative damage");
                Check(result.leftDamageReceived>0&&result.leftMinimumBPRatio<1,"Stage "+stage+" damage and minimum telemetry populated");
                Near(result.leftDamageExposure,Math.Min(1,result.leftDamageReceived/result.leftMaxBP),"Stage "+stage+" exposure denominator is effective cap");
                Check(result.leftBP<result.leftMaxBP,"Stage "+stage+" end result retains actual remaining BP");
                session.Leave();session.Leave();yield return Wait(()=>session.IsClosed);
                Check(settlements==1,"Stage "+stage+" Completed and Closed settle once");
                Check(SceneManager.GetActiveScene()==caller&&BattleSceneFlow.Active==null,"Stage "+stage+" caller scene restored");
            }
            Near(state.BattleLimits().bp,Math.Pow(.9,6),"Six scene settlements compound exactly once");
            var next=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=Roster(5,true),right=Roster(5,false),autoPlay=false,playerLimits=state.BattleLimits()});
            yield return Wait(()=>next.IsReady);
            var nextEngine=FindObjectOfType<BattleSceneController>().presentation.battleEngine;
            Near(nextEngine.Runtime.teams[0].bp,100000*Math.Pow(.9,6),"Next battle refills current effective cap");
            Check(nextEngine.Runtime.teams[0].DamageReceived==0&&nextEngine.Runtime.teams[0].uses[0]==0,"Next battle resets damage and skill counters");
            nextEngine.ExecuteNextTurn();next.Leave();yield return Wait(()=>next.IsClosed);
            Check(next.Result.outcome==BattleSceneOutcome.Interrupted,"Midbattle leave stays interrupted");
            Check(!state.SettleBattle("interrupted-scene",next.Result,new double[] {.5,0,0,0,0}),"Interrupted scene does not mutate travel state");
            var standard=BattleSceneFlow.Enter(new BattleSceneRequest {stage=1,left=Roster(5,true),right=Roster(5,false),autoPlay=false});
            yield return Wait(()=>standard.IsReady);
            Near(FindObjectOfType<BattleSceneController>().presentation.battleEngine.Runtime.teams[0].bp,100000,"Omitted limits keep existing full-budget scene behavior");
            standard.Leave();yield return Wait(()=>standard.IsClosed);
        }
        private IEnumerator Run()
        { Numeric();yield return Scenes(); }
        private IEnumerator Start()
        {
            var stack=new Stack<IEnumerator>();stack.Push(Run());
            while(stack.Count>0)
            {
                bool more=false;object current=null;Exception failure=null;
                try {more=stack.Peek().MoveNext();if(more)current=stack.Peek().Current;} catch(Exception ex) {failure=ex;}
                if(failure!=null)
                { Debug.LogException(failure);UnityEditor.EditorApplication.Exit(1);yield break; }
                if(!more){stack.Pop();continue;}
                if(current is IEnumerator nested){stack.Push(nested);continue;}yield return current;
            }
            string path=Environment.GetEnvironmentVariable("LEGION_EXPEDITION_VALIDATION");
            File.WriteAllText(path,JsonUtility.ToJson(new ProbeResult {passed=true,checks=checks.ToArray()},true));
            Debug.Log("EXPEDITION_RUNTIME_PASSED "+checks.Count);UnityEditor.EditorApplication.Exit(0);
        }
        [Serializable] private sealed class ProbeResult { public bool passed; public string[] checks; }
    }
}
#endif
