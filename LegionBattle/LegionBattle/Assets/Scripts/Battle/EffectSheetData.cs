using System;
using System.Collections.Generic;
using UnityEngine;

namespace LegionBattle.Battle
{
    [Serializable]
    public class EffectFrameRect
    {
        public int x;
        public int y;
        public int w;
        public int h;
    }

    [Serializable]
    public class EffectEntry
    {
        public int animationId;
        public string baseKey;
        public string color;
        public string cnName;
        public string categoryCn;
        public string folderName;
        public int fps = 15;
        public bool isDirectionalRight;
        public bool playOnCaster;
        public float recommendedScale = 2.2f;
        public Sprite[] frames;
        public Sprite[] frontFrames;
        public Sprite[] backFrames;
        public bool HasLayerSprites => frontFrames!=null&&backFrames!=null&&frontFrames.Length>0&&backFrames.Length>0;
        public List<EffectFrameRect> rawRects = new List<EffectFrameRect>();

        public bool HasValidSprites => frames != null && frames.Length > 0 && frames[0] != null;
    }

}
