using System;
using System.Collections.Generic;

namespace LegionBattle.Battle
{
    [Serializable] public class CombatMacro
    {
        public double alpha=1,beta=1,gamma,delta,theta,mu=1;
    }
    [Serializable] public class BattleSceneRequest
    {
        public int stage=6;
        public List<BattleMember> left,right;
        public string leftName="我方",rightName="敌方",leftFlow="C_I",rightFlow="M_R";
        public bool fixedEncounter=true,maxLevel,topEquipment,autoPlay=true,autoLeave;
        public string difficulty="hard";
        public CombatMacro enemyMacro;
        public CombatPersistentLimits playerLimits;
        public bool useSeed;
        public int seed;
    }
    public enum BattleSceneOutcome { LeftWon,RightWon,Draw,Unresolved,Interrupted,Failed }
    public sealed class BattleSceneResult
    {
        public bool initialized;
        public BattleSceneOutcome outcome;
        public int rounds,winnerTroopId;
        public double leftBP,leftMaxBP,rightBP,rightMaxBP;
        public double leftUnrestrictedMaxBP,rightUnrestrictedMaxBP;
        public double leftDamageReceived,rightDamageReceived,leftMinimumBPRatio,rightMinimumBPRatio;
        public double leftDamageExposure,rightDamageExposure;
        public int[] leftCasts,rightCasts;
        public string error;
    }
    public sealed class BattleSceneSession
    {
        public BattleSceneRequest Request {get;internal set;}
        public BattleSceneResult Result {get;internal set;}
        public bool IsReady {get;internal set;}
        public bool IsClosed {get;internal set;}
        public event Action<BattleSceneSession> Entered;
        public event Action<BattleSceneResult> Completed;
        public event Action<BattleSceneResult> Closed;
        public event Action<BattleTurnReport> TurnResolved;
        public void Leave(){BattleSceneFlow.Leave(this);}
        public void Advance(){BattleSceneFlow.Advance(this);}
        internal void Ready(){IsReady=true;Notify(Entered,this);}
        internal void Complete(BattleSceneResult result){if(Result!=null)return;Result=result;Notify(Completed,result);}
        internal void Close(){if(IsClosed)return;IsClosed=true;Notify(Closed,Result);}
        internal void Report(BattleTurnReport report){Notify(TurnResolved,report);}
        private static void Notify<T>(Action<T> callback,T value)
        {
            if(callback==null)return;
            foreach(Action<T> handler in callback.GetInvocationList())
                try{handler(value);}catch(Exception ex){UnityEngine.Debug.LogException(ex);}
        }
    }
}
