package com.fnaf.horror.night;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.block.GeneratorBlock;
import com.fnaf.horror.pizzeria.MapCollision;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModBlocks;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.block.BlockState;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.item.Item;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockBox;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.Direction;
import net.minecraft.util.math.Vec3d;
import net.minecraft.util.math.random.Random;
import net.minecraft.util.shape.VoxelShape;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * Blackout refuelling: when the power runs out, petrol cans turn up around the pizzeria. Carried to the
 * generator in the supply closet and poured in (a minigame on the client, see RefuelScreen) they bring
 * the power back. Spots are picked at runtime from the map collision: floor cells a player can walk to
 * from the office (side-room doors count as open) that hold no map geometry.
 */
public final class Fuel {
	/** S2C: generator pos, cans the player carries, current power. Opens the refuel minigame. */
	public static final Identifier OPEN = FnafHorror.id("refuel_open");
	/** C2S: cans used, fuel poured (0..cans used, 1 = a full can into the tank). */
	public static final Identifier POUR = FnafHorror.id("refuel");
	public static final int CANS_PER_BLACKOUT = 3;
	public static final float POWER_PER_CAN = 15f;

	private static List<BlockPos> floor;
	private static final Map<UUID, BlockPos> OPEN_AT = new HashMap<>();

	public static void init() {
		ServerPlayNetworking.registerGlobalReceiver(POUR, (server, player, handler, buf, responseSender) -> {
			int cans = buf.readInt();
			float fuel = buf.readFloat();
			server.execute(() -> pour(player, cans, fuel));
		});
	}

	public static Item canItem() {
		return ModBlocks.GAS_CAN.asItem();
	}

	// ------------------------------------------------------------------ generator

	/** Puts the generator in the supply closet (every night start; a rebuild clears it). */
	static BlockPos placeGenerator(ServerWorld world) {
		BlockBox b = PizzeriaManager.bounds();
		for (BlockPos p : BlockPos.iterate(b.getMinX(), b.getMinY(), b.getMinZ(), b.getMaxX(), b.getMaxY(), b.getMaxZ())) {
			if (world.getBlockState(p).isOf(ModBlocks.GENERATOR)) {
				world.removeBlock(p, false);          // re-placed below (the spot may have moved)
			}
		}
		NightLayout.Node supply = NightLayout.node("supply");
		Vec3d want = supply != null ? supply.pos() : Vec3d.ofCenter(PizzeriaManager.ORIGIN.add(12, 1, 33));
		Set<BlockPos> walk = new HashSet<>(floor(world));
		BlockPos best = null;
		double bestScore = Double.MAX_VALUE;
		for (BlockPos p : walk) {
			if (!emptyCell(world, p)) {
				continue;
			}
			int walls = 0;
			boolean doorway = false;
			for (Direction d : Direction.Type.HORIZONTAL) {
				BlockPos n = p.offset(d);
				if (!walk.contains(n)) {
					walls++;
				}
				doorway |= (MapCollision.flags(n) & MapCollision.ROOM_DOOR) != 0 || (MapCollision.flags(p) & MapCollision.ROOM_DOOR) != 0;
			}
			if (doorway || walls == 0 || walls >= 3) {
				continue;                  // never in a doorway, in the middle of a room or at a dead end
			}
			double score = Vec3d.ofBottomCenter(p).squaredDistanceTo(want.x, p.getY(), want.z) - walls * 4;
			if (score < bestScore) {
				bestScore = score;
				best = p;
			}
		}
		if (best == null) {
			return null;
		}
		// face the free side so the player stands in front of it
		Direction facing = Direction.SOUTH;
		for (Direction d : Direction.Type.HORIZONTAL) {
			if (walk.contains(best.offset(d))) {
				facing = d;
				break;
			}
		}
		world.setBlockState(best, ModBlocks.GENERATOR.getDefaultState().with(HorizontalFacingBlock.FACING, facing)
				.with(GeneratorBlock.RUNNING, false));
		FnafHorror.LOGGER.info("Generator placed at {}", best.subtract(PizzeriaManager.ORIGIN));
		return best;
	}

	// ------------------------------------------------------------------ cans

	/** Drops `count` cans on walkable floor spread over the building, away from the office and the generator. */
	static List<BlockPos> spawnCans(ServerWorld world, int count, BlockPos generator) {
		List<BlockPos> spots = new ArrayList<>(floor(world));
		Random random = world.random;
		NightLayout.Node office = NightLayout.node("office_left");
		Vec3d officePos = office != null ? office.pos() : Vec3d.ofCenter(PizzeriaManager.ORIGIN);
		List<BlockPos> placed = new ArrayList<>();
		for (int tries = 0; tries < 4000 && placed.size() < count && !spots.isEmpty(); tries++) {
			BlockPos p = spots.get(random.nextInt(spots.size()));
			double minGap = tries < 2000 ? 9 : 5;
			if (!emptyCell(world, p)
					|| Vec3d.ofCenter(p).squaredDistanceTo(officePos.x, p.getY() + 0.5, officePos.z) < 8 * 8
					|| generator != null && p.getSquaredDistance(generator) < 8 * 8
					|| placed.stream().anyMatch(q -> q.getSquaredDistance(p) < minGap * minGap)) {
				continue;
			}
			Direction facing = Direction.Type.HORIZONTAL.random(random);
			world.setBlockState(p, ModBlocks.GAS_CAN.getDefaultState().with(HorizontalFacingBlock.FACING, facing));
			placed.add(p.toImmutable());
		}
		FnafHorror.LOGGER.info("Petrol cans at {}", placed.stream().map(p -> p.subtract(PizzeriaManager.ORIGIN)).toList());
		return placed;
	}

	/** Removes every can lying in the building. */
	static void clearCans(ServerWorld world) {
		BlockBox b = PizzeriaManager.bounds();
		for (BlockPos p : BlockPos.iterate(b.getMinX(), b.getMinY(), b.getMinZ(), b.getMaxX(), b.getMaxY(), b.getMaxZ())) {
			if (world.getBlockState(p).isOf(ModBlocks.GAS_CAN)) {
				world.removeBlock(p, false);
			}
		}
	}

	private static boolean emptyCell(ServerWorld world, BlockPos p) {
		BlockState s = world.getBlockState(p);
		return s.isAir() && world.getBlockState(p.up()).isAir();
	}

	/**
	 * Rooms of the building in map cells {x1, z1, x2, z2} (see tools/pizzeria/map_rooms.png): dining area,
	 * west/east halls, supply closet, backstage, restrooms + kitchen, office. The source map lies on a big
	 * ground plane, so everything outside these is bare floor around the building.
	 */
	private static final int[][] ROOMS = {{11, 14, 39, 30}, {16, 30, 22, 44}, {28, 30, 34, 44}, {11, 31, 15, 36},
			{4, 10, 10, 26}, {40, 14, 44, 30}, {23, 38, 27, 44}};

	/** Ground-floor cells (absolute, y = floor + 1) reachable on foot from the office. */
	private static synchronized List<BlockPos> floor(ServerWorld world) {
		if (floor != null) {
			return floor;
		}
		NightLayout.Node office = NightLayout.node("office_left");
		BlockPos o = PizzeriaManager.ORIGIN;
		BlockPos start = office != null ? BlockPos.ofFloored(office.pos().x, o.getY() + 1, office.pos().z) : o.add(25, 1, 41);
		Set<BlockPos> seen = new HashSet<>();
		ArrayDeque<BlockPos> todo = new ArrayDeque<>();
		seen.add(start);
		todo.add(start);
		while (!todo.isEmpty()) {
			BlockPos p = todo.poll();
			for (Direction d : Direction.Type.HORIZONTAL) {
				BlockPos n = p.offset(d);
				if (!seen.contains(n) && walkable(n) && canCross(p, n, d.getAxis())) {
					seen.add(n);
					todo.add(n);
				}
			}
		}
		floor = new ArrayList<>(seen);
		FnafHorror.LOGGER.info("{} walkable floor cells for petrol cans", floor.size());
		return floor;
	}

	private static boolean inRooms(BlockPos p) {
		int x = p.getX() - PizzeriaManager.ORIGIN.getX(), z = p.getZ() - PizzeriaManager.ORIGIN.getZ();
		for (int[] r : ROOMS) {
			if (x >= r[0] && x <= r[2] && z >= r[1] && z <= r[3]) {
				return true;
			}
		}
		return false;
	}

	private static boolean walkable(BlockPos p) {
		if (!inRooms(p) || !solidFloor(p.down())) {
			return false;
		}
		for (int dy = 0; dy < 2; dy++) {
			BlockPos c = p.up(dy);
			if ((MapCollision.flags(c) & MapCollision.ROOM_DOOR) != 0) {
				continue;                  // side-room doors can be opened
			}
			if (blocksMiddle(MapCollision.shape(c, false), dy == 0 ? 0.6 : 0.0)) {
				return false;
			}
		}
		return true;
	}

	/** A wall plane running through either cell (anywhere inside it) blocks the step between them. */
	private static boolean canCross(BlockPos a, BlockPos b, Direction.Axis axis) {
		for (int dy = 0; dy < 2; dy++) {
			for (BlockPos c : new BlockPos[]{a.up(dy), b.up(dy)}) {
				if ((MapCollision.flags(c) & MapCollision.ROOM_DOOR) != 0) {
					continue;
				}
				for (Box box : MapCollision.shape(c, false).getBoundingBoxes()) {
					boolean across = axis == Direction.Axis.X ? box.minZ < 0.31 && box.maxZ > 0.69 : box.minX < 0.31 && box.maxX > 0.69;
					if (across && box.maxY > (dy == 0 ? 0.6 : 0.0)) {
						return false;
					}
				}
			}
		}
		return true;
	}

	private static boolean solidFloor(BlockPos p) {
		VoxelShape s = MapCollision.shape(p, false);
		return !s.isEmpty() && s.getMax(Direction.Axis.Y) > 0.9;
	}

	/** True when a box covers the middle of the cell above minTop (low steps can be walked over). */
	private static boolean blocksMiddle(VoxelShape s, double minTop) {
		for (Box box : s.getBoundingBoxes()) {
			if (box.maxY > minTop && box.minX < 0.69 && box.maxX > 0.31 && box.minZ < 0.69 && box.maxZ > 0.31) {
				return true;
			}
		}
		return false;
	}

	// ------------------------------------------------------------------ minigame

	/** Generator used during a night: opens the minigame when the player carries cans. */
	public static void useGenerator(ServerPlayerEntity player, BlockPos generator) {
		int cans = player.getInventory().count(canItem());
		if (cans == 0) {
			player.sendMessage(net.minecraft.text.Text.translatable(NightManager.isBlackout()
					? "message.fnaf.generator_need_fuel" : "message.fnaf.generator_night").formatted(net.minecraft.util.Formatting.YELLOW), true);
			return;
		}
		if (NightManager.power() >= 99.5f) {
			player.sendMessage(net.minecraft.text.Text.translatable("message.fnaf.generator_full"), true);
			return;
		}
		OPEN_AT.put(player.getUuid(), generator.toImmutable());
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeBlockPos(generator);
		buf.writeInt(cans);
		buf.writeFloat(NightManager.power());
		ServerPlayNetworking.send(player, OPEN, buf);
	}

	private static void pour(ServerPlayerEntity player, int cans, float fuel) {
		BlockPos generator = OPEN_AT.remove(player.getUuid());
		if (generator == null || !NightManager.isActive() || !player.isAlive()
				|| player.squaredDistanceTo(Vec3d.ofCenter(generator)) > 6 * 6) {
			return;
		}
		cans = Math.min(cans, player.getInventory().count(canItem()));
		if (cans <= 0) {
			return;
		}
		fuel = Math.max(0, Math.min(fuel, cans));
		int left = cans;
		for (int i = 0; i < player.getInventory().size() && left > 0; i++) {
			var stack = player.getInventory().getStack(i);
			if (stack.isOf(canItem())) {
				int take = Math.min(left, stack.getCount());
				stack.decrement(take);
				left -= take;
			}
		}
		NightManager.refuel((ServerWorld) player.getWorld(), generator, fuel * POWER_PER_CAN, player);
	}

	private Fuel() {
	}
}
