using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace LegionBattle.Battle
{
    public sealed class BattleSceneController : MonoBehaviour
    {
        public BattleInspectionManager presentation;
        public Button leaveButton;
        public Text resultText;
        public BattleSceneRequest directPlayRequest=new BattleSceneRequest();
        private BattleSceneSession session;
        private bool started;
        private void Awake()
        {
            if(presentation!=null)presentation.productionMode=true;
            var effectObject=new GameObject("BattleEffects");
            SceneManager.MoveGameObjectToScene(effectObject,gameObject.scene);effectObject.transform.SetParent(transform,false);
            BattleEffectPlayer.BindSceneInstance(effectObject.AddComponent<BattleEffectPlayer>());
            if(leaveButton!=null){leaveButton.onClick.RemoveAllListeners();leaveButton.onClick.AddListener(LeaveBattle);}
            if(resultText!=null)resultText.gameObject.SetActive(false);
        }
        private void Start()
        {
            if(started||BattleSceneFlow.Active!=null)return;
            // Unity serializes unassigned inline lists as empty lists in a scene.
            if(directPlayRequest.left!=null&&directPlayRequest.left.Count==0)directPlayRequest.left=null;
            if(directPlayRequest.right!=null&&directPlayRequest.right.Count==0)directPlayRequest.right=null;
            BattleSceneFlow.Adopt(this,directPlayRequest);
        }
        public void Begin(BattleSceneSession handle)
        {
            if(started)throw new InvalidOperationException("Battle scene was already initialized");
            if(presentation==null)throw new InvalidOperationException("Battle presentation is not configured");
            session=handle;var request=session.Request;var rule=BattleRuntimeCatalogue.Stage(request.stage);
            List<BattleMember> left,right;
            var randomState=UnityEngine.Random.state;
            if(request.useSeed)UnityEngine.Random.InitState(request.seed);
            try
            {
                left=request.left??BattleRosterStrategy.BuildStrategyRoster(presentation.Database,request.leftName,request.stage,request.leftFlow,request.maxLevel,request.topEquipment).selected30;
                right=request.right??(request.fixedEncounter?BattleRosterStrategy.BuildEncounterRoster(presentation.Database,request.stage,request.difficulty):
                    BattleRosterStrategy.BuildStrategyRoster(presentation.Database,request.rightName,request.stage,request.rightFlow,request.maxLevel,request.topEquipment)).selected30;
            }
            finally{if(request.useSeed)UnityEngine.Random.state=randomState;}
            if(left.Count>rule.members||right.Count>rule.members)throw new ArgumentException("Roster exceeds the stage member cap");
            CombatMacro macro=request.enemyMacro;
            if(request.right==null&&request.fixedEncounter)
            {var enemy=BattleRuntimeCatalogue.Encounter(request.stage,request.difficulty);macro=new CombatMacro {alpha=enemy.alpha,beta=enemy.beta};}
            presentation.StartBattleFromRosters(Clone(left),Clone(right),macro,request.useSeed?(int?)request.seed:null,request.leftName,request.rightName,request.playerLimits,request.leftOpeningBonds,request.rightOpeningBonds,request.leftEvasionBonds,request.rightEvasionBonds,rule.members,request.leftSupportBonds,request.rightSupportBonds,request.leftAmplificationBonds,request.rightAmplificationBonds,request.leftAugmentationBonds,request.rightAugmentationBonds,request.leftTacticalBonds,request.rightTacticalBonds,request.leftCompoundBonds,request.rightCompoundBonds);
            presentation.battleEngine.OnTurnCompleted+=session.Report;
            started=true;session.Ready();
            if(request.autoPlay&&session.Result==null)StartCoroutine(Play());
        }
        internal static List<BattleMember> Clone(List<BattleMember> source)
        {
            var copy=new List<BattleMember>();
            foreach(var m in source)
            {
                if(m==null)throw new ArgumentException("Null battle member");
                var member=new BattleMember {memberIndex=copy.Count,characterName=m.characterName,rarityTier=m.rarityTier,level=m.level,baseBP=m.baseBP,
                    dodge=m.dodge,defense=m.defense,speed=m.speed,authority=m.authority,sheetData=m.sheetData,
                    levelOneStats=m.levelOneStats==null?null:(int[])m.levelOneStats.Clone(),levelThirtyStats=m.levelThirtyStats==null?null:(int[])m.levelThirtyStats.Clone(),
                    equipment=JsonUtility.FromJson<CombatItem>(JsonUtility.ToJson(m.equipment??new CombatItem())),traits=m.traits==null?null:m.traits.Clone()};
                foreach(var skill in m.skills)member.skills.Add(JsonUtility.FromJson<BattleSkill>(JsonUtility.ToJson(skill)));
                copy.Add(member);
            }
            return copy;
        }
        private IEnumerator Play()
        {
            while(!presentation.battleEngine.isBattleOver)
            {
                presentation.TriggerNextCast();
                while(presentation.IsPlaybackBusy)yield return null;
            }
            Finish(false);
            if(session.Request.autoLeave)session.Leave();
        }
        private void Update()
        {
            if(!started||session==null||session.Request.autoPlay||session.Result!=null)return;
            if(Input.GetKeyDown(KeyCode.Space))AdvanceBattle();
            if(presentation.battleEngine.isBattleOver&&!presentation.IsPlaybackBusy)Finish(false);
        }
        private void Finish(bool interrupted)
        {
            if(session==null||session.Result!=null)return;
            var engine=presentation.battleEngine;var runtime=engine.Runtime;
            var result=new BattleSceneResult {initialized=true,rounds=runtime.Round,winnerTroopId=engine.winnerTroopId,
                leftBP=Math.Max(0,runtime.teams[0].bp),leftMaxBP=runtime.teams[0].maxBP,rightBP=Math.Max(0,runtime.teams[1].bp),rightMaxBP=runtime.teams[1].maxBP,
                leftUnrestrictedMaxBP=runtime.teams[0].UnrestrictedMaxBP,rightUnrestrictedMaxBP=runtime.teams[1].UnrestrictedMaxBP,
                leftDamageReceived=runtime.teams[0].DamageReceived,rightDamageReceived=runtime.teams[1].DamageReceived,
                leftMinimumBPRatio=runtime.teams[0].MinimumBPRatio,rightMinimumBPRatio=runtime.teams[1].MinimumBPRatio,
                leftDamageExposure=runtime.teams[0].DamageExposure,rightDamageExposure=runtime.teams[1].DamageExposure,
                leftCasts=(int[])runtime.teams[0].casts.Clone(),rightCasts=(int[])runtime.teams[1].casts.Clone(),
                leftOpeningBonds=JsonUtility.FromJson<OpeningBondReport>(JsonUtility.ToJson(runtime.teams[0].OpeningBonds)),
                rightOpeningBonds=JsonUtility.FromJson<OpeningBondReport>(JsonUtility.ToJson(runtime.teams[1].OpeningBonds)),
                leftEvasionBonds=runtime.teams[0].EvasionBonds.Snapshot(),rightEvasionBonds=runtime.teams[1].EvasionBonds.Snapshot(),
                leftSupportBonds=runtime.teams[0].SupportBonds.Snapshot(),rightSupportBonds=runtime.teams[1].SupportBonds.Snapshot(),
                leftAmplificationBonds=runtime.teams[0].AmplificationBonds.Snapshot(),rightAmplificationBonds=runtime.teams[1].AmplificationBonds.Snapshot(),
                leftAugmentationBonds=runtime.teams[0].AugmentationBonds.Snapshot(),rightAugmentationBonds=runtime.teams[1].AugmentationBonds.Snapshot(),
                leftTacticalBonds=runtime.teams[0].TacticalBonds.Snapshot(),rightTacticalBonds=runtime.teams[1].TacticalBonds.Snapshot(),
                leftCompoundBonds=runtime.teams[0].CompoundBonds.Snapshot(),rightCompoundBonds=runtime.teams[1].CompoundBonds.Snapshot(),
                outcome=interrupted&&!engine.isBattleOver?BattleSceneOutcome.Interrupted:engine.isCensored?BattleSceneOutcome.Unresolved:
                    engine.winnerTroopId==1?BattleSceneOutcome.LeftWon:engine.winnerTroopId==2?BattleSceneOutcome.RightWon:BattleSceneOutcome.Draw};
            session.Complete(result);
            if(resultText!=null){resultText.text=result.outcome==BattleSceneOutcome.LeftWon?"胜利":result.outcome==BattleSceneOutcome.RightWon?"失败":result.outcome==BattleSceneOutcome.Draw?"同时耗尽":"未决";resultText.gameObject.SetActive(true);}
        }
        public void LeaveBattle(){if(session!=null)session.Leave();}
        public void AdvanceBattle(){if(started&&session!=null&&!session.Request.autoPlay&&session.Result==null&&!presentation.IsPlaybackBusy)presentation.TriggerNextCast();}
        internal void StopAndCapture(){StopAllCoroutines();if(presentation!=null){presentation.StopBattlePlayback();if(started)Finish(true);}}
        private void OnDestroy(){if(started&&session!=null&&!session.IsClosed){StopAndCapture();session.Leave();}}
    }
}
