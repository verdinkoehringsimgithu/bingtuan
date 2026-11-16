using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 30v30 军团战斗极简中心像素特效播放器 (高性能零 Animator / 零 GC 对象池驱动)
    /// 1. 极简中心模式：所有技能均在受击方军团中心（守护/治疗技能在施法方军团中心）播放 1 个放大像素特效
    /// 2. 朝向自适应：带向右方向特征的投射物/剑气在右军攻左军时自动水平翻转 (flipX = true)
    /// 3. 双模加载保障：优先读取 Editor 烘焙的 EffectDatabase.asset；若尚未烘焙则自动从 Assets/Effects/Spritesheets 按需实时切帧并缓存
    /// </summary>
    public class BattleEffectPlayer : MonoBehaviour
    {
        private static BattleEffectPlayer _instance;
        public static BattleEffectPlayer ExistingInstance => _instance;
        public static void BindSceneInstance(BattleEffectPlayer player) { _instance = player; }
        public static BattleEffectPlayer Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = FindObjectOfType<BattleEffectPlayer>();
                    if (_instance == null)
                    {
                        GameObject go = new GameObject("BattleEffectPlayer");
                        _instance = go.AddComponent<BattleEffectPlayer>();
                    }
                }
                return _instance;
            }
        }

        [Header("特效数据库与全局缩放调节")]
        public EffectDatabase database;
        [Range(0.5f, 3.0f)]
        public float globalScaleMultiplier = 1.15f;
        public int effectSortingOrder = 5000;

        private class ActiveEffectNode
        {
            public GameObject gameObject;
            public Transform transform;
            public SpriteRenderer renderer;
            public SpriteRenderer backRenderer;
            public Sprite[] frames;
            public Sprite[] frontFrames, backFrames;
            public float fps;
            public float elapsed;
            public int currentFrameIndex;
            public bool isPlaying;
        }

        private const int PoolSize = 4;
        private readonly List<ActiveEffectNode> _pool = new List<ActiveEffectNode>(PoolSize);
        private readonly Dictionary<int, Sprite[]> _runtimeSpriteCache = new Dictionary<int, Sprite[]>();
        private readonly Dictionary<int, EffectRuntimeMeta> _runtimeMetaCache = new Dictionary<int, EffectRuntimeMeta>();

        private class EffectRuntimeMeta
        {
            public bool isDirectionalRight;
            public bool playOnCaster;
            public float recommendedScale;
            public int fps;
        }

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }
            _instance = this;
            InitPool();
            EnsureDatabaseLoaded();
        }

        private void InitPool()
        {
            if (_pool.Count > 0) return;
            for (int i = 0; i < PoolSize; i++)
            {
                GameObject nodeObj = new GameObject(string.Format("EffectNode_{0}", i));
                nodeObj.transform.SetParent(transform, false);
                SpriteRenderer sr = nodeObj.AddComponent<SpriteRenderer>();
                sr.sortingOrder = effectSortingOrder + i;
                var backObj=new GameObject("EffectBackLayer");backObj.transform.SetParent(nodeObj.transform,false);
                var back=backObj.AddComponent<SpriteRenderer>();
                nodeObj.SetActive(false);

                _pool.Add(new ActiveEffectNode
                {
                    gameObject = nodeObj,
                    transform = nodeObj.transform,
                    renderer = sr,
                    backRenderer = back,
                    frames = null,
                    fps = 15f,
                    elapsed = 0f,
                    currentFrameIndex = -1,
                    isPlaying = false
                });
            }
        }

        private void EnsureDatabaseLoaded()
        {
            if (database == null)
            {
                database = Resources.Load<EffectDatabase>("EffectDatabase");
            }
        }

        private void Update()
        {
            float dt = Time.deltaTime;
            for (int i = 0; i < _pool.Count; i++)
            {
                ActiveEffectNode node = _pool[i];
                if (!node.isPlaying || node.frames == null || node.frames.Length == 0) continue;

                node.elapsed += dt;
                int frameIdx = Mathf.FloorToInt(node.elapsed * node.fps);
                if (frameIdx >= node.frames.Length)
                {
                    node.isPlaying = false;
                    node.renderer.sprite = null;
                    node.backRenderer.sprite = null;
                    node.gameObject.SetActive(false);
                }
                else if (frameIdx != node.currentFrameIndex)
                {
                    node.currentFrameIndex = frameIdx;
                    AssignFrame(node.renderer,node.backRenderer,node.frames,node.frontFrames,node.backFrames,frameIdx);
                }
            }
        }

        private void OnDestroy()
        {
            var textures = new HashSet<Texture>();
            foreach (var frames in _runtimeSpriteCache.Values)
                foreach (var sprite in frames)
                    if (sprite != null) { textures.Add(sprite.texture); Destroy(sprite); }
            foreach (var texture in textures) if (texture != null) Destroy(texture);
            _runtimeSpriteCache.Clear(); _runtimeMetaCache.Clear();
            if (_instance == this) _instance = null;
        }


        /// <summary>
        /// 静态便捷入口：在 30v30 军团战斗中根据技能 animationId 在军团中心播放特效
        /// </summary>
        public static void PlaySkillEffect(
            BattleSkill skill,
            Vector3 attackerCenterPos,
            Vector3 defenderCenterPos,
            bool leftAttacking,
            BattleCharacterPreview[] attackers = null,
            BattleCharacterPreview[] defenders = null)
        {
            int animId=PrepareSkillEffect(skill);
            var timing=EffectTimingConfig.For(animId);
            Instance.PlayById(animId, attackerCenterPos, defenderCenterPos, leftAttacking, skill,timing.playOnCaster?attackers:defenders);
        }
        public static int PrepareSkillEffect(BattleSkill skill)
        {
            if(skill==null)return 1329;
            SkillEffectMatcher.VariantEntry variant;SkillEffectMatcher.FamilyEntry family;
            int id=skill.animationId;
            if(!SkillEffectMatcher.TryGetById(id,out variant,out family)||family.IsDisabled)
            {
                string name,folder,category,hitName;int hit;
                SkillEffectMatcher.ResolveSkillEffect(skill.name,GetGenreFromSkill(skill),skill.rarityTier,"",out id,out name,out folder,out category,out hit,out hitName);
                skill.animationId=id;skill.effectCnName=name;skill.effectFolder=folder;skill.hitReactionType=hit;
            }
            return id;
        }

        public static string GetGenreFromSkill(BattleSkill skill)
        {
            if (skill == null) return "勇气";
            switch (skill.effectType)
            {
                case BattleSkillEffectType.Critical: return "勇气";
                case BattleSkillEffectType.TrueDamage: return "先机";
                case BattleSkillEffectType.HealBySelfMaxBP:
                case BattleSkillEffectType.BPSteal: return "坚韧";
                default: return "魔力";
            }
        }

        public void PlayById(
            int animationId,
            Vector3 attackerCenterPos,
            Vector3 defenderCenterPos,
            bool leftAttacking,
            BattleSkill skillContext = null,
            BattleCharacterPreview[] followFormation = null)
        {
            InitPool();
            EnsureDatabaseLoaded();
            SkillEffectMatcher.VariantEntry variant;SkillEffectMatcher.FamilyEntry family;
            if(!SkillEffectMatcher.TryGetById(animationId,out variant,out family)||family.IsDisabled)return;

            Sprite[] frames = null;
            bool isDirectionalRight = false;
            bool playOnCaster = false;
            float recScale = 2.2f;
            int fps = 15;

            // 1. 优先从烘焙好的 EffectDatabase.asset 获取
            EffectEntry dbEntry;
            if (database != null && database.TryGetEffect(animationId, out dbEntry) && dbEntry.HasValidSprites)
            {
                frames = dbEntry.frames;
                isDirectionalRight = dbEntry.isDirectionalRight;
                playOnCaster = dbEntry.playOnCaster;
                recScale = dbEntry.recommendedScale;
                fps = dbEntry.fps > 0 ? dbEntry.fps : 15;
            }
            else
            {
                // 2. 运行时按需自动切图与内存缓存 (无需提前点编辑器菜单也能 100% 播放)
                frames = GetOrSliceRuntimeSprites(animationId, out isDirectionalRight, out playOnCaster, out recScale, out fps);
            }

            if (frames == null || frames.Length == 0) return;

            var timing = EffectTimingConfig.For(animationId);
            playOnCaster = timing.playOnCaster;
            fps = timing.fps;

            Vector3 baseCenter = playOnCaster ? attackerCenterPos : defenderCenterPos;
            Vector3 spawnPos = new Vector3(baseCenter.x, baseCenter.y, 0f);
            if(followFormation!=null)spawnPos=BattleFormationCenter.GetCenter(followFormation);

            // 获取空闲或最早播放的节点
            ActiveEffectNode node = AcquireNode();
            node.transform.position = spawnPos + new Vector3(timing.offsetX*(leftAttacking?1:-1), timing.offsetY, 0);
            float finalScale = recScale * globalScaleMultiplier * timing.scale;
            node.transform.localScale = new Vector3(finalScale, finalScale, 1f);

            // 向右方向型特效：当右军攻击左军 (!leftAttacking) 时自动水平镜像翻转朝左
            node.renderer.flipX = (!leftAttacking && isDirectionalRight);
            node.backRenderer.flipX=node.renderer.flipX;
            LoadLayers(animationId,out node.frontFrames,out node.backFrames);
            BattleEffectSorting.Apply(node.renderer,node.backRenderer,followFormation,timing.useFormationSorting,effectSortingOrder);
            node.frames = frames;
            node.fps = fps;
            node.elapsed = 0f;
            node.currentFrameIndex = 0;
            AssignFrame(node.renderer,node.backRenderer,frames,node.frontFrames,node.backFrames,0);
            node.isPlaying = true;
            node.gameObject.SetActive(true);
        }

        public Sprite[] GetFrames(int animationId, out float scale, out bool directional)
        {
            SkillEffectMatcher.VariantEntry variant;SkillEffectMatcher.FamilyEntry family;
            if(!SkillEffectMatcher.TryGetById(animationId,out variant,out family)||family.IsDisabled){scale=1;directional=false;return null;}
            EnsureDatabaseLoaded(); EffectEntry entry;
            if(database!=null&&database.TryGetEffect(animationId,out entry)&&entry.HasValidSprites)
            { scale=entry.recommendedScale;directional=entry.isDirectionalRight;return entry.frames; }
            bool caster;int fps;
            return GetOrSliceRuntimeSprites(animationId,out directional,out caster,out scale,out fps);
        }
        public bool HasLayers(int animationId)
        {
            EnsureDatabaseLoaded();EffectEntry entry;
            return database!=null&&database.TryGetEffect(animationId,out entry)&&entry.HasLayerSprites;
        }
        private void LoadLayers(int animationId,out Sprite[] front,out Sprite[] back)
        {
            EffectEntry entry;front=back=null;
            if(database!=null&&database.TryGetEffect(animationId,out entry)&&entry.HasLayerSprites){front=entry.frontFrames;back=entry.backFrames;}
        }
        private static void AssignFrame(SpriteRenderer renderer,SpriteRenderer back,Sprite[] frames,Sprite[] frontFrames,Sprite[] backFrames,int index)
        {
            bool layered=frontFrames!=null&&backFrames!=null&&frontFrames.Length>0&&backFrames.Length>0;
            renderer.sprite=layered?(index<frontFrames.Length?frontFrames[index]:null):frames[index];
            back.sprite=layered&&index<backFrames.Length?backFrames[index]:null;
        }
        private SpriteRenderer scrubRenderer,scrubBackRenderer;
        public void ClearScrub() { if(scrubRenderer!=null)scrubRenderer.gameObject.SetActive(false); }
        public bool ShowFrame(int animationId, int frame, Vector3 center, bool leftAttacking,BattleCharacterPreview[] formation=null)
        {
            float scale;bool directional;var frames=GetFrames(animationId,out scale,out directional);
            if(frames==null||frames.Length==0){ClearScrub();return false;}
            if(scrubRenderer==null){var go=new GameObject("EffectFramePreview");go.transform.SetParent(transform,false);scrubRenderer=go.AddComponent<SpriteRenderer>();var child=new GameObject("EffectBackLayer");child.transform.SetParent(go.transform,false);scrubBackRenderer=child.AddComponent<SpriteRenderer>();}
            if(frame<0||frame>=frames.Length){ClearScrub();return true;}
            var profile=EffectTimingConfig.For(animationId);
            Vector3 pos=new Vector3(center.x,center.y,0);
            pos.x+=profile.offsetX*(leftAttacking?1:-1);
            pos.y+=profile.offsetY;
            scrubRenderer.transform.position=pos;
            scrubRenderer.transform.localScale=Vector3.one*(scale*globalScaleMultiplier*profile.scale);
            scrubRenderer.flipX=!leftAttacking&&directional;scrubBackRenderer.flipX=scrubRenderer.flipX;
            Sprite[] front,back;LoadLayers(animationId,out front,out back);
            AssignFrame(scrubRenderer,scrubBackRenderer,frames,front,back,frame);
            BattleEffectSorting.Apply(scrubRenderer,scrubBackRenderer,formation,profile.useFormationSorting,effectSortingOrder);
            scrubRenderer.gameObject.SetActive(true);return true;
        }

        private ActiveEffectNode AcquireNode()
        {
            for (int i = 0; i < _pool.Count; i++)
            {
                if (!_pool[i].isPlaying) return _pool[i];
            }
            // 若全忙则复用最早启动的节点
            ActiveEffectNode oldest = _pool[0];
            for (int i = 1; i < _pool.Count; i++)
            {
                if (_pool[i].elapsed > oldest.elapsed) oldest = _pool[i];
            }
            return oldest;
        }

        private Sprite[] GetOrSliceRuntimeSprites(
            int animationId,
            out bool isDirectionalRight,
            out bool playOnCaster,
            out float recommendedScale,
            out int fps)
        {
            isDirectionalRight = false;
            playOnCaster = false;
            recommendedScale = 2.2f;
            fps = 15;

            SkillEffectMatcher.VariantEntry ve;
            SkillEffectMatcher.FamilyEntry fe;
            if (!SkillEffectMatcher.TryGetById(animationId, out ve, out fe))
            {
                return null;
            }

            EffectRuntimeMeta cachedMeta;
            Sprite[] cachedSprites;
            if (_runtimeSpriteCache.TryGetValue(animationId, out cachedSprites) &&
                _runtimeMetaCache.TryGetValue(animationId, out cachedMeta))
            {
                isDirectionalRight = cachedMeta.isDirectionalRight;
                playOnCaster = cachedMeta.playOnCaster;
                recommendedScale = cachedMeta.recommendedScale;
                fps = cachedMeta.fps;
                return cachedSprites;
            }

            string folder = ve.FolderName;
            isDirectionalRight = ve.CnName.Contains("向右") || folder.StartsWith("pj1_") || folder.StartsWith("pj2_") || folder.Contains("boost");
            playOnCaster = fe != null && fe.PlayOnCaster;

            string spritesheetsDir = Path.Combine(Application.dataPath, "Effects/Spritesheets");
            string pngPath = Path.Combine(spritesheetsDir, folder + ".png");
            string txtPath = Path.Combine(spritesheetsDir, folder + ".txt");

            if (!File.Exists(pngPath) || !File.Exists(txtPath))
            {
                return null;
            }

            byte[] pngBytes = File.ReadAllBytes(pngPath);
            Texture2D tex = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            tex.filterMode = FilterMode.Point;
            tex.wrapMode = TextureWrapMode.Clamp;
            if (!tex.LoadImage(pngBytes))
            {
                return null;
            }

            int texH = tex.height;
            var pixels=tex.GetPixels32();
            string[] lines = File.ReadAllLines(txtPath);
            List<Sprite> spriteList = new List<Sprite>();
            int maxDim = 64;

            for (int i = 0; i < lines.Length; i++)
            {
                string line = lines[i].Trim();
                if (string.IsNullOrEmpty(line)) continue;
                int eqIdx = line.IndexOf('=');
                if (eqIdx < 0) continue;

                string[] nums = line.Substring(eqIdx + 1).Trim().Split(new char[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                if (nums.Length < 4) continue;

                int x = int.Parse(nums[0]);
                int y = int.Parse(nums[1]);
                int w = int.Parse(nums[2]);
                int h = int.Parse(nums[3]);
                if (w > maxDim) maxDim = w;
                if (h > maxDim) maxDim = h;

                // spritesheet.txt 为左上角原点，转换为 Unity 左下角原点
                int unityY = texH - y - h;
                Rect rect = new Rect(x, unityY, w, h);
                Sprite sp = Sprite.Create(tex, rect, EffectFrameAlignment.Pivot(pixels,tex.width,rect), 32f);
                sp.name = string.Format("{0}_{1:D2}", folder, i);
                spriteList.Add(sp);
            }

            if (maxDim <= 32) recommendedScale = 3.6f;
            else if (maxDim <= 48) recommendedScale = 3.0f;
            else if (maxDim <= 64) recommendedScale = 2.4f;
            else if (maxDim <= 76) recommendedScale = 2.1f;
            else if (maxDim <= 96) recommendedScale = 1.75f;
            else if (maxDim <= 128) recommendedScale = 1.40f;
            else if (maxDim <= 160) recommendedScale = 1.15f;
            else recommendedScale = 1.00f;

            Sprite[] result = spriteList.ToArray();
            _runtimeSpriteCache[animationId] = result;
            _runtimeMetaCache[animationId] = new EffectRuntimeMeta
            {
                isDirectionalRight = isDirectionalRight,
                playOnCaster = playOnCaster,
                recommendedScale = recommendedScale,
                fps = fps
            };
            return result;
        }
    }
}
