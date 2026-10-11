package com.fnaf.horror.item;

import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.block.LightBlock;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.hit.HitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Vec3d;
import net.minecraft.world.RaycastContext;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/**
 * Vanilla has no dynamic lights, so the beam is faked server side: an invisible light block sits in the
 * air cell where the flashlight's ray hits, plus a dimmer one halfway along the beam. They follow the
 * ray every tick and are removed as soon as the flashlight is off or put away.
 */
public final class FlashlightLights {
	private static final double RANGE = 26.0;
	private static final Map<UUID, Placed> PLACED = new HashMap<>();

	private record Placed(ServerWorld world, BlockPos spot, BlockPos mid) {
	}

	public static void init() {
		ServerTickEvents.END_SERVER_TICK.register(FlashlightLights::tick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			PLACED.values().forEach(FlashlightLights::remove);
			PLACED.clear();
		});
	}

	private static void tick(MinecraftServer server) {
		Map<UUID, Placed> next = new HashMap<>();
		for (ServerPlayerEntity player : server.getPlayerManager().getPlayerList()) {
			if (!player.isAlive() || player.isSpectator() || FlashlightItem.litIn(player) == null) {
				continue;
			}
			ServerWorld world = player.getServerWorld();
			Vec3d eye = player.getEyePos();
			Vec3d dir = player.getRotationVec(1.0f);
			Vec3d end = eye.add(dir.multiply(RANGE));
			BlockHitResult hit = world.raycast(new RaycastContext(eye, end, RaycastContext.ShapeType.COLLIDER,
					RaycastContext.FluidHandling.NONE, player));
			BlockPos spot = hit.getType() == HitResult.Type.BLOCK ? hit.getBlockPos().offset(hit.getSide()) : BlockPos.ofFloored(end);
			spot = emptyNear(world, spot, eye, hit.getPos());
			double dist = hit.getPos().distanceTo(eye);
			BlockPos mid = dist > 8 ? BlockPos.ofFloored(eye.add(dir.multiply(dist * 0.5))) : null;
			if (mid != null && !world.getBlockState(mid).isAir() && !world.getBlockState(mid).isOf(Blocks.LIGHT)) {
				mid = null;
			}
			next.put(player.getUuid(), new Placed(world, spot, mid));
		}
		// drop lights that moved or whose owner switched off, then place the current ones
		for (Map.Entry<UUID, Placed> e : PLACED.entrySet()) {
			Placed now = next.get(e.getKey());
			Placed old = e.getValue();
			if (now == null || now.world != old.world || !now.spot.equals(old.spot)) {
				removeAt(old.world, old.spot);
			}
			if (now == null || now.world != old.world || old.mid != null && !old.mid.equals(now.mid)) {
				removeAt(old.world, old.mid);
			}
		}
		PLACED.clear();
		for (Map.Entry<UUID, Placed> e : next.entrySet()) {
			Placed p = e.getValue();
			placeAt(p.world, p.spot, 15);
			placeAt(p.world, p.mid, 9);
			PLACED.put(e.getKey(), p);
		}
	}

	/**
	 * Map cells carry real geometry, and changing their state re-meshes the whole chunk section, so the
	 * beam prefers an empty cell a little closer to the player when the hit cell is a map block.
	 */
	private static BlockPos emptyNear(ServerWorld world, BlockPos spot, Vec3d eye, Vec3d hit) {
		if (!(world.getBlockState(spot).getBlock() instanceof com.fnaf.horror.block.MapBlock)) {
			return spot;
		}
		Vec3d back = eye.subtract(hit).normalize().multiply(0.5);
		Vec3d p = hit;
		for (int i = 0; i < 6; i++) {
			p = p.add(back);
			BlockPos b = BlockPos.ofFloored(p);
			BlockState s = world.getBlockState(b);
			if (s.isAir() || s.isOf(Blocks.LIGHT)) {
				return b;
			}
		}
		return spot;
	}

	private static void placeAt(ServerWorld world, BlockPos pos, int level) {
		if (pos == null || !world.isInBuildLimit(pos)) {
			return;
		}
		BlockState state = world.getBlockState(pos);
		if (state.getBlock() instanceof com.fnaf.horror.block.MapBlock) {
			if (state.get(com.fnaf.horror.block.MapBlock.FLASH) != level) {
				world.setBlockState(pos, state.with(com.fnaf.horror.block.MapBlock.FLASH, level), Block.NOTIFY_LISTENERS);
			}
			return;
		}
		if (state.isAir() || state.isOf(Blocks.LIGHT) && state.get(LightBlock.LEVEL_15) != level) {
			world.setBlockState(pos, Blocks.LIGHT.getDefaultState().with(LightBlock.LEVEL_15, level), Block.NOTIFY_LISTENERS);
		}
	}

	private static void removeAt(ServerWorld world, BlockPos pos) {
		if (pos == null) {
			return;
		}
		BlockState state = world.getBlockState(pos);
		if (state.getBlock() instanceof com.fnaf.horror.block.MapBlock && state.get(com.fnaf.horror.block.MapBlock.FLASH) > 0) {
			world.setBlockState(pos, state.with(com.fnaf.horror.block.MapBlock.FLASH, 0), Block.NOTIFY_LISTENERS);
			return;
		}
		if (state.isOf(Blocks.LIGHT)) {
			world.setBlockState(pos, Blocks.AIR.getDefaultState(), Block.NOTIFY_LISTENERS);
		}
	}

	private static void remove(Placed p) {
		removeAt(p.world, p.spot);
		removeAt(p.world, p.mid);
	}

	private FlashlightLights() {
	}
}
