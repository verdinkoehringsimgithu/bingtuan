using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.EventSystems;

namespace LegionBattle.Battle
{
    public sealed class BattleSceneFlowDriver : MonoBehaviour
    {
        private BattleSceneSession session;
        private Scene origin,battle;
        private AsyncOperation loading;
        private BattleSceneController controller;
        private bool closing;
        private readonly List<Behaviour> hiddenBehaviours=new List<Behaviour>();
        private readonly List<Renderer> hiddenRenderers=new List<Renderer>();
        private BattleEffectPlayer previousEffects;
        public void Open(BattleSceneSession handle,Scene source){session=handle;origin=source;HideCaller();StartCoroutine(Load());}
        public void Adopt(BattleSceneSession handle,BattleSceneController current)
        {
            session=handle;origin=battle=current.gameObject.scene;controller=current;
            try{controller.Begin(session);}catch(Exception ex){session.Complete(new BattleSceneResult {outcome=BattleSceneOutcome.Failed,error=ex.Message});Close();}
        }
        private void HideCaller()
        {
            previousEffects=BattleEffectPlayer.ExistingInstance;
            foreach(var b in Resources.FindObjectsOfTypeAll<Behaviour>())
            {
                if(!b.gameObject.scene.isLoaded || !b.enabled)continue;
                if(b is Camera || b is Canvas || b is EventSystem || b is BattleInspectionManager || b is BattleEffectPlayer)
                {hiddenBehaviours.Add(b);b.enabled=false;}
            }
            foreach(var r in Resources.FindObjectsOfTypeAll<Renderer>())
                if(r.gameObject.scene.isLoaded&&r.enabled){hiddenRenderers.Add(r);r.enabled=false;}
        }
        private void RestoreCaller()
        {
            foreach(var b in hiddenBehaviours)if(b!=null)b.enabled=true;
            foreach(var r in hiddenRenderers)if(r!=null)r.enabled=true;
            hiddenBehaviours.Clear();hiddenRenderers.Clear();BattleEffectPlayer.BindSceneInstance(previousEffects);
        }
        private IEnumerator Load()
        {
            yield return null;
            if(closing)yield break;
            Exception failure=null;
            try {loading=SceneManager.LoadSceneAsync(BattleSceneFlow.SceneName,LoadSceneMode.Additive);}
            catch(Exception ex){failure=ex;}
            if(failure!=null || loading==null)
            {Fail(failure==null?"Battle scene failed to load":failure.Message);yield break;}
            while(!loading.isDone)yield return null;
            battle=SceneManager.GetSceneByName(BattleSceneFlow.SceneName);
            if(closing)yield break;
            SceneManager.SetActiveScene(battle);
            foreach(var root in battle.GetRootGameObjects())
            {controller=root.GetComponentInChildren<BattleSceneController>(true);if(controller!=null)break;}
            if(controller==null){session.Complete(new BattleSceneResult {outcome=BattleSceneOutcome.Failed,error="BattleSceneController is missing"});Close();yield break;}
            try{controller.Begin(session);}catch(Exception ex){failure=ex;}
            if(failure!=null){session.Complete(new BattleSceneResult {outcome=BattleSceneOutcome.Failed,error=failure.Message});Close();}
        }
        private void Fail(string error)
        {
            session.Complete(new BattleSceneResult {outcome=BattleSceneOutcome.Failed,error=error});
            RestoreCaller();BattleSceneFlow.Release(session);session.Close();Destroy(gameObject);
        }
        public void Close(){if(closing)return;closing=true;StartCoroutine(Unload());}
        public void Advance(){if(!closing&&controller!=null)controller.AdvanceBattle();}
        private IEnumerator Unload()
        {
            if(loading!=null)while(!loading.isDone)yield return null;
            if(!battle.IsValid())battle=SceneManager.GetSceneByName(BattleSceneFlow.SceneName);
            if(controller==null&&battle.IsValid())foreach(var root in battle.GetRootGameObjects())
            {controller=root.GetComponentInChildren<BattleSceneController>(true);if(controller!=null)break;}
            if(controller!=null)controller.StopAndCapture();
            if(session.Result==null)session.Complete(new BattleSceneResult {outcome=BattleSceneOutcome.Interrupted});
            bool canUnload=SceneManager.sceneCount>1;
            if(battle.IsValid()&&battle.isLoaded&&canUnload)
            {
                var operation=SceneManager.UnloadSceneAsync(battle);if(operation!=null)while(!operation.isDone)yield return null;
            }
            if(!canUnload&&battle.IsValid()&&battle.isLoaded)
            {
                // Unity cannot unload its last scene. Direct Play stops this scene's content;
                // its external Closed listener owns the next scene decision.
                foreach(var root in battle.GetRootGameObjects())root.SetActive(false);
            }
            RestoreCaller();
            BattleSceneFlow.Release(session);session.Close();Destroy(gameObject);
        }
    }
}
