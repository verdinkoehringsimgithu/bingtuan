"""Mechanical wiring of the optional tactical rule/snapshot pair."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
B=ROOT/'LegionBattle/LegionBattle/Assets/Scripts/Battle'
def change(name,old,new):
    path=B/name;s=path.read_text(encoding='utf-8-sig');assert old in s,(name,old);path.write_text(s.replace(old,new),encoding='utf-8')
change('BattleTroop.cs','public CombatAugmentationRules augmentationBonds;','public CombatAugmentationRules augmentationBonds;\n        public CombatTacticalRules tacticalBonds;')
change('BattleTroop.cs','supportBonds,amplificationBonds,augmentationBonds);','supportBonds,amplificationBonds,augmentationBonds,tacticalBonds);')
change('BattleSceneRequest.cs','public CombatAugmentationRules leftAugmentationBonds,rightAugmentationBonds;','public CombatAugmentationRules leftAugmentationBonds,rightAugmentationBonds;\n        public CombatTacticalRules leftTacticalBonds,rightTacticalBonds;')
change('BattleSceneRequest.cs','public CombatAugmentationSummary leftAugmentationBonds,rightAugmentationBonds;','public CombatAugmentationSummary leftAugmentationBonds,rightAugmentationBonds;\n        public CombatTacticalSummary leftTacticalBonds,rightTacticalBonds;')
change('BattleSceneFlow.cs','rightAugmentationBonds=request.rightAugmentationBonds==null?null:request.rightAugmentationBonds.Clone()};','rightAugmentationBonds=request.rightAugmentationBonds==null?null:request.rightAugmentationBonds.Clone(),\n                leftTacticalBonds=request.leftTacticalBonds==null?null:request.leftTacticalBonds.Clone(),\n                rightTacticalBonds=request.rightTacticalBonds==null?null:request.rightTacticalBonds.Clone()};')
change('BattleSceneController.cs','request.leftAugmentationBonds,request.rightAugmentationBonds);','request.leftAugmentationBonds,request.rightAugmentationBonds,request.leftTacticalBonds,request.rightTacticalBonds);')
change('BattleSceneController.cs','leftAugmentationBonds=runtime.teams[0].AugmentationBonds.Snapshot(),rightAugmentationBonds=runtime.teams[1].AugmentationBonds.Snapshot(),','leftAugmentationBonds=runtime.teams[0].AugmentationBonds.Snapshot(),rightAugmentationBonds=runtime.teams[1].AugmentationBonds.Snapshot(),\n                leftTacticalBonds=runtime.teams[0].TacticalBonds.Snapshot(),rightTacticalBonds=runtime.teams[1].TacticalBonds.Snapshot(),')
change('BattleInspectionManager.cs','CombatAugmentationRules rightAugmentation = null)','CombatAugmentationRules rightAugmentation = null, CombatTacticalRules leftTactical = null, CombatTacticalRules rightTactical = null)')
change('BattleInspectionManager.cs','leftTroop.augmentationBonds=leftAugmentation==null?null:leftAugmentation.Clone();rightTroop.augmentationBonds=rightAugmentation==null?null:rightAugmentation.Clone();','leftTroop.augmentationBonds=leftAugmentation==null?null:leftAugmentation.Clone();rightTroop.augmentationBonds=rightAugmentation==null?null:rightAugmentation.Clone();\n            leftTroop.tacticalBonds=leftTactical==null?null:leftTactical.Clone();rightTroop.tacticalBonds=rightTactical==null?null:rightTactical.Clone();')
change('BattleTurnReport.cs','public bool killerMarked;','public bool killerMarked;\n        public double coinsEarned;')
change('BattleEngine.cs','killerMarked=action.killerMarked','killerMarked=action.killerMarked,coinsEarned=action.coinsEarned')
