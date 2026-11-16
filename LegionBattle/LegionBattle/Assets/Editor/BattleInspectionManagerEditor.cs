#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using LegionBattle.Battle;

namespace LegionBattle.EditorTools
{
    [CustomEditor(typeof(BattleInspectionManager))]
    public class BattleInspectionManagerEditor : Editor
    {
        public override void OnInspectorGUI()
        {
            DrawDefaultInspector();

            BattleInspectionManager manager = (BattleInspectionManager)target;

            EditorGUILayout.Space(12);
            EditorGUILayout.LabelField("阵列点位与间距控制", EditorStyles.boldLabel);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("实时刷新点位", GUILayout.Height(30)))
            {
                Undo.RecordObject(manager, "Apply Formation Layout");
                manager.ApplyFormationLayout();
                EditorUtility.SetDirty(manager);
                SceneView.RepaintAll();
            }
            if (GUILayout.Button("【记录并保存数值到配置文件】", GUILayout.Height(30)))
            {
                manager.SaveFormationConfig();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(12);
            EditorGUILayout.LabelField("快速换波审阅控制", EditorStyles.boldLabel);

            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("上一波 (← / Q)", GUILayout.Height(36)))
            {
                Undo.RecordObject(manager, "Prev Wave");
                manager.PrevWave();
                EditorUtility.SetDirty(manager);
                SceneView.RepaintAll();
            }
            if (GUILayout.Button("下一波 (→ / E / 空格)", GUILayout.Height(36)))
            {
                Undo.RecordObject(manager, "Next Wave");
                manager.NextWave();
                EditorUtility.SetDirty(manager);
                SceneView.RepaintAll();
            }
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(12);
            EditorGUILayout.LabelField("战力机制与对攻测试", EditorStyles.boldLabel);
            EditorGUILayout.BeginHorizontal();
            if (GUILayout.Button("左军施法 (1)", GUILayout.Height(30))) manager.TriggerLeftCast();
            if (GUILayout.Button("右军施法 (2)", GUILayout.Height(30))) manager.TriggerRightCast();
            if (GUILayout.Button("交替施法 (Space)", GUILayout.Height(30))) manager.TriggerNextCast();
            if (GUILayout.Button("满血重置 (B)", GUILayout.Height(30))) manager.ResetBattlePower();
            EditorGUILayout.EndHorizontal();

            EditorGUILayout.Space(4);
            if (GUILayout.Button("【全场战斗极速演算推演 (Simulate)】", GUILayout.Height(32)))
            {
                manager.SimulateAndPrintBattle();
            }

            EditorGUILayout.Space(6);
            EditorGUILayout.HelpBox(string.Format("当前波次: 第 {0} / {1} 波 (左军战力: {2:N0}/{3:N0} | 右军战力: {4:N0}/{5:N0})", 
                manager.CurrentWaveIndex + 1, manager.TotalWaves, manager.LeftCurrentBP, manager.LeftMaxBP, manager.RightCurrentBP, manager.RightMaxBP), MessageType.Info);
        }
    }
}
#endif
