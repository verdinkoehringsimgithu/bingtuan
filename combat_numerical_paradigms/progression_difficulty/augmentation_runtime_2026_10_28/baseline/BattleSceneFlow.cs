using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.EventSystems;

namespace LegionBattle.Battle
{
    public static class BattleSceneFlow
    {
        public const string SceneName="BattleScene";
        public static BattleSceneSession Active {get;private set;}
        private static BattleSceneFlowDriver driver;
        public static BattleSceneSession Enter(BattleSceneRequest request)
        {
            if(request==null)throw new ArgumentNullException("request");
            if(Active!=null)throw new InvalidOperationException("A battle session is already open");
            BattleRuntimeCatalogue.Stage(request.stage);
            var snapshot=new BattleSceneRequest {stage=request.stage,left=request.left==null?null:BattleSceneController.Clone(request.left),right=request.right==null?null:BattleSceneController.Clone(request.right),
                leftName=request.leftName,rightName=request.rightName,leftFlow=request.leftFlow,rightFlow=request.rightFlow,fixedEncounter=request.fixedEncounter,
                maxLevel=request.maxLevel,topEquipment=request.topEquipment,autoPlay=request.autoPlay,autoLeave=request.autoLeave,difficulty=request.difficulty,
                useSeed=request.useSeed,seed=request.seed,enemyMacro=request.enemyMacro==null?null:JsonUtility.FromJson<CombatMacro>(JsonUtility.ToJson(request.enemyMacro)),
                playerLimits=request.playerLimits==null?null:request.playerLimits.Clone(),
                leftOpeningBonds=request.leftOpeningBonds==null?null:request.leftOpeningBonds.Clone(),
                rightOpeningBonds=request.rightOpeningBonds==null?null:request.rightOpeningBonds.Clone(),
                leftEvasionBonds=request.leftEvasionBonds==null?null:request.leftEvasionBonds.Clone(),
                rightEvasionBonds=request.rightEvasionBonds==null?null:request.rightEvasionBonds.Clone(),
                leftSupportBonds=request.leftSupportBonds==null?null:request.leftSupportBonds.Clone(),
                rightSupportBonds=request.rightSupportBonds==null?null:request.rightSupportBonds.Clone(),
                leftAmplificationBonds=request.leftAmplificationBonds==null?null:request.leftAmplificationBonds.Clone(),
                rightAmplificationBonds=request.rightAmplificationBonds==null?null:request.rightAmplificationBonds.Clone()};
            var handle=new BattleSceneSession {Request=snapshot};Active=handle;
            driver=new GameObject("BattleSceneFlow").AddComponent<BattleSceneFlowDriver>();
            UnityEngine.Object.DontDestroyOnLoad(driver.gameObject);
            driver.Open(handle,SceneManager.GetActiveScene());return handle;
        }
        internal static BattleSceneSession Adopt(BattleSceneController controller,BattleSceneRequest request)
        {
            if(Active!=null)return Active;
            Active=new BattleSceneSession {Request=request};
            driver=new GameObject("BattleSceneFlow").AddComponent<BattleSceneFlowDriver>();
            UnityEngine.Object.DontDestroyOnLoad(driver.gameObject);
            driver.Adopt(Active,controller);return Active;
        }
        internal static void Leave(BattleSceneSession session)
        {
            if(session==Active && driver!=null)driver.Close();
        }
        internal static void Advance(BattleSceneSession session)
        {
            if(session==Active&&driver!=null)driver.Advance();
        }
        internal static void Release(BattleSceneSession session)
        {
            if(session!=Active)return;
            Active=null;driver=null;
        }
    }
}
