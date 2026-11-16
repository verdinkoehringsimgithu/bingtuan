using System;
using System.Collections.Generic;
using System.IO;
using System.Text;

namespace LegionBattle.Battle
{
    /// <summary>
    /// 技能词条 -> 像素特效 (Super Pixel Effects Megapack 1) 高精双轴适配引擎
    /// 轴1：前缀/修饰词/宾语/流派 -> 决定特效颜色 (Color) 与元素亲和 (Element)
    /// 轴2：后缀/兵器载体/极境领域/子机制 -> 决定特效核心动作家族 (BaseKey)
    /// 双标签过滤：
    ///   - 第一标签 (UserTag)：先机 / 坚韧 / 勇气 / 魔力 / 通用 / 禁用
    ///   - 第二标签 (PlayOnCaster / 是否针对自身)：
    ///       * 针对自身 (PlayOnCaster == true)：仅限【坚韧】技能使用，在己方身上播放，对敌方受击固定为普通击退 [1]水平震退
    ///       * 针对敌方 (PlayOnCaster == false)：根据第一标签决定哪些流派可用（【坚韧】同样可使用对敌特效），对敌方触发专属受击表现 (1~10)
    /// </summary>
    public static class SkillEffectMatcher
    {
        public class VariantEntry
        {
            public int AnimationId;
            public string Color;
            public string CnName;
            public string FolderName;
        }

        public class FamilyEntry
        {
            public string BaseKey;
            public string CategoryCn;
            public string PureTitleCn;
            public string UserTag;
            public bool PlayOnCaster;
            public bool IsDisabled;
            public int HitReactionType;
            public string HitReactionName;
            public int DefaultHitReactionType;
            public string DefaultHitReactionName;
            public Dictionary<string, VariantEntry> Variants = new Dictionary<string, VariantEntry>();
        }

        private static bool _initialized = false;
        private static DateTime _lastJsonWriteTimeUtc = DateTime.MinValue;
        private static readonly Dictionary<string, FamilyEntry> _families = new Dictionary<string, FamilyEntry>();
        private static readonly List<FamilyEntry> _familyList = new List<FamilyEntry>();
        private static readonly Dictionary<int, VariantEntry> _idToVariant = new Dictionary<int, VariantEntry>();
        private static readonly Dictionary<int, FamilyEntry> _idToFamily = new Dictionary<int, FamilyEntry>();

        public static void EnsureInitialized()
        {
            if (!_initialized)
            {
                _initialized = true;
                _families.Clear();
                _familyList.Clear();
                _idToVariant.Clear();
                _idToFamily.Clear();

            Reg("expfx1_epic_explosion_A", "[通用|对敌] 冲天爆破气柱", "通用", false, 2, "垂直击飞", "blue:1001:大蓝上升爆炸|green:1002:大绿上升爆炸|orange:1003:大橙上升爆炸|pink:1004:大粉上升爆炸|red:1005:大红上升爆炸|violet:1006:大紫上升爆炸|white:1007:大白上升爆炸|yellow:1008:大黄上升爆炸");
            Reg("expfx1_epic_explosion_B", "[通用|对敌] 史诗毁灭大爆炸", "通用", false, 6, "中心炸散复位", "blue:1009:巨蓝大爆炸|green:1010:巨绿大爆炸|orange:1011:巨橙大爆炸|pink:1012:巨粉大爆炸|red:1013:巨红大爆炸|violet:1014:巨紫大爆炸|white:1015:巨白大爆炸|yellow:1016:巨黄大爆炸");
            Reg("expfx1_stylized_explosion_A", "[通用|对敌] 气浪烟雾大爆炸", "通用", false, 5, "波浪状掀飞", "blue:1017:大蓝气浪烟雾爆炸|green:1018:大绿气浪烟雾爆炸|orange:1019:大橙气浪烟雾爆炸|pink:1020:大粉气浪烟雾爆炸|red:1021:大红气浪烟雾爆炸|violet:1022:大紫气浪烟雾爆炸|white:1023:大白气浪烟雾爆炸|yellow:1024:大黄气浪烟雾爆炸");
            Reg("expfx1_stylized_explosion_B", "[通用|对敌] 旋风球乱舞爆炸", "通用", false, 10, "集体旋转散开", "blue:1025:大蓝旋风球爆炸|green:1026:大绿旋风球爆炸|orange:1027:大橙旋风球爆炸|pink:1028:大粉旋风球爆炸|red:1029:大红旋风球爆炸|violet:1030:大紫旋风球爆炸|white:1031:大白旋风球爆炸|yellow:1032:大黄旋风球爆炸");
            Reg("expfx1_stylized_explosion_C", "[通用|对敌] 云朵升腾巨爆", "通用", false, 2, "垂直击飞", "blue:1033:巨蓝云朵上升爆炸|green:1034:巨绿云朵上升爆炸|orange:1035:巨橙云朵上升爆炸|pink:1036:巨粉云朵上升爆炸|red:1037:巨红云朵上升爆炸|violet:1038:巨紫云朵上升爆炸|white:1039:巨白云朵上升爆炸|yellow:1040:巨黄云朵上升爆炸");
            Reg("expfx1_symmetrical_explosion_A", "[通用|对敌] 密集烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1041:大蓝密集烟雾爆炸|green:1042:大绿密集烟雾爆炸|orange:1043:大橙密集烟雾爆炸|pink:1044:大粉密集烟雾爆炸|red:1045:大红密集烟雾爆炸|violet:1046:大紫密集烟雾爆炸|white:1047:大白密集烟雾爆炸|yellow:1048:大黄密集烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_B", "[通用|对敌] 闪光烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1049:大蓝闪光烟雾爆炸|green:1050:大绿闪光烟雾爆炸|orange:1051:大橙闪光烟雾爆炸|pink:1052:大粉闪光烟雾爆炸|red:1053:大红闪光烟雾爆炸|violet:1054:大紫闪光烟雾爆炸|white:1055:大白闪光烟雾爆炸|yellow:1056:大黄闪光烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_C", "[通用|对敌] 聚拢烟雾对称爆", "通用", false, 8, "地震颠簸", "blue:1057:大蓝聚拢烟雾爆炸|green:1058:大绿聚拢烟雾爆炸|orange:1059:大橙聚拢烟雾爆炸|pink:1060:大粉聚拢烟雾爆炸|red:1061:大红聚拢烟雾爆炸|violet:1062:大紫聚拢烟雾爆炸|white:1063:大白聚拢烟雾爆炸|yellow:1064:大黄聚拢烟雾爆炸");
            Reg("expfx1_symmetrical_explosion_D", "[通用|对敌] 分裂烟雾对称爆", "通用", false, 6, "中心炸散复位", "blue:1065:大蓝分裂烟雾爆炸|green:1066:大绿分裂烟雾爆炸|orange:1067:大橙分裂烟雾爆炸|pink:1068:大粉分裂烟雾爆炸|red:1069:大红分裂烟雾爆炸|violet:1070:大紫分裂烟雾爆炸|white:1071:大白分裂烟雾爆炸|yellow:1072:大黄分裂烟雾爆炸");
            Reg("fanfx1_magic_burst_A", "[通用|对敌] 奥术星星爆裂", "通用", false, 3, "抛物线后仰", "blue:1073:大蓝星星爆裂|green:1074:大绿星星爆裂|orange:1075:大橙星星爆裂|rainbow:1076:大彩虹星星爆裂|red:1077:大红星星爆裂|violet:1078:大紫星星爆裂|white:1079:大白星星爆裂|yellow:1080:大黄星星爆裂");
            Reg("fanfx1_magic_burst_B", "[通用|对敌] 璀璨星辰闪光爆裂", "通用", false, 3, "抛物线后仰", "blue:1081:巨蓝星星闪光爆裂|green:1082:巨绿星星闪光爆裂|orange:1083:巨橙星星闪光爆裂|rainbow:1084:巨彩虹星星闪光爆裂|red:1085:巨红星星闪光爆裂|violet:1086:巨紫星星闪光爆裂|white:1087:巨白星星闪光爆裂|yellow:1088:巨黄星星闪光爆裂");
            Reg("fanfx1_magic_puff_A", "[通用|对敌] 秘法星星烟雾爆炸", "通用", false, 8, "地震颠簸", "blue:1089:大蓝魔法星星烟雾爆炸|green:1090:大绿魔法星星烟雾爆炸|orange:1091:大橙魔法星星烟雾爆炸|red:1092:大红魔法星星烟雾爆炸|violet:1093:大紫魔法星星烟雾爆炸|white:1094:大白魔法星星烟雾爆炸|yellow:1095:大黄魔法星星烟雾爆炸");
            Reg("fanfx1_magic_puff_B", "[坚韧|对敌] 灵气烟雾升腾", "坚韧", false, 1, "水平震退", "blue:1096:大蓝烟雾上升|green:1097:大绿烟雾上升|orange:1098:大橙烟雾上升|red:1099:大红烟雾上升|violet:1100:大紫烟雾上升|white:1101:大白烟雾上升|yellow:1102:大黄烟雾上升");
            Reg("fanfx1_skull_puff", "[通用|对敌] 死灵骷髅烟雾爆炸", "通用", false, 8, "地震颠簸", "blue:1103:大蓝骷髅烟雾爆炸|green:1104:大绿骷髅烟雾爆炸|orange:1105:大橙骷髅烟雾爆炸|red:1106:大红骷髅烟雾爆炸|violet:1107:大紫骷髅烟雾爆炸|white:1108:大白骷髅烟雾爆炸|yellow:1109:大黄骷髅烟雾爆炸");
            Reg("fanfx1_spellcast_A", "[通用|对敌] 禁锢波纹眩晕星星", "通用", false, 10, "集体旋转散开", "blue:1110:大蓝波纹眩晕星星|green:1111:大绿波纹眩晕星星|orange:1112:大橙波纹眩晕星星|rainbow:1113:大彩虹波纹眩晕星星|red:1114:大红波纹眩晕星星|violet:1115:大紫波纹眩晕星星|yellow:1116:大黄波纹眩晕星星");
            Reg("fanfx1_spellcast_B", "[坚韧|自身] 祈愿波纹星星上升", "坚韧", true, 1, "水平震退", "blue:1117:大蓝波纹星星上升|green:1118:大绿波纹星星上升|orange:1119:大橙波纹星星上升|red:1120:大红波纹星星上升|violet:1121:大紫波纹星星上升|yellow:1122:大黄波纹星星上升");
            Reg("fanfx1_spellcast_C", "[魔力|对敌] 诅咒火焰波纹下降", "魔力", false, 8, "地震颠簸", "blue:1123:大蓝火焰波纹烟雾下降|green:1124:大绿火焰波纹烟雾下降|orange:1125:大橙火焰波纹烟雾下降|red:1126:大红火焰波纹烟雾下降|violet:1127:大紫火焰波纹烟雾下降|yellow:1128:大黄火焰波纹烟雾下降");
            Reg("fanfx1_spellcast_D", "[坚韧|自身] 金星波纹火焰升腾", "坚韧", true, 1, "水平震退", "blue:1129:大蓝金星波纹火焰上升|green:1130:大绿金星波纹火焰上升|orange:1131:大橙金星波纹火焰上升|red:1132:大红金星波纹火焰上升|violet:1133:大紫金星波纹火焰上升|yellow:1134:大黄金星波纹火焰上升");
            Reg("fanfx2_absorb", "[通用|对敌] 泡沫聚拢星星虹吸", "通用", false, 9, "中心聚拢吸附", "black:1135:大黑泡沫聚拢星星|blue:1136:大蓝泡沫聚拢星星|green:1137:大绿泡沫聚拢星星|orange:1138:大橙泡沫聚拢星星|pink:1139:大粉泡沫聚拢星星|red:1140:大红泡沫聚拢星星|violet:1141:大紫泡沫聚拢星星|white:1142:大白泡沫聚拢星星|yellow:1143:大黄泡沫聚拢星星");
            Reg("fanfx2_claw", "[通用|对敌] 流光裂空爪斩", "通用", false, 3, "抛物线后仰", "black:1144:大黑流星或爪击|blue:1145:大蓝流星或爪击|green:1146:大绿流星或爪击|orange:1147:大橙流星或爪击|pink:1148:大粉流星或爪击|red:1149:大红流星或爪击|violet:1150:大紫流星或爪击|white:1151:大白流星或爪击|yellow:1152:大黄流星或爪击");
            Reg("fanfx2_cure", "[坚韧|自身] 波浪金星治疗", "坚韧", true, 1, "水平震退", "blue:1153:大蓝波浪金星治疗|green:1154:大绿波浪金星治疗|orange:1155:大橙波浪金星治疗|pink:1156:大粉波浪金星治疗|red:1157:大红波浪金星治疗|violet:1158:大紫波浪金星治疗|yellow:1159:大黄波浪金星治疗");
            Reg("fanfx2_earth_spikes", "[通用|对敌] 大地冰锥尖刺突起", "通用", false, 4, "四向旋转翻滚", "black:1160:大黑冰锥地刺上升|blue:1161:大蓝冰锥地刺上升|brown:1162:大棕冰锥地刺上升|green:1163:大绿冰锥地刺上升|orange:1164:大橙冰锥地刺上升|red:1165:大红冰锥地刺上升|violet:1166:大紫冰锥地刺上升|yellow:1167:大黄冰锥地刺上升");
            Reg("fanfx2_fire_spell", "[通用|对敌] 冲天烈焰火柱", "通用", false, 6, "中心炸散复位", "black:1168:大黑火焰上升消散|blue:1169:大蓝火焰上升消散|gray:1170:大灰火焰上升消散|green:1171:大绿火焰上升消散|orange:1172:大橙火焰上升消散|pink:1173:大粉火焰上升消散|red:1174:大红火焰上升消散|violet:1175:大紫火焰上升消散|white:1176:大白火焰上升消散|yellow:1177:大黄火焰上升消散");
            Reg("fanfx2_ice_spell", "[通用|对敌] 史诗冰晶聚拢爆炸", "通用", false, 9, "中心聚拢吸附", "black:1178:大黑史诗冰晶聚拢冰锥爆炸|blue:1179:大蓝史诗冰晶聚拢冰锥爆炸|gray:1180:大灰史诗冰晶聚拢冰锥爆炸|green:1181:大绿史诗冰晶聚拢冰锥爆炸|orange:1182:大橙史诗冰晶聚拢冰锥爆炸|pink:1183:大粉史诗冰晶聚拢冰锥爆炸|red:1184:大红史诗冰晶聚拢冰锥爆炸|violet:1185:大紫史诗冰晶聚拢冰锥爆炸|yellow:1186:大黄史诗冰晶聚拢冰锥爆炸");
            Reg("fanfx2_poison", "[通用|对敌] 剧毒骷髅烟雾上升", "通用", false, 8, "地震颠簸", "black:1187:大黑骷髅烟雾上升|blue:1188:大蓝骷髅烟雾上升|brown:1189:大棕骷髅烟雾上升|gray:1190:大灰骷髅烟雾上升|green:1191:大绿骷髅烟雾上升|orange:1192:大橙骷髅烟雾上升|pink:1193:大粉骷髅烟雾上升|red:1194:大红骷髅烟雾上升|violet:1195:大紫骷髅烟雾上升|yellow:1196:大黄骷髅烟雾上升");
            Reg("fanfx2_shatter", "[通用|对敌] 镜面次元碎片爆炸", "通用", false, 9, "中心聚拢吸附", "black:1197:巨黑镜子碎片爆炸|blue:1198:巨蓝镜子碎片爆炸|gray:1199:巨灰镜子碎片爆炸|green:1200:巨绿镜子碎片爆炸|orange:1201:巨橙镜子碎片爆炸|pink:1202:巨粉镜子碎片爆炸|red:1203:巨红镜子碎片爆炸|violet:1204:巨紫镜子碎片爆炸|yellow:1205:巨黄镜子碎片爆炸");
            Reg("fanfx2_wind_spell", "[通用|对敌] 狂风聚拢爆裂", "通用", false, 9, "中心聚拢吸附", "black:1206:大黑狂风聚拢爆炸|blue:1207:大蓝狂风聚拢爆炸|brown:1208:大棕狂风聚拢爆炸|green:1209:大绿狂风聚拢爆炸|orange:1210:大橙狂风聚拢爆炸|pink:1211:大粉狂风聚拢爆炸|red:1212:大红狂风聚拢爆炸|violet:1213:大紫狂风聚拢爆炸|white:1214:大白狂风聚拢爆炸|yellow:1215:大黄狂风聚拢爆炸");
            Reg("fx1_electric_zap", "[通用|对敌] 疾电火花闪击", "通用", false, 1, "水平震退", "blue:1216:大灰蓝电火花|green:1217:大绿蓝电火花|orange:1218:大橙黄电火花|red:1219:大粉橙电火花|violet:1220:大紫黄电火花|white:1221:大灰黄电火花|yellow:1222:大黄粉电火花");
            Reg("fx1_explosion", "[通用|对敌] 毁灭蘑菇云轰炸", "通用", false, 6, "中心炸散复位", "blue:1223:大蓝蘑菇云|green:1224:大绿蘑菇云|orange:1225:大橙蘑菇云|red:1226:大红蘑菇云|violet:1227:大紫蘑菇云|yellow:1228:大黄蘑菇云");
            Reg("fx1_magic_puff", "[通用|对敌] 星辉烟团爆炸星星", "通用", false, 8, "地震颠簸", "black:1229:大灰烟团爆炸星星|blue:1230:大蓝烟团爆炸星星|green:1231:大绿烟团爆炸星星|orange:1232:大橙烟团爆炸星星|red:1233:大红烟团爆炸星星|violet:1234:大紫烟团爆炸星星|white:1235:大白烟团爆炸星星|yellow:1236:大黄烟团爆炸星星");
            Reg("fx2_bubble_appear", "[坚韧|自身] 圣洁泡泡护盾显现", "坚韧", true, 1, "水平震退", "blue:1237:大蓝泡泡出现与消散|green:1238:大绿泡泡出现与消散|orange:1239:大橙泡泡出现与消散|red:1240:大红泡泡出现与消散|violet:1241:大紫泡泡出现与消散|white:1242:大白泡泡出现与消散|yellow:1243:大黄泡泡出现与消散");

            Reg("fx2_claw", "[通用|对敌] 利爪撕裂", "通用", false, 7, "手风琴压缩", "black:1251:大黑爪击|blue:1252:大蓝爪击|green:1253:大绿爪击|orange:1254:大橙爪击|red:1255:大红爪击|violet:1256:大紫爪击|white:1257:大白爪击|yellow:1258:大黄爪击");
            Reg("fx2_electric_burst", "[通用|对敌] 八芒星圣裁雷光", "通用", false, 5, "波浪状掀飞", "blue:1259:大蓝八芒星电火花|green:1260:大绿八芒星电火花|orange:1261:大橙八芒星电火花|red:1262:大红八芒星电火花|violet:1263:大紫八芒星电火花|white:1264:大白八芒星电火花|yellow:1265:大黄八芒星电火花");
            Reg("fx2_explosion", "[通用|对敌] 巨型大爆炸", "通用", false, 6, "中心炸散复位", "blue:1266:大蓝大爆炸|green:1267:大绿大爆炸|orange:1268:大橙大爆炸|red:1269:大红大爆炸|violet:1270:大紫大爆炸|yellow:1271:大黄大爆炸");

            Reg("fx2_slash", "[通用|对敌] 刀剑圆斩", "通用", false, 1, "水平震退", "black:1278:大黑圆斩|blue:1279:大蓝圆斩|green:1280:大绿圆斩|orange:1281:大橙圆斩|red:1282:大红圆斩|violet:1283:大紫圆斩|white:1284:大白圆斩|yellow:1285:大黄圆斩");
            Reg("fx3_bite", "[通用|对敌] 狂暴利齿咬合", "通用", false, 8, "地震颠簸", "blue:1286:大蓝利齿咬合|green:1287:大绿利齿咬合|orange:1288:大橙利齿咬合|red:1289:大红利齿咬合|violet:1290:大紫利齿咬合|yellow:1291:大黄利齿咬合");
            Reg("fx3_impact_hit", "[通用|对敌] 重钧圆环打击", "通用", false, 2, "垂直击飞", "blue:1292:大蓝圆环打击|green:1293:大绿圆环打击|orange:1294:大橙圆环打击|red:1295:大红圆环打击|violet:1296:大紫圆环打击|yellow:1297:大黄圆环打击");

            Reg("fx3_magic_spawn", "[通用|对敌] 秘法聚合闪光", "通用", false, 9, "中心聚拢吸附", "blue:1304:大蓝魔法聚合闪光|green:1305:大绿魔法聚合闪光|orange:1306:大橙魔法聚合闪光|red:1307:大红魔法聚合闪光|violet:1308:大紫魔法聚合闪光|yellow:1309:大黄魔法聚合闪光");
            Reg("fx3_smoke_bomb", "[通用|对敌] 暗影孢子烟雾爆炸", "通用", false, 8, "地震颠簸", "black:1310:大黑孢子烟雾爆炸|blue:1311:大蓝孢子烟雾爆炸|brown:1312:大棕孢子烟雾爆炸|green:1313:大绿孢子烟雾爆炸|orange:1314:大橙孢子烟雾爆炸|red:1315:大红孢子烟雾爆炸|violet:1316:大紫孢子烟雾爆炸|white:1317:大白孢子烟雾爆炸|yellow:1318:大黄孢子烟雾爆炸");
            Reg("fx3_splatter", "[通用|对敌] 腐蚀烟雾泡沫爆炸", "通用", false, 8, "地震颠簸", "blue:1319:大蓝烟雾泡沫爆炸|gray:1320:大灰烟雾泡沫爆炸|green:1321:大绿烟雾泡沫爆炸|orange:1322:大橙烟雾泡沫爆炸|red:1323:大红烟雾泡沫爆炸|violet:1324:大紫烟雾泡沫爆炸|yellow:1325:大黄烟雾泡沫爆炸");
            Reg("fx3_toon_explosion", "[坚韧|自身] 守护正圆气浪爆", "坚韧", true, 1, "水平震退", "blue:1326:大蓝正圆爆炸|green:1327:大绿正圆爆炸|orange:1328:大橙正圆爆炸|red:1329:大红正圆爆炸|violet:1330:大紫正圆爆炸|white:1331:大白正圆爆炸|yellow:1332:大黄正圆爆炸");
            Reg("fx3_toon_impact", "[通用|对敌] 重压气泡爆裂", "通用", false, 5, "波浪状掀飞", "blue:1333:大蓝气泡爆炸|green:1334:大绿气泡爆炸|orange:1335:大橙气泡爆炸|red:1336:大红气泡爆炸|violet:1337:大紫气泡爆炸|yellow:1338:大黄气泡爆炸");
            Reg("fx3_warp", "[通用|对敌] 虚空带电跃迁爆炸", "通用", false, 5, "波浪状掀飞", "blue:1339:大蓝带电爆炸|green:1340:大绿带电爆炸|orange:1341:大橙带电爆炸|pink:1342:大粉带电爆炸|red:1343:大红带电爆炸|violet:1344:大紫带电爆炸|yellow:1345:大黄带电爆炸");
            Reg("impfx1_dust_impact_A", "[通用|对敌] 震地气浪烟雾爆炸", "通用", false, 5, "波浪状掀飞", "blue:1346:大蓝气浪烟雾爆炸|green:1347:大绿气浪烟雾爆炸|orange:1348:大橙气浪烟雾爆炸|red:1349:大红气浪烟雾爆炸|violet:1350:大紫气浪烟雾爆炸|white:1351:大白气浪烟雾爆炸|yellow:1352:大黄气浪烟雾爆炸");
            Reg("impfx1_dust_impact_B", "[通用|对敌] 裂地分散烟雾爆炸", "通用", false, 5, "波浪状掀飞", "blue:1353:大蓝分散气浪烟雾爆炸|green:1354:大绿分散气浪烟雾爆炸|orange:1355:大橙分散气浪烟雾爆炸|red:1356:大红分散气浪烟雾爆炸|violet:1357:大紫分散气浪烟雾爆炸|white:1358:大白分散气浪烟雾爆炸|yellow:1359:大黄分散气浪烟雾爆炸");
            Reg("impfx1_quick_impact_A", "[通用|对敌] 迅捷轻微气闪", "通用", false, 1, "水平震退", "blue:1360:大蓝轻微气体闪光|green:1361:大绿轻微气体闪光|orange:1362:大橙轻微气体闪光|red:1363:大红轻微气体闪光|violet:1364:大紫轻微气体闪光|white:1365:大白轻微气体闪光|yellow:1366:大黄轻微气体闪光");
            Reg("impfx1_quick_impact_B", "[通用|对敌] 极速锐芒闪光", "通用", false, 1, "水平震退", "blue:1367:大蓝闪光|green:1368:大绿闪光|orange:1369:大橙闪光|red:1370:大红闪光|violet:1371:大紫闪光|white:1372:大白闪光|yellow:1373:大黄闪光");
            Reg("impfx1_quick_impact_C", "[通用|对敌] 寒芒冰晶闪光", "通用", false, 1, "水平震退", "blue:1374:大蓝冰晶闪光|green:1375:大绿冰晶闪光|orange:1376:大橙冰晶闪光|red:1377:大红冰晶闪光|violet:1378:大紫冰晶闪光|white:1379:大白冰晶闪光|yellow:1380:大黄冰晶闪光");
            Reg("impfx1_quick_impact_D", "[通用|对敌] 疾闪命中闪光", "通用", false, 1, "水平震退", "blue:1381:大蓝击中闪光|green:1382:大绿击中闪光|orange:1383:大橙击中闪光|red:1384:大红击中闪光|violet:1385:大紫击中闪光|white:1386:大白击中闪光|yellow:1387:大黄击中闪光");
            Reg("impfx1_toon_impact_A", "[通用|对敌] 弥散羽毛闪光", "通用", false, 2, "垂直击飞", "blue:1388:大蓝弥散羽毛闪光|green:1389:大绿弥散羽毛闪光|orange:1390:大橙弥散羽毛闪光|red:1391:大红弥散羽毛闪光|violet:1392:大紫弥散羽毛闪光|white:1393:大白弥散羽毛闪光|yellow:1394:大黄弥散羽毛闪光");
            Reg("impfx1_toon_impact_B", "[通用|对敌] 要害刺状闪光", "通用", false, 1, "水平震退", "blue:1395:大蓝刺状闪光|green:1396:大绿刺状闪光|orange:1397:大橙刺状闪光|red:1398:大红刺状闪光|violet:1399:大紫刺状闪光|white:1400:大白刺状闪光|yellow:1401:大黄刺状闪光");
            Reg("impfx1_toon_impact_C", "[通用|对敌] 圆形气浪复合闪光", "通用", false, 3, "抛物线后仰", "blue:1402:大蓝圆形气浪复合闪光|green:1403:大绿圆形气浪复合闪光|orange:1404:大橙圆形气浪复合闪光|red:1405:大红圆形气浪复合闪光|violet:1406:大紫圆形气浪复合闪光|white:1407:大白圆形气浪复合闪光|yellow:1408:大黄圆形气浪复合闪光");
            Reg("impfx1_toon_impact_D", "[通用|对敌] 波纹羽毛闪光", "通用", false, 5, "波浪状掀飞", "blue:1409:大蓝波纹羽毛闪光|green:1410:大绿波纹羽毛闪光|orange:1411:大橙波纹羽毛闪光|red:1412:大红波纹羽毛闪光|violet:1413:大紫波纹羽毛闪光|white:1414:大白波纹羽毛闪光|yellow:1415:大黄波纹羽毛闪光");
            Reg("scifx1_explosion_A", "[通用|对敌] 坍缩泡沫收束爆炸", "通用", false, 3, "抛物线后仰", "blue:1416:大蓝泡沫爆炸后收束|green:1417:大绿泡沫爆炸后收束|orange:1418:大橙泡沫爆炸后收束|red:1419:大红泡沫爆炸后收束|violet:1420:大紫泡沫爆炸后收束|yellow:1421:大黄泡沫爆炸后收束");
            Reg("scifx1_explosion_B", "[通用|对敌] 激流带电爆裂", "通用", false, 5, "波浪状掀飞", "blue:1422:大蓝溅水带电爆炸|green:1423:大绿溅水带电爆炸|orange:1424:大橙溅水带电爆炸|red:1425:大红溅水带电爆炸|violet:1426:大紫溅水带电爆炸|yellow:1427:大黄溅水带电爆炸");
            Reg("scifx1_wormhole", "[通用|对敌] 异界时空虫洞", "通用", false, 9, "中心聚拢吸附", "blue:1428:大蓝虫洞出现与消散|green:1429:大绿虫洞出现与消散|orange:1430:大橙虫洞出现与消散|red:1431:大红虫洞出现与消散|violet:1432:大紫虫洞出现与消散|yellow:1433:大黄虫洞出现与消散");
            Reg("scifx1_zap_A", "[通用|对敌] 繁复电弧爆炸", "通用", false, 4, "四向旋转翻滚", "blue:1434:大蓝繁复电弧爆炸|green:1435:大绿繁复电弧爆炸|orange:1436:大橙繁复电弧爆炸|red:1437:大红繁复电弧爆炸|violet:1438:大紫繁复电弧爆炸|yellow:1439:大黄繁复电弧爆炸");
            Reg("scifx1_zap_B", "[通用|对敌] 双色高压电弧爆", "通用", false, 8, "地震颠簸", "blue:1440:大蓝双色电弧爆炸|green:1441:大绿双色电弧爆炸|orange:1442:大橙双色电弧爆炸|red:1443:大红双色电弧爆炸|violet:1444:大紫双色电弧爆炸|yellow:1445:大黄双色电弧爆炸");
            Reg("scifx2_black_hole", "[通用|对敌] 虚空引力黑洞", "通用", false, 9, "中心聚拢吸附", "blue:1446:大蓝黑洞出现与消散|green:1447:大绿黑洞出现与消散|orange:1448:大橙黑洞出现与消散|pink:1449:大粉黑洞出现与消散|red:1450:大红黑洞出现与消散|violet:1451:大紫黑洞出现与消散|white:1452:大白黑洞出现与消散|yellow:1453:大黄黑洞出现与消散");
            Reg("scifx2_buff", "[通用|自身] 战意科技增益上升", "通用", true, 1, "水平震退", "blue:1454:大蓝科技增益上升|green:1455:大绿科技增益上升|orange:1456:大橙科技增益上升|pink:1457:大粉科技增益上升|red:1458:大红科技增益上升|violet:1459:大紫科技增益上升|yellow:1460:大黄科技增益上升");
            Reg("scifx2_debuff", "[魔力|对敌] 虚弱压制力场下降", "魔力", false, 8, "地震颠簸", "blue:1461:大蓝科技就减益下降|green:1462:大绿科技就减益下降|orange:1463:大橙科技就减益下降|pink:1464:大粉科技就减益下降|red:1465:大红科技就减益下降|violet:1466:大紫科技就减益下降|yellow:1467:大黄科技就减益下降");
            Reg("scifx2_hex_shield", "[通用|自身] 多边形坚壁护盾", "通用", true, 1, "水平震退", "black:1468:大黑科技多边形护盾|blue:1469:大蓝科技多边形护盾|gray:1470:大灰科技多边形护盾|green:1471:大绿科技多边形护盾|orange:1472:大橙科技多边形护盾|pink:1473:大粉科技多边形护盾|red:1474:大红科技多边形护盾|violet:1475:大紫科技多边形护盾|white:1476:大白科技多边形护盾|yellow:1477:大黄科技多边形护盾");

            Reg("scifx2_warp", "[通用|对敌] 次元电弧气环爆炸", "通用", false, 8, "地震颠簸", "black:1487:大黑电弧气环爆炸|blue:1488:大蓝电弧气环爆炸|green:1489:大绿电弧气环爆炸|orange:1490:大橙电弧气环爆炸|pink:1491:大粉电弧气环爆炸|red:1492:大红电弧气环爆炸|violet:1493:大紫电弧气环爆炸|white:1494:大白电弧气环爆炸|yellow:1495:大黄电弧气环爆炸");
            }
            SyncFromEffectNamesJsonIfChanged();
        }

        private static void Reg(string baseKey, string categoryCn, string userTag, bool playOnCaster, int hitReactionType, string hitReactionName, string encodedVariants)
        {
            string pureTitle = categoryCn;
            int closeBracket = categoryCn.IndexOf(']');
            if (closeBracket >= 0 && closeBracket + 1 < categoryCn.Length)
            {
                pureTitle = categoryCn.Substring(closeBracket + 1).Trim();
            }

            int effHitType = playOnCaster ? 1 : hitReactionType;
            string effHitName = playOnCaster ? "水平震退" : hitReactionName;

            FamilyEntry fam = new FamilyEntry
            {
                BaseKey = baseKey,
                PureTitleCn = pureTitle,
                UserTag = string.IsNullOrEmpty(userTag) ? "通用" : userTag,
                PlayOnCaster = playOnCaster,
                IsDisabled = !string.IsNullOrEmpty(userTag) && userTag.Contains("禁用"),
                HitReactionType = effHitType,
                HitReactionName = effHitName,
                DefaultHitReactionType = hitReactionType,
                DefaultHitReactionName = hitReactionName,
                CategoryCn = string.Format("[{0}|{1}] {2}", string.IsNullOrEmpty(userTag) ? "通用" : userTag, playOnCaster ? "自身" : "对敌", pureTitle)
            };
            string[] items = encodedVariants.Split('|');
            for (int i = 0; i < items.Length; i++)
            {
                string[] parts = items[i].Split(':');
                if (parts.Length < 3) continue;
                string col = parts[0];
                int aid = int.Parse(parts[1]);
                string cn = parts[2];
                VariantEntry ve = new VariantEntry
                {
                    AnimationId = aid,
                    Color = col,
                    CnName = cn,
                    FolderName = string.Format("{0}_large_{1}", baseKey, col)
                };
                fam.Variants[col] = ve;
                _idToVariant[aid] = ve;
                _idToFamily[aid] = fam;
            }
            _families[baseKey] = fam;
            _familyList.Add(fam);
        }

        /// <summary>
        /// 实时监听命名工具保存的 d:\123\effect_names.json：
        /// 当用户在命名软件里调整第一标签(先机/坚韧/勇气/魔力/通用/禁用)或第二标签(是否针对自身)时，立即热同步生效！
        /// </summary>
        public static void SyncFromEffectNamesJsonIfChanged()
        {
            try
            {
                string jsonPath = @"D:\123\effect_names.json";
                if (!File.Exists(jsonPath))
                {
                    string alt = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "effect_names.json");
                    if (File.Exists(alt)) jsonPath = alt;
                    else return;
                }

                DateTime writeUtc = File.GetLastWriteTimeUtc(jsonPath);
                if (writeUtc == _lastJsonWriteTimeUtc) return;
                _lastJsonWriteTimeUtc = writeUtc;

                string curFolder = "";
                string curCategory = "通用";
                bool curTargetSelf = false;
                bool hasTargetSelfField = false;

                string[] lines = File.ReadAllLines(jsonPath, Encoding.UTF8);
                for (int i = 0; i < lines.Length; i++)
                {
                    string line = lines[i].Trim();
                    if (line.StartsWith("\"folder\"", StringComparison.Ordinal))
                    {
                        curFolder = ExtractJsonStr(line);
                    }
                    else if (line.StartsWith("\"category\"", StringComparison.Ordinal))
                    {
                        curCategory = ExtractJsonStr(line);
                    }
                    else if (line.StartsWith("\"target_self\"", StringComparison.Ordinal))
                    {
                        curTargetSelf = line.IndexOf("true", StringComparison.OrdinalIgnoreCase) >= 0;
                        hasTargetSelfField = true;
                    }
                    else if (line.StartsWith("\"target_tag\"", StringComparison.Ordinal) && !hasTargetSelfField)
                    {
                        string ttag = ExtractJsonStr(line);
                        if (ttag.Contains("自身")) curTargetSelf = true;
                    }
                    else if (line == "}," || line == "}")
                    {
                        if (!string.IsNullOrEmpty(curFolder))
                        {
                            int largeIdx = curFolder.IndexOf("_large_", StringComparison.Ordinal);
                            if (largeIdx > 0)
                            {
                                string rawBase = curFolder.Substring(0, largeIdx);
                                if (rawBase == "scifx1_wormhole_appear" || rawBase == "scifx1_wormhole_disappear" || rawBase == "scifx1_wormhole_start" || rawBase == "scifx1_wormhole_stop")
                                    rawBase = "scifx1_wormhole";
                                else if (rawBase == "scifx2_black_hole_appear" || rawBase == "scifx2_black_hole_disappear")
                                    rawBase = "scifx2_black_hole";
                                else if (rawBase == "fx2_bubble_disappear")
                                    rawBase = "fx2_bubble_appear";
                                else if (rawBase == "fx2_bubble")
                                    rawBase = curFolder.EndsWith("_pop", StringComparison.Ordinal) ? "fx2_bubble_appear" : "fx2_bubble_appear";

                                FamilyEntry fam;
                                if (_families.TryGetValue(rawBase, out fam))
                                {
                                    string cleanCat = string.IsNullOrEmpty(curCategory) ? "通用" : curCategory.Trim();
                                    fam.UserTag = cleanCat;
                                    fam.IsDisabled = cleanCat.Contains("禁用");
                                    if (hasTargetSelfField)
                                    {
                                        fam.PlayOnCaster = curTargetSelf;
                                    }
                                    // 针对自身的特效：对敌人受击固定为普通击退 [1]水平震退
                                    if (fam.PlayOnCaster)
                                    {
                                        fam.HitReactionType = 1;
                                        fam.HitReactionName = "水平震退";
                                    }
                                    else
                                    {
                                        fam.HitReactionType = fam.DefaultHitReactionType > 0 ? fam.DefaultHitReactionType : 1;
                                        fam.HitReactionName = !string.IsNullOrEmpty(fam.DefaultHitReactionName) ? fam.DefaultHitReactionName : "水平震退";
                                    }
                                    fam.CategoryCn = string.Format("[{0}|{1}] {2}", fam.UserTag, fam.PlayOnCaster ? "自身" : "对敌", fam.PureTitleCn);
                                }
                            }
                        }
                        curFolder = "";
                        curCategory = "通用";
                        curTargetSelf = false;
                        hasTargetSelfField = false;
                    }
                }
            }
            catch { }
        }

        private static string ExtractJsonStr(string line)
        {
            int colon = line.IndexOf(':');
            if (colon < 0) return "";
            int q1 = line.IndexOf('"', colon + 1);
            if (q1 < 0) return "";
            int q2 = line.IndexOf('"', q1 + 1);
            if (q2 < 0) return "";
            return line.Substring(q1 + 1, q2 - q1 - 1);
        }

        /// <summary>
        /// 双标签核心准入判定：
        /// 1. 被标记为【禁用】的特效家族一律不可用；
        /// 2. 第二标签为【针对自身】(PlayOnCaster == true) 的特效，只会出现在【坚韧】流派中（其他流派严禁拿针对自身的特效去打人）；
        /// 3. 第二标签为【针对敌方】(PlayOnCaster == false) 的特效，按第一标签判定（通用=四流派皆可用，含坚韧对敌特效；否则仅对应流派可用）。
        /// </summary>
        public static bool IsFamilyAllowedForGenre(FamilyEntry fam, string genre)
        {
            if (fam == null || fam.IsDisabled) return false;

            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            string normGenre = isResilience ? "坚韧"
                : (genre.Contains("先机") || genre.Contains("精准") ? "先机"
                : (genre.Contains("魔力") || genre.Contains("机制") ? "魔力" : "勇气"));

            if (TargetsCaster(fam))
            {
                // 针对自身的特效只会出现在坚韧里
                return isResilience;
            }

            // 针对敌方的特效：看第一词条标签
            if (string.IsNullOrEmpty(fam.UserTag) || fam.UserTag == "通用")
                return true;

            return fam.UserTag.Contains(normGenre);
        }

        private static uint StableHash(string value)
        {
            unchecked { uint hash=2166136261;foreach(char c in value){hash^=c;hash*=16777619;}return hash; }
        }
        public static bool TargetsCaster(FamilyEntry family)
        {
#if UNITY_5_3_OR_NEWER
            foreach(var variant in family.Variants.Values)return EffectTimingConfig.For(variant.AnimationId).playOnCaster;
#endif
            return family.PlayOnCaster;
        }
        private static FamilyEntry FallbackAllowedFamily(string skillName, string genre, bool preferSelfOnResilience)
        {
            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            string normGenre = isResilience ? "坚韧"
                : (genre.Contains("先机") || genre.Contains("精准") ? "先机"
                : (genre.Contains("魔力") || genre.Contains("机制") ? "魔力" : "勇气"));

            List<FamilyEntry> primary = new List<FamilyEntry>();
            List<FamilyEntry> secondary = new List<FamilyEntry>();

            for (int i = 0; i < _familyList.Count; i++)
            {
                FamilyEntry f = _familyList[i];
                if (!IsFamilyAllowedForGenre(f, genre)) continue;

                if (isResilience)
                {
                    if (preferSelfOnResilience && TargetsCaster(f)) primary.Add(f);
                    else if (!preferSelfOnResilience && !TargetsCaster(f) && f.UserTag.Contains("坚韧")) primary.Add(f);
                    else secondary.Add(f);
                }
                else
                {
                    if (!string.IsNullOrEmpty(f.UserTag) && f.UserTag.Contains(normGenre)) primary.Add(f);
                    else secondary.Add(f);
                }
            }

            List<FamilyEntry> pool = primary.Count > 0 ? primary : secondary;
            if (pool.Count == 0) throw new InvalidOperationException("No allowed effect family for " + genre);

            uint hash = StableHash(skillName ?? "斩");
            return pool[(int)(hash % (uint)pool.Count)];
        }

        public static IReadOnlyList<FamilyEntry> AllFamilies
        {
            get { EnsureInitialized(); return _familyList.AsReadOnly(); }
        }

        public static bool TryGetById(int animationId, out VariantEntry variant, out FamilyEntry family)
        {
            EnsureInitialized();
            family = null;
            if (_idToVariant.TryGetValue(animationId, out variant))
            {
                _idToFamily.TryGetValue(animationId, out family);
                return true;
            }
            return false;
        }

        public static void ResolveSkillEffect(
            string skillName,
            string genre,
            int tier,
            string subEffectName,
            out int animationId,
            out string effectCnName,
            out string effectFolder,
            out string effectCategory)
        {
            int hitReactionType;
            string hitReactionName;
            ResolveSkillEffect(
                skillName,
                genre,
                tier,
                subEffectName,
                out animationId,
                out effectCnName,
                out effectFolder,
                out effectCategory,
                out hitReactionType,
                out hitReactionName);
        }

        public static void ResolveSkillEffect(
            string skillName,
            string genre,
            int tier,
            string subEffectName,
            out int animationId,
            out string effectCnName,
            out string effectFolder,
            out string effectCategory,
            out int hitReactionType,
            out string hitReactionName)
        {
            EnsureInitialized();
            if (string.IsNullOrEmpty(skillName)) skillName = "斩天剑";
            if (string.IsNullOrEmpty(genre)) genre = "勇气";
            if (string.IsNullOrEmpty(subEffectName)) subEffectName = "";

            string headPart;
            string midPart;
            if (skillName.Length == 3)
            {
                headPart = skillName.Substring(0, 1);
                midPart = skillName.Substring(1, 1);
            }
            else if (skillName.Length >= 6)
            {
                headPart = skillName.Substring(0, 2);
                midPart = skillName.Substring(2, 2);
            }
            else
            {
                headPart = skillName.Substring(0, Math.Min(2, skillName.Length));
                midPart = "";
            }
            string prefixPart = headPart + midPart;
            string tail2 = skillName.Length >= 2 ? skillName.Substring(skillName.Length - 2) : skillName;
            string tail1 = skillName.Length >= 1 ? skillName.Substring(skillName.Length - 1) : skillName;

            string elementTag;
            string targetColor = ResolveNameColor(headPart,midPart,skillName,genre,tier,subEffectName,out elementTag);
            string baseKey = ResolveBaseFamily(skillName, prefixPart, tail2, tail1, genre, tier, elementTag, subEffectName);

            FamilyEntry fam=ChooseCompatibleFamily(skillName,genre,tier,baseKey,targetColor);
            if (fam==null)
            {
                bool preferSelf = (fam != null && TargetsCaster(fam)) || MatchesTail(tail2, tail1, "壁垒", "屏障", "坚壁", "圣盾", "铁壁", "坚甲", "盾御", "圣铠", "格挡", "之盾", "之铠", "盾", "庇护", "护佑", "结界", "护持", "守卫", "护界", "圣障", "纯净", "恩赐", "愈合", "救赎", "慈悲", "慰藉", "甘霖", "圣泉", "圣雨", "洗礼", "祝福", "奉献", "圣威", "圣誓", "之冠", "祷言", "之心", "之歌", "心", "圣震", "圣辉", "灵气", "复苏", "唤醒", "战意", "鼓舞", "觉醒", "增幅");
                fam = FallbackAllowedFamily(skillName, genre, preferSelf);
            }

            VariantEntry chosen = PickColorVariant(fam, targetColor);
            animationId = chosen.AnimationId;
            effectCnName = chosen.CnName;
            effectFolder = chosen.FolderName;
            effectCategory = string.Format("[{0}|{1}] {2}",fam.UserTag,TargetsCaster(fam)?"自身":"对敌",fam.PureTitleCn);
            // 针对自身的特效：对敌人受击固定为普通击退 [1]水平震退
            hitReactionType = TargetsCaster(fam) ? 1 : fam.HitReactionType;
            hitReactionName = TargetsCaster(fam) ? "水平震退" : fam.HitReactionName;
        }

        private static bool IsApexName(string name)
        {
            return name.Length>=6&&ContainsAny(name.Substring(2,2),"斩击","连刺","穿心","崩山","洗礼","侵蚀","乱舞","闪击","坠击","吞噬","强劈","贯穿","爆射","震裂","狂斩","破阵","突袭","轰鸣","撕裂","碾压","旋刃","裂地","突刺","飞星","绝杀","破霸","疾射","逆击","破空","碎骨");
        }
        private static FamilyEntry ChooseCompatibleFamily(string name,string genre,int tier,string baseKey,string color)
        {
            string[] keys=new[]{baseKey};
            switch(baseKey)
            {
                case "expfx1_epic_explosion_B": case "fx2_explosion": case "fx1_explosion":
                    keys=new[]{"expfx1_epic_explosion_B","fx2_explosion","fx1_explosion","expfx1_stylized_explosion_C"};break;
                case "expfx1_stylized_explosion_A": case "expfx1_symmetrical_explosion_A": case "expfx1_symmetrical_explosion_B": case "expfx1_symmetrical_explosion_D":
                    keys=new[]{"expfx1_stylized_explosion_A","expfx1_symmetrical_explosion_A","expfx1_symmetrical_explosion_B","expfx1_symmetrical_explosion_D"};break;
                case "fanfx1_magic_burst_A": case "fanfx1_magic_burst_B": case "fx3_magic_spawn":
                    keys=new[]{"fanfx1_magic_burst_A","fanfx1_magic_burst_B","fx3_magic_spawn"};break;
                case "fanfx1_magic_puff_A": case "fx1_magic_puff": case "fx3_smoke_bomb":
                    keys=new[]{"fanfx1_magic_puff_A","fx1_magic_puff","fx3_smoke_bomb"};break;
                case "scifx1_zap_A": case "scifx1_zap_B": case "fx1_electric_zap":
                    keys=new[]{"scifx1_zap_A","scifx1_zap_B","fx1_electric_zap"};break;
                case "impfx1_quick_impact_A": case "impfx1_quick_impact_B": case "impfx1_quick_impact_C": case "impfx1_quick_impact_D": case "impfx1_toon_impact_B":
                    keys=new[]{"impfx1_quick_impact_A","impfx1_quick_impact_B","impfx1_quick_impact_C","impfx1_quick_impact_D","impfx1_toon_impact_B"};break;
                case "fx3_impact_hit": case "impfx1_toon_impact_C": case "fx3_toon_impact":
                    keys=new[]{"fx3_impact_hit","impfx1_toon_impact_C","fx3_toon_impact"};break;
                case "impfx1_dust_impact_A": case "impfx1_dust_impact_B":
                    keys=new[]{"impfx1_dust_impact_A","impfx1_dust_impact_B"};break;
                case "fanfx2_poison":
                    keys=new[]{"fanfx2_poison","fx3_splatter"};break;
                case "fanfx1_spellcast_C":
                    keys=new[]{"fanfx1_spellcast_C","fanfx1_spellcast_A","fanfx1_skull_puff"};break;
                case "scifx2_debuff":
                    keys=new[]{"scifx2_debuff","fx3_toon_impact"};break;
                case "fanfx1_magic_puff_B":
                    if(MatchesTail(name.Substring(Math.Max(0,name.Length-2)),name.Substring(name.Length-1),"圣罚","圣击","灵光","回响","圣辉","耀光","圣震"))
                        keys=new[]{"fanfx1_magic_puff_B","fanfx1_magic_burst_A","fx2_electric_burst"};
                    break;
                case "fanfx1_spellcast_D":
                    keys=new[]{"fanfx1_spellcast_D","scifx2_buff"};break;
                case "fanfx2_absorb": case "scifx1_explosion_A": case "expfx1_symmetrical_explosion_C":
                    keys=new[]{"fanfx2_absorb","scifx1_explosion_A","expfx1_symmetrical_explosion_C"};break;
            }
            var allowed=new List<FamilyEntry>();var exact=new List<FamilyEntry>();
            FamilyEntry anchor;bool sameTarget=_families.TryGetValue(baseKey,out anchor)&&IsFamilyAllowedForGenre(anchor,genre);
            bool caster=sameTarget&&TargetsCaster(anchor);
            foreach(string key in keys)
            {
                FamilyEntry candidate;if(!_families.TryGetValue(key,out candidate)||!IsFamilyAllowedForGenre(candidate,genre))continue;
                if(sameTarget&&TargetsCaster(candidate)!=caster)continue;
                allowed.Add(candidate);if(candidate.Variants.ContainsKey(color))exact.Add(candidate);
            }
            var pool=exact.Count>0?exact:allowed;
            if(pool.Count==0)return null;
            return pool[(int)(StableHash(name+"|"+genre+"|"+tier+"|family")%(uint)pool.Count)];
        }
        private static string ResolveNameColor(string head,string middle,string name,string genre,int tier,string subEffect,out string element)
        {
            string context=head+middle;
            if(ContainsAny(context,"钢铁","坚钢","铁壁","坚甲","断钢","斩铁","金属","磐石","劫灰")){element="metal";return "gray";}
            if(ContainsAny(context,"大地","尘世","碎石","巨石","崩岩","沙","泥","尘")){element="earth";return "brown";}
            string color=ResolveColorAndElement(head,head,"",tier,subEffect,out element);
            if(string.IsNullOrEmpty(color))
            {
                string midElement;color=ResolveColorAndElement(middle,middle,"",tier,subEffect,out midElement);
                if(element=="none")element=midElement;
            }
            if(tier>=5&&ContainsAny(middle,"因果","万物","轮回","诸界","幻梦","命运","混沌")&&element!="fire"&&element!="ice"&&element!="lightning")
            {element="arcane";return "rainbow";}
            if(string.IsNullOrEmpty(color))color=ResolveColorAndElement("",name,"",tier,subEffect,out element);
            return string.IsNullOrEmpty(color)?GetGenreDefaultColor(genre):color;
        }

        private static string ResolveColorAndElement(
            string prefixPart,
            string fullName,
            string genre,
            int tier,
            string subEffectName,
            out string elementTag)
        {
            elementTag = "none";

            if (ContainsAny(prefixPart, "寒冰", "冰霜", "极寒", "冻结", "寒芒", "冰", "霜") || ContainsAny(fullName, "冰原"))
            {
                elementTag = "ice";
                if (ContainsAny(prefixPart, "极寒", "寒芒")) return "white";
                return "blue";
            }
            if (ContainsAny(prefixPart, "闪电", "雷霆", "苍雷", "迅雷", "天谴", "雷") || ContainsAny(fullName, "狂雷", "天劫", "轰顶"))
            {
                elementTag = "lightning";
                if (ContainsAny(prefixPart, "苍雷", "迅雷")) return "blue";
                return "yellow";
            }
            if (ContainsAny(prefixPart, "烈焰", "炽热", "焦热", "怒火", "龙炎", "灼热", "炽煌", "冥炎", "黑炎", "焚", "炽", "炎") || ContainsAny(fullName, "火海", "怒炎", "之火", "圣焰", "冥火"))
            {
                elementTag = "fire";
                if (ContainsAny(prefixPart, "黑炎", "冥炎") || ContainsAny(fullName, "冥火")) return "violet";
                if (ContainsAny(prefixPart, "熔岩", "焦热", "炽煌")) return "orange";
                return "red";
            }
            if (ContainsAny(prefixPart, "剧毒", "巫毒", "腐化", "腐蚀", "凋零", "毒", "蛇", "蛛", "蟒", "蜂") || subEffectName.Contains("中毒"))
            {
                elementTag = "poison";
                if (ContainsAny(prefixPart, "巫毒", "腐化", "凋零")) return "violet";
                return "green";
            }
            if (ContainsAny(prefixPart, "浴血", "嗜血", "猩红", "血") || subEffectName.Contains("流血"))
            {
                elementTag = "blood";
                return "red";
            }
            if (ContainsAny(prefixPart, "狂风", "暴风", "旋风", "疾风", "追风", "穿林", "飞燕", "风", "雀", "鹏") || ContainsAny(fullName, "风暴", "裂风"))
            {
                elementTag = "wind";
                if (ContainsAny(prefixPart, "暴风", "苍穹", "天空", "追风", "飞燕")) return "blue";
                return "green";
            }
            if (ContainsAny(prefixPart, "流水", "骤雨", "怒涛", "圣泉", "甘霖", "狂澜", "潮", "鲲", "蛟") || ContainsAny(fullName, "怒涛", "狂潮", "激流", "奔流"))
            {
                elementTag = "water";
                return "blue";
            }
            if (ContainsAny(prefixPart, "裂地", "碎石", "熔岩", "巨石", "崩岩", "崩山", "磐石", "大地", "天崩", "地"))
            {
                elementTag = "earth";
                if (ContainsAny(prefixPart, "熔岩")) return "red";
                return "orange";
            }

            if (tier >= 5 && ContainsAny(prefixPart, "极光", "幻梦", "因果", "轮回", "诸界", "万物", "时空", "次元", "元素", "重塑"))
            {
                elementTag = "arcane";
                return "rainbow";
            }
            if (ContainsAny(prefixPart, "极光", "幻梦", "蝶", "狐", "妖术", "妖"))
            {
                elementTag = "arcane";
                return "pink";
            }
            if (ContainsAny(prefixPart, "漆黑", "黑夜", "永夜", "死线", "刺杀", "暗杀", "锁喉", "抹喉", "夺命", "致命", "绝命", "孤影", "盲区", "潜行", "偷袭", "影缝", "碎颅", "冥府", "绝望", "劫灰", "幽域", "黑", "暗", "死"))
            {
                elementTag = "dark";
                return "black";
            }
            if (ContainsAny(prefixPart, "暗影", "混沌", "幻象", "奥术", "以太", "虚空", "深渊", "秘法", "灵能", "蚀魂", "湮灭", "禁断", "幽冥", "灾祸", "虹吸", "魔力", "邪能", "咒术", "烙印", "星界", "蚀刻", "魂能", "秘术", "恶魔", "痛苦", "灾厄", "幽暗", "冥界", "裂隙", "维度", "诡术", "死灵", "禁忌", "异界", "聚能", "崩解", "解离", "虚弱", "咒缚", "噬魂", "鬼神", "逆鳞", "瞬影", "影袭", "幻影", "匿踪", "绝影", "影遁", "潜雾", "迷踪", "邪", "魔", "鬼", "冥", "幻", "幽", "魂", "虚", "渊", "劫", "狱", "魄", "梦", "蝠", "枭", "扭曲", "支配"))
            {
                elementTag = "dark";
                return "violet";
            }
            if (ContainsAny(prefixPart, "净白", "纯洁", "纯白", "圣洁", "洗礼", "赎罪", "庇护", "守护", "固守", "不屈", "专注", "护持", "坚毅", "坚韧", "守望", "断钢", "斩铁", "破甲", "穿甲", "无影", "实体", "锐利", "锋锐", "白", "真", "灵", "道", "净化", "驱散"))
            {
                elementTag = "holy";
                return "white";
            }
            if (ContainsAny(prefixPart, "圣光", "圣堂", "神圣", "圣佑", "祈愿", "戒律", "祝福", "圣盾", "奉献", "恩赐", "光辉", "晨曦", "神恩", "圣殿", "圣灵", "圣域", "圣裁", "圣印", "崇高", "誓约", "虔信", "剑圣", "无双", "破晓", "鹰眼", "锐眼", "定点", "要害", "黎明", "极昼", "金刚", "究极", "圣", "神", "皇", "帝", "耀", "星", "麟", "凤", "雕", "鹰", "审判", "裁决", "救赎"))
            {
                elementTag = "holy";
                return "yellow";
            }
            if (ContainsAny(prefixPart, "回春", "抚慰", "活血", "治愈", "慈悲", "猎犬", "灵巧", "伺机", "敏锐", "唤醒"))
            {
                elementTag = "holy";
                return "green";
            }
            if (ContainsAny(prefixPart, "修罗", "罗刹", "死狂", "屠龙", "狂暴", "狂怒", "狂乱", "暴烈", "残暴", "凶暴", "毁灭", "极灭", "灭界", "灭世", "处决", "决斗", "强袭", "天灾", "献祭", "狂", "怒", "暴", "凶", "煞", "灭", "弑", "诛"))
            {
                elementTag = "fire";
                return "red";
            }
            if (ContainsAny(prefixPart, "霸王", "霸道", "巨力", "战意", "破军", "破城", "斗神", "战鬼", "刚勇", "豪胆", "狮心", "铁拳", "战吼", "开天", "刚猛", "刚刃", "强击", "坚钢", "铁壁", "坚牢", "坚壁", "震荡", "震天", "霸", "虎", "狮", "熊", "猿", "象", "獒"))
            {
                elementTag = "earth";
                return "orange";
            }
            if (ContainsAny(prefixPart, "苍穹", "星辰", "天空", "深空", "裂天", "旋天", "飞跃", "回旋", "穿刺", "迅捷", "连环", "破空", "贯穿", "贯通", "居合", "极速", "燕返", "绝速", "疾刃", "疾驰", "疾步", "超流", "极限", "天", "空", "月", "苍", "狼"))
            {
                return "blue";
            }

            return "";
        }

        private static string GetGenreDefaultColor(string genre)
        {
            if (genre.Contains("勇气") || genre.Contains("暴击")) return "red";
            if (genre.Contains("先机") || genre.Contains("精准")) return "blue";
            if (genre.Contains("坚韧") || genre.Contains("恢复")) return "green";
            if (genre.Contains("魔力") || genre.Contains("机制")) return "violet";
            return "blue";
        }

        private static string ResolveBaseFamily(
            string fullName,
            string prefixPart,
            string tail2,
            string tail1,
            string genre,
            int tier,
            string elementTag,
            string subEffectName)
        {
            bool isResilience = genre.Contains("坚韧") || genre.Contains("恢复");
            if(IsApexName(fullName))
            {
                string action=fullName.Substring(2,2);
                if(tail2=="风暴"||tail2=="旋涡"||tail2=="乱流")return ContainsAny(action,"斩","旋","乱舞")?"expfx1_stylized_explosion_B":"fanfx2_wind_spell";
                if(tail2=="陨星")return "expfx1_epic_explosion_A";
                if(tail2=="骤雨")return ContainsAny(action,"刺","射","贯穿")?"impfx1_toon_impact_A":"scifx1_explosion_B";
                if(tail2=="火海"||tail2=="怒炎")return "fanfx2_fire_spell";
                if(tail2=="冰原")return "fanfx2_ice_spell";
                if(tail2=="天劫"||tail2=="狂雷"||tail2=="轰顶")return "scifx1_zap_A";
                if(tail2=="射线"||tail2=="辉光")return isResilience&&action=="洗礼"?"fanfx2_cure":"fx2_electric_burst";
                if(tail2=="狂潮"||tail2=="怒涛"||tail2=="狂澜")return "scifx1_explosion_B";
                if(tail2=="裂变"||tail2=="极境"||tail2=="领域")return isResilience&&tail2=="领域"?"scifx2_buff":"scifx2_warp";
                if(tail2=="结界")return isResilience?"fx2_bubble_appear":"fanfx1_spellcast_A";
                if(tail2=="暗涌")return "scifx2_debuff";
                if(tail2=="爆轰"||tail2=="绝杀"||tail2=="崩灭"||tail2=="浩劫")return "expfx1_epic_explosion_B";
                if(tail2=="暴乱"||tail2=="狂宴"||tail2=="狂啸")return "expfx1_symmetrical_explosion_B";
                if(tail2=="冲击"||tail2=="震荡")return "impfx1_dust_impact_A";
            }

            // ── 1. 用户显式定性【坚韧】护盾 / 治疗 / 祈愿 / 圣堂光柱类 (仅限坚韧流派进入针对自身及护盾反震池) ──
            if (isResilience)
            {
                if(MatchesTail(tail2,tail1,"圣罚","圣击","灵光","回响","圣辉","耀光","圣震"))return "fanfx1_magic_puff_B";
                if (MatchesTail(tail2, tail1, "壁垒", "屏障", "坚壁", "圣盾", "铁壁", "坚甲", "盾御", "圣铠", "格挡", "之盾", "之铠", "盾"))
                    return "scifx2_hex_shield";
                if (MatchesTail(tail2, tail1, "庇护", "护佑", "结界", "护持", "守卫", "护界", "圣障", "纯净", "恩赐"))
                    return "fx2_bubble_appear";
                if (MatchesTail(tail2, tail1, "反震", "赎罪", "净除", "圣环"))
                    return "fx2_bubble_appear";
                if (MatchesTail(tail2, tail1, "固守", "磐石", "圣佑", "坚守"))
                    return "fx3_toon_explosion";
                if (MatchesTail(tail2, tail1, "愈合", "救赎", "慈悲", "慰藉", "甘霖", "圣泉", "圣雨", "洗礼"))
                    return "fanfx2_cure";
                if (MatchesTail(tail2, tail1, "祝福", "奉献", "圣威", "圣誓", "之冠"))
                    return "fanfx1_spellcast_D";
                if (MatchesTail(tail2, tail1, "祷言", "之心", "之歌", "心"))
                    return "fanfx1_spellcast_B";
                if (MatchesTail(tail2, tail1, "圣震", "圣辉"))
                    return "fanfx2_cure";
                if (MatchesTail(tail2, tail1, "灵气", "复苏", "唤醒"))
                    return "fanfx1_magic_puff_B";
                if (MatchesTail(tail2, tail1, "战意", "鼓舞", "觉醒", "增幅"))
                    return "scifx2_buff";
            }

            // ── 2. 近战刀剑 / 流光裂空爪斩 / 撕咬类 (无向右弹道，全部采用中心爆发斩击) ──
            if (MatchesTail(tail2, tail1, "之剑", "之刃", "之镰", "连斩", "重斩", "狂斩", "怒斩", "斩铁", "轮斩", "旋劈", "旋刃", "拔刀", "挥砍", "剑", "斩", "刃", "镰", "扇") || fullName.Contains("斩击"))
                return "fx2_slash";
            if (MatchesTail(tail2, tail1, "斩杀", "乱劈", "猛劈", "挑斩", "逆斩", "割裂", "裂劈", "劈裂", "截断", "之翼", "飞燕", "鹰击", "掠杀", "甩尾", "翼"))
                return "fanfx2_claw";
            if (MatchesTail(tail2, tail1, "之爪", "狂袭", "奇袭", "突袭", "疾掠", "撕裂", "穿心", "爪"))
                return "fx2_claw";
            if (MatchesTail(tail2, tail1, "索命", "封喉", "绞杀", "枭首", "牙", "角"))
                return "fx3_bite";

            // ── 3. 先机刺击 / 寒芒穿透 / 极速闪光类 (替代已禁用的手里剑/苦无/冰锥向右弹道) ──
            if (MatchesTail(tail2, tail1, "之枪", "之矛", "破绽", "要害", "挑刺", "破甲", "刺杀", "暗杀", "抹杀", "追命", "穿刺", "枪", "矛", "刺"))
                return "impfx1_toon_impact_B";
            if (MatchesTail(tail2, tail1, "之箭", "之弓", "飞刀", "突刺", "疾刺", "射击", "狙杀", "直击", "绝突", "瞬斩", "疾斩", "爆射", "弓", "矢"))
                return "impfx1_quick_impact_B";
            if (MatchesTail(tail2, tail1, "之戟", "贯穿", "穿透", "穿甲", "绝刺", "闪刺", "连刺", "疾射", "戟") || fullName.Contains("连刺") || fullName.Contains("贯穿"))
                return "impfx1_quick_impact_C";
            if (MatchesTail(tail2, tail1, "飞刃", "旋刺", "之轮", "连弩", "乱射", "骤雨", "轮"))
                return "impfx1_toon_impact_A";
            if (MatchesTail(tail2, tail1, "闪避", "残影", "影步", "疾闪", "瞬步", "影突", "影刃"))
                return "impfx1_quick_impact_D";
            if (MatchesTail(tail2, tail1, "潜行", "匿踪", "孤影", "盲区", "偷袭"))
                return "impfx1_quick_impact_A";
            if (MatchesTail(tail2, tail1, "破势", "破霸", "逆击", "截击"))
                return "impfx1_toon_impact_D";

            // ── 4. 勇气重锤 / 圆环重击 / 震地气浪类 (替代已禁用的横向重击/向下冲击/接地冲击波向右) ──
            if (MatchesTail(tail2, tail1, "之锤", "崩击", "碎击", "碎骨", "裂颅", "霸击", "强劈", "碎心", "裂魄", "锤", "斧"))
                return "fx3_impact_hit";
            if (MatchesTail(tail2, tail1, "踏击", "踏破", "坠击", "轰落", "震击", "强袭", "突霸", "破阵", "激突", "龙击") || fullName.Contains("坠击"))
                return "impfx1_dust_impact_A";
            if (MatchesTail(tail2, tail1, "扫荡", "突进", "飞踢", "挑击", "冲击", "激荡", "震荡"))
                return "impfx1_dust_impact_B";
            if (MatchesTail(tail2, tail1, "扫击", "猛攻", "撞击", "掌击", "肘击", "狂打", "狂攻", "连击", "闪击", "锐击", "音速", "伏击", "拳", "击"))
                return "impfx1_toon_impact_C";
            if (MatchesTail(tail2, tail1, "碾压", "碾碎", "碎压", "强压", "压杀", "塌陷", "镇压"))
                return "fx3_toon_impact";

            // ── 5. 大地尖刺 / 镜面破碎 / 冲天爆破类 ──
            if (MatchesTail(tail2, tail1, "裂地", "崩山", "断岳", "碎岳", "震裂", "崩裂"))
                return "fanfx2_earth_spikes";
            if (MatchesTail(tail2, tail1, "之镜", "碎裂", "裂空", "破空", "裂隙", "镜"))
                return "fanfx2_shatter";
            if (MatchesTail(tail2, tail1, "陨星", "飞星", "投掷"))
                return "expfx1_epic_explosion_A";

            // ── 6. 用户显式定性【魔力】诅咒波纹 / 禁锢封印 / 虚空黑洞(出现+消散) / 异界虫洞(出现+消散) / 剧毒死灵 / 奥术星辰类 ──
            if (MatchesTail(tail2, tail1, "烙印", "诅咒", "灾厄", "天罚"))
                return "fanfx1_spellcast_C";
            if (MatchesTail(tail2, tail1, "封印", "锁魂", "枷锁", "咒缚", "缠绕", "之印", "之锁", "之牢", "之符", "之誓", "之歌", "结界", "圣印", "链", "环", "阵", "印"))
                return "fanfx1_spellcast_A";
            if (MatchesTail(tail2, tail1, "虚弱", "暗涌", "压制", "沉沦"))
                return "scifx2_debuff";
            if (MatchesTail(tail2, tail1, "引力", "湮灭"))
                return "scifx2_black_hole";
            if (MatchesTail(tail2, tail1, "之门", "逆流", "折跃"))
                return "scifx1_wormhole";
            if (MatchesTail(tail2, tail1, "虹吸", "吞噬"))
                return "fanfx2_absorb";
            if (MatchesTail(tail2, tail1, "坍缩", "收束", "崩解"))
                return "scifx1_explosion_A";
            if (MatchesTail(tail2, tail1, "毒爆", "腐蚀", "侵蚀", "凋零"))
                return "fanfx2_poison";
            if (MatchesTail(tail2, tail1, "之雾", "潜雾", "迷雾", "烟幕"))
                return "fx3_smoke_bomb";
            if (MatchesTail(tail2, tail1, "反噬", "骨"))
                return "fanfx1_skull_puff";
            if (MatchesTail(tail2, tail1, "之眼", "凝视", "眼", "瞳"))
                return "fx3_magic_spawn";
            if (MatchesTail(tail2, tail1, "之核", "圣核", "之心", "珠", "心"))
                return "expfx1_symmetrical_explosion_C";
            if (MatchesTail(tail2, tail1, "圣击", "灵光", "回响", "杖", "魄"))
                return "fanfx1_magic_burst_A";
            if (MatchesTail(tail2, tail1, "之权", "之冠", "星辰", "诸界"))
                return "fanfx1_magic_burst_B";
            if (MatchesTail(tail2, tail1, "极境", "次元"))
                return "scifx2_warp";
            if (MatchesTail(tail2, tail1, "领域"))
                return isResilience ? "scifx2_buff" : "scifx2_warp";

            // ── 7. 寒冰 / 雷电 / 狂风 / 激流 / 烈焰元素爆发类 (禁用所有循环球体/循环落雷) ──
            if (MatchesTail(tail2, tail1, "冰原"))
                return "fanfx2_ice_spell";
            if (MatchesTail(tail2, tail1, "狂雷", "天劫", "轰顶"))
                return "scifx1_zap_A";
            if (MatchesTail(tail2, tail1, "轰鸣", "脉冲"))
                return "scifx1_zap_A";
            if (MatchesTail(tail2, tail1, "圣裁", "之裁", "耀光", "辉光", "射线", "贯日", "之光"))
                return "fx2_electric_burst";
            if (MatchesTail(tail2, tail1, "极光", "穿魂"))
                return "fx1_electric_zap";
            if (MatchesTail(tail2, tail1, "风暴", "裂风", "乱流", "之息"))
                return "fanfx2_wind_spell";
            if (MatchesTail(tail2, tail1, "旋风", "乱舞", "翻腾", "旋涡", "漩涡"))
                return "expfx1_stylized_explosion_B";
            if (MatchesTail(tail2, tail1, "激流", "奔流", "狂潮", "怒涛", "狂澜", "圣潮"))
                return "scifx1_explosion_B";
            if (MatchesTail(tail2, tail1, "之火", "圣焰", "灼烧", "冥火", "怒炎", "弹射", "炮"))
                return "fanfx2_fire_spell";
            if (MatchesTail(tail2, tail1, "焚尽", "献祭", "火海", "狂宴", "怒啸", "狂啸", "暴乱"))
                return "expfx1_symmetrical_explosion_B";

            // ── 8. 前缀元素亲和驱动 (ElementTag) ──
            if (elementTag == "ice")
                return "fanfx2_ice_spell";
            if (elementTag == "lightning")
                return tier >= 4 ? "scifx1_zap_A" : "scifx1_zap_B";
            if (elementTag == "wind")
                return tier >= 4 ? "fanfx2_wind_spell" : "expfx1_stylized_explosion_B";
            if (elementTag == "water")
                return (genre.Contains("坚韧") || genre.Contains("恢复")) ? "fanfx2_cure" : "scifx1_explosion_B";
            if (elementTag == "blood")
                return "fx3_splatter";
            if (elementTag == "poison")
                return "fanfx2_poison";

            // ── 9. 细分高能爆炸后缀 ──
            if (MatchesTail(tail2, tail1, "灭杀", "碎灭", "聚爆", "崩灭", "终结", "处刑", "绝杀"))
                return "expfx1_epic_explosion_B";
            if (MatchesTail(tail2, tail1, "灾变", "浩劫", "狂涌"))
                return "expfx1_stylized_explosion_C";
            if (MatchesTail(tail2, tail1, "裂变"))
                return "fx3_warp";
            if (MatchesTail(tail2, tail1, "爆轰", "暴轰", "爆裂", "震爆", "爆碎", "轰击"))
                return "fx2_explosion";
            if (MatchesTail(tail2, tail1, "爆破", "爆散", "破裂", "击碎", "飞弹"))
                return "fx1_explosion";
            if (MatchesTail(tail2, tail1, "迸发", "溃散", "爆鸣", "圣爆"))
                return "expfx1_stylized_explosion_A";
            if (MatchesTail(tail2, tail1, "溃灭", "裂解"))
                return "expfx1_symmetrical_explosion_D";

            // ── 10. 附加机制与四大流派定性标签兜底 ──
            if (subEffectName.Contains("中毒")) return "fanfx2_poison";
            if (subEffectName.Contains("流血")) return "fx3_splatter";
            if (subEffectName.Contains("封印")) return "fanfx1_spellcast_A";
            if (subEffectName.Contains("吸收")) return "fanfx2_absorb";

            if (genre.Contains("坚韧") || genre.Contains("恢复"))
                return "fanfx2_cure";
            if (genre.Contains("先机") || genre.Contains("精准"))
                return tier >= 5 ? "fanfx2_claw" : "impfx1_toon_impact_B";
            if (genre.Contains("魔力") || genre.Contains("机制"))
                return tier >= 5 ? "fanfx1_magic_burst_B" : "fanfx1_spellcast_C";
            return tier >= 5 ? "expfx1_epic_explosion_B" : "fx2_slash";
        }

        private static VariantEntry PickColorVariant(FamilyEntry fam, string targetColor)
        {
            VariantEntry ve;
            if (fam.Variants.TryGetValue(targetColor, out ve)) return ve;

            // 多级平滑颜色降级链
            string[] fallbacks = GetColorFallbackChain(targetColor);
            for (int i = 0; i < fallbacks.Length; i++)
            {
                if (fam.Variants.TryGetValue(fallbacks[i], out ve)) return ve;
            }

            // 任意可用变体兜底
            foreach (var kv in fam.Variants)
            {
                return kv.Value;
            }
            return null;
        }

        private static string[] GetColorFallbackChain(string color)
        {
            switch (color)
            {
                case "black": return new string[] { "black", "violet", "gray", "dark_brown", "red", "blue" };
                case "white": return new string[] { "white", "yellow", "light_blue", "blue", "gray" };
                case "pink": return new string[] { "pink", "violet", "red", "yellow" };
                case "rainbow": return new string[] { "rainbow", "pink", "violet", "yellow", "blue" };
                case "gray": return new string[] { "gray", "white", "blue", "black" };
                case "brown": return new string[] { "brown", "orange", "red", "yellow" };
                case "orange": return new string[] { "orange", "red", "yellow", "brown", "dark_brown" };
                case "red": return new string[] { "red", "orange", "violet", "yellow", "blue" };
                case "yellow": return new string[] { "yellow", "orange", "white", "light_brown", "blue" };
                case "green": return new string[] { "green", "blue", "yellow", "white" };
                case "violet": return new string[] { "violet", "blue", "red", "black" };
                case "blue":
                default: return new string[] { "blue", "dark_blue", "light_blue", "white", "violet" };
            }
        }

        private static bool ContainsAny(string text, params string[] keywords)
        {
            if (string.IsNullOrEmpty(text)) return false;
            for (int i = 0; i < keywords.Length; i++)
            {
                if (text.Contains(keywords[i])) return true;
            }
            return false;
        }

        private static bool MatchesTail(string tail2, string tail1, params string[] suffixes)
        {
            for (int i = 0; i < suffixes.Length; i++)
            {
                string s = suffixes[i];
                if (s.Length == 2 && tail2 == s) return true;
                if (s.Length == 1 && tail1 == s) return true;
            }
            return false;
        }
    }
}
