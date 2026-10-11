package com.fnaf.horror.block;

import com.fnaf.horror.pizzeria.MapCollision;
import com.fnaf.horror.registry.ModSounds;
import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.block.LightBlock;
import net.minecraft.block.ShapeContext;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.state.StateManager;
import net.minecraft.state.property.BooleanProperty;
import net.minecraft.state.property.IntProperty;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Hand;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.random.Random;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.util.shape.VoxelShapes;
import net.minecraft.world.BlockView;
import net.minecraft.world.World;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * One cell of the downloaded FNAF 1 map. It draws its piece of the real 3D model (client: MapModel) and
 * collides with the boxes computed from that geometry (MapCollision), both looked up by position.
 * LAMP cells hold a ceiling lamp and shine while POWERED; FLASH is the flashlight beam passing through.
 * CLOSED is used by the office door cells; the red wall buttons close/open the nearest door and the
 * white ones light up the hall outside it for a few seconds.
 */
public class MapBlock extends Block {
	public static final BooleanProperty LAMP = BooleanProperty.of("lamp");
	public static final BooleanProperty POWERED = BooleanProperty.of("powered");
	public static final IntProperty FLASH = IntProperty.of("flash", 0, 15);
	public static final BooleanProperty CLOSED = BooleanProperty.of("closed");
	private static final int HALL_LIGHT_TICKS = 70;
	/** Thin pick box in the middle of door / button cells so they can be clicked when open. */
	private static final VoxelShape DOOR_PICK = Block.createCuboidShape(1, 1, 1, 15, 15, 15);
	/** Light-button cell -> the hall cells it lit, switched off by the scheduled tick. */
	private static final Map<BlockPos, List<BlockPos>> LIT_HALLS = new HashMap<>();

	public MapBlock(Settings settings) {
		super(settings);
		setDefaultState(getDefaultState().with(LAMP, false).with(POWERED, false).with(FLASH, 0).with(CLOSED, false));
	}

	public static int luminance(BlockState state) {
		return Math.max(state.get(FLASH), state.get(LAMP) && state.get(POWERED) ? 13 : 0);
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(LAMP, POWERED, FLASH, CLOSED);
	}

	@Override
	public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		// buttons and doorways stay clickable even when the door is open (no collision there)
		if ((MapCollision.flags(pos) & (MapCollision.DOOR_BUTTON | MapCollision.LIGHT_BUTTON | MapCollision.ROOM_DOOR)) != 0) {
			return VoxelShapes.union(MapCollision.shape(pos, state.get(CLOSED)), DOOR_PICK);
		}
		return MapCollision.shape(pos, state.get(CLOSED));
	}

	/**
	 * For mob pathfinding a map cell is open when nothing blocks its middle (vanilla treats every non-full
	 * cube as open, so animatronics would try to walk through tables and could not stand on the stage).
	 */
	@Override
	public boolean canPathfindThrough(BlockState state, BlockView world, BlockPos pos, net.minecraft.entity.ai.pathing.NavigationType type) {
		if (type != net.minecraft.entity.ai.pathing.NavigationType.LAND) {
			return false;
		}
		for (net.minecraft.util.math.Box b : getCollisionShape(state, world, pos, ShapeContext.absent()).getBoundingBoxes()) {
			if (b.maxY > 0.2 && b.minX < 0.7 && b.maxX > 0.3 && b.minZ < 0.7 && b.maxZ > 0.3) {
				return false;
			}
		}
		return true;
	}

	@Override
	public VoxelShape getCollisionShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		return MapCollision.shape(pos, state.get(CLOSED));
	}

	@Override
	public VoxelShape getCullingShape(BlockState state, BlockView world, BlockPos pos) {
		return VoxelShapes.empty();
	}

	@Override
	public boolean isTransparent(BlockState state, BlockView world, BlockPos pos) {
		return true;
	}

	@Override
	public float getAmbientOcclusionLightLevel(BlockState state, BlockView world, BlockPos pos) {
		return 1.0f;
	}

	@Override
	public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, Hand hand, BlockHitResult hit) {
		int flags = MapCollision.flags(pos);
		if ((flags & (MapCollision.DOOR_BUTTON | MapCollision.LIGHT_BUTTON | MapCollision.ROOM_DOOR)) == 0) {
			return ActionResult.PASS;           // the office doors themselves only move by their buttons
		}
		if (world.isClient) {
			return ActionResult.SUCCESS;
		}
		// clicking an ordinary door (not the office ones) opens / closes it
		if ((flags & (MapCollision.DOOR_BUTTON | MapCollision.LIGHT_BUTTON)) == 0) {
			List<BlockPos> door = nearestDoor(pos);
			if (!door.isEmpty()) {
				setDoor(world, door, !world.getBlockState(door.get(0)).get(CLOSED));
			}
			return ActionResult.CONSUME;
		}
		if (com.fnaf.horror.night.NightManager.buttonsBlocked(pos)) {
			world.playSound(null, pos, ModSounds.BUTTON_CLICK, SoundCategory.BLOCKS, 0.6f, 0.6f);
			return ActionResult.CONSUME;
		}
		List<BlockPos> door = nearestDoor(pos);
		if (door.isEmpty()) {
			return ActionResult.CONSUME;
		}
		world.playSound(null, pos, ModSounds.BUTTON_CLICK, SoundCategory.BLOCKS, 1.0f, 1.0f);
		// a cell can hold both buttons: the door button sits above the light button
		boolean doorButton = (flags & MapCollision.DOOR_BUTTON) != 0
				&& ((flags & MapCollision.LIGHT_BUTTON) == 0 || hit.getPos().y - pos.getY() > 0.85);
		if (doorButton) {
			boolean close = !world.getBlockState(door.get(0)).get(CLOSED);
			setDoor(world, door, close);
		} else {
			lightHall((ServerWorld) world, pos, door);
		}
		return ActionResult.CONSUME;
	}

	/** Closes or opens one office door (all cells of the door nearest to the button). */
	public static void setDoor(World world, List<BlockPos> door, boolean close) {
		for (BlockPos p : door) {
			BlockState s = world.getBlockState(p);
			if (s.getBlock() instanceof MapBlock && s.get(CLOSED) != close) {
				world.setBlockState(p, s.with(CLOSED, close), Block.NOTIFY_ALL);
			}
		}
		world.playSound(null, door.get(0), close ? ModSounds.DOOR_CLOSE : ModSounds.DOOR_OPEN, SoundCategory.BLOCKS, 1.2f, 1.0f);
		com.fnaf.horror.FnafHorror.LOGGER.debug("Door at {} {}", door.get(0), close ? "closed" : "opened");
	}

	/** All cells of the door closest to pos (door cells touching each other form one door). */
	public static List<BlockPos> nearestDoor(BlockPos pos) {
		List<BlockPos> all = MapCollision.doorCells();
		BlockPos best = all.stream().min(Comparator.comparingDouble(p -> p.getSquaredDistance(pos))).orElse(null);
		List<BlockPos> door = new ArrayList<>();
		if (best == null || best.getSquaredDistance(pos) > 64) {
			return door;
		}
		door.add(best);
		for (int i = 0; i < door.size(); i++) {
			BlockPos c = door.get(i);
			for (BlockPos p : all) {
				// same door = touching cells in the door's plane (neighbouring doors only meet at corners)
				if (!door.contains(p) && Math.abs(p.getX() - c.getX()) <= 1 && Math.abs(p.getY() - c.getY()) <= 1
						&& Math.abs(p.getZ() - c.getZ()) <= 1 && (p.getX() == best.getX() || p.getZ() == best.getZ())) {
					door.add(p);
				}
			}
		}
		door.sort(Comparator.comparingInt(BlockPos::getY));
		return door;
	}

	/** Lights the hall cells just outside the door (the side away from the button) for a few seconds. */
	private static void lightHall(ServerWorld world, BlockPos button, List<BlockPos> door) {
		BlockPos d = door.get(0);
		int dx = Integer.signum(d.getX() - button.getX());
		int dz = Integer.signum(d.getZ() - button.getZ());
		boolean alongX = door.stream().allMatch(p -> p.getX() == d.getX());
		List<BlockPos> lit = new ArrayList<>();
		for (BlockPos p : door) {
			if (p.getY() != d.getY() && p.getY() != d.getY() + 1) {
				continue;
			}
			for (int step = 1; step <= 3; step += 2) {
				BlockPos q = alongX ? p.add(dx * step, 0, 0) : p.add(0, 0, dz * step);
				BlockState s = world.getBlockState(q);
				if (s.getBlock() instanceof MapBlock) {
					world.setBlockState(q, s.with(FLASH, 14), Block.NOTIFY_LISTENERS);
					lit.add(q);
				} else if (s.isAir()) {
					world.setBlockState(q, Blocks.LIGHT.getDefaultState().with(LightBlock.LEVEL_15, 14), Block.NOTIFY_LISTENERS);
					lit.add(q);
				}
			}
		}
		LIT_HALLS.computeIfAbsent(button.toImmutable(), k -> new ArrayList<>()).addAll(lit);
		world.playSound(null, button, ModSounds.DOOR_LIGHT_BUZZ, SoundCategory.BLOCKS, 0.9f, 1.0f);
		world.scheduleBlockTick(button, world.getBlockState(button).getBlock(), HALL_LIGHT_TICKS);
	}

	@Override
	public void scheduledTick(BlockState state, ServerWorld world, BlockPos pos, Random random) {
		List<BlockPos> lit = LIT_HALLS.remove(pos);
		if (lit == null) {
			return;
		}
		for (BlockPos q : lit) {
			BlockState s = world.getBlockState(q);
			if (s.getBlock() instanceof MapBlock) {
				world.setBlockState(q, s.with(FLASH, 0), Block.NOTIFY_LISTENERS);
			} else if (s.isOf(Blocks.LIGHT)) {
				world.setBlockState(q, Blocks.AIR.getDefaultState(), Block.NOTIFY_LISTENERS);
			}
		}
	}
}
