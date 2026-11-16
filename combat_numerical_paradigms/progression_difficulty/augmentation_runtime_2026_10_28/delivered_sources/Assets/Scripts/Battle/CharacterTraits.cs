using System;

namespace LegionBattle.Battle
{
    [Serializable] public sealed class CharacterTraits
    {
        public string personId, assetGuid, raceId, race, gender, identityId, identity;
        public int markedTier;
        public CharacterTraits Clone()
        {
            return new CharacterTraits {personId=personId,assetGuid=assetGuid,raceId=raceId,race=race,gender=gender,
                identityId=identityId,identity=identity,markedTier=markedTier};
        }
    }
}
