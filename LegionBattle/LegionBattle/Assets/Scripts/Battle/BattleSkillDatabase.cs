using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 前后字段词库组
    /// </summary>
    public class SkillAffixBank
    {
        public List<string> Prefixes = new List<string>();
        public List<string> Suffixes = new List<string>();
    }

    /// <summary>
    /// 技能数据仓库与随机词库生成引擎
    /// 支持从 skill_affixes.txt 读取自定义前后字段，并动态组合生成四流派各阶位全机制技能
    /// 涵盖：暴击、真伤、回复、怒气、反噬、吸血、虚弱、重伤、流血、中毒、名刀锁血与四维动态修改
    /// </summary>
    public static class BattleSkillDatabase
    {
        private static bool _initialized = false;
        private static int _nextCustomId = 2000001;

        // ─── 前后字段词库管理器 ───
        public static int ConnectMode = 0; // 0: 智能混合 (70%直接, 30%之), 1: 纯直接拼接, 2: 纯“之”字拼接
        public static SkillAffixBank CommonAffixes = new SkillAffixBank();
        public static SkillAffixBank HavocAffixes = new SkillAffixBank();
        public static SkillAffixBank PrecisionAffixes = new SkillAffixBank();
        public static SkillAffixBank TenacityAffixes = new SkillAffixBank();
        public static SkillAffixBank UtilityAffixes = new SkillAffixBank();

        // ─── 高阶构词范式扩展库 ───
        public static List<string> MonoActions = new List<string>();
        public static List<string> MonoObjects = new List<string>();
        public static List<string> MonoCarriers = new List<string>();
        public static List<string> MonoModifiers = new List<string>();
        public static List<string> MonoBeasts = new List<string>();

        public static List<string> EpicVerbs = new List<string>();
        public static List<string> EpicTargets = new List<string>();
        public static List<string> EpicRelics = new List<string>();

        public static List<string> ApexPrefixes = new List<string>();
        public static List<string> ApexActions = new List<string>();
        public static List<string> ApexFields = new List<string>();


        public static void EnsureInitialized()
        {
            if (_initialized) return;
            _initialized = true;
            LoadAffixBank();
        }

        private static void LoadAffixBank()
        {
            try
            {
                TextAsset affixAsset = Resources.Load<TextAsset>("skill_affixes");
                if (affixAsset != null)
                {
                    string[] lines = affixAsset.text.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                    string currentSection = "";

                    CommonAffixes.Prefixes.Clear(); CommonAffixes.Suffixes.Clear();
                    HavocAffixes.Prefixes.Clear(); HavocAffixes.Suffixes.Clear();
                    PrecisionAffixes.Prefixes.Clear(); PrecisionAffixes.Suffixes.Clear();
                    TenacityAffixes.Prefixes.Clear(); TenacityAffixes.Suffixes.Clear();
                    UtilityAffixes.Prefixes.Clear(); UtilityAffixes.Suffixes.Clear();

                    MonoActions.Clear(); MonoObjects.Clear(); MonoCarriers.Clear();
                    MonoModifiers.Clear(); MonoBeasts.Clear();
                    EpicVerbs.Clear(); EpicTargets.Clear(); EpicRelics.Clear();
                    ApexPrefixes.Clear(); ApexActions.Clear(); ApexFields.Clear();

                    foreach (var rawLine in lines)
                    {
                        string line = rawLine.Trim();
                        if (string.IsNullOrEmpty(line) || line.StartsWith("#")) continue;

                        if (line.StartsWith("[") && line.EndsWith("]"))
                        {
                            currentSection = line.Substring(1, line.Length - 2);
                            continue;
                        }

                        if (currentSection == "ConnectMode")
                        {
                            int mode;
                            if (int.TryParse(line, out mode)) ConnectMode = mode;
                        }
                        else if (currentSection == "Common_Prefixes") CommonAffixes.Prefixes.Add(line);
                        else if (currentSection == "Common_Suffixes") CommonAffixes.Suffixes.Add(line);
                        else if (currentSection == "Havoc_Prefixes" || currentSection == "Courage_Prefixes") HavocAffixes.Prefixes.Add(line);
                        else if (currentSection == "Havoc_Suffixes" || currentSection == "Courage_Suffixes") HavocAffixes.Suffixes.Add(line);
                        else if (currentSection == "Precision_Prefixes" || currentSection == "Initiative_Prefixes") PrecisionAffixes.Prefixes.Add(line);
                        else if (currentSection == "Precision_Suffixes" || currentSection == "Initiative_Suffixes") PrecisionAffixes.Suffixes.Add(line);
                        else if (currentSection == "Tenacity_Prefixes" || currentSection == "Resilience_Prefixes") TenacityAffixes.Prefixes.Add(line);
                        else if (currentSection == "Tenacity_Suffixes" || currentSection == "Resilience_Suffixes") TenacityAffixes.Suffixes.Add(line);
                        else if (currentSection == "Utility_Prefixes" || currentSection == "Magic_Prefixes") UtilityAffixes.Prefixes.Add(line);
                        else if (currentSection == "Utility_Suffixes" || currentSection == "Magic_Suffixes") UtilityAffixes.Suffixes.Add(line);
                        else if (currentSection == "Mono_Actions") MonoActions.Add(line);
                        else if (currentSection == "Mono_Objects") MonoObjects.Add(line);
                        else if (currentSection == "Mono_Carriers") MonoCarriers.Add(line);
                        else if (currentSection == "Mono_Modifiers") MonoModifiers.Add(line);
                        else if (currentSection == "Mono_Beasts") MonoBeasts.Add(line);
                        else if (currentSection == "Epic_Verbs") EpicVerbs.Add(line);
                        else if (currentSection == "Epic_Targets") EpicTargets.Add(line);
                        else if (currentSection == "Epic_Relics") EpicRelics.Add(line);
                        else if (currentSection == "Apex_Prefixes") ApexPrefixes.Add(line);
                        else if (currentSection == "Apex_Actions") ApexActions.Add(line);
                        else if (currentSection == "Apex_Fields") ApexFields.Add(line);
                    }
                }
                else
                {
                    InitDefaultAffixes();
                }
            }
            catch
            {
                InitDefaultAffixes();
            }
        }

        private static void InitDefaultAffixes()
        {
            CommonAffixes.Prefixes = new List<string> { "狂暴", "疾风", "烈焰", "暗影", "圣光", "虚空", "末日", "极光" };
            CommonAffixes.Suffixes = new List<string> { "斩", "刺", "之刃", "之光", "咆哮", "冲击", "破" };
            HavocAffixes.Prefixes = new List<string> { "崩山", "裂地", "毁灭", "怒斩", "狂怒", "修罗" };
            HavocAffixes.Suffixes = new List<string> { "崩天斩", "巨刃", "暴风", "旋风斩", "断头台" };
            PrecisionAffixes.Prefixes = new List<string> { "透甲", "穿心", "无影", "弑神", "绝灭" };
            PrecisionAffixes.Suffixes = new List<string> { "真伤刺", "影刃", "死线", "断界刃" };
            TenacityAffixes.Prefixes = new List<string> { "圣愈", "生息", "涅槃", "大地", "坚毅" };
            TenacityAffixes.Suffixes = new List<string> { "祈言", "壁垒", "苏生", "庇护" };
            UtilityAffixes.Prefixes = new List<string> { "因果", "命格", "虚弱", "剧毒", "逆转" };
            UtilityAffixes.Suffixes = new List<string> { "诅咒", "互换", "抽离", "天平" };
        }

        private static SkillAffixBank GetBankByGenre(string genre)
        {
            if (genre == "勇气" || genre.Contains("勇气")) return HavocAffixes;
            if (genre == "先机" || genre.Contains("先机")) return PrecisionAffixes;
            if (genre == "坚韧" || genre.Contains("坚韧")) return TenacityAffixes;
            if (genre == "魔力" || genre.Contains("魔力")) return UtilityAffixes;
            return CommonAffixes;
        }

        public static string GenerateMonoName(out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            if (MonoActions.Count == 0 || MonoObjects.Count == 0 || MonoCarriers.Count == 0)
            {
                return "斩天剑";
            }

            if (UnityEngine.Random.Range(0, 100) < 50 && MonoModifiers.Count > 0 && MonoBeasts.Count > 0)
            {
                // 1B: 修饰(1) + 主体(1) + 核心部位(1) = 3字 (如: 邪龙眼、圣兽心、魔王角)
                string m = MonoModifiers[UnityEngine.Random.Range(0, MonoModifiers.Count)];
                string b = MonoBeasts[UnityEngine.Random.Range(0, MonoBeasts.Count)];
                string c = MonoCarriers[UnityEngine.Random.Range(0, MonoCarriers.Count)];
                if (c == "盾" || c == "塔") c = "矛";
                string name = m + b + c;

                if (c == "枪" || c == "矛" || c == "眼" || c == "心" || c == "瞳" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "骨" || c == "印") { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (c == "爪" || c == "翼" || c == "轮" || c == "扇") { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (c == "锤" || c == "斧") { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (c == "炮" || c == "珠") { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else
            {
                // 1A: 动词(1) + 宾语(1) + 兵器/载体(1) = 3字 (如: 斩天剑、破魔刃、断魂枪)
                string a = MonoActions[UnityEngine.Random.Range(0, MonoActions.Count)];
                string o = MonoObjects[UnityEngine.Random.Range(0, MonoObjects.Count)];
                string c = MonoCarriers[UnityEngine.Random.Range(0, MonoCarriers.Count)];
                if (c == "盾" || c == "塔") c = "刃";
                string name = a + o + c;

                if (c == "枪" || c == "矛" || c == "弓" || c == "矢") { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (c == "印") { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (c == "轮" || c == "链" || c == "爪") { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (c == "锤" || c == "斧") { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (c == "炮") { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (c == "拳") { hitReactionType = 2; reactionName = "垂直击飞"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
        }

        public static string GenerateSixCharName(out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            bool pickEpic = (UnityEngine.Random.Range(0, 100) < 50);
            if (pickEpic && EpicVerbs.Count > 0 && EpicTargets.Count > 0 && EpicRelics.Count > 0)
            {
                // 范式 3：宏大长句诗意式 (2+2+2=6字，如: 撕裂天空之剑、贯穿星辰之枪、毁灭世界之矛)
                string ev = EpicVerbs[UnityEngine.Random.Range(0, EpicVerbs.Count)];
                string et = EpicTargets[UnityEngine.Random.Range(0, EpicTargets.Count)];
                string er = EpicRelics[UnityEngine.Random.Range(0, EpicRelics.Count)];
                if (er.Contains("盾") || er.Contains("铠")) er = "之矛";
                string name = ev + et + er;

                if (er.Contains("枪") || er.Contains("矛") || er.Contains("箭")) { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (er.Contains("锁") || er.Contains("牢")) { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else if (er.Contains("火") || er.Contains("光") || er.Contains("核")) { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (er.Contains("锤") || er.Contains("息") || er.Contains("印")) { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (er.Contains("爪") || er.Contains("歌") || er.Contains("门")) { hitReactionType = 5; reactionName = "波浪状掀飞"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else if (ApexPrefixes.Count > 0 && ApexActions.Count > 0 && ApexFields.Count > 0)
            {
                // 范式 4：极境战技风暴式 (2+2+2=6字，如: 究极斩击风暴、极限连刺骤雨、苍穹坠击陨星)
                string ap = ApexPrefixes[UnityEngine.Random.Range(0, ApexPrefixes.Count)];
                string aa = ApexActions[UnityEngine.Random.Range(0, ApexActions.Count)];
                string af = ApexFields[UnityEngine.Random.Range(0, ApexFields.Count)];
                string name = ap + aa + af;

                if (af.Contains("风暴") || af.Contains("旋涡")) { hitReactionType = 4; reactionName = "四向旋转翻滚"; }
                else if (af.Contains("骤雨") || af.Contains("射线") || aa.Contains("刺")) { hitReactionType = 3; reactionName = "抛物线后仰"; }
                else if (af.Contains("爆轰") || af.Contains("陨星") || af.Contains("裂变") || af.Contains("火海")) { hitReactionType = 6; reactionName = "中心炸散复位"; }
                else if (af.Contains("冲击") || af.Contains("狂潮") || af.Contains("辉光") || af.Contains("狂澜")) { hitReactionType = 5; reactionName = "波浪状掀飞"; }
                else if (af.Contains("震荡") || af.Contains("怒涛") || af.Contains("怒炎") || af.Contains("暗涌")) { hitReactionType = 8; reactionName = "地震颠簸"; }
                else if (af.Contains("结界") || af.Contains("领域")) { hitReactionType = 7; reactionName = "手风琴压缩"; }
                else { hitReactionType = 1; reactionName = "水平震退"; }
                return name;
            }
            else if (EpicVerbs.Count > 0 && EpicTargets.Count > 0 && EpicRelics.Count > 0)
            {
                string ev = EpicVerbs[UnityEngine.Random.Range(0, EpicVerbs.Count)];
                string et = EpicTargets[UnityEngine.Random.Range(0, EpicTargets.Count)];
                string er = EpicRelics[UnityEngine.Random.Range(0, EpicRelics.Count)];
                return ev + et + er;
            }

            return "究极斩击风暴";
        }

        public static string GenerateFourCharName(string genre, out int hitReactionType, out string reactionName)
        {
            hitReactionType = 1;
            reactionName = "水平震退";

            SkillAffixBank genreBank = GetBankByGenre(genre);

            List<string> pList = new List<string>();
            if (genreBank.Prefixes.Count > 0) pList.AddRange(genreBank.Prefixes);
            else if (CommonAffixes.Prefixes.Count > 0) pList.AddRange(CommonAffixes.Prefixes);

            List<string> sList = new List<string>();
            if (genreBank.Suffixes.Count > 0) sList.AddRange(genreBank.Suffixes);
            else if (CommonAffixes.Suffixes.Count > 0) sList.AddRange(CommonAffixes.Suffixes);

            if (pList.Count == 0 && sList.Count == 0) return "修罗崩击";
            if (pList.Count == 0) pList.Add("狂暴");
            if (sList.Count == 0) sList.Add("崩击");

            for (int retry = 0; retry < 25; retry++)
            {
                string p = pList[UnityEngine.Random.Range(0, pList.Count)];
                string rawS = sList[UnityEngine.Random.Range(0, sList.Count)];
                string s;
                TryParseSuffixHitReaction(rawS, out s, out hitReactionType, out reactionName);

                string res;
                if (s.Length == 1)
                {
                    // 2字前缀 + "之" + 1字后缀 = 4字 (如: 疾风之斩, 烈焰之击)
                    res = p + "之" + s;
                }
                else if (s.Length == 2)
                {
                    // 2字前缀 + 2字后缀 = 4字 (如: 修罗崩击, 以太脉冲)
                    res = p + s;
                }
                else
                {
                    res = p + s;
                }

                if (res.Length == 4 && !HasAwkwardOverlap(res))
                {
                    return res;
                }
            }

            // 兜底直接组合为4字
            string fbRawS = sList[UnityEngine.Random.Range(0, sList.Count)];
            string fbS;
            TryParseSuffixHitReaction(fbRawS, out fbS, out hitReactionType, out reactionName);
            string fallback = pList[UnityEngine.Random.Range(0, pList.Count)] + (fbS.Length == 1 ? ("之" + fbS) : fbS);
            return fallback;
        }

        private static bool HasAwkwardOverlap(string name)
        {
            if (string.IsNullOrEmpty(name)) return false;
            for (int i = 0; i < name.Length; i++)
            {
                for (int j = i + 1; j < name.Length; j++)
                {
                    if (name[i] == name[j]) return true;
                }
            }
            return false;
        }

        /// <summary>
        /// 从用户词库动态生成技能名字，严格遵循阶位构词规则：
        /// 1. T1、T2：100% 用单字组合 (3字，如: 斩天剑、邪龙眼)
        /// 2. T6：100% 用 6字 (宏大长句诗意式 + 极境战技风暴式，如: 撕裂天空之剑、究极斩击风暴)
        /// 3. T3、T4、T5：四字始终占 75%，从单字更高过渡到多字更高：
        ///    - T3: 四字 75%, 单字 20%, 六字 5%   (单字更高)
        ///    - T4: 四字 75%, 单字 12.5%, 六字 12.5% (平分过渡)
        ///    - T5: 四字 75%, 单字 5%, 六字 20%   (多字更高)
        /// </summary>
        public static string GenerateRandomSkillName(string genre)
        {
            int hitReactionType;
            string reactionName;
            return GenerateRandomSkillName(genre, 0, out hitReactionType, out reactionName);
        }

        public static string GenerateRandomSkillName(string genre, int tier, out int hitReactionType, out string reactionName)
        {
            EnsureInitialized();
            hitReactionType = 1;
            reactionName = "水平震退";

            if (tier == 1 || tier == 2)
            {
                return GenerateMonoName(out hitReactionType, out reactionName);
            }
            else if (tier == 6)
            {
                return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 3)
            {
                float roll = UnityEngine.Random.value;
                if (roll < 0.75f) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.95f) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 4)
            {
                float roll = UnityEngine.Random.value;
                if (roll < 0.75f) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.875f) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else if (tier == 5)
            {
                float roll = UnityEngine.Random.value;
                if (roll < 0.75f) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.80f) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
            else
            {
                float roll = UnityEngine.Random.value;
                if (roll < 0.75f) return GenerateFourCharName(genre, out hitReactionType, out reactionName);
                else if (roll < 0.875f) return GenerateMonoName(out hitReactionType, out reactionName);
                else return GenerateSixCharName(out hitReactionType, out reactionName);
            }
        }

        /// <summary>
        /// 解析后缀绑定的受击表现效果 (例如 "斩:震退", "刺:击飞", "轰:后仰", "旋:旋转", "浪:掀飞", "爆:炸散", "压:压缩", "震:颠簸", 或数字 "斩:1", "挑:2")
        /// </summary>
        public static bool TryParseSuffixHitReaction(string rawSuffix, out string cleanSuffix, out int hitReactionType, out string reactionName)
        {
            cleanSuffix = rawSuffix ?? "";
            hitReactionType = 1;
            reactionName = "水平震退";
            if (string.IsNullOrEmpty(rawSuffix)) return false;

            char[] seps = new char[] { ':', '：', '|', '=' };
            int idx = rawSuffix.IndexOfAny(seps);
            if (idx < 0) return false;

            cleanSuffix = rawSuffix.Substring(0, idx).Trim();
            string tag = rawSuffix.Substring(idx + 1).Trim().ToLowerInvariant();

            if (tag == "1" || tag.Contains("水平") || tag.Contains("震退") || tag.Contains("击退") || tag.Contains("knockback"))
            {
                hitReactionType = 1; reactionName = "水平震退"; return true;
            }
            if (tag == "2" || tag.Contains("垂直") || tag.Contains("击飞") || tag.Contains("浮空") || tag.Contains("popup") || tag.Contains("pop-up"))
            {
                hitReactionType = 2; reactionName = "垂直击飞"; return true;
            }
            if (tag == "3" || tag.Contains("抛物线") || tag.Contains("后仰") || tag.Contains("击倒") || tag.Contains("launch"))
            {
                hitReactionType = 3; reactionName = "抛物线后仰"; return true;
            }
            if (tag == "4" || tag.Contains("旋转") || tag.Contains("翻滚") || tag.Contains("四向") || tag.Contains("spin"))
            {
                hitReactionType = 4; reactionName = "四向旋转翻滚"; return true;
            }
            if (tag == "5" || tag.Contains("波浪") || tag.Contains("掀飞") || tag.Contains("wave"))
            {
                hitReactionType = 5; reactionName = "波浪状掀飞"; return true;
            }
            if (tag == "6" || tag.Contains("炸散") || tag.Contains("中心炸散") || tag.Contains("爆散") || tag.Contains("disperse"))
            {
                hitReactionType = 6; reactionName = "中心炸散复位"; return true;
            }
            if (tag == "7" || tag.Contains("手风琴") || tag.Contains("压缩") || tag.Contains("压制") || tag.Contains("squeeze"))
            {
                hitReactionType = 7; reactionName = "手风琴压缩"; return true;
            }
            if (tag == "8" || tag.Contains("地震") || tag.Contains("颠簸") || tag.Contains("震颤") || tag.Contains("tremor"))
            {
                hitReactionType = 8; reactionName = "地震颠簸"; return true;
            }
            if (tag == "9" || tag.Contains("聚拢") || tag.Contains("吸附") || tag.Contains("坍缩") || tag.Contains("黑洞") || tag.Contains("converge") || tag.Contains("pull"))
            {
                hitReactionType = 9; reactionName = "中心聚拢吸附"; return true;
            }
            if (tag == "10" || tag.Contains("旋转散开") || tag.Contains("集体旋转") || tag.Contains("漩涡") || tag.Contains("波纹") || tag.Contains("swirl"))
            {
                hitReactionType = 10; reactionName = "集体旋转散开"; return true;
            }

            return false;
        }

        public static string GetHitReactionName(int type)
        {
            switch (type)
            {
                case 1: return "水平震退";
                case 2: return "垂直击飞";
                case 3: return "抛物线后仰";
                case 4: return "四向旋转翻滚";
                case 5: return "波浪状掀飞";
                case 6: return "中心炸散复位";
                case 7: return "手风琴压缩";
                case 8: return "地震颠簸";
                case 9: return "中心聚拢吸附";
                case 10: return "集体旋转散开";
                default: return "水平震退";
            }
        }

        public static int GetDefaultHitReactionForGenre(string genre)
        {
            switch (genre)
            {
                case "勇气": return 1; // 水平震退
                case "先机": return 2; // 垂直击飞
                case "坚韧": return 7; // 手风琴压缩
                case "魔力": return 6; // 中心炸散复位
                default: return 1;
            }
        }

        /// <summary>
        /// 根据阶位（T1~T6）由词库动态组合生成全功能随机技能 (包含全套伤害、门槛与BUFF附加机制)
        /// 支持通过特效家族表现绑定 10 种受击动作（含 9:中心聚拢吸附 适配黑洞虫洞、10:集体旋转散开 适配漩涡波纹）
        /// </summary>
        public static BattleSkill GenerateRandomSkill(int tier, string selectedAxis = null, string role = "filler", RuntimeSkillRecord selectedSource = null)
        {
            EnsureInitialized();
            int t = Mathf.Clamp(tier, 1, 6);

            // 1. 抽取流派
            string[] genres = new string[] { "勇气", "先机", "坚韧", "魔力" };
            string genre = selectedAxis == null ? genres[UnityEngine.Random.Range(0, genres.Length)] : BattleRuntimeCatalogue.AxisName(selectedAxis);
            SkillAffixBank bank = GetBankByGenre(genre);

            // 抽取技能名字与受击动作 (严格遵照阶位构词规则: T1/T2单字组合3字, T6全6字, T3/4/5四字占75%且从单字过渡到多字)
            int hitReactionType;
            string reactionName;
            string skillName = GenerateRandomSkillName(genre, t, out hitReactionType, out reactionName);

            // 2. 构建技能实体并绑定受击动作类型
            BattleSkill skill = new BattleSkill();
            skill.id = _nextCustomId++;
            skill.name = skillName;
            skill.rarityTier = t;
            skill.hitReactionType = hitReactionType;

            // Numerical fields come from the same measured generator catalogue as research.
            RuntimeSkillRecord source = selectedSource ?? BattleRuntimeCatalogue.Pick(t, genre, role);
            skill.rarityTier = source.tier;
            skill.combat = source.skill;
            skill.combat.name = skill.name;
            skill.levelOneStats = source.start;
            skill.levelThirtyStats = source.end;
            skill.effectType = source.skill.axis == "C" ? BattleSkillEffectType.Critical :
                source.skill.axis == "R" ? BattleSkillEffectType.HealBySelfMaxBP :
                source.skill.axis == "I" ? BattleSkillEffectType.TrueDamage : BattleSkillEffectType.IncreaseDamage;
            skill.bufferId = source.skill.subEffect == "最大流失" ? 2 : source.skill.subEffect == "已损流失" ? 1 : 0;

            // 6.5 根据技能前缀(决定颜色与元素) + 后缀/载体(决定特效种类) 绑定唯一 animationId、中文特征名及高度匹配的受击表现
            string subHint = "";
            if (skill.bufferId == 1) subHint = "流血伤害";
            else if (skill.bufferId == 2) subHint = "中毒伤害";
            else if (skill.effectType == BattleSkillEffectType.BPSteal) subHint = "吸收";

            string effectCategory;
            int matchedHitType;
            string matchedHitName;
            SkillEffectMatcher.ResolveSkillEffect(
                skill.name,
                genre,
                t,
                subHint,
                out skill.animationId,
                out skill.effectCnName,
                out skill.effectFolder,
                out effectCategory,
                out matchedHitType,
                out matchedHitName);
            if (matchedHitType > 0)
            {
                skill.hitReactionType = matchedHitType;
            }

            // 7. 组装技能描述
            skill.desc = source.description;
            return skill;
        }

        /// <summary>
        /// 根据角色品阶分配随机技能（完全由前后字段词库与机制引擎实时动态生成）
        /// </summary>
        public static BattleSkill GetRandomSkillForTier(int tier)
        {
            return GenerateRandomSkill(tier);
        }
    }
}
