using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    [CreateAssetMenu(fileName="CharacterDatabase",menuName="LegionBattle/CharacterDatabase")]
    public class CharacterDatabase : ScriptableObject
    {
        public List<CharacterSheetData> characters=new List<CharacterSheetData>();
    }
}
