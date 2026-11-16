using UnityEngine;

namespace LegionBattle.Battle
{
    public sealed class BattlePresentationTimeline
    {
        public const float ChargeDistance=1.6f;
        public readonly float Contact,AttackHold,ReturnDuration;
        public readonly float effectStart,effectEnd,damageTime,physicsTime,healTime,startTime,endTime,rotationDuration,reactionDuration;
        public readonly int rotations;
        public float ReturnStart => Contact+AttackHold;
        public float ReturnEnd => ReturnStart+ReturnDuration;
        public BattlePresentationTimeline(EffectTimingProfile profile,int frames)
        {
            profile.Normalize();
            Contact=profile.advanceDuration;AttackHold=profile.holdDuration;ReturnDuration=profile.retreatDuration;
            effectStart=(profile.playOnCaster?ReturnEnd:Contact)+profile.effectStartFrame/(float)profile.fps;
            effectEnd=effectStart+frames/(float)profile.fps;
            damageTime=profile.playOnCaster?Contact:effectStart+profile.DamageDelay;
            physicsTime=profile.playOnCaster?Contact:effectStart+profile.PhysicsDelay;
            healTime=effectStart+profile.HealDelay;
            float fallback=profile.reactionType==4?.68f:.56f;
            rotationDuration=effectEnd>physicsTime?Mathf.Max(.05f,effectEnd-physicsTime):fallback;
            rotations=profile.autoRotationCount?Mathf.Max(1,Mathf.RoundToInt(rotationDuration/profile.secondsPerRotation)):profile.rotationCount;
            reactionDuration=profile.reactionType==4?rotationDuration+.22f:profile.reactionType==10?rotationDuration+.36f:EffectTimingConfig.ReactionDuration(profile.reactionType);
            startTime=Mathf.Min(0,Mathf.Min(effectStart,Mathf.Min(damageTime,Mathf.Min(physicsTime,healTime))));
            endTime=Mathf.Max(ReturnEnd,Mathf.Max(effectEnd,Mathf.Max(damageTime+CameraShakeController.MaximumDuration,Mathf.Max(physicsTime+reactionDuration,healTime+.35f))));
        }
        public float AttackOffset(float time)
        {
            if(time<0)return 0;
            if(time<Contact)return Mathf.SmoothStep(0,ChargeDistance,time/Contact);
            if(time<ReturnStart)return ChargeDistance;
            if(ReturnDuration<=0)return 0;
            return Mathf.Lerp(ChargeDistance,0,Mathf.SmoothStep(0,1,(time-ReturnStart)/ReturnDuration));
        }
    }
}
