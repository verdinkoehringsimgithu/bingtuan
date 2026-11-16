using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    // The test module replays one real numerical report. Seeking never calls the engine.
    public class BattleEffectTestModule : MonoBehaviour
    {
        public BattleInspectionManager presentation;
        private readonly List<SkillEffectMatcher.FamilyEntry> families=new List<SkillEffectMatcher.FamilyEntry>();
        private readonly List<SkillEffectMatcher.VariantEntry> variants=new List<SkillEffectMatcher.VariantEntry>();
        private int familyIndex,variantIndex;
        private Vector2 scroll,configScroll;
        private readonly Dictionary<string,string> inputText=new Dictionary<string,string>();
        private bool hasInputFocus;
        private bool playing, leftAttacking=true, showPanel=true;
        private bool filterSelfOnly = false;
        public bool FilterSelfOnly { get => filterSelfOnly; set => filterSelfOnly = value; }
        public int SelfFamilyCount => GetSelfCount();
        private int GetSelfCount()
        {
            int count = 0;
            foreach (var f in families)
            {
                foreach (var v in f.Variants.Values)
                {
                    if (EffectTimingConfig.For(v.AnimationId).playOnCaster) { count++; break; }
                }
            }
            return count;
        }
        private List<SkillEffectMatcher.FamilyEntry> GetVisibleFamilies()
        {
            if (!filterSelfOnly) return families;
            var result = new List<SkillEffectMatcher.FamilyEntry>();
            foreach (var f in families)
            {
                bool isSelf = false;
                foreach (var v in f.Variants.Values)
                {
                    if (EffectTimingConfig.For(v.AnimationId).playOnCaster) { isSelf = true; break; }
                }
                if (isSelf) result.Add(f);
            }
            return result;
        }
        private float seconds;
        private BattleTurnReport report;
        private int beforeLeft,beforeRight,beforeLeftShield,beforeRightShield;
        private string feedback="";
        public int AnimationId => variants.Count==0?0:variants[variantIndex].AnimationId;
        public EffectTimingProfile Profile => EffectTimingConfig.For(AnimationId);
        public int FamilyCount => families.Count;
        public float CurrentTime => seconds;
        public BattleTurnReport CapturedReport => report;
        public const float TimelineFPS=60;
        public BattlePresentationTimeline Timeline => new BattlePresentationTimeline(Profile,FrameCount);
        public float EffectStart => Timeline.effectStart;
        public float DamageTime => Timeline.damageTime;
        public float PhysicsTime => Timeline.physicsTime;
        public float ReturnStart => Timeline.ReturnStart;
        public float StartTime => Timeline.startTime;
        public int RotationCount => Timeline.rotations;
        public int FrameCount {
            get {float scale;bool directional;var frames=BattleEffectPlayer.Instance.GetFrames(AnimationId,out scale,out directional);return frames==null?0:frames.Length;}
        }
        public float Duration => Timeline.endTime;
        private void Start()
        {
            if(presentation==null)presentation=GetComponent<BattleInspectionManager>();
            presentation.productionMode=true;presentation.StopBattlePlayback();presentation.DraftStrategyBattle();
            families.AddRange(SkillEffectMatcher.AllFamilies);
            SelectFamily(0);CaptureReport();Seek(StartTime);
        }
        public void SelectFamily(int index)
        {
            familyIndex=Mathf.Clamp(index,0,families.Count-1);variantIndex=0;variants.Clear();
            variants.AddRange(families[familyIndex].Variants.Values);variants.Sort((a,b)=>a.AnimationId.CompareTo(b.AnimationId));
            seconds=0;playing=false;inputText.Clear();
        }
        public void CaptureReport()
        {
            presentation.StopBattlePlayback();presentation.DraftStrategyBattle();
            beforeLeft=presentation.leftTroop.currentBP;beforeRight=presentation.rightTroop.currentBP;
            beforeLeftShield=presentation.leftTroop.shieldBP;beforeRightShield=presentation.rightTroop.shieldBP;
            report=presentation.battleEngine.ExecuteNextTurn();leftAttacking=report.actingTroopId==presentation.leftTroop.troopId;
        }
        private void Update()
        {
            if(report==null)return;
            if(Input.GetKeyDown(KeyCode.F2))showPanel=!showPanel;
            if(!hasInputFocus){
            if(Input.GetKeyDown(KeyCode.Space)){if(seconds>=Duration)Seek(StartTime);playing=!playing;}
            if(Input.GetKeyDown(KeyCode.LeftArrow)){playing=false;Seek(seconds-1/TimelineFPS);}
            if(Input.GetKeyDown(KeyCode.RightArrow)){playing=false;Seek(seconds+1/TimelineFPS);}
            }
            if(playing){Seek(seconds+Time.unscaledDeltaTime);if(seconds>=Duration)playing=false;}
        }
        public void Seek(float time)
        {
            if(report==null||AnimationId==0)return;
            Profile.Normalize();var timeline=Timeline;seconds=Mathf.Clamp(time,timeline.startTime,timeline.endTime);
            var attackers=leftAttacking?presentation.LeftSlots:presentation.RightSlots;
            var defenders=leftAttacking?presentation.RightSlots:presentation.LeftSlots;
            foreach(var character in presentation.LeftSlots)if(character!=null){character.manualAnimation=true;character.ResetCombatState();character.SampleAnimation(seconds);}
            foreach(var character in presentation.RightSlots)if(character!=null){character.manualAnimation=true;character.ResetCombatState();character.SampleAnimation(seconds);}
            float offset=timeline.AttackOffset(seconds);
            foreach(var character in attackers)if(character!=null){character.SetDirectionOverride(leftAttacking?2:1);character.SetActionOffset(new Vector3(offset*(leftAttacking?1:-1),0,0));}
            Vector3 center=Center(defenders);
            for(int i=0;i<defenders.Length;i++)
            {
                var character=defenders[i];if(character==null||!character.gameObject.activeInHierarchy)continue;
                int col=i/5,row=i%5,rank=leftAttacking?col:5-col;
                int type=Profile.reactionType;float elapsed=seconds-PhysicsTime-(type==5?rank*.045f:0);
                float intensity=type==7?Mathf.Lerp(2.2f,.15f,rank/5f):1;
                Vector3 scatter=type==6?(character.BasePosition-center).normalized:
                    type==8?new Vector3((col-2.5f)*.16f,-(row-2f)*.12f,0):
                    type==9?center-character.BasePosition:type==10?character.BasePosition-center:Vector3.up;
                if(type==6&&scatter.sqrMagnitude<.001f)scatter=Vector3.up;
                character.SampleHitReaction(type,!leftAttacking,intensity,elapsed,scatter,173+i,timeline.rotations,timeline.rotationDuration,Profile.scatterDistanceScale);
                character.SampleDamageFlash(!report.isDodge&&report.damageDealt>0?seconds-timeline.damageTime:-1);
                character.SampleAnimation(seconds);
            }
            CameraShakeController.SampleByDamage(seconds-timeline.damageTime,report.isDodge?0:report.damageDealt,report.defenderMaxBP);
            int effectFrame=Mathf.FloorToInt((seconds-EffectStart)*Profile.fps+0.00001f);
            var targetFormation=Profile.playOnCaster?attackers:defenders;
            Vector3 effectCenter=BattleFormationCenter.GetCenter(targetFormation);
            BattleEffectPlayer.Instance.ShowFrame(AnimationId,effectFrame,effectCenter,leftAttacking,targetFormation);
            var bars=presentation.HealthBarUI;
            if(bars!=null)
            {
                bool mirrored=leftAttacking!=(report.actingTroopId==presentation.leftTroop.troopId);
                var leftView=mirrored?presentation.rightTroop:presentation.leftTroop;
                var rightView=mirrored?presentation.leftTroop:presentation.rightTroop;
                if(Profile.playOnCaster)
                {
                    bool healReached=seconds+0.000001f>=timeline.healTime;
                    int leftBP=leftAttacking?(healReached?leftView.maxBP:0):leftView.maxBP;
                    int rightBP=!leftAttacking?(healReached?rightView.maxBP:0):rightView.maxBP;
                    bars.ApplyDamage(true,0,false,leftBP,leftView.maxBP,0);
                    bars.ApplyDamage(false,0,false,rightBP,rightView.maxBP,0);
                    SnapBar(bars.LeftBar);SnapBar(bars.RightBar);
                }
                else
                {
                    bool after=seconds+0.000001f>=DamageTime;
                    bars.ApplyDamage(true,0,false,after?leftView.currentBP:(mirrored?beforeRight:beforeLeft),leftView.maxBP,after?leftView.shieldBP:(mirrored?beforeRightShield:beforeLeftShield));
                    bars.ApplyDamage(false,0,false,after?rightView.currentBP:(mirrored?beforeLeft:beforeRight),rightView.maxBP,after?rightView.shieldBP:(mirrored?beforeLeftShield:beforeRightShield));
                    SnapBar(bars.LeftBar);SnapBar(bars.RightBar);
                }
            }
        }
        private static void SnapBar(BattleHealthBarUI.TroopBarView bar)
        {
            bar.displayBP=bar.currentBP;bar.currentRatio=bar.targetRatio;bar.lagRatio=bar.targetRatio;bar.lagDelayTimer=0;bar.UpdateVisual(0);
        }
        private static Vector3 Center(BattleCharacterPreview[] characters,bool home=false)
        {
            Vector3 sum=Vector3.zero;int count=0;
            foreach(var character in characters)if(character!=null&&character.gameObject.activeInHierarchy){sum+=home?character.BasePosition:character.transform.position;count++;}
            return count==0?sum:sum/count;
        }
        private void OnGUI()
        {
            if(report==null||families.Count==0)return;
            var prior=GUI.matrix;float uiScale=Mathf.Min(Screen.width/1280f,Screen.height/720f);GUI.matrix=Matrix4x4.Scale(new Vector3(uiScale,uiScale,1));
            if(showPanel) {
            GUILayout.BeginArea(new Rect(8,8,285,704),GUI.skin.box);
            bool newFilter = GUILayout.Toggle(filterSelfOnly, "仅看对自身特效 (" + GetSelfCount() + "/" + families.Count + ")");
            if (newFilter != filterSelfOnly) { filterSelfOnly = newFilter; }
            var visibleFamilies = GetVisibleFamilies();
            GUILayout.Label("特效测试 · " + visibleFamilies.Count + "种类型");
            scroll=GUILayout.BeginScrollView(scroll,GUILayout.Height(130));
            for(int i=0;i<visibleFamilies.Count;i++)
            {
                var f = visibleFamilies[i];
                int fIdx = families.IndexOf(f);
                if(GUILayout.Button((fIdx==familyIndex?"> ":"")+f.PureTitleCn+" / "+f.BaseKey)){SelectFamily(fIdx);Seek(StartTime);}
            }
            GUILayout.EndScrollView();
            GUILayout.BeginHorizontal();if(GUILayout.Button("上一变体")){variantIndex=(variantIndex+variants.Count-1)%variants.Count;Seek(seconds);}if(GUILayout.Button("下一变体")){variantIndex=(variantIndex+1)%variants.Count;Seek(seconds);}GUILayout.EndHorizontal();
            GUILayout.Label(variants[variantIndex].CnName+" ["+AnimationId+"] · "+FrameCount+"帧");
            configScroll=GUILayout.BeginScrollView(configScroll);
            bool caster=GUILayout.Toggle(Profile.playOnCaster,"对自身：攻击归位后播放");if(caster!=Profile.playOnCaster){Profile.playOnCaster=caster;Seek(seconds);}
            GUILayout.Label(Profile.playOnCaster ? "播放位置：己方阵容中心" : "对敌人：攻击同时播放，对应敌方中心");
            Profile.useFormationSorting=GUILayout.Toggle(Profile.useFormationSorting,"参与阵容排序（取消：最高层）");
            GUILayout.Label(BattleEffectPlayer.Instance.HasLayers(AnimationId)?"素材图层：原始前层 + 后层":"素材图层：单层");
            Profile.scale=FloatNumber("缩放",Profile.scale,.10f);
            Profile.offsetX=FloatNumber("水平中心偏移",Profile.offsetX,.05f);
            Profile.offsetY=FloatNumber("垂直中心偏移",Profile.offsetY,.05f);
            EffectTimingConfig.Motion.advanceDuration=FloatNumber("前移时长（秒）",EffectTimingConfig.Motion.advanceDuration,.05f);
            EffectTimingConfig.Motion.holdDuration=FloatNumber("停留时长（秒）",EffectTimingConfig.Motion.holdDuration,.05f);
            EffectTimingConfig.Motion.retreatDuration=FloatNumber("后退时长（秒）",EffectTimingConfig.Motion.retreatDuration,.05f);
            Profile.fps=Number("特效每秒帧数",Profile.fps);
            Profile.effectStartFrame=Number("特效开始帧（负数提前）",Profile.effectStartFrame);
            if(Profile.playOnCaster)
            {
                Profile.healFrame=Number("回血时点（特效帧）",Profile.healFrame);
                GUILayout.Label(string.Format("回血时点：{0:F3}s（空血→满血校准）",Timeline.healTime));
            }
            else
            {
                Profile.damageFrame=Number("伤害时点（特效帧）",Profile.damageFrame);
                Profile.physicsFrame=Number("物理效果时点（特效帧）",Profile.physicsFrame);
            }
            Profile.reactionType=Number("受击物理模式 1–10",Profile.reactionType);Profile.Normalize();
            if(Profile.reactionType==6)
            {
                Profile.scatterDistanceScale=FloatNumber("炸散距离倍率",Profile.scatterDistanceScale,.05f);
            }
            if(Profile.reactionType==4||Profile.reactionType==10) {
                Profile.autoRotationCount=GUILayout.Toggle(Profile.autoRotationCount,"按特效时长计算旋转次数");
                if(Profile.autoRotationCount)Profile.secondsPerRotation=FloatNumber("每圈秒数",Profile.secondsPerRotation,.05f);
                else Profile.rotationCount=Number("旋转次数",Profile.rotationCount);
                GUILayout.Label("本次旋转 "+RotationCount+" 圈");
            }
            if(presentation!=null&&presentation.Formation!=null)
            {
                GUILayout.Space(6);
                GUILayout.Label("<b>【两军站位间距调节】</b>");
                float curDist=presentation.Formation.ArmyDistance;
                float newDist=FloatNumber("两军间距",curDist,.10f);
                if(Mathf.Abs(newDist-curDist)>0.001f)
                {
                    presentation.Formation.ArmyDistance=newDist;
                    presentation.ApplyFormationLayout();
                    presentation.Formation.AutoSaveIfChanged();
                    Seek(seconds);
                }
            }
            GUILayout.EndScrollView();
            GUILayout.BeginHorizontal();
            if(GUILayout.Button("保存配置"))
            {
                try
                {
                    EffectTimingConfig.Save();
                    if(presentation!=null&&presentation.Formation!=null)presentation.Formation.Save();
                    feedback="配置与站位已保存";
                }
                catch(Exception e){feedback=e.Message;}
            }
            if(GUILayout.Button("重新读取"))
            {
                EffectTimingConfig.Reload();
                if(presentation!=null)presentation.ApplyFormationLayout();
                inputText.Clear();Seek(seconds);
            }
            GUILayout.EndHorizontal();
            GUILayout.Label(feedback);GUILayout.EndArea();
            }
            GUILayout.BeginArea(new Rect(310,570,955,140),GUI.skin.box);
            GUILayout.Label(string.Format("时间 {0:F3}s / {1:F3}s · 时间轴帧 {2}（60帧/秒） · 特效帧 {3}",seconds,Duration,Mathf.RoundToInt(seconds*TimelineFPS),Mathf.FloorToInt((seconds-EffectStart)*Profile.fps)));
            float selected=GUILayout.HorizontalSlider(seconds,StartTime,Duration);if(Mathf.Abs(selected-seconds)>.00001f){playing=false;Seek(selected);}
            GUILayout.BeginHorizontal();
            if(GUILayout.Button(playing?"暂停":"播放")){if(seconds>=Duration)Seek(StartTime);playing=!playing;}
            if(GUILayout.Button("重播")){Seek(StartTime);playing=true;}
            if(GUILayout.Button("前一帧")){playing=false;Seek(seconds-1/TimelineFPS);}
            if(GUILayout.Button("后一帧")){playing=false;Seek(seconds+1/TimelineFPS);}
            if(GUILayout.Button("前一特效帧")){playing=false;Seek(EffectStart+(Mathf.FloorToInt((seconds-EffectStart)*Profile.fps)-1)/(float)Profile.fps);}
            if(GUILayout.Button("后一特效帧")){playing=false;Seek(EffectStart+(Mathf.FloorToInt((seconds-EffectStart)*Profile.fps)+1)/(float)Profile.fps);}
            if(GUILayout.Button("交换攻击方向")){leftAttacking=!leftAttacking;Seek(seconds);}
            if(GUILayout.Button("重新取样战报")){playing=false;CaptureReport();Seek(StartTime);}
            GUILayout.EndHorizontal();
            GUILayout.Label(string.Format("特效 {0:F3}s · 回血 {1:F3}s · 物理效果 {2:F3}s · 伤害 {3:F3}s · 本次真实伤害 {4} · 真实治疗 {5} {6}",
                EffectStart,Timeline.healTime,PhysicsTime,DamageTime,report.damageDealt,report.healDone,report.isDodge?"（闪避）":""));
            GUILayout.EndArea();GUI.matrix=prior;
            hasInputFocus=GUI.GetNameOfFocusedControl().StartsWith("effect-field-");
            if(GUI.changed){TryAutoSave();Seek(seconds);}
        }
        private void TryAutoSave()
        {
            try
            {
                bool timingSaved=EffectTimingConfig.AutoSaveIfChanged();
                bool formationSaved=presentation!=null&&presentation.Formation!=null&&presentation.Formation.AutoSaveIfChanged();
                if(timingSaved||formationSaved)feedback="自动保存";
            }
            catch(Exception e){feedback="自动保存失败："+e.Message;Debug.LogWarning(feedback);}
        }
        private int Number(string label,int value)
        {
            string key="effect-field-"+label;string draft;
            if(!inputText.TryGetValue(key,out draft)||GUI.GetNameOfFocusedControl()!=key)draft=value.ToString();
            GUILayout.BeginHorizontal();GUILayout.Label(label);
            if(GUILayout.Button("−",GUILayout.Width(24))){value--;draft=value.ToString();}
            GUI.SetNextControlName(key);draft=GUILayout.TextField(draft,GUILayout.Width(62));int parsed;if(int.TryParse(draft,out parsed))value=parsed;
            if(GUILayout.Button("+",GUILayout.Width(24))){value++;draft=value.ToString();}
            inputText[key]=draft;GUILayout.EndHorizontal();return value;
        }
        private float FloatNumber(string label,float value,float step)
        {
            string key="effect-field-"+label;string draft;var culture=System.Globalization.CultureInfo.InvariantCulture;
            if(!inputText.TryGetValue(key,out draft)||GUI.GetNameOfFocusedControl()!=key)draft=value.ToString("F2",culture);
            GUILayout.BeginHorizontal();GUILayout.Label(label);
            if(GUILayout.Button("−",GUILayout.Width(24))){value-=step;draft=value.ToString("F2",culture);}
            GUI.SetNextControlName(key);draft=GUILayout.TextField(draft,GUILayout.Width(62));float parsed;
            if(float.TryParse(draft,System.Globalization.NumberStyles.Float,culture,out parsed)&&!float.IsNaN(parsed)&&!float.IsInfinity(parsed))value=parsed;
            if(GUILayout.Button("+",GUILayout.Width(24))){value+=step;draft=value.ToString("F2",culture);}
            inputText[key]=draft;GUILayout.EndHorizontal();return value;
        }
        private void OnDisable()
        {
            TryAutoSave();
            if(presentation!=null){foreach(var character in presentation.LeftSlots)if(character!=null){character.manualAnimation=false;character.ResetCombatState();}foreach(var character in presentation.RightSlots)if(character!=null){character.manualAnimation=false;character.ResetCombatState();}}
            if(BattleEffectPlayer.ExistingInstance!=null)BattleEffectPlayer.ExistingInstance.ClearScrub();
            if(CameraShakeController.Instance!=null)CameraShakeController.Instance.ResetShake();
        }
        private void OnApplicationQuit(){TryAutoSave();}
        private void OnApplicationPause(bool paused){if(paused)TryAutoSave();}
    }
}
