using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    [CreateAssetMenu(fileName = "EffectDatabase", menuName = "LegionBattle/EffectDatabase")]
    public class EffectDatabase : ScriptableObject
    {
        public bool visibleFramesCentered;
        public List<EffectEntry> effects = new List<EffectEntry>();

        private Dictionary<int, EffectEntry> _lookup;

        public void RebuildLookup()
        {
            _lookup = new Dictionary<int, EffectEntry>(effects.Count);
            for (int i = 0; i < effects.Count; i++)
            {
                EffectEntry e = effects[i];
                if (e != null)
                {
                    _lookup[e.animationId] = e;
                }
            }
        }

        public bool TryGetEffect(int animationId, out EffectEntry entry)
        {
            if (_lookup == null || _lookup.Count != effects.Count)
            {
                RebuildLookup();
            }
            return _lookup.TryGetValue(animationId, out entry);
        }
    }
}
