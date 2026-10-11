package com.fnaf.horror.entity;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.item.FlashlightItem;
import com.fnaf.horror.lobby.LobbyManager;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModEntities;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.block.BlockState;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.ai.goal.ActiveTargetGoal;
import net.minecraft.entity.ai.goal.Goal;
import net.minecraft.entity.ai.goal.SwimGoal;
import net.minecraft.entity.ai.goal.WanderAroundFarGoal;
import net.minecraft.entity.attribute.DefaultAttributeContainer;
import net.minecraft.entity.attribute.EntityAttributes;
import net.minecraft.entity.damage.DamageSource;
import net.minecraft.entity.data.DataTracker;
import net.minecraft.entity.data.TrackedData;
import net.minecraft.entity.data.TrackedDataHandlerRegistry;
import net.minecraft.entity.effect.StatusEffectInstance;
import net.minecraft.entity.effect.StatusEffects;
import net.minecraft.entity.mob.HostileEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvent;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.World;
import software.bernie.geckolib.animatable.GeoEntity;
import software.bernie.geckolib.core.animatable.instance.AnimatableInstanceCache;
import software.bernie.geckolib.core.animation.AnimatableManager;
import software.bernie.geckolib.core.animation.AnimationController;
import software.bernie.geckolib.core.animation.RawAnimation;
import software.bernie.geckolib.core.object.PlayState;
import software.bernie.geckolib.util.GeckoLibUtil;

import java.util.EnumSet;
import java.util.UUID;

/**
 * FNAF-style animatronic. It hunts the nearest player but freezes in place while any player is
 * looking at it. Once it reaches its victim unseen it performs a jumpscare: it plants itself in
 * front of the player's face, the victim's camera is locked onto it (client side), a scream plays
 * and the player dies, which sends them back to the white-box lobby.
 * Foxy sprints; Golden Freddy never walks but teleports behind the player and vanishes when stared at.
 */
public class AnimatronicEntity extends HostileEntity implements GeoEntity {
	public static final Identifier JUMPSCARE_PACKET = FnafHorror.id("jumpscare");
	private static final TrackedData<Boolean> FROZEN = DataTracker.registerData(AnimatronicEntity.class, TrackedDataHandlerRegistry.BOOLEAN);

	private static final RawAnimation IDLE = RawAnimation.begin().thenLoop("idle");
	private static final RawAnimation WALK = RawAnimation.begin().thenLoop("walk");
	private static final RawAnimation ATTACK = RawAnimation.begin().thenPlay("attack");

	private static final int JUMPSCARE_TICKS = 24;
	private static final double WATCH_COS = 0.62;

	private final AnimatableInstanceCache cache = GeckoLibUtil.createInstanceCache(this);
	private int jumpscareTicks;
	private UUID victim;
	private int cooldown;
	private int servoTimer;
	private int teleportTimer = 100;
	private int stareTicks;
	private float frozenYaw;
	/** Set by NightManager: the animatronic only moves between route nodes and attacks on command. */
	public boolean nightControlled;
	/** Set by NightManager when this animatronic spotted a player outside the office: it runs after them. */
	public LivingEntity nightChase;
	/** Set by NightManager after a chase: walk back to this route node. */
	public Vec3d nightReturn;
	private int nightRepath;

	/**
	 * The collision box is capped below 2 blocks so they fit under the map's low ceilings (the stage, the
	 * doorways) and can path anywhere; the model keeps its real size (modelHeight).
	 */
	@Override
	public net.minecraft.entity.EntityDimensions getDimensions(net.minecraft.entity.EntityPose pose) {
		net.minecraft.entity.EntityDimensions d = getType().getDimensions();
		return net.minecraft.entity.EntityDimensions.fixed(d.width, Math.min(1.9f, d.height));
	}

	/** Height of the animatronic model (the registered entity size). */
	public float modelHeight() {
		return getType().getDimensions().height;
	}

	public AnimatronicEntity(EntityType<? extends HostileEntity> type, World world) {
		super(type, world);
		this.experiencePoints = 10;
		calculateDimensions();
	}

	public static DefaultAttributeContainer.Builder createAttributes() {
		return HostileEntity.createHostileAttributes()
				.add(EntityAttributes.GENERIC_MAX_HEALTH, 100.0)
				.add(EntityAttributes.GENERIC_MOVEMENT_SPEED, 0.23)
				.add(EntityAttributes.GENERIC_ATTACK_DAMAGE, 0.0)
				.add(EntityAttributes.GENERIC_FOLLOW_RANGE, 48.0)
				.add(EntityAttributes.GENERIC_ARMOR, 8.0)
				.add(EntityAttributes.GENERIC_KNOCKBACK_RESISTANCE, 1.0);
	}

	private int characterSoundTimer = 100;

	/** FNAF 1 audio cues: Chica rattling pots in the kitchen, Foxy sprinting and banging on a closed office door. */
	private void tickCharacterSounds(boolean watched) {
		if (--characterSoundTimer > 0) {
			return;
		}
		characterSoundTimer = 20;
		if (getType() == ModEntities.CHICA && PizzeriaManager.inKitchen(getWorld(), getBlockPos()) && random.nextInt(4) == 0) {
			getWorld().playSound(null, getBlockPos(), ModSounds.KITCHEN_POTS, SoundCategory.HOSTILE, 1.0f, 0.9f + random.nextFloat() * 0.2f);
			characterSoundTimer = 60 + random.nextInt(120);
		} else if (isFoxy() && !watched) {
			if (getVelocity().horizontalLengthSquared() > 0.02) {
				playSound(ModSounds.FOXY_RUN, 1.2f, 1.0f);
				characterSoundTimer = 55;
			}
			BlockPos door = closedSecurityDoorNear();
			if (door != null) {
				getWorld().playSound(null, door, ModSounds.FOXY_BANG, SoundCategory.HOSTILE, 1.5f, 0.9f + random.nextFloat() * 0.2f);
				characterSoundTimer = 40 + random.nextInt(40);
			}
		}
	}

	private BlockPos closedSecurityDoorNear() {
		for (BlockPos p : BlockPos.iterate(getBlockPos().add(-2, 0, -2), getBlockPos().add(2, 1, 2))) {
			BlockState s = getWorld().getBlockState(p);
			boolean mapDoor = s.getBlock() instanceof com.fnaf.horror.block.MapBlock && s.get(com.fnaf.horror.block.MapBlock.CLOSED);
			if (mapDoor || s.isOf(com.fnaf.horror.registry.ModBlocks.SECURITY_DOOR) && !s.get(net.minecraft.block.DoorBlock.OPEN)) {
				return p.toImmutable();
			}
		}
		return null;
	}

	private boolean isFoxy() {
		return getType() == ModEntities.FOXY;
	}

	private boolean isGolden() {
		return getType() == ModEntities.GOLDEN_FREDDY;
	}

	public boolean isFrozen() {
		return this.dataTracker.get(FROZEN);
	}

	@Override
	protected void initDataTracker() {
		super.initDataTracker();
		this.dataTracker.startTracking(FROZEN, false);
	}

	@Override
	protected void initGoals() {
		this.goalSelector.add(0, new SwimGoal(this));
		this.goalSelector.add(1, new StalkGoal());
		this.goalSelector.add(6, new WanderAroundFarGoal(this, 0.6) {
			@Override
			public boolean canStart() {
				return !nightControlled && !isFrozen() && !isGolden() && jumpscareTicks == 0 && super.canStart();
			}
		});
		this.targetSelector.add(1, new ActiveTargetGoal<>(this, PlayerEntity.class, 10, false, false, e -> !nightControlled && canHunt(e)));
	}

	private boolean canHunt(LivingEntity target) {
		return target instanceof ServerPlayerEntity player && !player.isCreative() && !player.isSpectator()
				&& !LobbyManager.isInLobby(player);
	}

	/** True while any (non-spectator, non-lobby) player has this animatronic on screen with a clear line of sight. */
	private boolean isWatched() {
		Vec3d center = getPos().add(0, modelHeight() * 0.6, 0);
		int light = getWorld().getLightLevel(BlockPos.ofFloored(center));
		for (ServerPlayerEntity p : ((ServerWorld) getWorld()).getPlayers()) {
			if (p.isSpectator() || LobbyManager.isInLobby(p) || p.squaredDistanceTo(this) > 48 * 48) {
				continue;
			}
			Vec3d to = center.subtract(p.getEyePos());
			double len = to.length();
			if (len < 1e-3) {
				return true;
			}
			// in the dark you only see what is close or what your flashlight shines on
			boolean visible = len < 3.0 || light >= 4 || FlashlightItem.litIn(p) != null && p.getRotationVec(1.0f).dotProduct(to) / len > 0.9;
			if (visible && p.getRotationVec(1.0f).dotProduct(to) / len > WATCH_COS && p.canSee(this)) {
				return true;
			}
		}
		return false;
	}

	@Override
	public void tick() {
		super.tick();
		if (getWorld().isClient) {
			return;
		}
		if (cooldown > 0) {
			cooldown--;
		}
		if (jumpscareTicks > 0) {
			tickJumpscare();
			return;
		}
		if (nightControlled) {
			// a puppet of the night: stays where NightManager put it until the next move, unless it is
			// chasing a player it saw or walking back to its node afterwards
			this.dataTracker.set(FROZEN, false);
			setTarget(null);
			if (nightChase != null && nightChase.isAlive()) {
				getLookControl().lookAt(nightChase, 40f, 40f);
				if (--nightRepath <= 0) {
					nightRepath = 5;
					getNavigation().startMovingTo(nightChase, isFoxy() ? 1.9 : 1.15);
				}
			} else if (nightReturn != null) {
				if (--nightRepath <= 0) {
					nightRepath = 20;
					getNavigation().startMovingTo(nightReturn.x, nightReturn.y, nightReturn.z, 1.0);
				}
			} else {
				getNavigation().stop();
			}
			if (getVelocity().horizontalLengthSquared() > 1.0e-4 && --servoTimer <= 0) {
				servoTimer = 20 + random.nextInt(25);
				playSound(ModSounds.SERVO, 0.7f, 0.85f + random.nextFloat() * 0.3f);
			}
			tickCharacterSounds(false);
			return;
		}
		boolean watched = isWatched();
		if (watched && !isFrozen()) {
			frozenYaw = getYaw();
		}
		this.dataTracker.set(FROZEN, watched);
		if (watched) {
			getNavigation().stop();
			setVelocity(0, getVelocity().y, 0);
			setYaw(frozenYaw);
			setBodyYaw(frozenYaw);
			setHeadYaw(frozenYaw);
		} else if (getVelocity().horizontalLengthSquared() > 1.0e-4 && --servoTimer <= 0) {
			servoTimer = 25 + random.nextInt(30);
			playSound(ModSounds.SERVO, 0.6f, 0.85f + random.nextFloat() * 0.3f);
		}

		tickCharacterSounds(watched);

		LivingEntity target = getTarget();
		if (isGolden()) {
			tickGolden(target, watched);
		}
		if (!watched && cooldown == 0 && target instanceof ServerPlayerEntity player && canHunt(player)
				&& squaredDistanceTo(player) < 2.3 * 2.3) {
			startJumpscare(player);
		}
	}

	/** Golden Freddy: blinks in behind the player when unseen, fades away when stared at. */
	private void tickGolden(LivingEntity target, boolean watched) {
		if (watched) {
			if (++stareTicks > 60) {
				stareTicks = 0;
				teleportAround(target, 18 + random.nextInt(10), false);
			}
			return;
		}
		stareTicks = 0;
		if (target instanceof ServerPlayerEntity player && canHunt(player) && --teleportTimer <= 0) {
			teleportTimer = 80 + random.nextInt(120);
			double dist = squaredDistanceTo(player) < 10 * 10 ? 1.6 : 4 + random.nextInt(4);
			teleportAround(player, dist, true);
		}
	}

	private void teleportAround(LivingEntity anchor, double dist, boolean behind) {
		if (anchor == null) {
			return;
		}
		Vec3d look = Vec3d.fromPolar(0, anchor.getYaw());
		double angle = behind ? 0 : random.nextDouble() * Math.PI * 2;
		Vec3d dir = behind ? look.multiply(-1) : new Vec3d(Math.cos(angle), 0, Math.sin(angle));
		Vec3d p = anchor.getPos().add(dir.multiply(dist));
		for (int dy : new int[]{0, 1, -1, 2, -2}) {
			double y = Math.floor(anchor.getY()) + dy;
			BlockPos below = BlockPos.ofFloored(p.x, y - 1, p.z);
			if (getWorld().getBlockState(below).isSolidBlock(getWorld(), below)
					&& getWorld().isSpaceEmpty(this, getDimensions(getPose()).getBoxAt(p.x, y, p.z))) {
				float yaw = (float) (MathHelper.atan2(anchor.getZ() - p.z, anchor.getX() - p.x) * (180 / Math.PI)) - 90f;
				requestTeleport(p.x, y, p.z);
				setYaw(yaw);
				setHeadYaw(yaw);
				setBodyYaw(yaw);
				playSound(ModSounds.STATIC, 0.8f, 0.8f + random.nextFloat() * 0.4f);
				return;
			}
		}
	}

	public boolean isJumpscaring() {
		return jumpscareTicks > 0;
	}

	public void startJumpscare(ServerPlayerEntity player) {
		jumpscareTicks = JUMPSCARE_TICKS;
		victim = player.getUuid();
		getNavigation().stop();
		this.noClip = true;
		setNoGravity(true);
		triggerAnim("attack", "attack");
		player.addStatusEffect(new StatusEffectInstance(StatusEffects.SLOWNESS, JUMPSCARE_TICKS + 5, 10, false, false));
		getWorld().playSound(player, getX(), getY(), getZ(), ModSounds.JUMPSCARE, SoundCategory.HOSTILE, 2.0f, 1.0f);
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeVarInt(getId());
		buf.writeVarInt(JUMPSCARE_TICKS);
		ServerPlayNetworking.send(player, JUMPSCARE_PACKET, buf);
	}

	private void tickJumpscare() {
		ServerPlayerEntity player = victim == null ? null : (ServerPlayerEntity) getWorld().getPlayerByUuid(victim);
		if (player == null || !player.isAlive()) {
			endJumpscare();
			return;
		}
		// stand right in the player's face, head at their eye level
		Vec3d facing = Vec3d.fromPolar(0, player.getYaw());
		Vec3d spot = player.getPos().add(facing.multiply(1.25));
		double y = player.getEyeY() - modelHeight() * 0.86;
		float yaw = player.getYaw() + 180f;
		requestTeleport(spot.x, y, spot.z);
		setYaw(yaw);
		setBodyYaw(yaw);
		setHeadYaw(yaw);
		setPitch(0);
		player.setVelocity(Vec3d.ZERO);
		player.velocityModified = true;
		if (--jumpscareTicks == 0) {
			player.damage(getDamageSources().mobAttack(this), 1000f);
			endJumpscare();
		}
	}

	private void endJumpscare() {
		jumpscareTicks = 0;
		victim = null;
		cooldown = 200;
		this.noClip = false;
		setNoGravity(false);
		setTarget(null);
		Vec3d back = Vec3d.fromPolar(0, getYaw()).multiply(-2.5);
		requestTeleport(getX() + back.x, getY(), getZ() + back.z);
	}

	@Override
	public boolean canImmediatelyDespawn(double distanceSquared) {
		return false;
	}

	@Override
	public boolean isPushable() {
		return jumpscareTicks == 0 && super.isPushable();
	}

	@Override
	protected SoundEvent getAmbientSound() {
		if (isFrozen()) {
			return null;
		}
		return getType() == ModEntities.FREDDY && random.nextInt(3) == 0 ? ModSounds.LAUGH : ModSounds.AMBIENT;
	}

	@Override
	public int getMinAmbientSoundDelay() {
		return 320;
	}

	@Override
	protected SoundEvent getHurtSound(DamageSource source) {
		return ModSounds.HURT;
	}

	@Override
	protected SoundEvent getDeathSound() {
		return ModSounds.DEATH;
	}

	@Override
	protected void playStepSound(BlockPos pos, BlockState state) {
		this.playSound(ModSounds.STEP, isFoxy() ? 0.9f : 0.7f, 0.85f + random.nextFloat() * 0.2f);
	}

	/** Hunts its target, pausing whenever it is being watched. */
	private class StalkGoal extends Goal {
		private int repath;

		StalkGoal() {
			setControls(EnumSet.of(Control.MOVE, Control.LOOK));
		}

		@Override
		public boolean canStart() {
			LivingEntity t = getTarget();
			return !nightControlled && t != null && t.isAlive() && jumpscareTicks == 0;
		}

		@Override
		public boolean shouldContinue() {
			return canStart();
		}

		@Override
		public void stop() {
			getNavigation().stop();
		}

		@Override
		public void tick() {
			LivingEntity t = getTarget();
			if (t == null || isFrozen() || isGolden()) {
				getNavigation().stop();
				return;
			}
			getLookControl().lookAt(t, 20f, 20f);
			if (--repath <= 0) {
				repath = 8;
				getNavigation().startMovingTo(t, isFoxy() ? 2.1 : 1.05);
			}
		}
	}

	@Override
	public void registerControllers(AnimatableManager.ControllerRegistrar controllers) {
		controllers.add(new AnimationController<>(this, "movement", 3, state -> {
			// a watched animatronic freezes mid-pose
			state.getController().setAnimationSpeed(isFrozen() ? 0.0 : 1.0);
			return state.setAndContinue(state.isMoving() ? WALK : IDLE);
		}));
		controllers.add(new AnimationController<>(this, "attack", 1, state -> PlayState.STOP)
				.triggerableAnim("attack", ATTACK));
	}

	@Override
	public AnimatableInstanceCache getAnimatableInstanceCache() {
		return cache;
	}
}
