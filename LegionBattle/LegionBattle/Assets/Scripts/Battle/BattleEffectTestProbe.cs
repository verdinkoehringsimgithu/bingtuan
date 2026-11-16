#if UNITY_EDITOR
using System;
using System.Collections;
using System.IO;
using UnityEngine;
using UnityEditor;

namespace LegionBattle.Battle
{
    public class BattleEffectTestProbe : MonoBehaviour
    {
        private int checks,variants,layeredVariants;
        private void Check(bool condition,string label){if(!condition)throw new Exception(label);checks++;}
        private IEnumerator Start()
        {
            yield return null;yield return null;
            EffectTimingConfig.UseValidationDirectory(Path.Combine(Application.temporaryCachePath,"EffectTimingProbe-"+Guid.NewGuid().ToString("N")));
            FormationConfig.UseValidationDirectory(Path.Combine(Application.temporaryCachePath,"FormationProbe-"+Guid.NewGuid().ToString("N")));
            string error=null;
            try
            {
                var module=FindObjectOfType<BattleEffectTestModule>();
                Check(module!=null&&module.CapturedReport!=null,"Real battle report captured");
                Check(module.FamilyCount==63,"63 reviewed families are available without genre filtering");
                var camera=Camera.main;var homeCamera=camera.transform.position;
                var originalLeft=BattleFormationCenter.GetCenter(module.presentation.LeftSlots);var originalRight=BattleFormationCenter.GetCenter(module.presentation.RightSlots);
                Check(Mathf.Abs((originalLeft.x+originalRight.x)*.5f-homeCamera.x)<.0001f,"Both formations are centered around the camera rest position");
                module.Seek(module.DamageTime+.02f);module.presentation.ApplyFormationLayout();
                Check(Vector3.Distance(originalLeft,BattleFormationCenter.GetCenter(module.presentation.LeftSlots))<.0001f&&Vector3.Distance(originalRight,BattleFormationCenter.GetCenter(module.presentation.RightSlots))<.0001f,"Shake and repeated layout do not shift formation anchors");
                for(int repeat=0;repeat<20;repeat++){module.Seek(module.Duration);module.Seek(module.StartTime);}
                Check(Vector3.Distance(originalLeft,BattleFormationCenter.GetCenter(module.presentation.LeftSlots))<.0001f&&Vector3.Distance(originalRight,BattleFormationCenter.GetCenter(module.presentation.RightSlots))<.0001f,"Seeking does not accumulate formation drift");
                foreach(string fixture in new[]{"ReviewedEffectParity.tsv","MatchingParity.tsv","MatchingSemanticCases.tsv"})
                {
                string corpus=Path.Combine(Application.dataPath,"Resources/"+fixture);
                if(File.Exists(corpus))foreach(string row in File.ReadAllLines(corpus))
                {
                    if(string.IsNullOrEmpty(row))continue;var columns=row.Split('\t');int id;string name,folder,category;
                    SkillEffectMatcher.ResolveSkillEffect(columns[0],columns[1],int.Parse(columns[2]),"",out id,out name,out folder,out category);
                    Check(id==int.Parse(columns[3]),"Unity and generator choose the same eligible effect for "+columns[0]);
                }
                }
                foreach(int removedId in new[]{1244,1272,1298,1478})
                {
                    SkillEffectMatcher.VariantEntry variant;SkillEffectMatcher.FamilyEntry family;
                    Check(!SkillEffectMatcher.TryGetById(removedId,out variant,out family),"Removed family is absent from lookup "+removedId);
                    float rejectedScale;bool rejectedDirection;
                    Check(BattleEffectPlayer.Instance.GetFrames(removedId,out rejectedScale,out rejectedDirection)==null,"Packaged legacy resource cannot bypass catalogue removal "+removedId);
                    var stale=new BattleSkill {name="苍雷脉冲",animationId=removedId,rarityTier=6};
                    int replacement=BattleEffectPlayer.PrepareSkillEffect(stale);
                    Check(replacement!=removedId&&SkillEffectMatcher.TryGetById(replacement,out variant,out family),"Stale skill effect is replaced by an active family "+removedId);
                }
                Check(BattleEffectPlayer.PrepareSkillEffect(new BattleSkill {name="指定特效",animationId=1096,effectType=BattleSkillEffectType.Critical})==1096,"An explicitly assigned active effect remains unchanged");
                string defaultProfile=JsonUtility.ToJson(module.Profile),familyKey=module.Profile.familyKey;
                Directory.CreateDirectory(Path.GetDirectoryName(EffectTimingConfig.SavePath));
                foreach(int oldVersion in new[]{2,3,4})
                {
                    File.WriteAllText(EffectTimingConfig.SavePath,"{\"version\":"+oldVersion+",\"profiles\":[{\"familyKey\":\""+familyKey+"\",\"scale\":2.3,\"fps\":12,\"damageFrame\":-4,\"physicsFrame\":7,\"offsetY\":0.25,\"useFormationSorting\":false}]}");
                    EffectTimingConfig.Reload();var migrated=module.Profile;
                    Check(migrated.advanceDuration==.30f&&migrated.holdDuration==.50f&&migrated.retreatDuration==.40f,"Older configuration receives motion defaults version "+oldVersion);
                    Check(migrated.scale==2.3f&&migrated.fps==12&&migrated.damageFrame==-4&&migrated.physicsFrame==7&&migrated.offsetY==.25f&&!migrated.useFormationSorting,"Motion migration preserves existing calibration version "+oldVersion);
                    Check(migrated.scatterDistanceScale==0.45f&&migrated.healFrame==0,"Older configuration receives scatterDistanceScale 0.45 and healFrame 0 version "+oldVersion);
                    JsonUtility.FromJsonOverwrite(defaultProfile,migrated);
                }
                EffectTimingConfig.Motion.advanceDuration=.30f;EffectTimingConfig.Motion.holdDuration=.50f;EffectTimingConfig.Motion.retreatDuration=.40f;
                var player=BattleEffectPlayer.Instance;
                Check(player.database!=null,"Baked database is loaded through Resources");
                Check(player.database.visibleFramesCentered,"Baked visible-frame alignment is enabled");
                float firstScale;bool firstDirection;var explosion=player.GetFrames(1001,out firstScale,out firstDirection);
                Check(Mathf.Abs(explosion[0].pivot.y-5.5f)<.001f,"First flash padding regression: visible center is the pivot");
                Check(Mathf.Abs(explosion[6].pivot.y-61.5f)<.001f,"Expanded cloud uses its visible center");
                var sortingFormation=module.presentation.RightSlots;
                int minimum=int.MaxValue,maximum=int.MinValue;
                foreach(var member in sortingFormation)if(member!=null&&member.CharacterData!=null){int order=member.GetComponent<SpriteRenderer>().sortingOrder;minimum=Math.Min(minimum,order);maximum=Math.Max(maximum,order);}
                foreach(var family in SkillEffectMatcher.AllFamilies)
                    foreach(var variant in family.Variants.Values)
                    {
                        float scale;bool direction;var frames=player.GetFrames(variant.AnimationId,out scale,out direction);
                        Check(frames!=null&&frames.Length>0,"Missing atlas "+variant.FolderName);
                        EffectEntry baked;
                        Check(player.database.TryGetEffect(variant.AnimationId,out baked)&&baked.HasValidSprites,"Packaged sprite references "+variant.AnimationId);
                        Check(player.ShowFrame(variant.AnimationId,frames.Length-1,Vector3.zero,true),"Last frame "+variant.AnimationId);
                        var settings=EffectTimingConfig.For(variant.AnimationId);bool savedSorting=settings.useFormationSorting;
                        settings.useFormationSorting=true;
                        player.ShowFrame(variant.AnimationId,frames.Length-1,BattleFormationCenter.GetCenter(sortingFormation),true,sortingFormation);
                        var frontRenderer=player.transform.Find("EffectFramePreview").GetComponent<SpriteRenderer>();
                        Check(frontRenderer.sortingOrder>minimum&&frontRenderer.sortingOrder<maximum,"Depth sorting between back and front ranks "+variant.AnimationId);
                        bool sameRowConsistent=true;
                        for(int a=0;a<sortingFormation.Length;a++)for(int b=a+1;b<sortingFormation.Length;b++){
                            var one=sortingFormation[a];var two=sortingFormation[b];
                            if(one==null||two==null||one.CharacterData==null||two.CharacterData==null)continue;
                            if(Mathf.Abs(one.BasePosition.y-two.BasePosition.y)>.0001f)continue;
                            if((one.GetComponent<SpriteRenderer>().sortingOrder>frontRenderer.sortingOrder)!=(two.GetComponent<SpriteRenderer>().sortingOrder>frontRenderer.sortingOrder))sameRowConsistent=false;
                        }
                        Check(sameRowConsistent,"One effect does not split actors in the same row "+variant.AnimationId);
                        settings.useFormationSorting=false;
                        player.ShowFrame(variant.AnimationId,frames.Length-1,BattleFormationCenter.GetCenter(sortingFormation),true,sortingFormation);
                        Check(frontRenderer.sortingOrder>maximum,"Highest-layer marker "+variant.AnimationId);
                        if(baked.HasLayerSprites){
                            var backRenderer=frontRenderer.transform.Find("EffectBackLayer").GetComponent<SpriteRenderer>();
                            Check(baked.frontFrames.Length==frames.Length&&baked.backFrames.Length==frames.Length,"Synchronized native layer lengths "+variant.AnimationId);
                            Check(frontRenderer.sprite==baked.frontFrames[frames.Length-1]&&backRenderer.sprite==baked.backFrames[frames.Length-1],"Use native layers rather than composite "+variant.AnimationId);
                            Check(backRenderer.sortingOrder<minimum,"Native back layer is below every character "+variant.AnimationId);layeredVariants++;
                        }
                        settings.useFormationSorting=savedSorting;
                        variants++;
                    }
                Check(layeredVariants==19,"All 19 active native layer variants are adapted");
                for(int stage=1;stage<=6;stage++){
                    module.presentation.battleStage=stage;module.presentation.DraftStrategyBattle();
                    var members=module.presentation.RightSlots;var range=BattleEffectSorting.Resolve(members,true);
                    for(int a=0;a<members.Length;a++)for(int b=a+1;b<members.Length;b++){
                        var one=members[a];var two=members[b];if(one==null||two==null||one.CharacterData==null||two.CharacterData==null)continue;
                        if(Mathf.Abs(one.BasePosition.y-two.BasePosition.y)>.0001f)continue;
                        Check((one.GetComponent<SpriteRenderer>().sortingOrder>range.frontOrder)==(two.GetComponent<SpriteRenderer>().sortingOrder>range.frontOrder),"Same-row occlusion at stage "+stage);
                    }
                }
                module.presentation.battleStage=6;module.CaptureReport();module.Seek(0);
                double left=module.presentation.battleEngine.Runtime.teams[0].bp,right=module.presentation.battleEngine.Runtime.teams[1].bp;
                int round=module.presentation.battleEngine.currentRound;
                int savedId=module.AnimationId;
                var original=JsonUtility.ToJson(module.Profile);
                var profile=module.Profile;profile.playOnCaster=false;profile.fps=15;profile.damageFrame=6;profile.physicsFrame=1;
                var hitMembers=module.CapturedReport.actingTroopId==1?module.presentation.RightSlots:module.presentation.LeftSlots;
                module.Seek(module.PhysicsTime+.05f);
                Check(module.PhysicsTime<module.DamageTime,"Physics can precede damage");
                Check(hitMembers[0].DisplayColor==Color.white,"Early physics does not start the damage flash");
                Check(CameraShakeController.DamageOffset(module.CurrentTime-module.DamageTime,100000,1000000)==Vector3.zero,"Early physics does not start camera shake");
                int preLeft=module.presentation.HealthBarUI.LeftBar.currentBP,preRight=module.presentation.HealthBarUI.RightBar.currentBP;
                module.Seek(module.DamageTime+.001f);
                Check(hitMembers[0].DisplayColor==(!module.CapturedReport.isDodge&&module.CapturedReport.damageDealt>0?new Color(2.5f,2.5f,1.8f,1):Color.white),"Damage flash follows the damage cue");
                Check(module.presentation.HealthBarUI.LeftBar.currentBP==Mathf.Min(module.presentation.leftTroop.currentBP,module.presentation.leftTroop.maxBP)&&module.presentation.HealthBarUI.RightBar.currentBP==Mathf.Min(module.presentation.rightTroop.currentBP,module.presentation.rightTroop.maxBP),"Damage cue uses the real result (display caps rounded maximum BP)");
                module.Seek(module.DamageTime-.001f);
                Check(hitMembers[0].DisplayColor==Color.white,"Backward seek resets the damage flash");
                Check(module.presentation.HealthBarUI.LeftBar.currentBP==preLeft&&module.presentation.HealthBarUI.RightBar.currentBP==preRight,"Backward seek restores previous BP");
                foreach(int type in new[]{1,2,3,4,5,6,7,8,9,10})
                {
                    profile.reactionType=type;
                    module.Seek(module.PhysicsTime+.18f);
                    var targets=module.CapturedReport.actingTroopId==1?module.presentation.RightSlots:module.presentation.LeftSlots;
                    Vector3 position=targets[0].transform.position;
                    module.Seek(module.Duration);module.Seek(module.PhysicsTime+.18f);
                    Check(Vector3.Distance(position,targets[0].transform.position)<.0001f,"Deterministic backward physics type "+type);
                }
                Check(left==module.presentation.battleEngine.Runtime.teams[0].bp&&right==module.presentation.battleEngine.Runtime.teams[1].bp&&round==module.presentation.battleEngine.currentRound,"Seeking does not execute numerical turns");
                var randomState=UnityEngine.Random.state;float expectedRandom=UnityEngine.Random.value;UnityEngine.Random.state=randomState;
                module.Seek(module.PhysicsTime+.21f);
                Check(UnityEngine.Random.value==expectedRandom,"Seeking preserves the global random stream");UnityEngine.Random.state=randomState;
                profile.damageFrame=1;profile.physicsFrame=6;
                Check(module.DamageTime<module.PhysicsTime,"Damage can precede physics");
                module.Seek(module.DamageTime+.08f);
                Check(hitMembers[0].DisplayColor==(!module.CapturedReport.isDodge&&module.CapturedReport.damageDealt>0?new Color(1,.94f,.1f,1):Color.white),"Flash changes before delayed physics");
                Check(CameraShakeController.DamageOffset(-.01f,100000,1000000)==Vector3.zero&&CameraShakeController.DamageOffset(.02f,100000,1000000).sqrMagnitude>0,"Camera shake starts only at damage");
                Check(CameraShakeController.DamageOffset(.40f,100000,1000000)==Vector3.zero,"Camera shake finishes independently of physics");
                profile.reactionType=2;profile.physicsFrame=0;
                var lifted=module.CapturedReport.actingTroopId==1?module.presentation.RightSlots:module.presentation.LeftSlots;
                module.Seek(module.PhysicsTime+.113f);
                var effectTransform=player.transform.Find("EffectFramePreview");
                Vector3 expectedCenter=BattleFormationCenter.Visible(lifted)+new Vector3(0,profile.offsetY,0);
                Check(Vector3.Distance(effectTransform.position,expectedCenter)<.00001f,"Effect stays firmly at static formation center during pop-up");
                module.Seek(module.Duration);
                Check(!effectTransform.gameObject.activeSelf||Vector3.Distance(effectTransform.position,expectedCenter)<.00001f,"Finished effect is hidden or kept at static formation center");

                profile.physicsFrame=6;
                profile.playOnCaster=true;
                Check(module.EffectStart>=module.Timeline.ReturnEnd-.00001f,"Self effect waits for return");
                Check(module.DamageTime==module.Timeline.Contact&&module.PhysicsTime==module.Timeline.Contact,"Self effects retain contact damage and physics");
                profile.playOnCaster=false;profile.fps=1;profile.reactionType=1;profile.damageFrame=profile.physicsFrame=0;
                var attackMembers=module.CapturedReport.actingTroopId==1?module.presentation.LeftSlots:module.presentation.RightSlots;
                var actionTimeline=module.Timeline;
                Check(actionTimeline.Contact==.30f&&actionTimeline.ReturnDuration==.40f,"Motion defaults retain the slower movement durations");
                Check(actionTimeline.ReturnStart-actionTimeline.Contact==EffectTimingConfig.ReactionDuration(1),"Default attack hold equals normal attack duration");
                module.Seek(actionTimeline.ReturnStart-.01f);
                Check(Mathf.Abs(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)-BattlePresentationTimeline.ChargeDistance)<.00001f,"Attacker holds at contact before returning");
                module.Seek(actionTimeline.ReturnStart+.20f);
                Check(Mathf.Abs(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)-BattlePresentationTimeline.ChargeDistance*.5f)<.00001f,"Attacker returns smoothly over the full duration");
                module.Seek(actionTimeline.ReturnEnd+.01f);
                Check(module.Duration>10&&Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)<.00001f,"Attacker returns while a long effect is still playing");
                profile.advanceDuration=.60f;profile.holdDuration=.25f;profile.retreatDuration=.70f;
                var customMotion=module.Timeline;
                Check(Mathf.Abs(customMotion.Contact-.60f)<.00001f&&Mathf.Abs(customMotion.ReturnStart-.85f)<.00001f&&Mathf.Abs(customMotion.ReturnEnd-1.55f)<.00001f,"Configured motion sets contact, return start and return end");
                module.Seek(.30f);
                Check(Mathf.Abs(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)-.80f)<.00001f,"Preview uses the configured forward duration");
                module.Seek(.75f);
                Check(Mathf.Abs(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)-1.60f)<.00001f,"Preview uses the configured hold duration");
                module.Seek(1.20f);
                Check(Mathf.Abs(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)-.80f)<.00001f,"Preview uses the configured return duration");
                profile.playOnCaster=true;
                Check(Mathf.Abs(module.EffectStart-1.55f)<.00001f&&module.DamageTime==.60f,"Self effect timing follows the configured return and contact");
                profile.playOnCaster=false;profile.advanceDuration=.30f;profile.holdDuration=.50f;profile.retreatDuration=.40f;
                var zeroMotion=new EffectTimingProfile {advanceDuration=0,holdDuration=.20f,retreatDuration=0};var zeroTimeline=new BattlePresentationTimeline(zeroMotion,10);
                Check(zeroTimeline.AttackOffset(-.001f)==0&&zeroTimeline.AttackOffset(0)==1.6f&&zeroTimeline.AttackOffset(.21f)==0,"Zero forward and return durations work without division by zero");
                zeroMotion.holdDuration=0;zeroTimeline=new BattlePresentationTimeline(zeroMotion,10);
                Check(zeroTimeline.AttackOffset(0)==0&&!float.IsNaN(zeroTimeline.endTime),"All zero motion durations remain valid");
                zeroMotion.advanceDuration=-1;zeroMotion.holdDuration=float.NaN;zeroMotion.retreatDuration=float.PositiveInfinity;zeroMotion.Normalize();
                Check(zeroMotion.advanceDuration==0&&zeroMotion.holdDuration==.50f&&zeroMotion.retreatDuration==.40f,"Motion normalization keeps nonnegative finite durations");
                profile.fps=15;profile.effectStartFrame=-6;profile.damageFrame=6;
                module.Seek(module.StartTime);
                Check(module.StartTime<0&&module.CurrentTime<0&&Mathf.Abs(module.EffectStart+.1f)<.00001f,"Negative effect frames include pre-roll");
                Check(Vector3.Distance(attackMembers[0].transform.position,attackMembers[0].BasePosition)<.00001f,"Pre-roll does not move attacker before the charge");
                Check(effectTransform.gameObject.activeSelf,"Pre-roll displays atlas frame zero rather than skipping it");
                profile.damageFrame=-1;profile.physicsFrame=-2;profile.Normalize();
                Check(profile.damageFrame==-1&&profile.physicsFrame==-2&&module.DamageTime<module.EffectStart&&module.PhysicsTime<module.DamageTime,"Negative damage and physics frames are preserved");
                var rotationProfile=new EffectTimingProfile {fps=15,reactionType=10,secondsPerRotation=1,autoRotationCount=true};
                var once=new BattlePresentationTimeline(rotationProfile,10);
                Check(once.rotations==1,"Ten-frame whirlwind plays one automatic revolution");
                rotationProfile.fps=5;var twice=new BattlePresentationTimeline(rotationProfile,10);
                Check(twice.rotations==2,"Longer effects adapt automatic revolution count");
                rotationProfile.autoRotationCount=false;rotationProfile.rotationCount=3;
                Check(new BattlePresentationTimeline(rotationProfile,10).rotations==3,"Manual revolution count overrides automatic count");
                var subject=lifted[0];subject.SampleHitReaction(10,false,1,.51f,Vector3.right,173,1,1);
                Check(subject.DisplayDirection==3,"One revolution has one sequence of four directions");
                subject.SampleHitReaction(10,false,1,.51f,Vector3.right,173,2,1);
                Check(subject.DisplayDirection==0,"Two revolutions have two direction sequences");

                // 炸散距离倍率验证 (模式6及其他模式不受影响)
                var scatterSubject = lifted[0];
                scatterSubject.SampleHitReaction(6, false, 1.0f, 0.20f, Vector3.right, 173, 1, 0, 1.0f);
                Vector3 fullScatterPos = scatterSubject.transform.position;
                scatterSubject.SampleHitReaction(6, false, 1.0f, 0.20f, Vector3.right, 173, 1, 0, 0.45f);
                Vector3 scaledScatterPos = scatterSubject.transform.position;
                float fullDist = Vector3.Distance(scatterSubject.BasePosition, fullScatterPos);
                float scaledDist = Vector3.Distance(scatterSubject.BasePosition, scaledScatterPos);
                Check(scaledDist < fullDist && Mathf.Abs(scaledDist / fullDist - 0.45f) < 0.05f, "Scatter distance scales with scatterDistanceScale");
                scatterSubject.SampleHitReaction(6, false, 1.0f, 0.70f, Vector3.right, 173, 1, 0, 0.45f);
                Check(Vector3.Distance(scatterSubject.transform.position, scatterSubject.BasePosition) < 0.001f, "Mode 6 regroups to base position after blast");
                scatterSubject.SampleHitReaction(1, false, 1.0f, 0.10f, Vector3.right, 173, 1, 0, 1.0f);
                Vector3 posMode1A = scatterSubject.transform.position;
                scatterSubject.SampleHitReaction(1, false, 1.0f, 0.10f, Vector3.right, 173, 1, 0, 0.45f);
                Vector3 posMode1B = scatterSubject.transform.position;
                Check(Vector3.Distance(posMode1A, posMode1B) < 0.0001f, "Other reaction modes are unaffected by scatterDistanceScale");

                // 两军站位间距验证 (对称靠近且居中于相机静止点)
                var formation = module.presentation.Formation;
                float originalDist = formation.ArmyDistance;
                formation.ArmyDistance = originalDist * 0.8f;
                module.presentation.ApplyFormationLayout();
                var newLeft = BattleFormationCenter.GetCenter(module.presentation.LeftSlots);
                var newRight = BattleFormationCenter.GetCenter(module.presentation.RightSlots);
                Check(Mathf.Abs((newLeft.x + newRight.x) * 0.5f - homeCamera.x) < 0.0001f, "Formations remain centered around camera rest position after distance adjustment");
                Check(newRight.x - newLeft.x < originalRight.x - originalLeft.x, "Armies moved closer when ArmyDistance was reduced");
                formation.Save();
                Check(File.Exists(FormationConfig.GetConfigFilePath()), "FormationConfig.Save writes configuration file");
                formation.ArmyDistance = originalDist;
                module.presentation.ApplyFormationLayout();

                // 自身特效筛选与回血时点空血校准验证
                module.FilterSelfOnly = true;
                Check(module.SelfFamilyCount > 0, "Self effect count is positive");
                profile.playOnCaster = true;
                profile.healFrame = 4;
                profile.fps = 15;
                float healTime = module.Timeline.healTime;
                Check(healTime > module.EffectStart, "healTime is computed from effectStart + healFrame/fps");
                module.Seek(healTime - 0.05f);
                var actingBar = module.presentation.HealthBarUI.LeftBar;
                var defendingBar = module.presentation.HealthBarUI.RightBar;
                Check(actingBar.currentBP == 0, "Acting troop displays 0 BP before heal time in self-effect preview");
                Check(defendingBar.currentBP > 0, "Defending troop retains BP in self-effect preview");
                module.Seek(healTime + 0.05f);
                Check(actingBar.currentBP == module.presentation.leftTroop.maxBP, "Acting troop snaps to max BP at heal time");
                module.Seek(healTime - 0.05f);
                Check(actingBar.currentBP == 0, "Seeking backward reverts acting troop to 0 BP");
                module.Seek(module.StartTime);
                Check(actingBar.currentBP == 0, "Self effect preview starts at 0 BP from StartTime");
                profile.healFrame = -3;
                Check(module.Timeline.healTime < module.EffectStart, "Negative healFrame places healTime before effectStart");
                profile.playOnCaster = false;
                module.FilterSelfOnly = false;

                profile.fps=15;profile.effectStartFrame=0;profile.damageFrame=1;profile.physicsFrame=6;profile.reactionType=2;
                profile.scale=1.4f;
                profile.offsetX=0;profile.offsetY=0;
                Vector3 formationCenter=new Vector3(1.25f,-.4f,0);
                player.ShowFrame(savedId,0,formationCenter,true);
                var renderer=player.transform.Find("EffectFramePreview");
                Check(Vector3.Distance(renderer.position,formationCenter)<.00001f,"Effect is at formation center");
                player.ShowFrame(savedId,0,formationCenter,false);
                Check(Vector3.Distance(renderer.position,formationCenter)<.00001f,"Direction does not shift the formation center");
                profile.offsetX=.15f;profile.offsetY=-.1f;
                player.ShowFrame(savedId,0,formationCenter,true);
                Check(Vector3.Distance(renderer.position,formationCenter+new Vector3(.15f,-.1f,0))<.00001f,"Fine horizontal and vertical offsets are applied");
                player.ShowFrame(savedId,0,formationCenter,false);
                Check(Vector3.Distance(renderer.position,formationCenter+new Vector3(-.15f,-.1f,0))<.00001f,"Horizontal fine offset mirrors for reverse attacks");
                profile.effectStartFrame=-3;profile.autoRotationCount=false;profile.rotationCount=2;
                profile.advanceDuration=.60f;profile.holdDuration=.25f;profile.retreatDuration=.70f;
                profile.scatterDistanceScale=0.65f;profile.healFrame=5;
                EffectTimingConfig.Save();EffectTimingConfig.Reload();
                EffectTimingConfig.For(savedId).useFormationSorting=false;EffectTimingConfig.Save();EffectTimingConfig.Reload();
                var saved=EffectTimingConfig.For(savedId);
                Check(saved.damageFrame==1&&saved.physicsFrame==6&&saved.scale==1.4f&&!saved.useFormationSorting&&saved.effectStartFrame==-3&&saved.rotationCount==2&&!saved.autoRotationCount&&saved.offsetX==.15f,"Persisted signed timing, rotation, fine offsets and sorting marker round trip");
                Check(saved.scatterDistanceScale==0.65f&&saved.healFrame==5,"Persisted scatterDistanceScale and healFrame round trip");
                Check(saved.advanceDuration==.60f&&saved.holdDuration==.25f&&saved.retreatDuration==.70f,"Motion durations survive manual save and reload");
                Check(EffectTimingConfig.For(1002)==saved&&EffectTimingConfig.For(1144).advanceDuration==.60f&&EffectTimingConfig.For(1144).holdDuration==.25f&&EffectTimingConfig.For(1144).retreatDuration==.70f,"Every family inherits movement from the first effect");
                var claw=EffectTimingConfig.For(1144);string originalClaw=JsonUtility.ToJson(claw);
                claw.scale=1;player.ShowFrame(1144,0,Vector3.zero,true);float normalSize=renderer.localScale.x;
                claw.scale=8;player.ShowFrame(1144,0,Vector3.zero,true);
                Check(Mathf.Abs(renderer.localScale.x/normalSize-8)<.0001f,"Claw effect supports a directly configured larger size");
                Check(EffectTimingConfig.AutoSaveIfChanged(),"Editing writes an automatic checkpoint without pressing Save");
                EffectTimingConfig.Reload();claw=EffectTimingConfig.For(1144);
                Check(claw.scale==8,"Reload restores the latest unsaved claw size");
                claw.scale=7;EffectTimingConfig.AutoSaveIfChanged();
                Check(File.Exists(EffectTimingConfig.AutoSavePath+".bak"),"Automatic checkpoint keeps the previous valid backup");
                File.WriteAllText(EffectTimingConfig.AutoSavePath,"broken");EffectTimingConfig.Reload();
                Check(EffectTimingConfig.For(1144).scale==8,"Corrupt automatic checkpoint recovers the previous calibration");
                EffectTimingConfig.For(1144).scale=6;EffectTimingConfig.AutoSaveIfChanged();EffectTimingConfig.Save();
                Check(File.Exists(EffectTimingConfig.SavePath+".bak"),"Manual save also preserves a recovery copy");
                Check(!EffectTimingConfig.AutoSaveIfChanged(),"Unchanged profile does not rewrite checkpoints");
                EffectTimingConfig.For(savedId).damageFrame=11;module.enabled=false;EffectTimingConfig.Reload();
                Check(EffectTimingConfig.For(savedId).damageFrame==11,"Disabling the real test module saves the current adjustments");
                Check(EffectTimingConfig.For(savedId).advanceDuration==.60f&&EffectTimingConfig.For(savedId).retreatDuration==.70f,"Automatic recovery retains configured movement durations");
                module.enabled=true;
                File.WriteAllText(EffectTimingConfig.SavePath,"broken");File.WriteAllText(EffectTimingConfig.AutoSavePath,"broken");EffectTimingConfig.Reload();
                Check(EffectTimingConfig.For(1144).scale==6&&EffectTimingConfig.For(savedId).damageFrame==1,"Damaged primary files fall back to the latest valid backup");
                EffectTimingConfig.Save();
                Check(JsonUtility.FromJson<EffectTimingDocument>(File.ReadAllText(EffectTimingConfig.SavePath)).profiles.Find(x=>x.familyKey==EffectTimingConfig.For(1144).familyKey).scale==6,"Recovered checkpoint can be published into the build resource");
                JsonUtility.FromJsonOverwrite(originalClaw,EffectTimingConfig.For(1144));
                JsonUtility.FromJsonOverwrite(original,EffectTimingConfig.For(savedId));
                module.Seek(0);
                int notifications=0;module.presentation.battleEngine.OnTurnCompleted+=r=>notifications++;
                var next=module.presentation.battleEngine.ExecuteNextTurn(false);
                Check(notifications==0,"Preparing a numerical report does not notify the damage cue");
                module.presentation.battleEngine.PublishPresentationCue(next);
                module.presentation.battleEngine.PublishPresentationCue(next);
                Check(notifications==1,"The damage cue notifies once even when requested twice");
                if(SystemInfo.graphicsDeviceType!=UnityEngine.Rendering.GraphicsDeviceType.Null)CaptureSortingImages(module,player);
                Debug.Log("Effect tuning validation passed: "+checks+" checks, "+variants+" variants");
            }
            catch(Exception e){error=e.ToString();Debug.LogException(e);}
            finally
            {
                EffectTimingConfig.Reload();
                FormationConfig.UseValidationDirectory(null);
            }
            string output=Environment.GetEnvironmentVariable("LEGION_EFFECT_VALIDATION");
            if(!string.IsNullOrEmpty(output))File.WriteAllText(output,"{\"passed\":"+(error==null?"true":"false")+",\"checks\":"+checks+",\"families\":63,\"variants\":"+variants+",\"layered_variants\":"+layeredVariants+",\"error\":"+(error==null?"null":JsonUtility.ToJson(new Failure{message=error}))+"}");
            EditorApplication.Exit(error==null?0:1);
        }
        [Serializable]private class Failure{public string message;}
        private void CaptureSortingImages(BattleEffectTestModule module,BattleEffectPlayer player)
        {
            string output=Environment.GetEnvironmentVariable("LEGION_EFFECT_VALIDATION");if(string.IsNullOrEmpty(output))return;
            var camera=Camera.main;if(camera==null)throw new Exception("Preview camera is unavailable");
            var targets=module.presentation.RightSlots;foreach(var member in targets)if(member!=null)member.ResetCombatState();
            var center=BattleFormationCenter.GetCenter(targets);var oldPosition=camera.transform.position;float oldSize=camera.orthographicSize;var oldTarget=camera.targetTexture;var oldActive=RenderTexture.active;
            var texture=new RenderTexture(768,768,24);var image=new Texture2D(768,768,TextureFormat.RGBA32,false);
            try {
                camera.transform.position=new Vector3(center.x,center.y,-10);camera.orthographicSize=3.8f;camera.targetTexture=texture;
                foreach(var spec in new[]{"1001,0,true,effect_initial_center.png","1001,6,true,effect_depth.png","1001,6,false,effect_top.png","1117,12,true,effect_layers.png"}) {
                    var fields=spec.Split(',');int id=int.Parse(fields[0]),frame=int.Parse(fields[1]);var profile=EffectTimingConfig.For(id);string prior=JsonUtility.ToJson(profile);
                    profile.offsetY=0;profile.scale=1;profile.useFormationSorting=bool.Parse(fields[2]);
                    player.ShowFrame(id,frame,center,true,targets);camera.Render();RenderTexture.active=texture;
                    image.ReadPixels(new Rect(0,0,768,768),0,0);image.Apply();File.WriteAllBytes(Path.Combine(Path.GetDirectoryName(output),fields[3]),image.EncodeToPNG());
                    JsonUtility.FromJsonOverwrite(prior,profile);
                }
            } finally {camera.transform.position=oldPosition;camera.orthographicSize=oldSize;camera.targetTexture=oldTarget;RenderTexture.active=oldActive;Destroy(image);texture.Release();Destroy(texture);player.ClearScrub();}
        }
    }
}
#endif
