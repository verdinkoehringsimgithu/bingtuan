#if UNITY_2017_1_OR_NEWER || UNITY_5_3_OR_NEWER || UNITY_STANDALONE
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using LegionBattle.Core.Bridge;
using LegionBattle.Core.Data;
using LegionBattle.Core.Enums;
using LegionBattle.Core.Simulation;

namespace LegionBattle.Bridge.Unity
{
    /// <summary>
    /// 单个像素小人的四向走动与受击物理控制器 (纯代码驱动，适配 RPG Maker 标准 3x4 / 4x4 步行图)
    /// </summary>
    public class PixelActorView : MonoBehaviour
    {
        [Header("Sprite Sheet Settings")]
        public SpriteRenderer spriteRenderer;
        public Sprite[] walkDownFrames;   // 朝下 3~4 帧
        public Sprite[] walkLeftFrames;   // 朝左 3~4 帧
        public Sprite[] walkRightFrames;  // 朝右 3~4 帧
        public Sprite[] walkUpFrames;     // 朝上 3~4 帧

        public float animSpeed = 0.15f;   // 踏步动画频率
        public bool isFacingRight = true;

        public Vector3 OriginalLocalPos { get; private set; }
        private Coroutine _animCoroutine;
        private Coroutine _actionCoroutine;

        public enum Direction { Down = 0, Left = 1, Right = 2, Up = 3 }
        private Direction _currentDirection = Direction.Right;

        private void Awake()
        {
            if (spriteRenderer == null) spriteRenderer = GetComponent<SpriteRenderer>();
            OriginalLocalPos = transform.localPosition;
        }

        private void OnEnable()
        {
            StartWalking();
        }

        /// <summary>
        /// 1. 待机/两军对垒：原地踏步循环
        /// </summary>
        public void StartWalking()
        {
            if (_animCoroutine != null) StopCoroutine(_animCoroutine);
            _currentDirection = isFacingRight ? Direction.Right : Direction.Left;
            _animCoroutine = StartCoroutine(WalkAnimLoop());
        }

        private IEnumerator WalkAnimLoop()
        {
            int frameIndex = 0;
            while (true)
            {
                Sprite[] frames = GetFramesForDirection(_currentDirection);
                if (frames != null && frames.Length > 0)
                {
                    spriteRenderer.sprite = frames[frameIndex % frames.Length];
                }
                frameIndex++;
                yield return new WaitForSeconds(animSpeed);
            }
        }

        /// <summary>
        /// 2. 攻击突进：小人向前猛踏一段距离并弹性复位
        /// </summary>
        public void PlayLunge(float distance, float duration)
        {
            if (_actionCoroutine != null) StopCoroutine(_actionCoroutine);
            _actionCoroutine = StartCoroutine(LungeRoutine(distance, duration));
        }

        private IEnumerator LungeRoutine(float distance, float duration)
        {
            float directionSign = isFacingRight ? 1f : -1f;
            Vector3 targetPos = OriginalLocalPos + new Vector3(distance * directionSign, 0, 0);

            // 前突 (快速)
            float t = 0f;
            float halfDuration = duration * 0.4f;
            while (t < halfDuration)
            {
                t += Time.deltaTime;
                transform.localPosition = Vector3.Lerp(OriginalLocalPos, targetPos, t / halfDuration);
                yield return null;
            }

            // 复位 (弹性)
            t = 0f;
            float returnDuration = duration * 0.6f;
            while (t < returnDuration)
            {
                t += Time.deltaTime;
                transform.localPosition = Vector3.Lerp(targetPos, OriginalLocalPos, t / returnDuration);
                yield return null;
            }
            transform.localPosition = OriginalLocalPos;
        }

        /// <summary>
        /// 3. 数据驱动的纯代码受击动力学反应：
        /// 1=水平震退, 2=垂直击飞, 3=击飞后仰, 4=四向旋转翻滚,
        /// 5=波浪状起伏, 6=中心炸散小跑复位, 7=手风琴挤压, 8=地震颠簸
        /// </summary>
        public void PlayHitReaction(int reactionType, float intensity = 1.0f, Vector3 customScatterDir = default)
        {
            if (_actionCoroutine != null) StopCoroutine(_actionCoroutine);
            _actionCoroutine = StartCoroutine(HitReactionRoutine(reactionType, intensity, customScatterDir));
        }

        private IEnumerator HitReactionRoutine(int reactionType, float intensity, Vector3 customScatterDir)
        {
            float directionSign = isFacingRight ? -1f : 1f; // 受击后退方向
            float duration = 0.35f;
            float t = 0f;

            // 闪白视觉
            StartCoroutine(FlashWhiteRoutine(0.12f));

            switch (reactionType)
            {
                // 模式 1: 纯水平震退 (Knockback)
                case 1:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float offset = Mathf.Sin((t / duration) * Mathf.PI) * (0.45f * intensity * directionSign);
                        transform.localPosition = OriginalLocalPos + new Vector3(offset, 0, 0);
                        yield return null;
                    }
                    break;

                // 模式 2: 垂直小击飞下砸 (Pop-up Jump)
                case 2:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float height = Mathf.Sin((t / duration) * Mathf.PI) * (0.8f * intensity);
                        transform.localPosition = OriginalLocalPos + new Vector3(0, height, 0);
                        yield return null;
                    }
                    break;

                // 模式 3: 抛物线击飞后退 (Launch & Knockback)
                case 3:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float p = t / duration;
                        float height = Mathf.Sin(p * Mathf.PI) * (0.9f * intensity);
                        float back = Mathf.Sin(p * Mathf.PI) * (0.6f * intensity * directionSign);
                        transform.localPosition = OriginalLocalPos + new Vector3(back, height, 0);
                        yield return null;
                    }
                    break;

                // 模式 4: 四向切帧极速旋转击飞翻滚 (360° Directional Spin)
                case 4:
                    Direction[] spinDirs = new Direction[] { Direction.Down, Direction.Left, Direction.Up, Direction.Right };
                    int spinIndex = 0;
                    float spinTimer = 0f;
                    float spinStep = 0.05f;

                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        spinTimer += Time.deltaTime;
                        if (spinTimer >= spinStep)
                        {
                            spinTimer = 0f;
                            spinIndex = (spinIndex + 1) % spinDirs.Length;
                            _currentDirection = spinDirs[spinIndex];
                        }

                        float p = t / duration;
                        float height = Mathf.Sin(p * Mathf.PI) * (1.2f * intensity);
                        float back = Mathf.Sin(p * Mathf.PI) * (0.7f * intensity * directionSign);
                        transform.localPosition = OriginalLocalPos + new Vector3(back, height, 0);
                        yield return null;
                    }
                    _currentDirection = isFacingRight ? Direction.Right : Direction.Left;
                    break;

                // 模式 5: 波浪状抛物起伏 (Wave Ripple)
                case 5:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float p = t / duration;
                        float height = Mathf.Sin(p * Mathf.PI) * (1.1f * intensity);
                        float back = Mathf.Sin(p * Mathf.PI) * (0.4f * intensity * directionSign);
                        transform.localPosition = OriginalLocalPos + new Vector3(back, height, 0);
                        yield return null;
                    }
                    break;

                // 模式 6: 中心炸裂打散再小跑复位 (Disperse & Regroup)
                case 6:
                    Vector3 scatterOffset = customScatterDir * (1.2f * intensity);
                    Vector3 apexPos = OriginalLocalPos + scatterOffset;
                    float disperseDuration = 0.2f;
                    float returnDuration = 0.25f;

                    // 阶段 A: 被狂暴轰散到四周
                    while (t < disperseDuration)
                    {
                        t += Time.deltaTime;
                        float p = t / disperseDuration;
                        transform.localPosition = Vector3.Lerp(OriginalLocalPos, apexPos, Mathf.Sin(p * Mathf.PI * 0.5f));
                        yield return null;
                    }

                    // 阶段 B: 从四面八方快速小跑归位
                    t = 0f;
                    while (t < returnDuration)
                    {
                        t += Time.deltaTime;
                        float p = t / returnDuration;
                        transform.localPosition = Vector3.Lerp(apexPos, OriginalLocalPos, p);
                        yield return null;
                    }
                    break;

                // 模式 7: 手风琴式阵型挤压反弹 (Accordion Squeeze)
                case 7:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float offset = Mathf.Sin((t / duration) * Mathf.PI) * (0.8f * intensity * directionSign);
                        transform.localPosition = OriginalLocalPos + new Vector3(offset, 0, 0);
                        yield return null;
                    }
                    break;

                // 模式 8: 全员高频地震颠簸颤抖 (Earthquake Tremor)
                case 8:
                    while (t < duration)
                    {
                        t += Time.deltaTime;
                        float jitterY = Mathf.Sin(t * 50f) * (0.2f * intensity);
                        transform.localPosition = OriginalLocalPos + new Vector3(0, jitterY, 0);
                        yield return null;
                    }
                    break;
            }

            transform.localPosition = OriginalLocalPos;
        }

        private IEnumerator FlashWhiteRoutine(float flashDuration)
        {
            if (spriteRenderer == null) yield break;
            Color origColor = spriteRenderer.color;
            spriteRenderer.color = new Color(2.5f, 2.5f, 2.5f, 1f); // HDR 曝光闪白
            yield return new WaitForSeconds(flashDuration);
            spriteRenderer.color = origColor;
        }

        private Sprite[] GetFramesForDirection(Direction dir)
        {
            return dir switch
            {
                Direction.Down => walkDownFrames,
                Direction.Left => walkLeftFrames,
                Direction.Right => walkRightFrames,
                Direction.Up => walkUpFrames,
                _ => walkRightFrames
            };
        }
    }

    /// <summary>
    /// 30人战团军团表现层总控 (管理 30+30 人的阵型推进、数据驱动受击与技能演播)
    /// </summary>
    public class TroopVisualPresenter : MonoBehaviour, IBattlePresenter
    {
        [Header("Legion References")]
        public Transform leftTroopRoot;   // 左侧军团小人挂载根节点 (30个小人)
        public Transform rightTroopRoot;  // 右侧军团小人挂载根节点 (30个小人)

        public List<PixelActorView> leftActors = new List<PixelActorView>();
        public List<PixelActorView> rightActors = new List<PixelActorView>();

        [Header("FX & UI References")]
        public Camera battleCamera;
        public GameObject skillBannerUI; // 技能名大横幅 UI
        public TMPro.TextMeshProUGUI skillNameText;
        public ParticleSystem hitEffectPrefab; // 通用命中特效

        // 缓存当前出招技能，供受击判定直接读取表格配置
        private ActiveSkillData _lastCastedSkill;

        // ─── IBattlePresenter 接口实现 ───

        public void OnBattleStart(Legion left, Legion right)
        {
            // 全员开启朝向对方的原地踏步动画
            foreach (var a in leftActors) { a.isFacingRight = true; a.StartWalking(); }
            foreach (var a in rightActors) { a.isFacingRight = false; a.StartWalking(); }
        }

        public void OnTurnStart(int turnNumber, Legion attacker, Legion defender) { }

        public void OnSkillCast(Legion caster, ActiveSkillData skill)
        {
            _lastCastedSkill = skill;

            // 1. 弹出技能横幅
            if (skillBannerUI != null && skillNameText != null)
            {
                skillNameText.text = skill.Name;
                skillBannerUI.SetActive(false);
                skillBannerUI.SetActive(true); // 触发入场动效
            }

            // 2. 进攻方整军集体向前突进 0.25 秒
            var attackingActors = caster.IsLeft ? leftActors : rightActors;
            foreach (var actor in attackingActors)
            {
                actor.PlayLunge(0.4f, 0.25f);
            }
        }

        public void OnDamageDealt(Legion target, long damage, DamageType type)
        {
            var targetActors = target.IsLeft ? leftActors : rightActors;
            Transform root = target.IsLeft ? leftTroopRoot : rightTroopRoot;

            // ─── 数据驱动核心：优先读取技能表 HitReactionType 字段 ───
            int reactionMode = _lastCastedSkill?.HitReactionType ?? 0;

            // 若表格填 0，则根据伤害类型执行智能默认策略
            if (reactionMode == 0)
            {
                if (type == DamageType.Havoc) reactionMode = 4;           // 暴击 -> 360°旋转翻滚
                else if (type == DamageType.Precision) reactionMode = 3;  // 真伤 -> 抛物线击飞后退
                else reactionMode = UnityEngine.Random.Range(1, 3);        // 普攻 -> 随机震退或轻飞
            }

            // 计算军团中心点 (供模式 6 炸散计算散开向量)
            Vector3 centerPos = root != null ? root.position : Vector3.zero;

            // 遍历 30 个小人触发数据驱动动效
            for (int i = 0; i < targetActors.Count; i++)
            {
                var actor = targetActors[i];
                float delay = 0f;
                Vector3 scatterDir = Vector3.up;

                // 模式 5 (波浪状)：根据小人前后站位计算阶梯时差，形成多米诺大浪
                if (reactionMode == 5)
                {
                    float xPos = actor.transform.localPosition.x;
                    // 前排先被掀起，后排后被掀起
                    delay = target.IsLeft ? (xPos * 0.04f) : (-xPos * 0.04f);
                    delay = Mathf.Clamp(delay, 0f, 0.15f);
                }
                // 模式 6 (中心炸散)：计算从小人到中心的辐射方向
                else if (reactionMode == 6)
                {
                    Vector3 diff = actor.transform.position - centerPos;
                    scatterDir = diff.sqrMagnitude > 0.01f ? diff.normalized : UnityEngine.Random.insideUnitSphere;
                    scatterDir.z = 0f;
                    delay = UnityEngine.Random.Range(0f, 0.03f);
                }
                // 其他常规模式：微弱时差避免僵硬
                else
                {
                    delay = UnityEngine.Random.Range(0f, 0.06f);
                }

                StartCoroutine(DelayedHit(actor, reactionMode, delay, scatterDir));
            }

            // 触发屏幕震动 (Screen Shake)
            float shakeMagnitude = (reactionMode == 4 || reactionMode == 6) ? 0.35f : 0.18f;
            StartCoroutine(CameraShakeRoutine(0.18f, shakeMagnitude));
        }

        private IEnumerator DelayedHit(PixelActorView actor, int reaction, float delay, Vector3 scatterDir)
        {
            if (delay > 0) yield return new WaitForSeconds(delay);
            actor.PlayHitReaction(reaction, 1.0f, scatterDir);
        }

        public void OnHealApplied(Legion target, long heal, bool isOverheal) { }

        public void OnEvasion(Legion target)
        {
            // 敌方全员快速向后滑步闪开 MISS
            var targetActors = target.IsLeft ? leftActors : rightActors;
            foreach (var actor in targetActors)
            {
                actor.PlayHitReaction(1, 0.5f);
            }
        }

        public void OnBuffApplied(Legion target, BuffData buff) { }
        public void OnBuffTick(Legion target, string buffName, long tickDamage) { }
        public void OnDeathDefy(Legion target, int remainingCount) { }
        public void OnShieldBreak(Legion target) { }
        public void OnBerserkActivated(int turnNumber) { }
        public void OnBattleEnd(BattleResult result) { }

        private IEnumerator CameraShakeRoutine(float duration, float magnitude)
        {
            if (battleCamera == null) yield break;
            Vector3 originalPos = battleCamera.transform.localPosition;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float x = UnityEngine.Random.Range(-1f, 1f) * magnitude;
                float y = UnityEngine.Random.Range(-1f, 1f) * magnitude;
                battleCamera.transform.localPosition = new Vector3(originalPos.x + x, originalPos.y + y, originalPos.z);
                yield return null;
            }
            battleCamera.transform.localPosition = originalPos;
        }
    }
}
#endif
