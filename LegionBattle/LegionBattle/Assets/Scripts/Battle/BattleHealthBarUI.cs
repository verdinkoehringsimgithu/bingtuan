using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 军团战力条与对峙 UI (完全对齐《冒险与挖矿》原版 battle_panel.lua 布局)
    /// 左军绿色/青色战力条 + 右军红色战力条，中间回合信息，支持延迟扣战力缓冲残影与伤害飘字
    /// </summary>
    public class BattleHealthBarUI : MonoBehaviour
    {
        [Serializable]
        public class TroopBarView
        {
            public GameObject rootObj;
            public Image imgMainFill;
            public Image imgLagFill;
            public Image imgShieldFill;
            public Text txtName;
            public Text txtBP;

            public float targetRatio = 1f;
            public float currentRatio = 1f;
            public float lagRatio = 1f;
            public float lagDelayTimer = 0f;

            public int maxBP = 100000;
            public int currentBP = 100000;
            public int displayBP = 100000;

            public void SetMaxBP(int max)
            {
                maxBP = Mathf.Max(1, max);
                currentBP = maxBP;
                displayBP = maxBP;
                targetRatio = 1f;
                currentRatio = 1f;
                lagRatio = 1f;
                lagDelayTimer = 0f;
                shieldBP = 0;
                UpdateDisplayInstant();
            }

            public int shieldBP = 0;

            public void UpdateBP(int cur, int max, int shield = 0)
            {
                maxBP = Mathf.Max(1, max);
                int oldCur = currentBP;
                float oldRatio = currentRatio;
                currentBP = Mathf.Clamp(cur, 0, maxBP);
                targetRatio = (float)currentBP / maxBP;
                shieldBP = Mathf.Max(0, shield);

                if (currentBP < oldCur)
                {
                    // 受到伤害：主条立即变短，残影条保留在旧比例并等待 0.30 秒后平滑追赶
                    lagRatio = Mathf.Max(lagRatio, oldRatio);
                    currentRatio = targetRatio;
                    lagDelayTimer = 0.30f;
                }
                else
                {
                    // 回血：主条与残影条同步更新
                    currentRatio = targetRatio;
                    lagRatio = targetRatio;
                    lagDelayTimer = 0f;
                }
            }

            public void UpdateVisual(float dt)
            {
                // 主条迅速同步
                currentRatio = Mathf.MoveTowards(currentRatio, targetRatio, dt * 5.0f);
                if (imgMainFill != null)
                {
                    imgMainFill.fillAmount = currentRatio;
                }

                // 残影条延迟缓动追赶
                if (lagDelayTimer > 0f)
                {
                    lagDelayTimer -= dt;
                }
                else
                {
                    lagRatio = Mathf.MoveTowards(lagRatio, currentRatio, dt * 1.5f);
                }

                if (imgLagFill != null)
                {
                    imgLagFill.fillAmount = lagRatio;
                }

                // 护盾条更新
                if (imgShieldFill != null)
                {
                    float shieldRatio = maxBP > 0 ? Mathf.Clamp01((float)shieldBP / maxBP) : 0f;
                    imgShieldFill.fillAmount = shieldRatio;
                }

                // 数字滚动平滑显示 (保证 clamp 在 0..maxBP 之间)
                if (displayBP != currentBP)
                {
                    float step = Mathf.Max(300f, Mathf.Abs(displayBP - currentBP) * 8f * dt);
                    displayBP = Mathf.RoundToInt(Mathf.MoveTowards(displayBP, currentBP, step));
                    displayBP = Mathf.Clamp(displayBP, 0, maxBP);
                }

                if (txtBP != null)
                {
                    float pct = maxBP > 0 ? ((float)displayBP / maxBP * 100f) : 0f;
                    if (shieldBP > 0)
                    {
                        txtBP.text = string.Format("{0:N0} / {1:N0}  ({2:F1}%)  [护盾 {3:N0}]", displayBP, maxBP, pct, shieldBP);
                    }
                    else
                    {
                        txtBP.text = string.Format("{0:N0} / {1:N0}  ({2:F1}%)", displayBP, maxBP, pct);
                    }
                }
            }

            public void UpdateDisplayInstant()
            {
                currentRatio = 1f;
                targetRatio = 1f;
                lagRatio = 1f;
                lagDelayTimer = 0f;
                if (imgMainFill != null) imgMainFill.fillAmount = 1f;
                if (imgLagFill != null) imgLagFill.fillAmount = 1f;
                if (imgShieldFill != null) imgShieldFill.fillAmount = 0f;
                if (txtBP != null)
                {
                    txtBP.text = string.Format("{0:N0} / {1:N0}  (100.0%)", maxBP, maxBP);
                }
            }
        }

        [Header("左军 (我方) 战力条")]
        [SerializeField] private TroopBarView leftBar = new TroopBarView();

        [Header("右军 (敌方) 战力条")]
        [SerializeField] private TroopBarView rightBar = new TroopBarView();

        [Header("中央回合与战斗状态")]
        [SerializeField] private Text txtRound;

        [Header("飘字挂载容器")]
        [SerializeField] private Transform floatingTextContainer;

        private Font uiFont;

        public TroopBarView LeftBar => leftBar;
        public TroopBarView RightBar => rightBar;

        private void Awake()
        {
            EnsureUIBuilt();
        }

        private void Update()
        {
            float dt = Time.deltaTime;
            leftBar.UpdateVisual(dt);
            rightBar.UpdateVisual(dt);
        }

        public void SetTroopMaxBP(int leftMax, int rightMax)
        {
            EnsureUIBuilt();
            leftBar.SetMaxBP(leftMax);
            rightBar.SetMaxBP(rightMax);
        }

        public void ApplyDamage(bool isLeftTarget, int damage, bool isCrit, int remainingBP, int maxBP, int shield = 0)
        {
            EnsureUIBuilt();
            TroopBarView target = isLeftTarget ? leftBar : rightBar;
            target.UpdateBP(remainingBP, maxBP, shield);
        }

        public void ApplyHeal(bool isLeftTarget, int healAmount, int remainingBP, int maxBP, int shield = 0)
        {
            EnsureUIBuilt();
            TroopBarView target = isLeftTarget ? leftBar : rightBar;
            target.UpdateBP(remainingBP, maxBP, shield);
        }

        public void SetRoundText(string text)
        {
            if (txtRound != null) txtRound.text = text;
        }

        public void ResetBars()
        {
            leftBar.SetMaxBP(leftBar.maxBP);
            rightBar.SetMaxBP(rightBar.maxBP);
        }

        #region 伤害与回血动态飘字 (Float & Fade)
        public void SpawnFloatingText(Vector2 canvasPos, int amount, bool isCrit, bool isHeal)
        {
            if (floatingTextContainer == null) floatingTextContainer = this.transform;

            GameObject go = new GameObject("CombatFlyText");
            go.transform.SetParent(floatingTextContainer, false);

            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = canvasPos + new Vector2(UnityEngine.Random.Range(-30f, 30f), UnityEngine.Random.Range(-15f, 15f));
            rt.sizeDelta = new Vector2(300, 60);

            Text t = go.AddComponent<Text>();
            t.font = GetUIFont();
            t.alignment = TextAnchor.MiddleCenter;
            t.raycastTarget = false;

            // 描边增强打击感
            Outline outline = go.AddComponent<Outline>();
            outline.effectColor = Color.black;
            outline.effectDistance = new Vector2(2, -2);

            if (isHeal)
            {
                t.fontSize = 28;
                t.color = new Color(0.2f, 0.95f, 0.4f, 1f);
                t.text = string.Format("+{0:N0}", amount);
            }
            else if (isCrit)
            {
                t.fontSize = 36;
                t.fontStyle = FontStyle.Bold;
                t.color = new Color(1.0f, 0.85f, 0.1f, 1f);
                t.text = string.Format("暴击 -{0:N0}!", amount);
            }
            else
            {
                t.fontSize = 30;
                t.fontStyle = FontStyle.Bold;
                t.color = new Color(1.0f, 0.28f, 0.28f, 1f);
                t.text = string.Format("-{0:N0}", amount);
            }

            StartCoroutine(CoAnimateFlyText(go, rt, t, isCrit));
        }

        public void SpawnCustomFloatingText(Vector2 canvasPos, string text, Color color, float scale = 1.2f)
        {
            if (floatingTextContainer == null) floatingTextContainer = this.transform;

            GameObject go = new GameObject("CombatCustomFlyText");
            go.transform.SetParent(floatingTextContainer, false);

            RectTransform rt = go.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0.5f);
            rt.anchoredPosition = canvasPos + new Vector2(UnityEngine.Random.Range(-30f, 30f), UnityEngine.Random.Range(-15f, 15f));
            rt.sizeDelta = new Vector2(400, 60);

            Text t = go.AddComponent<Text>();
            t.font = GetUIFont();
            t.alignment = TextAnchor.MiddleCenter;
            t.raycastTarget = false;
            t.fontSize = Mathf.RoundToInt(30 * scale);
            t.fontStyle = FontStyle.Bold;
            t.color = color;
            t.text = text;

            Outline outline = go.AddComponent<Outline>();
            outline.effectColor = Color.black;
            outline.effectDistance = new Vector2(2, -2);

            StartCoroutine(CoAnimateFlyText(go, rt, t, scale > 1.2f));
        }

        private IEnumerator CoAnimateFlyText(GameObject go, RectTransform rt, Text t, bool isCrit)
        {
            float duration = isCrit ? 1.0f : 0.8f;
            float elapsed = 0f;
            Vector2 startPos = rt.anchoredPosition;
            Vector2 targetPos = startPos + new Vector2(0f, isCrit ? 90f : 70f);

            Vector3 baseScale = isCrit ? new Vector3(1.4f, 1.4f, 1f) : new Vector3(1.15f, 1.15f, 1f);

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float p = Mathf.Clamp01(elapsed / duration);

                // 冲击波放大回弹 (Punch effect 前 0.15s)
                if (elapsed < 0.15f)
                {
                    float punchP = elapsed / 0.15f;
                    rt.localScale = Vector3.Lerp(Vector3.zero, baseScale, punchP);
                }
                else
                {
                    rt.localScale = Vector3.Lerp(baseScale, Vector3.one, (elapsed - 0.15f) / 0.2f);
                }

                // 匀速上浮
                rt.anchoredPosition = Vector2.Lerp(startPos, targetPos, Mathf.SmoothStep(0f, 1f, p));

                // 尾部淡出 (后 35% 时间淡出)
                if (p > 0.65f)
                {
                    float fadeP = (p - 0.65f) / 0.35f;
                    Color c = t.color;
                    c.a = 1f - fadeP;
                    t.color = c;
                }

                yield return null;
            }

            Destroy(go);
        }
        #endregion

        #region 动态构建顶部经典双侧对峙血条
        public void EnsureUIBuilt()
        {
            if (leftBar.rootObj != null && rightBar.rootObj != null) return;

            Transform canvasTrans = transform;
            Canvas parentCanvas = GetComponentInParent<Canvas>();
            if (parentCanvas != null) canvasTrans = parentCanvas.transform;

            floatingTextContainer = canvasTrans;

            // 1. 构建左军血条 (Top-Left 贴合中央控制栏左侧)
            // 中央控制栏 X=-450..+450。左血条放置在 X=-465 处，宽度 480，高度 62
            leftBar = BuildTroopBar("LeftTroopBar", canvasTrans, new Vector2(-465, -18), new Vector2(480, 62), 
                "我方军团 (左军)", new Color(0.18f, 0.84f, 0.44f, 1f), new Color(1.0f, 0.95f, 0.45f, 0.95f), true);

            // 2. 构建右军血条 (Top-Right 贴合中央控制栏右侧)
            rightBar = BuildTroopBar("RightTroopBar", canvasTrans, new Vector2(465, -18), new Vector2(480, 62), 
                "敌方军团 (右军)", new Color(0.92f, 0.25f, 0.22f, 1f), new Color(1.0f, 0.65f, 0.25f, 0.95f), false);
        }

        private TroopBarView BuildTroopBar(string name, Transform parent, Vector2 pos, Vector2 size, string title, Color mainColor, Color lagColor, bool isLeft)
        {
            TroopBarView view = new TroopBarView();

            GameObject root = new GameObject(name);
            root.transform.SetParent(parent, false);
            RectTransform rootRt = root.AddComponent<RectTransform>();
            rootRt.anchorMin = new Vector2(0.5f, 1f);
            rootRt.anchorMax = new Vector2(0.5f, 1f);
            rootRt.pivot = isLeft ? new Vector2(1f, 1f) : new Vector2(0f, 1f);
            rootRt.anchoredPosition = pos;
            rootRt.sizeDelta = size;

            // 背景底板 (深灰半透明暗黑科技底座)
            Image bg = root.AddComponent<Image>();
            bg.color = new Color(0.08f, 0.10f, 0.14f, 0.92f);
            view.rootObj = root;

            Font font = GetUIFont();

            // 标题名称文本
            GameObject titleObj = new GameObject("TxtTitle");
            titleObj.transform.SetParent(root.transform, false);
            RectTransform titleRt = titleObj.AddComponent<RectTransform>();
            titleRt.anchorMin = new Vector2(0f, 1f);
            titleRt.anchorMax = new Vector2(1f, 1f);
            titleRt.pivot = new Vector2(0f, 1f);
            titleRt.anchoredPosition = new Vector2(isLeft ? 12 : 12, -4);
            titleRt.sizeDelta = new Vector2(size.x - 24, 22);

            Text txtTitle = titleObj.AddComponent<Text>();
            txtTitle.font = font;
            txtTitle.fontSize = 15;
            txtTitle.fontStyle = FontStyle.Bold;
            txtTitle.color = isLeft ? new Color(0.5f, 0.95f, 1f, 1f) : new Color(1f, 0.65f, 0.65f, 1f);
            txtTitle.alignment = isLeft ? TextAnchor.MiddleLeft : TextAnchor.MiddleRight;
            txtTitle.text = title;
            txtTitle.raycastTarget = false;
            view.txtName = txtTitle;

            // 血条槽容器 (Track)
            GameObject trackObj = new GameObject("BarTrack");
            trackObj.transform.SetParent(root.transform, false);
            RectTransform trackRt = trackObj.AddComponent<RectTransform>();
            trackRt.anchorMin = new Vector2(0f, 0f);
            trackRt.anchorMax = new Vector2(1f, 0f);
            trackRt.pivot = new Vector2(0.5f, 0f);
            trackRt.anchoredPosition = new Vector2(0, 8);
            trackRt.sizeDelta = new Vector2(size.x - 20, 26);

            Image trackBg = trackObj.AddComponent<Image>();
            trackBg.color = new Color(0.04f, 0.05f, 0.07f, 1f);

            Sprite whiteSprite = GetWhiteSprite();

            // 残影缓冲条 (Lag Fill)
            GameObject lagObj = new GameObject("LagFill");
            lagObj.transform.SetParent(trackObj.transform, false);
            RectTransform lagRt = lagObj.AddComponent<RectTransform>();
            lagRt.anchorMin = Vector2.zero;
            lagRt.anchorMax = Vector2.one;
            lagRt.sizeDelta = Vector2.zero;

            Image lagImg = lagObj.AddComponent<Image>();
            lagImg.sprite = whiteSprite;
            lagImg.color = lagColor;
            lagImg.type = Image.Type.Filled;
            lagImg.fillMethod = Image.FillMethod.Horizontal;
            lagImg.fillOrigin = isLeft ? (int)Image.OriginHorizontal.Left : (int)Image.OriginHorizontal.Right;
            lagImg.fillAmount = 1f;
            view.imgLagFill = lagImg;

            // 主血条 (Main Fill)
            GameObject mainObj = new GameObject("MainFill");
            mainObj.transform.SetParent(trackObj.transform, false);
            RectTransform mainRt = mainObj.AddComponent<RectTransform>();
            mainRt.anchorMin = Vector2.zero;
            mainRt.anchorMax = Vector2.one;
            mainRt.sizeDelta = Vector2.zero;

            Image mainImg = mainObj.AddComponent<Image>();
            mainImg.sprite = whiteSprite;
            mainImg.color = mainColor;
            mainImg.type = Image.Type.Filled;
            mainImg.fillMethod = Image.FillMethod.Horizontal;
            mainImg.fillOrigin = isLeft ? (int)Image.OriginHorizontal.Left : (int)Image.OriginHorizontal.Right;
            mainImg.fillAmount = 1f;
            view.imgMainFill = mainImg;

            // 护盾条 (Shield Fill)
            GameObject shieldObj = new GameObject("ShieldFill");
            shieldObj.transform.SetParent(trackObj.transform, false);
            RectTransform shieldRt = shieldObj.AddComponent<RectTransform>();
            shieldRt.anchorMin = Vector2.zero;
            shieldRt.anchorMax = Vector2.one;
            shieldRt.sizeDelta = Vector2.zero;

            Image shieldImg = shieldObj.AddComponent<Image>();
            shieldImg.sprite = whiteSprite;
            shieldImg.color = new Color(0.2f, 0.85f, 1f, 0.5f);
            shieldImg.type = Image.Type.Filled;
            shieldImg.fillMethod = Image.FillMethod.Horizontal;
            shieldImg.fillOrigin = isLeft ? (int)Image.OriginHorizontal.Left : (int)Image.OriginHorizontal.Right;
            shieldImg.fillAmount = 0f;
            view.imgShieldFill = shieldImg;

            // 战力数值文本 (居中覆盖在血条上，带文字描边)
            GameObject bpObj = new GameObject("TxtBP");
            bpObj.transform.SetParent(trackObj.transform, false);
            RectTransform bpRt = bpObj.AddComponent<RectTransform>();
            bpRt.anchorMin = Vector2.zero;
            bpRt.anchorMax = Vector2.one;
            bpRt.sizeDelta = Vector2.zero;

            Text txtBP = bpObj.AddComponent<Text>();
            txtBP.font = font;
            txtBP.fontSize = 15;
            txtBP.fontStyle = FontStyle.Bold;
            txtBP.color = Color.white;
            txtBP.alignment = TextAnchor.MiddleCenter;
            txtBP.text = "100,000 / 100,000  (100.0%)";
            txtBP.raycastTarget = false;

            Outline bpOutline = bpObj.AddComponent<Outline>();
            bpOutline.effectColor = new Color(0f, 0f, 0f, 0.9f);
            bpOutline.effectDistance = new Vector2(1.5f, -1.5f);
            view.txtBP = txtBP;

            return view;
        }

        private static Sprite _whiteSprite;
        public static Sprite GetWhiteSprite()
        {
            if (_whiteSprite != null) return _whiteSprite;
            Texture2D tex = Texture2D.whiteTexture;
            _whiteSprite = Sprite.Create(tex, new Rect(0, 0, 4, 4), new Vector2(0.5f, 0.5f), 100f);
            return _whiteSprite;
        }

        private Font GetUIFont()
        {
            if (uiFont != null) return uiFont;
            uiFont = Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
            if (uiFont == null) uiFont = Resources.GetBuiltinResource<Font>("Arial.ttf");
            if (uiFont == null) uiFont = Font.CreateDynamicFontFromOSFont("Microsoft YaHei", 16);
            return uiFont;
        }
        #endregion
    }
}
