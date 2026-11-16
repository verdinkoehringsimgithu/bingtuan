using UnityEngine;

namespace LegionBattle.Battle
{
    public struct EffectSortRange
    {
        public int layer,backLayer,frontOrder,backOrder;
    }
    public static class BattleEffectSorting
    {
        public static EffectSortRange Resolve(BattleCharacterPreview[] members,bool depthSorting,int fallback=5000)
        {
            int count=0,min=32767,max=-32768,layer=0,minLayer=0,minValue=int.MaxValue,maxValue=int.MinValue;
            float totalY=0;
            if(members!=null)foreach(var member in members)
            {
                if(member==null||!member.gameObject.activeInHierarchy||member.CharacterData==null)continue;
                var renderer=member.GetComponent<SpriteRenderer>();
                if(renderer==null||!renderer.enabled||renderer.sprite==null)continue;
                int value=SortingLayer.GetLayerValueFromID(renderer.sortingLayerID);
                if(value<minValue){minValue=value;minLayer=renderer.sortingLayerID;}
                if(value>maxValue){maxValue=value;layer=renderer.sortingLayerID;}
                min=Mathf.Min(min,renderer.sortingOrder);max=Mathf.Max(max,renderer.sortingOrder);totalY+=member.BasePosition.y;count++;
            }
            if(count==0)return new EffectSortRange {layer=0,backLayer=0,frontOrder=fallback,backOrder=fallback-1};
            int depthOrder=max+20;
            if(depthSorting)
            {
                float centerY=totalY/count;int rearMax=int.MinValue,frontMin=int.MaxValue;
                foreach(var member in members)
                {
                    if(member==null||!member.gameObject.activeInHierarchy||member.CharacterData==null)continue;
                    var renderer=member.GetComponent<SpriteRenderer>();
                    if(renderer==null||!renderer.enabled||renderer.sprite==null)continue;
                    // Classify by initial row height, preserving the entire row on one side.
                    if(member.BasePosition.y>centerY+.0001f)rearMax=Mathf.Max(rearMax,renderer.sortingOrder);
                    else frontMin=Mathf.Min(frontMin,renderer.sortingOrder);
                }
                depthOrder=rearMax==int.MinValue?frontMin-2:
                    frontMin==int.MaxValue?rearMax+2:
                    (int)System.Math.Floor((rearMax+(double)frontMin)/2);
            }
            return new EffectSortRange {layer=layer,backLayer=minLayer,
                frontOrder=Mathf.Clamp(depthOrder,-32768,32767),
                backOrder=Mathf.Clamp(min-20,-32768,32767)};
        }
        public static void Apply(SpriteRenderer front,SpriteRenderer back,BattleCharacterPreview[] members,bool depthSorting,int fallback=5000)
        {
            var range=Resolve(members,depthSorting,fallback);
            if(front!=null){front.sortingLayerID=range.layer;front.sortingOrder=range.frontOrder;}
            if(back!=null){back.sortingLayerID=range.backLayer;back.sortingOrder=range.backOrder;}
        }
    }
}
