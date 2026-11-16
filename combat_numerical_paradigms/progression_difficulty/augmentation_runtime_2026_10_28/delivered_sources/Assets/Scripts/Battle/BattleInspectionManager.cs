using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace LegionBattle.Battle
{
    public class BattleInspectionManager : MonoBehaviour
    {
        [Header("数据源")]
        [SerializeField] private CharacterDatabase database;
        public bool productionMode;
        public bool IsPlaybackBusy => isCombatRunning;
        public CharacterDatabase Database => database;
        [Range(1, 6)] public int battleStage = 6;
        public string playerFlow = "C_I";
        public string opponentFlow = "M_R";
        public bool useFixedEncounter;
        public string encounterDifficulty = "hard";
        public bool useTopEquipment;
        public bool useMaxLevel = true;

        [Header("左军 30 点位")]
        [SerializeField] private BattleCharacterPreview[] leftSlots = new BattleCharacterPreview[30];

        [Header("右军 30 点位")]
        [SerializeField] private BattleCharacterPreview[] rightSlots = new BattleCharacterPreview[30];

        [Header("阵列矩阵布局 (游戏模式实时调节与记录)")]
        [SerializeField] private FormationConfig formation = new FormationConfig();

        [Header("UI 控件")]
        [SerializeField] private Button btnNextWave;
        [SerializeField] private Button btnPrevWave;
        [SerializeField] private Text txtWaveInfo;

        [SerializeField] private int currentWaveIndex = 0;
        private const int CharactersPerWave = 60; // 左 30 + 右 30

        // 运行时调距面板状态
        [SerializeField] private bool showAdjustmentGUI = true;
        private string saveFeedbackText = "";
        private float saveFeedbackTimer = 0f;

        [Header("战力机制与血条系统 (Battle Power & HP Bar)")]
        [SerializeField] private BattleHealthBarUI healthBarUI;
        [SerializeField] private int leftMaxBP = 200000;
        [SerializeField] private int leftCurrentBP = 200000;
        [SerializeField] private int rightMaxBP = 200000;
        [SerializeField] private int rightCurrentBP = 200000;
        [SerializeField] private int combatRound = 1;

        [Header("核心战斗引擎与战团模型 (BattleEngine System)")]
        public BattleEngine battleEngine = new BattleEngine();
        public BattleTroop leftTroop = new BattleTroop(1, "我方先锋军");
        public BattleTroop rightTroop = new BattleTroop(2, "敌方精锐军");

        public FormationConfig Formation => formation;
        public int CurrentWaveIndex => currentWaveIndex;
        public int TotalWaves => database != null && database.characters != null && database.characters.Count > 0 
            ? Mathf.CeilToInt((float)database.characters.Count / CharactersPerWave) 
            : 1;

        public int LeftMaxBP => leftMaxBP;
        public int LeftCurrentBP => leftCurrentBP;
        public int RightMaxBP => rightMaxBP;
        public int RightCurrentBP => rightCurrentBP;
        public int CombatRound => combatRound;
        public BattleHealthBarUI HealthBarUI => healthBarUI;

        public void Configure(CharacterDatabase db, BattleCharacterPreview[] left, BattleCharacterPreview[] right, Button next, Button prev, Text info, BattleHealthBarUI hb = null)
        {
            database = db;
            leftSlots = left;
            rightSlots = right;
            btnNextWave = next;
            btnPrevWave = prev;
            txtWaveInfo = info;
            if (hb != null) healthBarUI = hb;
#if UNITY_EDITOR
            UnityEditor.EditorUtility.SetDirty(this);
#endif
        }

        private void Awake()
        {
            if (database == null)
            {
#if UNITY_EDITOR
                database = UnityEditor.AssetDatabase.LoadAssetAtPath<CharacterDatabase>("Assets/Characters/CharacterDatabase.asset");
#endif
            }

            // 自动检索或构建战力血条组件
            if (healthBarUI == null)
            {
                healthBarUI = FindObjectOfType<BattleHealthBarUI>();
                if (healthBarUI == null)
                {
                    Canvas c = FindObjectOfType<Canvas>();
                    if (c != null)
                    {
                        GameObject hbObj = new GameObject("BattleHealthBarUI");
                        hbObj.transform.SetParent(c.transform, false);
                        healthBarUI = hbObj.AddComponent<BattleHealthBarUI>();
                    }
                }
            }

            // 加载已记录的阵列配置
            formation = FormationConfig.Load();

            // 确保正交摄像机开启基于 Y 轴的自下而上遮挡排序模式 (越靠下越靠前)
            Camera mainCam = Camera.main;
            if (mainCam != null)
            {
                mainCam.transparencySortMode = TransparencySortMode.CustomAxis;
                mainCam.transparencySortAxis = new Vector3(0, 1, 0);
            }
        }

        private void Start()
        {
            if (productionMode) return;
            if (UnityEngine.EventSystems.EventSystem.current != null)
            {
                UnityEngine.EventSystems.EventSystem.current.sendNavigationEvents = false;
                UnityEngine.EventSystems.EventSystem.current.SetSelectedGameObject(null);
            }

            if (btnNextWave != null)
            {
                Navigation nav = btnNextWave.navigation;
                nav.mode = Navigation.Mode.None;
                btnNextWave.navigation = nav;
                btnNextWave.onClick.RemoveAllListeners();
                btnNextWave.onClick.AddListener(NextWave);
            }
            if (btnPrevWave != null)
            {
                Navigation nav = btnPrevWave.navigation;
                nav.mode = Navigation.Mode.None;
                btnPrevWave.navigation = nav;
                btnPrevWave.onClick.RemoveAllListeners();
                btnPrevWave.onClick.AddListener(PrevWave);
            }

            ApplyFormationLayout();
            ApplyWave(currentWaveIndex);
            DraftStrategyBattle();
        }

        [Header("军团战斗演练 (全体施法/全体受击)")]
        private bool isCombatRunning = false;
        private bool autoCombat = false;
        private float autoCombatTimer = 0f;
        private bool lastAttackerWasLeft = false;
        private string combatStatusText = "待命 (默认全员朝下朝向玩家)";
        private Coroutine combatCoroutine = null;
        [SerializeField] private bool turnTowardsEnemyOnAttack = false; // 冲锋施法时是否转向敌方，默认 false (全员朝下方，朝向玩家)

        [Header("十种受击动力学类型 (含黑洞聚拢吸附与漩涡波纹旋转散开)")]
        public int currentHitReactionType = 1; // 1 ~ 10
        public static readonly string[] HitReactionNames = new string[]
        {
            "1. 水平震退 (Knockback)",
            "2. 垂直击飞 (Pop-Up)",
            "3. 抛物线后仰 (Launch)",
            "4. 四向旋转翻滚 (Spin)",
            "5. 波浪状掀飞 (Wave)",
            "6. 中心炸散复位 (Disperse)",
            "7. 手风琴压缩 (Squeeze)",
            "8. 地震颠簸 (Tremor)",
            "9. 中心聚拢吸附 (Converge)",
            "10. 集体旋转散开 (Swirl)"
        };

        private void Update()
        {
            if (productionMode) return;
            if (saveFeedbackTimer > 0f)
            {
                saveFeedbackTimer -= Time.deltaTime;
                if (saveFeedbackTimer <= 0f) saveFeedbackText = "";
            }

            // F2 快捷键切换调距面板显示/隐藏
            if (Input.GetKeyDown(KeyCode.F2))
            {
                showAdjustmentGUI = !showAdjustmentGUI;
            }

            // 战斗演练快捷键
            if (Input.GetKeyDown(KeyCode.Space) || Input.GetKeyDown(KeyCode.C))
            {
                TriggerNextCast();
            }
            else if (Input.GetKeyDown(KeyCode.Alpha1) || Input.GetKeyDown(KeyCode.Keypad1))
            {
                TriggerLeftCast();
            }
            else if (Input.GetKeyDown(KeyCode.Alpha2) || Input.GetKeyDown(KeyCode.Keypad2))
            {
                TriggerRightCast();
            }
            else if (Input.GetKeyDown(KeyCode.V))
            {
                autoCombat = !autoCombat;
            }
            else if (Input.GetKeyDown(KeyCode.H))
            {
                // H 键顺序循环切换十种受击动力学类型
                currentHitReactionType = (currentHitReactionType % HitReactionNames.Length) + 1;
                combatStatusText = string.Format("已切换受击方式: {0}", HitReactionNames[currentHitReactionType - 1]);
                TriggerNextCast();
            }
            else if (Input.GetKeyDown(KeyCode.R))
            {
                // R 键切换四向自动巡回开关
                BattleCharacterPreview.autoRotateDirections = !BattleCharacterPreview.autoRotateDirections;
            }
            else if (Input.GetKeyDown(KeyCode.B))
            {
                // B 键：重置双方战力为满战力状态
                ResetBattlePower();
            }
            else if (Input.GetKeyDown(KeyCode.G))
            {
                // G 键：50选30满级策略阵容对决
                DraftStrategyBattle();
            }

            // 自动对攻循环处理
            if (autoCombat && !isCombatRunning)
            {
                autoCombatTimer += Time.deltaTime;
                if (autoCombatTimer >= 0.7f)
                {
                    autoCombatTimer = 0f;
                    TriggerNextCast();
                }
            }

            // 键盘左右箭头键翻页 (同时支持 A/D, Q/E, PageUp/PageDown)
            if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.D) || Input.GetKeyDown(KeyCode.E) || Input.GetKeyDown(KeyCode.PageDown))
            {
                NextWave();
            }
            else if (Input.GetKeyDown(KeyCode.LeftArrow) || Input.GetKeyDown(KeyCode.A) || Input.GetKeyDown(KeyCode.Q) || Input.GetKeyDown(KeyCode.PageUp))
            {
                PrevWave();
            }
        }

        #region 军团整体施法与受击战斗演练
        public void TriggerNextCast()
        {
            if (isCombatRunning || battleEngine.isBattleOver) return;
            // 依据战斗引擎当前裁定的行动方行动
            bool isLeft = (battleEngine.currentActingTroopId == 1);
            TriggerCast(isLeft);
        }

        public void TriggerLeftCast()
        {
            if (isCombatRunning || battleEngine.isBattleOver) return;
            battleEngine.currentActingTroopId = 1;
            TriggerCast(true);
        }

        public void TriggerRightCast()
        {
            if (isCombatRunning || battleEngine.isBattleOver) return;
            battleEngine.currentActingTroopId = 2;
            TriggerCast(false);
        }

        private void TriggerCast(bool leftAttacking)
        {
            if (combatCoroutine != null)
            {
                StopCoroutine(combatCoroutine);
            }
            combatCoroutine = StartCoroutine(CoExecuteTroopCombat(leftAttacking));
        }

        /// <summary>
        /// 完整还原《冒险与挖矿》troop.lua 与 role_action.csv 的军团整体冲锋施法与整体受击震颤流程
        /// </summary>
        private System.Collections.IEnumerator CoExecuteTroopCombat(bool leftAttacking)
        {
            isCombatRunning=true;
            BattleTurnReport report;
            do
            {
                report=battleEngine.ExecuteNextTurn(false);
                yield return CoPlayTroopAction(report);
            }while(report.hasContinuation&&!battleEngine.isBattleOver);
            isCombatRunning=false;combatCoroutine=null;
        }
        private System.Collections.IEnumerator CoPlayTroopAction(BattleTurnReport report)
        {
            bool leftAttacking;
            leftAttacking=report.actingTroopId==leftTroop.troopId;lastAttackerWasLeft=leftAttacking;
            BattleEffectPlayer.PrepareSkillEffect(report.skill);
            var attackers=leftAttacking?leftSlots:rightSlots;var defenders=leftAttacking?rightSlots:leftSlots;
            int animationId=report.skill!=null?report.skill.animationId:1329;
            var timing=EffectTimingConfig.For(animationId);
            float scale;bool direction;var frames=BattleEffectPlayer.Instance.GetFrames(animationId,out scale,out direction);
            var timeline=new BattlePresentationTimeline(timing,frames==null?0:frames.Length);
            int reactionType=timing.reactionType;
            string reactionName=HitReactionNames[Mathf.Clamp(reactionType-1,0,HitReactionNames.Length-1)];
            combatStatusText=report.logText;
            if(turnTowardsEnemyOnAttack){
                foreach(var member in attackers)if(member!=null)member.SetDirectionOverride(leftAttacking?2:1);
                foreach(var member in defenders)if(member!=null)member.SetDirectionOverride(leftAttacking?1:2);
            }
            Vector3 physicsCenter=Vector3.zero;int activeCount=0;
            foreach(var member in defenders)if(member!=null&&member.gameObject.activeInHierarchy&&member.CharacterData!=null){physicsCenter+=member.BasePosition;activeCount++;}
            if(activeCount>0)physicsCenter/=activeCount;
            bool effectDone=false,damageDone=false,physicsDone=false,healDone=report.healDone<=0;
            StartCoroutine(CoEffectCue(report.skill,attackers,defenders,leftAttacking,timeline.effectStart-timeline.startTime,()=>effectDone=true));
            StartCoroutine(CoDamageCue(report,leftAttacking,timeline.damageTime-timeline.startTime,()=>damageDone=true));
            StartCoroutine(CoPhysicsCue(defenders,leftAttacking,reactionType,physicsCenter,timeline.physicsTime-timeline.startTime,timeline.rotations,timeline.rotationDuration,timing.scatterDistanceScale,()=>physicsDone=true));
            if(report.healDone>0)StartCoroutine(CoHealCue(report,leftAttacking,timeline.healTime-timeline.startTime,()=>healDone=true));
            float time=timeline.startTime;bool flashed=false;
            while(time<timeline.endTime){
                float distance=timeline.AttackOffset(time)*(leftAttacking?1:-1);
                foreach(var member in attackers)if(member!=null)member.SetActionOffset(new Vector3(distance,0,0));
                if(!flashed&&time>=timeline.Contact){
                    flashed=true;foreach(var member in attackers)if(member!=null)member.SetFlashColor(new Color(2,2,1.4f,1));
                    StartCoroutine(CoResetAttackersFlash(attackers,.06f));
                }
                yield return null;time+=Time.deltaTime;
            }
            // Delayed coroutine cues may resume one frame after the nominal timeline ends.
            // Finish this report before a recursive skill replaces the pending presentation report.
            while(!effectDone||!damageDone||!physicsDone||!healDone)yield return null;
            foreach(var member in attackers)if(member!=null)member.ResetCombatState();
            foreach(var member in defenders)if(member!=null)member.ResetCombatState();
            combatStatusText=string.Format("待命 (当前受击模式: {0})",reactionName);
        }
        private System.Collections.IEnumerator CoEffectCue(BattleSkill skill,BattleCharacterPreview[] attackers,BattleCharacterPreview[] defenders,bool leftAttacking,float delay,System.Action complete=null)
        {
            if(delay>0)yield return new WaitForSeconds(delay);
            BattleEffectPlayer.PlaySkillEffect(skill,BattleFormationCenter.GetCenter(attackers),BattleFormationCenter.GetCenter(defenders),leftAttacking,attackers,defenders);
            complete?.Invoke();
        }

        private System.Collections.IEnumerator CoDamageCue(BattleTurnReport report, bool leftAttacking, float delay,System.Action complete=null)
        {
            if(delay>0)yield return new WaitForSeconds(delay);
            // 战力机制与血条更新：防守方承受伤害并驱动血条扣减与真实飘字
            bool isDefenderLeft = !leftAttacking;

            if(!report.isDodge&&report.damageDealt>0)
            {
                var defenders=isDefenderLeft?leftSlots:rightSlots;
                foreach(var member in defenders)if(member!=null&&member.gameObject.activeInHierarchy)member.PlayDamageFlash();
                CameraShakeController.ShakeByDamage(report.damageDealt,report.defenderMaxBP);
            }

            if (healthBarUI != null)
            {
                Vector2 targetPos = isDefenderLeft ? new Vector2(460, 560) : new Vector2(1460, 560);
                if (report.isDodge)
                {
                    healthBarUI.SpawnCustomFloatingText(targetPos, "MISS 闪避!", Color.cyan, 1.25f);
                }
                else if (report.damageDealt > 0)
                {
                    Color textColor = report.isCrit 
                        ? new Color(1.0f, 0.85f, 0.1f, 1f) 
                        : (report.isTrueDamage ? new Color(0.85f, 0.45f, 1.0f, 1f) : new Color(1.0f, 0.28f, 0.28f, 1f));
                    string prefix = report.isCrit ? "暴击 " : (report.isTrueDamage ? "真伤 " : "");
                    healthBarUI.SpawnCustomFloatingText(targetPos, string.Format("{0}-{1:N0}!", prefix, report.damageDealt), textColor, report.isCrit ? 1.4f : 1.15f);
                    int defenderShield = isDefenderLeft ? leftTroop.shieldBP : rightTroop.shieldBP;
                    healthBarUI.ApplyDamage(isDefenderLeft, report.damageDealt, report.isCrit, report.defenderCurrentBP, report.defenderMaxBP, defenderShield);
                }

                if (isDefenderLeft) leftCurrentBP = report.defenderCurrentBP;
                else rightCurrentBP = report.defenderCurrentBP;
                combatRound = report.round;
                healthBarUI.SetRoundText(string.Format("第 {0} 回合", combatRound));
            }

            if (report.healDone <= 0)
            {
                battleEngine.PublishPresentationCue(report);
            }
            complete?.Invoke();
        }

        private System.Collections.IEnumerator CoHealCue(BattleTurnReport report, bool leftAttacking, float delay,System.Action complete=null)
        {
            if (delay > 0) yield return new WaitForSeconds(delay);
            bool isActingLeft = leftAttacking;

            if (healthBarUI != null && report.healDone > 0)
            {
                Vector2 healPos = isActingLeft ? new Vector2(460, 620) : new Vector2(1460, 620);
                healthBarUI.SpawnCustomFloatingText(healPos, string.Format("+{0:N0}", report.healDone), new Color(0.2f, 0.95f, 0.4f, 1f), 1.25f);
                int actingShield = isActingLeft ? leftTroop.shieldBP : rightTroop.shieldBP;
                healthBarUI.ApplyHeal(isActingLeft, report.healDone, report.actingCurrentBP, report.actingMaxBP, actingShield);
                if (isActingLeft) leftCurrentBP = report.actingCurrentBP;
                else rightCurrentBP = report.actingCurrentBP;
            }

            battleEngine.PublishPresentationCue(report);
            complete?.Invoke();
        }

        private System.Collections.IEnumerator CoPhysicsCue(BattleCharacterPreview[] defenders, bool leftAttacking, int reactionType, Vector3 centerPos, float startDelay,int rotations,float rotationDuration,float scatterDistanceScale=1.0f,System.Action complete=null)
        {
            if(startDelay>0)yield return new WaitForSeconds(startDelay);
            bool isFacingRight = !leftAttacking; // 受击方是否面向右侧

            for (int i = 0; i < defenders.Length; i++)
            {
                if (defenders[i] == null||!defenders[i].gameObject.activeInHierarchy) continue;

                int col = i / 5;
                float delay = 0f;
                float intensity = 1.0f;
                Vector3 scatterDir = Vector3.up;

                // 距受击前排的相对列序号 (0: 最靠近施法方的最前排, 5: 远离施法方的最后排)
                int rankFromFront = leftAttacking ? col : (5 - col);

                // 模式 5 (波浪状)：从最靠近施法方的前排依次向后排传递多米诺大浪
                if (reactionType == 5)
                {
                    delay = rankFromFront * 0.045f;
                    intensity = 1.0f;
                }
                // 模式 6 (中心炸散)：从受击军团中心向外强力放射
                else if (reactionType == 6)
                {
                    Vector3 diff = defenders[i].transform.position - centerPos;
                    scatterDir = diff.sqrMagnitude > 0.01f ? diff.normalized : UnityEngine.Random.insideUnitSphere;
                    scatterDir.z = 0f;
                    delay = 0f;
                    intensity = 1.0f;
                }
                // 模式 7 (手风琴压缩)：前排承受最高挤压位移，逐层向后衰减，并在极限压缩状态明显停留
                else if (reactionType == 7)
                {
                    delay = 0f;
                    intensity = Mathf.Lerp(2.2f, 0.15f, rankFromFront / 5.0f);
                }
                // 模式 8 (地震颠簸)：整军阵列互相之间间距微幅拉大 (无单一爆炸中心，而是行列间距均匀微扩)
                else if (reactionType == 8)
                {
                    int row = i % 5;
                    float deltaSpacingX = 0.16f;
                    float deltaSpacingY = 0.12f;
                    scatterDir = new Vector3((col - 2.5f) * deltaSpacingX, -(row - 2.0f) * deltaSpacingY, 0f);
                    delay = 0f;
                    intensity = 1.0f;
                }
                // 模式 9 (中心聚拢吸附)：传入从当前单位指向受击军团中心的向心向量 (适配黑洞/虫洞/引力坍缩)
                else if (reactionType == 9)
                {
                    scatterDir = centerPos - defenders[i].transform.position;
                    scatterDir.z = 0f;
                    delay = 0f;
                    intensity = 1.0f;
                }
                // 模式 10 (集体旋转散开)：传入当前单位相对于受击军团中心的半径向量 (适配漩涡/波纹/风暴回旋)
                else if (reactionType == 10)
                {
                    scatterDir = defenders[i].transform.position - centerPos;
                    scatterDir.z = 0f;
                    delay = 0f;
                    intensity = 1.0f;
                }
                else
                {
                    delay = 0f;
                    intensity = 1.0f;
                }

                defenders[i].PlayHitReaction(reactionType, isFacingRight, intensity, delay, scatterDir,rotations,rotationDuration,scatterDistanceScale);
            }
            complete?.Invoke();
        }
        public BattleCharacterPreview[] LeftSlots => leftSlots;
        public BattleCharacterPreview[] RightSlots => rightSlots;

        private System.Collections.IEnumerator CoResetAttackersFlash(BattleCharacterPreview[] attackers, float delay)
        {
            yield return new WaitForSeconds(delay);
            if (attackers != null)
            {
                for (int i = 0; i < attackers.Length; i++)
                {
                    if (attackers[i] != null) attackers[i].SetFlashColor(Color.white);
                }
            }
        }
        #endregion

        public enum FormationDisplayMode
        {
            Standard30 = 0,     // 最终30人标准原版阵列 (5行x6列矩形对峙，由FormationConfig控制)
            DynamicPyramid = 1  // 1~30人动态对称演化阵型 (第一排1/3/5顶点，严禁2/4)
        }

        [Header("阵型排布模式与动态人数算法测试")]
        public FormationDisplayMode formationMode = FormationDisplayMode.Standard30;
        [Range(1, 30)] public int dynamicTroopCount = 30; // 动态测试人数 (1~30)
        public int dynamicFrontType = 1; // 顶点人数: 1, 3, 5

        [ContextMenu("实时应用阵列间距布局")]
        public void ApplyFormationLayout()
        {
            if (formation == null) return;
            var camera=Camera.main;float centerX=0;
            if(camera!=null){var shake=camera.GetComponent<CameraShakeController>();centerX=shake!=null?shake.RestWorldPosition.x:camera.transform.position.x;}
            float centerOffset=centerX-(formation.leftOriginX+formation.rightOriginX)*.5f;

            if (formationMode == FormationDisplayMode.Standard30)
            {
                // 最终30人标准原版阵列 (5行x6列矩形对峙，支持奇数行交错偏移，绝不修改最终30人排列方式)
                for (int i = 0; i < 30; i++)
                {
                    int row = i % 5;
                    int col = i / 5;
                    float xOffset = col * formation.spacingX + (row % 2 == 1 ? formation.rowStaggerX : 0f);
                    float y = formation.originY - row * formation.spacingY;
                    int baseOrder = Mathf.RoundToInt((10f - y) * 200f);

                    if (leftSlots != null && i < leftSlots.Length && leftSlots[i] != null)
                    {
                        leftSlots[i].gameObject.SetActive(true);
                        Vector3 pos = new Vector3(formation.leftOriginX + centerOffset - xOffset, y, 0f);
                        leftSlots[i].SetBasePosition(pos);
                        leftSlots[i].SetSortingOrder(baseOrder + col * 2);
                    }

                    if (rightSlots != null && i < rightSlots.Length && rightSlots[i] != null)
                    {
                        rightSlots[i].gameObject.SetActive(true);
                        Vector3 pos = new Vector3(formation.rightOriginX + centerOffset + xOffset, y, 0f);
                        rightSlots[i].SetBasePosition(pos);
                        rightSlots[i].SetSortingOrder(baseOrder + col * 2);
                    }
                }
            }
            else
            {
                // 1 到 30 人动态演进三角形对称阵型 (第一排优先保持 1/3/5 的排列，严禁 2/4)
                int count = Mathf.Clamp(dynamicTroopCount, 1, 30);
                int front = (dynamicFrontType == 3 || dynamicFrontType == 5) ? dynamicFrontType : 1;

                List<FormationAlgorithm.FormationSlot> leftSlotsForm = FormationAlgorithm.GenerateSlots(count, formation.spacingX, formation.spacingY, true, front);
                List<FormationAlgorithm.FormationSlot> rightSlotsForm = FormationAlgorithm.GenerateSlots(count, formation.spacingX, formation.spacingY, false, front);

                for (int i = 0; i < 30; i++)
                {
                    if (i < count && i < leftSlotsForm.Count)
                    {
                        if (leftSlots != null && i < leftSlots.Length && leftSlots[i] != null)
                        {
                            leftSlots[i].gameObject.SetActive(true);
                            var slot = leftSlotsForm[i];
                            Vector3 pos = new Vector3(formation.leftOriginX + centerOffset + slot.xOffset, formation.originY + slot.yOffset, 0f);
                            leftSlots[i].SetBasePosition(pos);
                            int baseOrder = Mathf.RoundToInt((10f - pos.y) * 200f);
                            leftSlots[i].SetSortingOrder(baseOrder + slot.colInRow * 2);
                        }

                        if (rightSlots != null && i < rightSlots.Length && rightSlots[i] != null)
                        {
                            rightSlots[i].gameObject.SetActive(true);
                            var slot = rightSlotsForm[i];
                            Vector3 pos = new Vector3(formation.rightOriginX + centerOffset + slot.xOffset, formation.originY + slot.yOffset, 0f);
                            rightSlots[i].SetBasePosition(pos);
                            int baseOrder = Mathf.RoundToInt((10f - pos.y) * 200f);
                            rightSlots[i].SetSortingOrder(baseOrder + slot.colInRow * 2);
                        }
                    }
                    else
                    {
                        // 动态人数少于 30 时，隐藏多余槽位以清晰展示当前 N 人阵型结构
                        if (leftSlots != null && i < leftSlots.Length && leftSlots[i] != null)
                        {
                            leftSlots[i].gameObject.SetActive(false);
                        }
                        if (rightSlots != null && i < rightSlots.Length && rightSlots[i] != null)
                        {
                            rightSlots[i].gameObject.SetActive(false);
                        }
                    }
                }
            }
        }

        [ContextMenu("50选30满级策略阵容对决")]
        public void DraftStrategyBattle()
        {
            if (database == null || database.characters == null || database.characters.Count == 0) return;
            StopAllCoroutines(); isCombatRunning = false; autoCombat = false;

            // 确保使用最终 30 人标准对峙阵型
            formationMode = FormationDisplayMode.Standard30;

            // 按当前阶段构建主C、保底与填充成员，并绑定各自装备。
            var leftDraft = BattleRosterStrategy.BuildStrategyRoster(database, "左军策略军团", battleStage, playerFlow, useMaxLevel, useTopEquipment);
            var rightDraft = useFixedEncounter ? BattleRosterStrategy.BuildEncounterRoster(database, battleStage, encounterDifficulty) :
                BattleRosterStrategy.BuildStrategyRoster(database, "右军策略军团", battleStage, opponentFlow, useMaxLevel, useTopEquipment);

            for (int i = 0; i < 30; i++)
            {
                if (leftSlots != null && i < leftSlots.Length && leftSlots[i] != null && i >= leftDraft.selected30.Count) leftSlots[i].SetCharacter(null);
                if (rightSlots != null && i < rightSlots.Length && rightSlots[i] != null && i >= rightDraft.selected30.Count) rightSlots[i].SetCharacter(null);
                if (leftSlots != null && i < leftSlots.Length && leftSlots[i] != null && i < leftDraft.selected30.Count)
                {
                    leftSlots[i].SetCharacter(leftDraft.selected30[i].sheetData);
                }
                if (rightSlots != null && i < rightSlots.Length && rightSlots[i] != null && i < rightDraft.selected30.Count)
                {
                    rightSlots[i].SetCharacter(rightDraft.selected30[i].sheetData);
                }
            }

            ApplyFormationLayout();

            leftTroop.InitializeFromMembers(leftDraft.selected30);
            rightTroop.InitializeFromMembers(rightDraft.selected30);
            if (useFixedEncounter)
            {
                var encounter = BattleRuntimeCatalogue.Encounter(battleStage, encounterDifficulty);
                rightTroop.alpha = encounter.alpha; rightTroop.beta = encounter.beta;
            }

            battleEngine.InitBattle(leftTroop, rightTroop);
            leftMaxBP = leftTroop.maxBP;
            rightMaxBP = rightTroop.maxBP;
            leftCurrentBP = leftTroop.currentBP;
            rightCurrentBP = rightTroop.currentBP;
            combatRound = 1;

            if (healthBarUI != null)
            {
                healthBarUI.SetTroopMaxBP(leftMaxBP, rightMaxBP);
                healthBarUI.ResetBars();
                healthBarUI.SetRoundText("第 1 回合");
            }

            combatStatusText = string.Format("阶段{0} | {1}人 | {2} VS {3} | BP:{4:N0}/{5:N0}", battleStage,
                leftDraft.selected30.Count, playerFlow, useFixedEncounter ? encounterDifficulty : opponentFlow, leftMaxBP, rightMaxBP);
            Debug.Log(combatStatusText);
        }

        [ContextMenu("记录并保存当前数值到配置文件")]
        public void SaveFormationConfig()
        {
            if (formation != null)
            {
                formation.Save();
                saveFeedbackText = string.Format("数值已成功记录保存！\n左第1位=({0:F2}, {1:F2}) | 右第1位=({2:F2}, {1:F2})\n横向间距={3:F2} | 纵向间距={4:F2} | 交错={5:F2}",
                    formation.leftOriginX, formation.originY, formation.rightOriginX, formation.spacingX, formation.spacingY, formation.rowStaggerX);
                saveFeedbackTimer = 5.0f;
            }
        }

        private void OnValidate()
        {
            ApplyFormationLayout();
        }

        [ContextMenu("下一波")]
        public void NextWave()
        {
            if (TotalWaves <= 0) return;
            currentWaveIndex = (currentWaveIndex + 1) % TotalWaves;
            ApplyWave(currentWaveIndex);
            ClearEventSystemSelection();
        }

        [ContextMenu("上一波")]
        public void PrevWave()
        {
            if (TotalWaves <= 0) return;
            currentWaveIndex = (currentWaveIndex - 1 + TotalWaves) % TotalWaves;
            ApplyWave(currentWaveIndex);
            ClearEventSystemSelection();
        }

        private void ClearEventSystemSelection()
        {
            if (UnityEngine.EventSystems.EventSystem.current != null)
            {
                UnityEngine.EventSystems.EventSystem.current.SetSelectedGameObject(null);
            }
        }

        private int debugTab = 0; // 0: 受击动力学调试 (8种模式), 1: 阵列点位与间距 (防折叠)
        private Vector2 tuningScroll;
        private static readonly string[] debugTabTitles = new string[] { "八种受击动力学调试", "阵列点位与间距调节" };

        public void ApplyWave(int waveIndex)
        {
            currentWaveIndex = waveIndex;
            if (database == null || database.characters == null) return;

            int total = database.characters.Count;
            int startIndex = waveIndex * CharactersPerWave;
            var rule = BattleRuntimeCatalogue.Stage(battleStage);

            // 1. 构建左军上阵成员 (支持动态战力与技能挂载)
            System.Collections.Generic.List<BattleMember> leftMembers = new System.Collections.Generic.List<BattleMember>();
            for (int i = 0; i < 30; i++)
            {
                if (leftSlots == null || i >= leftSlots.Length || leftSlots[i] == null) continue;
                int charIndex = startIndex + i;
                leftSlots[i].SetDefaultDirection(0);
                if (charIndex < total && i < rule.members)
                {
                    CharacterSheetData cdata = database.characters[charIndex];
                    leftSlots[i].SetCharacter(cdata);
                    if (cdata != null)
                    {
                        BattleMember m = BattleMember.FromSheetData(cdata, i);
                        // 为成员分配其阶位的流派代表技能
                        m.rarityTier = Math.Min(m.rarityTier, rule.tier);
                        m.skills.Add(BattleSkillDatabase.GetRandomSkillForTier(m.rarityTier));
                        BattleRosterStrategy.ConfigureReferenceMember(m, m.skills[0], battleStage, playerFlow, useMaxLevel ? 30 : rule.upper, useTopEquipment);
                        leftMembers.Add(m);
                    }
                }
                else
                {
                    leftSlots[i].SetCharacter(null);
                }
            }

            // 2. 构建右军上阵成员
            System.Collections.Generic.List<BattleMember> rightMembers = new System.Collections.Generic.List<BattleMember>();
            for (int i = 0; i < 30; i++)
            {
                if (rightSlots == null || i >= rightSlots.Length || rightSlots[i] == null) continue;
                int charIndex = startIndex + 30 + i;
                rightSlots[i].SetDefaultDirection(0);
                if (charIndex < total && i < rule.members)
                {
                    CharacterSheetData cdata = database.characters[charIndex];
                    rightSlots[i].SetCharacter(cdata);
                    if (cdata != null)
                    {
                        BattleMember m = BattleMember.FromSheetData(cdata, i);
                        m.rarityTier = Math.Min(m.rarityTier, rule.tier);
                        m.skills.Add(BattleSkillDatabase.GetRandomSkillForTier(m.rarityTier));
                        BattleRosterStrategy.ConfigureReferenceMember(m, m.skills[0], battleStage, opponentFlow, useMaxLevel ? 30 : rule.upper, useTopEquipment);
                        rightMembers.Add(m);
                    }
                }
                else
                {
                    rightSlots[i].SetCharacter(null);
                }
            }

            // 3. 驱动战团与核心战斗引擎初始化 (依据先攻决定先手)
            if (leftMembers.Count == 0 || rightMembers.Count == 0) { DraftStrategyBattle(); return; }
            leftTroop.InitializeFromMembers(leftMembers);
            rightTroop.InitializeFromMembers(rightMembers);
            battleEngine.InitBattle(leftTroop, rightTroop);

            leftMaxBP = leftTroop.maxBP;
            leftCurrentBP = leftTroop.currentBP;
            rightMaxBP = rightTroop.maxBP;
            rightCurrentBP = rightTroop.currentBP;
            combatRound = 1;

            if (healthBarUI != null)
            {
                healthBarUI.SetTroopMaxBP(leftMaxBP, rightMaxBP);
                healthBarUI.SetRoundText(string.Format("第 {0} 回合", combatRound));
            }

            combatStatusText = string.Format("【战斗就绪】先攻: 左军({0}) vs 右军({1}) -> {2}",
                leftTroop.speed, rightTroop.speed,
                (battleEngine.currentActingTroopId == 1 ? "左军先手" : "右军先手"));

            // 更新 UI 文本
            if (txtWaveInfo != null)
            {
                int startDisplay = total > 0 ? startIndex + 1 : 0;
                int endDisplay = Mathf.Min(startIndex + CharactersPerWave, total);
                txtWaveInfo.text = string.Format("第 {0} / {1} 波 ({2}~{3} / {4})",
                    waveIndex + 1, TotalWaves, startDisplay, endDisplay, total);
#if UNITY_EDITOR
                UnityEditor.EditorUtility.SetDirty(txtWaveInfo);
#endif
            }

#if UNITY_EDITOR
            UnityEditor.EditorUtility.SetDirty(this);
#endif
        }

        public void StopBattlePlayback()
        {
            StopAllCoroutines(); isCombatRunning = false; autoCombat = false;
        }

        public void StartBattleFromRosters(List<BattleMember> left, List<BattleMember> right, CombatMacro enemyMacro = null, int? seed = null, string leftName = "我方", string rightName = "敌方", CombatPersistentLimits playerLimits = null, OpeningBondRules leftBonds = null, OpeningBondRules rightBonds = null, CombatEvasionRules leftEvasion = null, CombatEvasionRules rightEvasion = null, int memberCapacity = 0, CombatSupportRules leftSupport = null, CombatSupportRules rightSupport = null, CombatAmplificationRules leftAmplification = null, CombatAmplificationRules rightAmplification = null, CombatAugmentationRules leftAugmentation = null, CombatAugmentationRules rightAugmentation = null)
        {
            StopBattlePlayback();
            leftTroop = new BattleTroop(1,leftName); rightTroop = new BattleTroop(2,rightName);
            leftTroop.persistentLimits = playerLimits == null ? null : playerLimits.Clone();
            leftTroop.openingBonds = leftBonds == null ? null : leftBonds.Clone();
            rightTroop.openingBonds = rightBonds == null ? null : rightBonds.Clone();
            leftTroop.evasionBonds=leftEvasion==null?null:leftEvasion.Clone();rightTroop.evasionBonds=rightEvasion==null?null:rightEvasion.Clone();
            leftTroop.memberCapacity=rightTroop.memberCapacity=memberCapacity;
            leftTroop.supportBonds=leftSupport==null?null:leftSupport.Clone();rightTroop.supportBonds=rightSupport==null?null:rightSupport.Clone();
            leftTroop.amplificationBonds=leftAmplification==null?null:leftAmplification.Clone();rightTroop.amplificationBonds=rightAmplification==null?null:rightAmplification.Clone();
            leftTroop.augmentationBonds=leftAugmentation==null?null:leftAugmentation.Clone();rightTroop.augmentationBonds=rightAugmentation==null?null:rightAugmentation.Clone();
            leftTroop.InitializeFromMembers(left); rightTroop.InitializeFromMembers(right);
            if(enemyMacro!=null)
            { rightTroop.alpha=enemyMacro.alpha;rightTroop.beta=enemyMacro.beta;rightTroop.gamma=enemyMacro.gamma;rightTroop.delta=enemyMacro.delta;rightTroop.theta=enemyMacro.theta;rightTroop.mu=enemyMacro.mu; }
            battleEngine.InitBattle(leftTroop,rightTroop,seed);
            formationMode=FormationDisplayMode.Standard30;ApplyFormationLayout();
            ApplyRosterVisuals(leftSlots,left);ApplyRosterVisuals(rightSlots,right);
            leftMaxBP=leftTroop.maxBP;rightMaxBP=rightTroop.maxBP;leftCurrentBP=leftTroop.currentBP;rightCurrentBP=rightTroop.currentBP;combatRound=1;
            if(healthBarUI!=null)
            {
                healthBarUI.SetTroopMaxBP(leftMaxBP,rightMaxBP);healthBarUI.ResetBars();healthBarUI.SetRoundText("第 1 回合");
                healthBarUI.ApplyDamage(true,0,false,leftCurrentBP,leftMaxBP,leftTroop.shieldBP);
                healthBarUI.ApplyDamage(false,0,false,rightCurrentBP,rightMaxBP,rightTroop.shieldBP);
            }
        }
        private void ApplyRosterVisuals(BattleCharacterPreview[] slots,List<BattleMember> roster)
        {
            if(slots==null)return;
            for(int i=0;i<slots.Length;i++)
            {
                if(slots[i]==null)continue;
                CharacterSheetData sheet=i<roster.Count?roster[i].sheetData:null;
                if(i<roster.Count && (sheet==null||!sheet.IsValid) && database!=null)
                    sheet=database.characters.Find(x=>x!=null&&x.IsValid);
                slots[i].gameObject.SetActive(i<roster.Count);slots[i].SetCharacter(sheet);
            }
        }

        [ContextMenu("重置双方战力为满战力")]
        public void ResetBattlePower()
        {
            if (leftTroop != null && rightTroop != null)
            {
                leftTroop.currentBP = leftTroop.maxBP;
                leftTroop.shieldBP = 0;
                leftTroop.buffs.Clear();
                leftTroop.exhaustTurns = 0;
                leftTroop.resistLethalCount = 0;

                rightTroop.currentBP = rightTroop.maxBP;
                rightTroop.shieldBP = 0;
                rightTroop.buffs.Clear();
                rightTroop.exhaustTurns = 0;
                rightTroop.resistLethalCount = 0;

                battleEngine.InitBattle(leftTroop, rightTroop);
                leftCurrentBP = leftTroop.currentBP;
                rightCurrentBP = rightTroop.currentBP;
                combatRound = 1;
            }

            if (healthBarUI != null)
            {
                healthBarUI.ResetBars();
                healthBarUI.SetRoundText("第 1 回合");
            }
            combatStatusText = string.Format("已重置双方战力为满战力状态 | 先手: {0}",
                (battleEngine.currentActingTroopId == 1 ? "左军先手" : "右军先手"));
        }

        [ContextMenu("全场极速模拟推演")]
        public void SimulateAndPrintBattle()
        {
            if (leftTroop == null || rightTroop == null) return;
            ResetBattlePower();
            var reports = battleEngine.SimulateFullBattle(100);
            Debug.Log(string.Format("=== 全场极速模拟推演完毕 (共耗时 {0} 回合) ===", reports.Count));
            for (int i = 0; i < reports.Count && i < 10; i++)
            {
                Debug.Log(reports[i].logText);
            }
            if (reports.Count > 10)
            {
                Debug.Log(string.Format("... [中间省略 {0} 回合详细战报] ...", reports.Count - 10));
                Debug.Log(reports[reports.Count - 1].logText);
            }

            leftCurrentBP = leftTroop.currentBP;
            rightCurrentBP = rightTroop.currentBP;
            combatRound = battleEngine.currentRound;

            if (healthBarUI != null)
            {
                healthBarUI.ApplyDamage(true, 0, false, leftTroop.currentBP, leftTroop.maxBP);
                healthBarUI.ApplyDamage(false, 0, false, rightTroop.currentBP, rightTroop.maxBP);
                healthBarUI.SetRoundText(string.Format("第 {0} 回合", combatRound));
            }

            combatStatusText = reports.Count > 0 ? reports[reports.Count - 1].logText : "模拟结束";
        }

        public void SetTroopFacingCombat()
        {
            if (leftSlots != null)
            {
                for (int i = 0; i < leftSlots.Length; i++)
                {
                    if (leftSlots[i] != null) leftSlots[i].SetDefaultDirection(2);
                }
            }
            if (rightSlots != null)
            {
                for (int i = 0; i < rightSlots.Length; i++)
                {
                    if (rightSlots[i] != null) rightSlots[i].SetDefaultDirection(1);
                }
            }
            combatStatusText = "已切换为两军对峙朝向 (左军面向右，右军面向左)";
        }

        public void SetTroopFacingFront()
        {
            if (leftSlots != null)
            {
                for (int i = 0; i < leftSlots.Length; i++)
                {
                    if (leftSlots[i] != null) leftSlots[i].SetDefaultDirection(0);
                }
            }
            if (rightSlots != null)
            {
                for (int i = 0; i < rightSlots.Length; i++)
                {
                    if (rightSlots[i] != null) rightSlots[i].SetDefaultDirection(0);
                }
            }
            combatStatusText = "已重置为默认全员朝下正面朝向 (朝向玩家)";
        }

        private void OnGUI()
        {
            if (productionMode) return;
            // 顶部左侧：调距面板折叠按钮
            if (GUI.Button(new Rect(16, 14, 130, 32), showAdjustmentGUI ? "收起调试面板 (F2)" : "展开调试面板 (F2)"))
            {
                showAdjustmentGUI = !showAdjustmentGUI;
            }

            // 顶部战斗演练控制栏 (依据 role_action.csv / troop.lua / BattleDataModels.cs)
            string curReactionName = HitReactionNames[Mathf.Clamp(currentHitReactionType - 1, 0, HitReactionNames.Length - 1)];
            GUI.backgroundColor = new Color(0.95f, 0.75f, 0.2f, 1f);
            if (GUI.Button(new Rect(152, 14, 210, 32), string.Format("受击模式: {0} (H)", curReactionName)))
            {
                currentHitReactionType = (currentHitReactionType % HitReactionNames.Length) + 1;
                combatStatusText = string.Format("已切换受击方式: {0}", HitReactionNames[currentHitReactionType - 1]);
                TriggerNextCast();
            }

            GUI.backgroundColor = new Color(0.2f, 0.6f, 1f, 1f);
            if (GUI.Button(new Rect(368, 14, 96, 32), "左军施法 (1)"))
            {
                TriggerLeftCast();
            }

            GUI.backgroundColor = new Color(1f, 0.4f, 0.3f, 1f);
            if (GUI.Button(new Rect(470, 14, 96, 32), "右军施法 (2)"))
            {
                TriggerRightCast();
            }

            GUI.backgroundColor = autoCombat ? new Color(0.2f, 0.85f, 0.3f, 1f) : new Color(0.7f, 0.7f, 0.7f, 1f);
            if (GUI.Button(new Rect(572, 14, 120, 32), autoCombat ? "自动对攻 [开] (V)" : "自动对攻 [关] (V)"))
            {
                autoCombat = !autoCombat;
            }

            GUI.backgroundColor = BattleCharacterPreview.autoRotateDirections ? new Color(0.3f, 0.8f, 0.9f, 1f) : new Color(0.7f, 0.7f, 0.7f, 1f);
            if (GUI.Button(new Rect(698, 14, 120, 32), BattleCharacterPreview.autoRotateDirections ? "四向巡回 [开] (R)" : "四向巡回 [关] (R)"))
            {
                BattleCharacterPreview.autoRotateDirections = !BattleCharacterPreview.autoRotateDirections;
            }

            GUI.backgroundColor = new Color(0.2f, 0.85f, 0.5f, 1f);
            if (GUI.Button(new Rect(826, 14, 110, 32), "满战力重置 (B)"))
            {
                ResetBattlePower();
            }

            GUI.backgroundColor = new Color(1.0f, 0.45f, 0.1f, 1f);
            if (GUI.Button(new Rect(942, 14, 175, 32), "50选30策略对决 (G)"))
            {
                DraftStrategyBattle();
            }
            GUI.backgroundColor = Color.white;

            // 战斗状态提示
            GUI.Label(new Rect(1124, 18, 550, 26), string.Format("<size=14><b>战斗演练:</b> <color=yellow>{0}</color></size>", combatStatusText));

            if (!showAdjustmentGUI) return;

            // 半透明调试面板
            float panelWidth = 470;
            float panelHeight = 520;
            Rect panelRect = new Rect(16, 54, panelWidth, panelHeight);
            GUI.Box(panelRect, "军团调试面板 (按 F2 可快速展开/收起)");

            GUILayout.BeginArea(new Rect(panelRect.x + 12, panelRect.y + 26, panelRect.width - 24, panelRect.height - 34));
            tuningScroll = GUILayout.BeginScrollView(tuningScroll);
            GUI.changed = false;
            GUILayout.Label("人数上限");
            battleStage = GUILayout.Toolbar(battleStage-1, new[] { "5", "10", "15", "20", "25", "30" })+1;
            string[] flows = { "C_I", "C_R", "M_I", "M_R", "M_C", "R_I" };
            GUILayout.Label("我方流派");
            playerFlow = flows[GUILayout.Toolbar(Math.Max(0,Array.IndexOf(flows,playerFlow)),flows)];
            useFixedEncounter = GUILayout.Toggle(useFixedEncounter,"固定敌人");
            if (!useFixedEncounter)
            {
                GUILayout.Label("敌方流派");
                opponentFlow = flows[GUILayout.Toolbar(Math.Max(0,Array.IndexOf(flows,opponentFlow)),flows)];
            }
            if (useFixedEncounter)
            {
                string[] difficulties = { "hard", "very_hard", "extremely_hard" };
                encounterDifficulty = difficulties[GUILayout.Toolbar(Math.Max(0,Array.IndexOf(difficulties,encounterDifficulty)),new[] { "难", "很难", "非常难" })];
            }
            useTopEquipment = GUILayout.Toggle(useTopEquipment,"最多4件顶级装备");
            useMaxLevel = GUILayout.Toggle(useMaxLevel,"30级满级");
            if (GUI.changed) DraftStrategyBattle();

            // 分页标签
            debugTab = GUILayout.Toolbar(debugTab, debugTabTitles, GUILayout.Height(30));
            GUILayout.Space(8);

            if (debugTab == 0)
            {
                // Tab 0: 十种受击动力学调试
                GUILayout.Label("<b>【十种受击动力学模式】(点击任意按钮切换并立即演练):</b>");
                GUILayout.Space(4);

                // 2列5行表格渲染10种受击模式
                int totalRows = (HitReactionNames.Length + 1) / 2;
                for (int row = 0; row < totalRows; row++)
                {
                    GUILayout.BeginHorizontal();
                    for (int col = 0; col < 2; col++)
                    {
                        int typeIndex = row * 2 + col + 1; // 1 ~ 10
                        if (typeIndex > HitReactionNames.Length) break;
                        bool isSelected = (currentHitReactionType == typeIndex);
                        GUI.backgroundColor = isSelected ? new Color(0.2f, 0.95f, 0.35f, 1f) : new Color(0.92f, 0.92f, 0.92f, 1f);

                        string prefix = isSelected ? "▶ " : "  ";
                        if (GUILayout.Button(prefix + HitReactionNames[typeIndex - 1], GUILayout.Height(30)))
                        {
                            currentHitReactionType = typeIndex;
                            TriggerNextCast();
                        }
                    }
                    GUILayout.EndHorizontal();
                    GUILayout.Space(2);
                }
                GUI.backgroundColor = Color.white;

                GUILayout.Space(8);
                GUILayout.Label("<b>【施法动作演练】:</b>");
                GUILayout.BeginHorizontal();
                GUI.backgroundColor = new Color(0.2f, 0.6f, 1f, 1f);
                if (GUILayout.Button("左军冲锋施法 (1)", GUILayout.Height(30))) TriggerLeftCast();
                GUI.backgroundColor = new Color(1f, 0.4f, 0.3f, 1f);
                if (GUILayout.Button("右军冲锋施法 (2)", GUILayout.Height(30))) TriggerRightCast();
                GUI.backgroundColor = new Color(0.95f, 0.75f, 0.2f, 1f);
                if (GUILayout.Button("交替施法 (Space/C)", GUILayout.Height(30))) TriggerNextCast();
                GUI.backgroundColor = Color.white;
                GUILayout.EndHorizontal();

                GUILayout.Space(8);
                GUILayout.Label("<b>【军团朝向与巡回控制】:</b>");
                GUILayout.BeginHorizontal();
                GUI.backgroundColor = new Color(0.2f, 0.9f, 0.4f, 1f);
                if (GUILayout.Button("全员正面朝向 (默认朝下/朝向玩家)", GUILayout.Height(28)))
                {
                    SetTroopFacingFront();
                }
                GUI.backgroundColor = Color.white;
                if (GUILayout.Button("两军对峙朝向 (左朝右/右朝左)", GUILayout.Height(28)))
                {
                    SetTroopFacingCombat();
                }
                GUILayout.EndHorizontal();

                GUILayout.Space(2);
                GUILayout.BeginHorizontal();
                string turnAtkBtn = turnTowardsEnemyOnAttack ? "冲锋转向敌方: [已开启]" : "冲锋转向敌方: [已关闭 - 保持朝下朝向玩家]";
                if (GUILayout.Button(turnAtkBtn, GUILayout.Height(28)))
                {
                    turnTowardsEnemyOnAttack = !turnTowardsEnemyOnAttack;
                }
                GUILayout.EndHorizontal();

                GUILayout.Space(2);
                GUILayout.BeginHorizontal();
                string rotBtnText = BattleCharacterPreview.autoRotateDirections ? "四向自动巡回: [已开启 - 点击关闭] (R)" : "四向自动巡回: [已关闭 - 点击开启] (R)";
                GUI.backgroundColor = BattleCharacterPreview.autoRotateDirections ? new Color(0.3f, 0.8f, 0.9f, 1f) : new Color(0.85f, 0.85f, 0.85f, 1f);
                if (GUILayout.Button(rotBtnText, GUILayout.Height(28)))
                {
                    BattleCharacterPreview.autoRotateDirections = !BattleCharacterPreview.autoRotateDirections;
                }
                GUI.backgroundColor = Color.white;
                GUILayout.EndHorizontal();

                GUILayout.Space(8);
                GUILayout.Label(string.Format("<b>【军团战力状态】:</b> 左军 {0:N0}/{1:N0} | 右军 {2:N0}/{3:N0} (第 {4} 回合)", 
                    leftCurrentBP, leftMaxBP, rightCurrentBP, rightMaxBP, combatRound));
                GUILayout.Label(string.Format("<size=11>左军四维: 先攻 {0} | 坚韧 {1} | 灵敏 {2} | 统御 {3}\n右军四维: 先攻 {4} | 坚韧 {5} | 灵敏 {6} | 统御 {7}</size>",
                    leftTroop.speed, leftTroop.defense, leftTroop.dodge, leftTroop.authority,
                    rightTroop.speed, rightTroop.defense, rightTroop.dodge, rightTroop.authority));

                GUILayout.BeginHorizontal();
                GUI.backgroundColor = new Color(0.2f, 0.85f, 0.5f, 1f);
                if (GUILayout.Button("一键满战力重置 (B)", GUILayout.Height(28)))
                {
                    ResetBattlePower();
                }
                GUI.backgroundColor = new Color(0.9f, 0.5f, 0.2f, 1f);
                if (GUILayout.Button("全场极速演算 (Simulate)", GUILayout.Height(28)))
                {
                    SimulateAndPrintBattle();
                }
                GUI.backgroundColor = Color.white;
                GUILayout.EndHorizontal();

                GUILayout.Space(6);
                GUI.color = Color.yellow;
                GUILayout.Label(string.Format("实时状态: {0}", combatStatusText));
                GUI.color = Color.white;
            }
            else
            {
                // Tab 1: 阵列点位与间距 (防折叠 & 支持 1~30 人演化与 30 人原版切换)
                bool changed = false;

                // 阵型模式切换
                GUILayout.BeginHorizontal();
                bool isStd = (formationMode == FormationDisplayMode.Standard30);
                GUI.backgroundColor = isStd ? new Color(0.2f, 0.8f, 0.4f, 1f) : Color.white;
                if (GUILayout.Button("【30人标准原版阵列】", GUILayout.Height(30)))
                {
                    formationMode = FormationDisplayMode.Standard30;
                    changed = true;
                }
                GUI.backgroundColor = !isStd ? new Color(0.2f, 0.7f, 1.0f, 1f) : Color.white;
                if (GUILayout.Button("【1~30人动态对称演化】", GUILayout.Height(30)))
                {
                    formationMode = FormationDisplayMode.DynamicPyramid;
                    changed = true;
                }
                GUI.backgroundColor = Color.white;
                GUILayout.EndHorizontal();

                if (formationMode == FormationDisplayMode.DynamicPyramid)
                {
                    GUILayout.Space(6);
                    GUILayout.Label(string.Format("<b>【动态队列算法】当前测试人数: {0} 人</b>", dynamicTroopCount));
                    GUILayout.BeginHorizontal();
                    if (GUILayout.Button("-5", GUILayout.Width(40))) { dynamicTroopCount = Mathf.Clamp(dynamicTroopCount - 5, 1, 30); changed = true; }
                    if (GUILayout.Button("-1", GUILayout.Width(40))) { dynamicTroopCount = Mathf.Clamp(dynamicTroopCount - 1, 1, 30); changed = true; }
                    int newCount = Mathf.RoundToInt(GUILayout.HorizontalSlider(dynamicTroopCount, 1f, 30f));
                    if (GUILayout.Button("+1", GUILayout.Width(40))) { dynamicTroopCount = Mathf.Clamp(dynamicTroopCount + 1, 1, 30); changed = true; }
                    if (GUILayout.Button("+5", GUILayout.Width(40))) { dynamicTroopCount = Mathf.Clamp(dynamicTroopCount + 5, 1, 30); changed = true; }
                    GUILayout.EndHorizontal();
                    if (newCount != dynamicTroopCount) { dynamicTroopCount = newCount; changed = true; }

                    GUILayout.BeginHorizontal();
                    GUILayout.Label("第一排顶点(严禁2/4):", GUILayout.Width(140));
                    if (GUILayout.Toggle(dynamicFrontType == 1, "1人(尖顶)", GUILayout.Width(80))) { if (dynamicFrontType != 1) { dynamicFrontType = 1; changed = true; } }
                    if (GUILayout.Toggle(dynamicFrontType == 3, "3人(锋矢)", GUILayout.Width(80))) { if (dynamicFrontType != 3) { dynamicFrontType = 3; changed = true; } }
                    if (GUILayout.Toggle(dynamicFrontType == 5, "5人(宽锋)", GUILayout.Width(80))) { if (dynamicFrontType != 5) { dynamicFrontType = 5; changed = true; } }
                    GUILayout.EndHorizontal();

                    GUI.color = Color.cyan;
                    GUILayout.Label(FormationAlgorithm.GetFormationSummary(dynamicTroopCount, dynamicFrontType));
                    GUI.color = Color.white;
                    GUILayout.Space(4);
                }

                // 1. 第一排第一位位置
                GUILayout.Label(string.Format("左军第1位 X: {0:F2}", formation.leftOriginX));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.1", GUILayout.Width(44))) { formation.leftOriginX -= 0.1f; changed = true; }
                float newLx = GUILayout.HorizontalSlider(formation.leftOriginX, -12.0f, -2.0f);
                if (GUILayout.Button("+0.1", GUILayout.Width(44))) { formation.leftOriginX += 0.1f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newLx - formation.leftOriginX) > 0.001f) { formation.leftOriginX = newLx; changed = true; }

                GUILayout.Label(string.Format("第1排第1位 Y: {0:F2}", formation.originY));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.1", GUILayout.Width(44))) { formation.originY -= 0.1f; changed = true; }
                float newY = GUILayout.HorizontalSlider(formation.originY, 0.0f, 6.0f);
                if (GUILayout.Button("+0.1", GUILayout.Width(44))) { formation.originY += 0.1f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newY - formation.originY) > 0.001f) { formation.originY = newY; changed = true; }

                GUILayout.Label(string.Format("右军第1位 X: {0:F2}", formation.rightOriginX));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.1", GUILayout.Width(44))) { formation.rightOriginX -= 0.1f; changed = true; }
                float newRx = GUILayout.HorizontalSlider(formation.rightOriginX, -1.0f, 8.0f);
                if (GUILayout.Button("+0.1", GUILayout.Width(44))) { formation.rightOriginX += 0.1f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newRx - formation.rightOriginX) > 0.001f) { formation.rightOriginX = newRx; changed = true; }

                GUILayout.Space(6);
                // 2. 横向与纵向间距 (分开调)
                GUILayout.Label(string.Format("横向间距 (Spacing X): {0:F2}", formation.spacingX));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.05", GUILayout.Width(50))) { formation.spacingX -= 0.05f; changed = true; }
                float newSx = GUILayout.HorizontalSlider(formation.spacingX, 0.3f, 2.5f);
                if (GUILayout.Button("+0.05", GUILayout.Width(50))) { formation.spacingX += 0.05f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newSx - formation.spacingX) > 0.001f) { formation.spacingX = newSx; changed = true; }

                GUILayout.Label(string.Format("纵向间距 (Spacing Y): {0:F2}", formation.spacingY));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.05", GUILayout.Width(50))) { formation.spacingY -= 0.05f; changed = true; }
                float newSy = GUILayout.HorizontalSlider(formation.spacingY, 0.3f, 2.5f);
                if (GUILayout.Button("+0.05", GUILayout.Width(50))) { formation.spacingY += 0.05f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newSy - formation.spacingY) > 0.001f) { formation.spacingY = newSy; changed = true; }

                // 3. 奇数行交错
                GUILayout.Label(string.Format("奇数行交错 (Stagger): {0:F2}", formation.rowStaggerX));
                GUILayout.BeginHorizontal();
                if (GUILayout.Button("-0.05", GUILayout.Width(50))) { formation.rowStaggerX -= 0.05f; changed = true; }
                float newSt = GUILayout.HorizontalSlider(formation.rowStaggerX, 0.0f, 1.0f);
                if (GUILayout.Button("+0.05", GUILayout.Width(50))) { formation.rowStaggerX += 0.05f; changed = true; }
                GUILayout.EndHorizontal();
                if (Mathf.Abs(newSt - formation.rowStaggerX) > 0.001f) { formation.rowStaggerX = newSt; changed = true; }

                if (changed)
                {
                    ApplyFormationLayout();
                }

                GUILayout.Space(8);
                // 4. 记录保存数值按钮
                GUI.backgroundColor = new Color(0.2f, 0.7f, 0.3f, 1f);
                if (GUILayout.Button("【记录并保存当前数值】", GUILayout.Height(36)))
                {
                    SaveFormationConfig();
                }
                GUI.backgroundColor = Color.white;

                if (!string.IsNullOrEmpty(saveFeedbackText))
                {
                    GUI.color = Color.green;
                    GUILayout.Label(saveFeedbackText);
                    GUI.color = Color.white;
                }
            }

            GUILayout.EndScrollView();
            GUILayout.EndArea();
        }
    }
}
