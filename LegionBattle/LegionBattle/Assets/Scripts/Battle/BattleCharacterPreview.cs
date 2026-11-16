using UnityEngine;

namespace LegionBattle.Battle
{
    [RequireComponent(typeof(SpriteRenderer))]
    public class BattleCharacterPreview : MonoBehaviour
    {
        [SerializeField] private SpriteRenderer spriteRenderer;
        [SerializeField] private GameObject shadowObject;
        [SerializeField] private SpriteRenderer shadowRenderer;
        [SerializeField] private CharacterSheetData characterData;
        public CharacterSheetData CharacterData => characterData;

        private float directionTimer = 0f;
        private float frameTimer = 0f;
        private int currentDirection = 0; // 0: 正面(Down), 1: 向左(Left), 2: 向右(Right), 3: 背面(Up)
        private int currentFrame = 0;

        private const float DirectionDuration = 2.0f; // 四向动画各播放两秒
        private const float FrameDuration = 0.16f;     // 步态帧间隔时间 (~6.25 fps)

        // 四向自动展示开关 (按需求默认关闭)
        public static bool autoRotateDirections = false;
        private int defaultDirection = 0; // 0: Down, 1: Left, 2: Right, 3: Up

        // 军团整体动作系统支持 (根据 role_action.csv 与 troop.lua)
        private Vector3 basePosition = Vector3.zero;
        private Vector3 actionOffset = Vector3.zero;
        private Vector3 vibrationOffset = Vector3.zero;
        private Color flashColor = Color.white;
        private int directionOverride = -1; // -1: 默认/自动循环; >=0: 强制指定朝向
        private Coroutine hitReactionCoroutine = null;
        private Coroutine hitFlashCoroutine;
        public const float HitFlashDuration = .18f;
        public Color DisplayColor => flashColor;
        public bool IsHitReactionRunning => hitReactionCoroutine != null;

        private void Awake()
        {
            if (spriteRenderer == null)
            {
                spriteRenderer = GetComponent<SpriteRenderer>();
            }
            if (shadowObject == null)
            {
                Transform sh = transform.Find("Shadow");
                if (sh != null) shadowObject = sh.gameObject;
            }
            if (shadowRenderer == null && shadowObject != null)
            {
                shadowRenderer = shadowObject.GetComponent<SpriteRenderer>();
            }
            basePosition = transform.position;
        }

        public void Init(SpriteRenderer sr, GameObject shadow)
        {
            spriteRenderer = sr;
            shadowObject = shadow;
            if (shadow != null)
            {
                shadowRenderer = shadow.GetComponent<SpriteRenderer>();
            }
            basePosition = transform.position;
#if UNITY_EDITOR
            UnityEditor.EditorUtility.SetDirty(this);
#endif
        }

        public void SetDefaultDirection(int dir)
        {
            defaultDirection = dir;
            currentDirection = dir;
            directionTimer = 0f;
            UpdateSprite();
        }

        public void SetBasePosition(Vector3 pos)
        {
            basePosition = pos;
            ApplyTransformPosition();
        }

        public void SetActionOffset(Vector3 offset)
        {
            actionOffset = offset;
            ApplyTransformPosition();
        }

        public void SetVibrationOffset(Vector3 vib)
        {
            vibrationOffset = vib;
            ApplyTransformPosition();
        }

        public void SetFlashColor(Color color)
        {
            flashColor = color;
            if (spriteRenderer != null)
            {
                spriteRenderer.color = flashColor;
            }
        }

        public void SetDirectionOverride(int dir)
        {
            directionOverride = dir;
            UpdateSprite();
        }

        public void ClearDirectionOverride()
        {
            directionOverride = -1;
            UpdateSprite();
        }

        public void ResetCombatState()
        {
            if(hitFlashCoroutine!=null){StopCoroutine(hitFlashCoroutine);hitFlashCoroutine=null;}
            if (hitReactionCoroutine != null)
            {
                StopCoroutine(hitReactionCoroutine);
                hitReactionCoroutine = null;
            }
            actionOffset = Vector3.zero;
            vibrationOffset = Vector3.zero;
            directionOverride = -1;
            currentDirection = defaultDirection;
            SetFlashColor(Color.white);
            ApplyTransformPosition();
            UpdateSprite();
        }

        private void ApplyTransformPosition()
        {
            transform.position = basePosition + actionOffset + vibrationOffset;
        }

        #region 八种受击动力学模式 (根据 BattleDataModels.cs 与 TroopVisualPresenter.cs)
        /// <summary>
        /// 播放受击动力学反应：
        /// 1=水平震退, 2=垂直击飞, 3=抛物线后仰, 4=四向旋转翻滚,
        /// 5=波浪状掀飞, 6=中心炸散再复位, 7=手风琴压缩, 8=地震颠簸
        /// </summary>
        public bool manualAnimation;
        private bool samplingReaction;
        private float sampleDelta;
        private float ReactionDelta => samplingReaction ? sampleDelta : Time.deltaTime;
        public Vector3 BasePosition => basePosition;
        public int DisplayDirection => directionOverride>=0?directionOverride:currentDirection;
        public void SampleAnimation(float seconds) {currentFrame=Mathf.FloorToInt(Mathf.Max(0,seconds)/FrameDuration)%4;UpdateSprite();}
        public void SampleHitReaction(int type, bool facingRight, float intensity, float seconds, Vector3 direction, int seed, int rotationCount=1, float rotationDuration=0, float scatterDistanceScale=1.0f)
        {
            ResetCombatState();if(seconds<0)return;
            var state=UnityEngine.Random.state;
            samplingReaction=true;
            try {
                UnityEngine.Random.InitState(seed);
                var routine=CoHitReaction(type,facingRight,intensity,0,direction,rotationCount,rotationDuration,scatterDistanceScale);
                float consumed=0;
                while(consumed<seconds) {
                    sampleDelta=Mathf.Min(1f/120,seconds-consumed);
                    if(!routine.MoveNext())break;consumed+=sampleDelta;
                }
            } finally { samplingReaction=false;UnityEngine.Random.state=state; }
        }

        public void PlayHitReaction(int reactionType, bool isFacingRight, float intensity = 1.0f, float delay = 0f, Vector3 customScatterDir = default, int rotationCount=1, float rotationDuration=0, float scatterDistanceScale=1.0f)
        {
            if (hitReactionCoroutine != null)
            {
                StopCoroutine(hitReactionCoroutine);
            }
            hitReactionCoroutine = StartCoroutine(CoHitReaction(reactionType, isFacingRight, intensity, delay, customScatterDir,rotationCount,rotationDuration,scatterDistanceScale));
        }

        private System.Collections.IEnumerator CoHitReaction(int reactionType, bool isFacingRight, float intensity, float delay, Vector3 customScatterDir,int rotationCount,float rotationDuration, float scatterDistanceScale=1.0f)
        {
            if (delay > 0f)
            {
                yield return new WaitForSeconds(delay);
            }

            float directionSign = isFacingRight ? -1f : 1f; // 受击后退方向
            float t = 0f;

            switch (reactionType)
            {
                // 模式 1: 纯水平震退 (Knockback) - 强力爆发式后撞 + 摩擦缓冲 + 弹性归位
                case 1:
                {
                    float maxDist = 1.7f * intensity * directionSign;
                    float dur = 0.48f;
                    while (t < dur)
                    {
                        t += ReactionDelta;
                        float p = Mathf.Clamp01(t / dur);
                        float x;
                        if (p < 0.22f)
                        {
                            // 极速炸退 (0 ~ 0.22s): 强力爆发式瞬间后冲
                            float subP = p / 0.22f;
                            x = Mathf.Lerp(0f, maxDist, 1f - Mathf.Pow(1f - subP, 3f));
                        }
                        else if (p < 0.52f)
                        {
                            // 顿挫摩擦缓冲 (0.22 ~ 0.52s): 保持最大后退位移，伴随脚底摩擦抖动
                            float subP = (p - 0.22f) / 0.30f;
                            float skid = Mathf.Sin(subP * Mathf.PI * 4f) * (0.08f * (1f - subP));
                            x = maxDist + skid * directionSign;
                        }
                        else
                        {
                            // 弹性复位 (0.52 ~ 1.0s): 平滑归位
                            float subP = (p - 0.52f) / 0.48f;
                            x = Mathf.Lerp(maxDist, 0f, Mathf.SmoothStep(0f, 1f, subP));
                        }
                        actionOffset = new Vector3(x, 0f, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 2: 垂直击飞 (Pop-up Jump) - 仅垂直击飞减半 (1.2)，滞空稍微增加 (0.22s ~ 0.60s 滞空悬停)
                case 2:
                {
                    float maxHeight = 1.2f * intensity;
                    float dur = 0.54f;
                    while (t < dur)
                    {
                        t += ReactionDelta;
                        float p = Mathf.Clamp01(t / dur);
                        float y;
                        if (p < 0.22f)
                        {
                            // 极速冲顶 (0 ~ 0.22s)
                            float subP = p / 0.22f;
                            y = Mathf.Lerp(0f, maxHeight, 1f - Mathf.Pow(1f - subP, 2.5f));
                        }
                        else if (p < 0.60f)
                        {
                            // 顶点滞空浮动 (0.22 ~ 0.60s): 滞空稍微增加，在最高点平稳浮空
                            float subP = (p - 0.22f) / 0.38f;
                            y = maxHeight + Mathf.Sin(subP * Mathf.PI) * 0.08f;
                        }
                        else if (p < 0.88f)
                        {
                            // 重力加速下砸 (0.60 ~ 0.88s)
                            float subP = (p - 0.60f) / 0.28f;
                            y = Mathf.Lerp(maxHeight, 0f, subP * subP);
                        }
                        else
                        {
                            // 落地触地微弹 (0.88 ~ 1.0s)
                            float subP = (p - 0.88f) / 0.12f;
                            y = Mathf.Sin(subP * Mathf.PI) * 0.10f;
                        }
                        actionOffset = new Vector3(0f, y, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 3: 抛物线后仰 (Launch & Knockback) - 恢复完整抛物线高度 (2.5) 与远距后退 (2.2)
                case 3:
                {
                    float maxHeight = 2.5f * intensity;
                    float maxBack = 2.2f * intensity * directionSign;
                    float flightDuration = 0.54f;
                    float returnDuration = 0.22f;
                    float totalDur = flightDuration + returnDuration;

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        float x, y;
                        if (t < flightDuration)
                        {
                            float p = Mathf.Clamp01(t / flightDuration);
                            // X 轴单调平滑向后飞退，绝不半途折返！
                            x = Mathf.Lerp(0f, maxBack, 1f - Mathf.Pow(1f - p, 1.8f));
                            // Y 轴标准对称抛物线
                            y = 4f * maxHeight * p * (1f - p);
                        }
                        else
                        {
                            // 落地滑步归位
                            float p = Mathf.Clamp01((t - flightDuration) / returnDuration);
                            y = 0f;
                            x = Mathf.Lerp(maxBack, 0f, Mathf.SmoothStep(0f, 1f, p));
                        }
                        actionOffset = new Vector3(x, y, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 4: 四向旋转翻滚 (Spin Pop-Up) - 恢复完整击飞高度 (2.8)，保持空中高速翻滚多圈
                case 4:
                {
                    float maxHeight = 2.8f * intensity;
                    float maxBack = 1.6f * intensity * directionSign;
                    float airDuration = rotationDuration>0?rotationDuration:.68f;
                    float returnDuration = 0.20f;
                    float totalDur = airDuration + returnDuration;

                    int[] spinDirs = (directionSign > 0)
                        ? new int[] { 0, 2, 3, 1 } // Down -> Right -> Up -> Left
                        : new int[] { 0, 1, 3, 2 }; // Down -> Left -> Up -> Right

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        float x, y;
                        if (t < airDuration)
                        {
                            if(rotationCount>0)SetDirectionOverride(spinDirs[Mathf.FloorToInt(Mathf.Clamp01(t/airDuration)*4*rotationCount)%4]);
                            else ClearDirectionOverride();

                            float p = Mathf.Clamp01(t / airDuration);
                            x = Mathf.Lerp(0f, maxBack, 1f - Mathf.Pow(1f - p, 1.6f));

                            // 空中高空滞空翻滚阶段
                            if (p < 0.28f)
                            {
                                float subP = p / 0.28f;
                                y = Mathf.Lerp(0f, maxHeight, 1f - Mathf.Pow(1f - subP, 2.2f));
                            }
                            else if (p < 0.65f)
                            {
                                // 高空狂暴滞空旋转浮动
                                float subP = (p - 0.28f) / 0.37f;
                                y = maxHeight + Mathf.Sin(subP * Mathf.PI) * 0.15f;
                            }
                            else
                            {
                                // 旋转下坠砸向地面
                                float subP = (p - 0.65f) / 0.35f;
                                y = Mathf.Lerp(maxHeight, 0f, subP * subP);
                            }
                        }
                        else
                        {
                            // 落地瞬间立即停止旋转，归位到默认正面朝向
                            ClearDirectionOverride();
                            float p = Mathf.Clamp01((t - airDuration) / returnDuration);
                            y = 0f;
                            x = Mathf.Lerp(maxBack, 0f, Mathf.SmoothStep(0f, 1f, p));
                        }

                        actionOffset = new Vector3(x, y, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    ClearDirectionOverride();
                    break;
                }

                // 模式 5: 波浪状抛物起伏 (Wave Ripple) - 恢复完整大浪高度 (2.3)
                case 5:
                {
                    float maxHeight = 2.3f * intensity;
                    float maxBack = 1.2f * intensity * directionSign;
                    float flightDur = 0.50f;
                    float returnDur = 0.22f;
                    float totalDur = flightDur + returnDur;

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        float x, y;
                        if (t < flightDur)
                        {
                            float p = Mathf.Clamp01(t / flightDur);
                            x = Mathf.Lerp(0f, maxBack, 1f - Mathf.Pow(1f - p, 1.8f));
                            y = 4f * maxHeight * p * (1f - p);
                        }
                        else
                        {
                            float p = Mathf.Clamp01((t - flightDur) / returnDur);
                            y = 0f;
                            x = Mathf.Lerp(maxBack, 0f, Mathf.SmoothStep(0f, 1f, p));
                        }
                        actionOffset = new Vector3(x, y, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 6: 中心炸散再小跑复位 (Disperse & Regroup) - 适度炸开四散，避免飞出屏幕过强
                case 6:
                {
                    float scatterScale = scatterDistanceScale > 0.001f ? scatterDistanceScale : 1f;
                    float dist = (2.2f + UnityEngine.Random.Range(0f, 0.6f)) * intensity * scatterScale;
                    Vector3 apexPos = customScatterDir.normalized * dist;
                    apexPos.y += UnityEngine.Random.Range(0.2f, 0.5f) * scatterScale; // 适度垂直起伏随倍率缩放

                    float blastDur = 0.20f;
                    float pauseDur = 0.12f;
                    float returnDur = 0.38f;
                    float totalDur = blastDur + pauseDur + returnDur;

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        if (t < blastDur)
                        {
                            // 阶段 1: 炸向四周 (0 ~ 0.20s)
                            float p = Mathf.Clamp01(t / blastDur);
                            actionOffset = Vector3.Lerp(Vector3.zero, apexPos, 1f - Mathf.Pow(1f - p, 2.5f));
                        }
                        else if (t < blastDur + pauseDur)
                        {
                            // 阶段 2: 震晕晃动停顿 (0.20 ~ 0.32s)
                            float subP = (t - blastDur) / pauseDur;
                            Vector3 wobble = new Vector3(Mathf.Sin(subP * 30f) * 0.05f, Mathf.Cos(subP * 24f) * 0.05f, 0f);
                            actionOffset = apexPos + wobble;
                        }
                        else
                        {
                            // 阶段 3: 快速奔跑归位 (0.32 ~ 0.70s)
                            float p = Mathf.Clamp01((t - blastDur - pauseDur) / returnDur);
                            actionOffset = Vector3.Lerp(apexPos, Vector3.zero, Mathf.SmoothStep(0f, 1f, p));
                        }
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 7: 手风琴式阵型挤压反弹 (Accordion Squeeze) - 暴退风箱压缩 + 最小压缩状态明显停留 + 弹簧反弹
                case 7:
                {
                    float maxSqueeze = 1.8f * intensity * directionSign;
                    float dur = 0.58f;
                    while (t < dur)
                    {
                        t += ReactionDelta;
                        float p = Mathf.Clamp01(t / dur);
                        float x;
                        if (p < 0.22f)
                        {
                            // 阶段 1: 前排猛力压入后排 (0 ~ 0.22s, 极速压缩风箱)
                            float subP = p / 0.22f;
                            x = Mathf.Lerp(0f, maxSqueeze, 1f - Mathf.Pow(1f - subP, 3f));
                        }
                        else if (p < 0.40f)
                        {
                            // 阶段 2: 最小压缩极限停留 (0.22 ~ 0.40s, 紧实停顿蓄力，伴随微幅紧绷抖动)
                            float subP = (p - 0.22f) / 0.18f;
                            float tensionWobble = Mathf.Sin(subP * Mathf.PI * 4f) * (0.04f * intensity * directionSign);
                            x = maxSqueeze + tensionWobble;
                        }
                        else if (p < 0.70f)
                        {
                            // 阶段 3: 弹簧释放反弹 (0.40 ~ 0.70s, 猛烈反弹过冲)
                            float subP = (p - 0.40f) / 0.30f;
                            x = Mathf.Lerp(maxSqueeze, -0.22f * intensity * directionSign, Mathf.Sin(subP * Mathf.PI * 0.5f));
                        }
                        else
                        {
                            // 阶段 4: 稳定归位 (0.70 ~ 1.0s)
                            float subP = (p - 0.70f) / 0.30f;
                            x = Mathf.Lerp(-0.22f * intensity * directionSign, 0f, Mathf.SmoothStep(0f, 1f, subP));
                        }
                        actionOffset = new Vector3(x, 0f, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }

                // 模式 8: 全员高频地震颠簸颤抖 (Earthquake Tremor) - 震颤 + 整军彼此间距微幅拉大再复位
                case 8:
                {
                    float dur = 0.50f;
                    Vector3 spacingExpandOffset = customScatterDir * intensity;

                    while (t < dur)
                    {
                        t += ReactionDelta;
                        float p = Mathf.Clamp01(t / dur);
                        float decay = 1f - p;

                        // 1. 地震高频震颤位移
                        float jitterY = Mathf.Sin(t * 55f) * (0.35f * intensity * decay);
                        float jitterX = Mathf.Cos(t * 40f) * (0.15f * intensity * decay);
                        vibrationOffset = new Vector3(jitterX, jitterY, 0f);

                        // 2. 互相之间间距微幅拉大效果：整军行列间距微扩，震后平息收拢
                        if (p < 0.25f)
                        {
                            // 间距微拉开 (0 ~ 0.25s)
                            float subP = p / 0.25f;
                            actionOffset = Vector3.Lerp(Vector3.zero, spacingExpandOffset, Mathf.Sin(subP * Mathf.PI * 0.5f));
                        }
                        else if (p < 0.65f)
                        {
                            // 保持微拉开间距，持续剧烈震颤 (0.25 ~ 0.65s)
                            actionOffset = spacingExpandOffset;
                        }
                        else
                        {
                            // 震颤渐消，阵列间距收拢复位 (0.65 ~ 1.0s)
                            float subP = (p - 0.65f) / 0.35f;
                            actionOffset = Vector3.Lerp(spacingExpandOffset, Vector3.zero, Mathf.SmoothStep(0f, 1f, subP));
                        }

                        ApplyTransformPosition();
                        yield return null;
                    }
                    vibrationOffset = Vector3.zero;
                    actionOffset = Vector3.zero;
                    break;
                }

                // 模式 9: 中心聚拢吸附 (Converge / Black Hole Pull) - 适配黑洞/虫洞/引力坍缩：强力向军团中心螺旋吸附聚拢 + 奇点高压震颤 + 奇点湮灭弹开归位
                case 9:
                {
                    // customScatterDir 为 (centerPos - unitPos)，即从当前单位指向受击军团中心的完整向心位移向量
                    Vector3 pullVec = customScatterDir * (0.82f * intensity);
                    Vector3 perpVec = new Vector3(-pullVec.y, pullVec.x, 0f) * (0.22f * directionSign);

                    float pullDur = 0.34f;
                    float holdDur = 0.22f;
                    float releaseDur = 0.30f;
                    float totalDur = pullDur + holdDur + releaseDur;

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        if (t < pullDur)
                        {
                            // 阶段 1: 强引力向心螺旋拉扯聚拢 (0 ~ 0.34s)
                            float p = Mathf.Clamp01(t / pullDur);
                            float easeIn = p * p * (3f - 2f * p);
                            float swirlArc = Mathf.Sin(p * Mathf.PI) * 0.85f;
                            actionOffset = pullVec * easeIn + perpVec * swirlArc;
                            vibrationOffset = Vector3.zero;
                        }
                        else if (t < pullDur + holdDur)
                        {
                            // 阶段 2: 黑洞/虫洞奇点核心高压吸附滞留与高频坍缩颤抖 (0.34 ~ 0.56s)
                            float subP = (t - pullDur) / holdDur;
                            Vector3 tighten = pullVec * Mathf.Lerp(1.0f, 1.07f, subP);
                            float jx = Mathf.Sin(t * 75f) * 0.08f * intensity;
                            float jy = Mathf.Cos(t * 68f) * 0.08f * intensity;
                            actionOffset = tighten;
                            vibrationOffset = new Vector3(jx, jy, 0f);
                        }
                        else
                        {
                            // 阶段 3: 奇点消散湮灭，被吸聚的军团向外过冲弹开并平滑归位 (0.56 ~ 0.86s)
                            vibrationOffset = Vector3.zero;
                            float p = Mathf.Clamp01((t - pullDur - holdDur) / releaseDur);
                            if (p < 0.38f)
                            {
                                float subP = p / 0.38f;
                                actionOffset = Vector3.Lerp(pullVec * 1.07f, -pullVec * 0.14f, 1f - Mathf.Pow(1f - subP, 2.2f));
                            }
                            else
                            {
                                float subP = (p - 0.38f) / 0.62f;
                                actionOffset = Vector3.Lerp(-pullVec * 0.14f, Vector3.zero, Mathf.SmoothStep(0f, 1f, subP));
                            }
                        }

                        ApplyTransformPosition();
                        yield return null;
                    }
                    vibrationOffset = Vector3.zero;
                    actionOffset = Vector3.zero;
                    break;
                }

                // 模式 10: 集体旋转散开 (Collective Swirl & Scatter) - 适配漩涡/飓风/波纹：整军围绕军团中心同步公转涡旋向外扩散 + 自身四向旋转翻滚 + 回旋归位
                case 10:
                {
                    // customScatterDir 为 (unitPos - centerPos)，即当前单位相对于军团中心的初始半径向量 r0
                    Vector3 r0 = customScatterDir;
                    if (r0.sqrMagnitude < 0.04f)
                    {
                        r0 = new Vector3(0.35f * directionSign, 0.25f, 0f);
                    }

                    float swirlDur = rotationDuration>0?rotationDuration:.56f;
                    float returnDur = 0.34f;
                    float totalDur = swirlDur + returnDur;

                    // 整军公转总角度 (~220度涡旋扩散) 与最大外扩倍率
                    float maxAngleRad = 2*Mathf.PI*Mathf.Max(0,rotationCount)*(-directionSign);
                    float maxExpandScale = 1.52f * intensity;

                    int[] spinDirs = (directionSign > 0)
                        ? new int[] { 0, 2, 3, 1 }
                        : new int[] { 0, 1, 3, 2 };
                    Vector3 peakOffset = Vector3.zero;

                    while (t < totalDur)
                    {
                        t += ReactionDelta;
                        if (t < swirlDur)
                        {
                            // 阶段 1: 集体围绕军团中心公转涡旋并向外散开，同时个体四向高速自转 (0 ~ 0.56s)
                            if(rotationCount>0)SetDirectionOverride(spinDirs[Mathf.FloorToInt(Mathf.Clamp01(t/swirlDur)*4*rotationCount)%4]);
                            else ClearDirectionOverride();

                            float p = Mathf.Clamp01(t / swirlDur);
                            float easeP = 1f - Mathf.Pow(1f - p, 2.0f);
                            float angle = maxAngleRad * easeP;
                            float radiusScale = Mathf.Lerp(1.0f, maxExpandScale, Mathf.Sin(p * Mathf.PI * 0.5f));

                            float cosA = Mathf.Cos(angle);
                            float sinA = Mathf.Sin(angle);
                            Vector3 rotatedR = new Vector3(
                                r0.x * cosA - r0.y * sinA,
                                r0.x * sinA + r0.y * cosA,
                                0f) * radiusScale;

                            // 目标坐标为 centerPos + rotatedR，而 basePosition = centerPos + r0，故 actionOffset = rotatedR - r0
                            peakOffset = rotatedR - r0;
                            peakOffset.y += Mathf.Sin(p * Mathf.PI) * (0.45f * intensity); // 伴随波纹/气旋轻度浮空感
                            actionOffset = peakOffset;
                        }
                        else
                        {
                            // 阶段 2: 停止自转，从散开位置平滑收拢归位 (0.56 ~ 0.90s)
                            ClearDirectionOverride();
                            float p = Mathf.Clamp01((t - swirlDur) / returnDur);
                            actionOffset = Vector3.Lerp(peakOffset, Vector3.zero, Mathf.SmoothStep(0f, 1f, p));
                        }

                        ApplyTransformPosition();
                        yield return null;
                    }
                    ClearDirectionOverride();
                    actionOffset = Vector3.zero;
                    break;
                }

                default:
                {
                    while (t < 0.4f)
                    {
                        t += ReactionDelta;
                        float offset = Mathf.Sin((t / 0.4f) * Mathf.PI) * (1.2f * intensity * directionSign);
                        actionOffset = new Vector3(offset, 0f, 0f);
                        ApplyTransformPosition();
                        yield return null;
                    }
                    break;
                }
            }

            actionOffset = Vector3.zero;
            vibrationOffset = Vector3.zero;
            ApplyTransformPosition();
            hitReactionCoroutine = null;
        }

        public void SampleDamageFlash(float elapsed)
        {
            SetFlashColor(elapsed<0||elapsed>=HitFlashDuration?Color.white:
                elapsed<.06f?new Color(2.5f,2.5f,1.8f,1):new Color(1,.94f,.1f,1));
        }
        public void PlayDamageFlash()
        {
            if(hitFlashCoroutine!=null)StopCoroutine(hitFlashCoroutine);
            hitFlashCoroutine=StartCoroutine(HitFlashRoutine());
        }

        private System.Collections.IEnumerator HitFlashRoutine()
        {
            // 阶段 1: 瞬间高亮曝光 (0.06s)
            SetFlashColor(new Color(2.5f, 2.5f, 1.8f, 1f));
            yield return new WaitForSeconds(0.06f);
            // 阶段 2: 经典黄白色闪光 (0.12s)
            SetFlashColor(new Color(1f, 0.94f, 0.1f, 1f));
            yield return new WaitForSeconds(0.12f);
            // 阶段 3: 恢复正常
            SetFlashColor(Color.white);
            hitFlashCoroutine=null;
        }
        #endregion

        public void SetSortingOrder(int order)
        {
            if (spriteRenderer == null)
            {
                spriteRenderer = GetComponent<SpriteRenderer>();
            }
            if (spriteRenderer != null)
            {
                spriteRenderer.sortingOrder = order;
#if UNITY_EDITOR
                UnityEditor.EditorUtility.SetDirty(spriteRenderer);
#endif
            }

            if (shadowRenderer == null && shadowObject != null)
            {
                shadowRenderer = shadowObject.GetComponent<SpriteRenderer>();
            }
            if (shadowRenderer != null)
            {
                // 脚底阴影始终紧随角色身体且处于其下一层级 (order - 1)
                shadowRenderer.sortingOrder = order - 1;
#if UNITY_EDITOR
                UnityEditor.EditorUtility.SetDirty(shadowRenderer);
#endif
            }
        }

        public void SetCharacter(CharacterSheetData data)
        {
            characterData = data;
            directionTimer = 0f;
            frameTimer = 0f;
            currentDirection = defaultDirection;
            currentFrame = 0;
            ResetCombatState();

            if (spriteRenderer == null)
            {
                spriteRenderer = GetComponent<SpriteRenderer>();
            }
            if (shadowObject == null)
            {
                Transform sh = transform.Find("Shadow");
                if (sh != null) shadowObject = sh.gameObject;
            }

            if (data == null || !data.IsValid)
            {
                if (spriteRenderer != null)
                {
                    spriteRenderer.sprite = null;
                    spriteRenderer.enabled = false;
                }
                if (shadowObject != null)
                {
                    shadowObject.SetActive(false);
                }
                return;
            }

            if (shadowObject != null)
            {
                shadowObject.SetActive(true);
            }

            if (spriteRenderer != null)
            {
                spriteRenderer.enabled = true;
                UpdateSprite();
#if UNITY_EDITOR
                UnityEditor.EditorUtility.SetDirty(spriteRenderer);
#endif
            }
        }

        private void Update()
        {
            if (manualAnimation) return;
            if (characterData == null || !characterData.IsValid || spriteRenderer == null || !spriteRenderer.enabled)
                return;

            // 四向自动展示开关 (按需求默认关闭，仅在用户显式开启且无外部朝向锁定时生效)
            if (autoRotateDirections && directionOverride < 0 && hitReactionCoroutine == null)
            {
                directionTimer += Time.deltaTime;
                if (directionTimer >= DirectionDuration)
                {
                    directionTimer -= DirectionDuration;
                    currentDirection = (currentDirection + 1) % 4;
                    UpdateSprite();
                }
            }

            // 四帧步态循环 (动作期间持续保持走动迈步状态)
            frameTimer += Time.deltaTime;
            if (frameTimer >= FrameDuration)
            {
                frameTimer -= FrameDuration;
                currentFrame = (currentFrame + 1) % 4;
                UpdateSprite();
            }
        }

        public void UpdateSprite()
        {
            if (characterData == null || spriteRenderer == null) return;

            int dir = directionOverride >= 0 ? directionOverride : currentDirection;
            Sprite[] frames = null;
            switch (dir)
            {
                case 0: frames = characterData.downFrames; break;
                case 1: frames = characterData.leftFrames; break;
                case 2: frames = characterData.rightFrames; break;
                case 3: frames = characterData.upFrames; break;
            }

            if (frames != null && frames.Length > 0)
            {
                int safeIndex = Mathf.Clamp(currentFrame, 0, frames.Length - 1);
                if (frames[safeIndex] != null)
                {
                    spriteRenderer.sprite = frames[safeIndex];
                }
            }
        }
    }
}
