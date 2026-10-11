package com.fnaf.horror.block;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvents;
import net.minecraft.state.StateManager;
import net.minecraft.state.property.BooleanProperty;
import net.minecraft.util.math.BlockBox;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.random.Random;

/**
 * Fluorescent ceiling panel. POWERED follows the generator; LIT is what is actually shining, so a
 * FLICKER panel can blink off for a few ticks on its own while it stays powered.
 */
public class CeilingLightBlock extends Block {
	public static final BooleanProperty POWERED = BooleanProperty.of("powered");
	public static final BooleanProperty LIT = BooleanProperty.of("lit");
	public static final BooleanProperty FLICKER = BooleanProperty.of("flicker");

	public CeilingLightBlock(Settings settings) {
		super(settings);
		setDefaultState(getDefaultState().with(POWERED, true).with(LIT, true).with(FLICKER, false));
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(POWERED, LIT, FLICKER);
	}

	@Override
	public void scheduledTick(BlockState state, ServerWorld world, BlockPos pos, Random random) {
		if (!state.get(FLICKER) || !state.get(POWERED)) {
			return;
		}
		boolean lit = !state.get(LIT);
		world.setBlockState(pos, state.with(LIT, lit), Block.NOTIFY_LISTENERS);
		if (!lit && random.nextInt(3) == 0) {
			world.playSound(null, pos, SoundEvents.BLOCK_REDSTONE_TORCH_BURNOUT, SoundCategory.BLOCKS, 0.15f, 1.8f);
		}
		// short blackouts, long stretches of light, sometimes a burst of quick blinks
		int delay = lit ? (random.nextInt(4) == 0 ? 2 + random.nextInt(4) : 30 + random.nextInt(200)) : 2 + random.nextInt(5);
		world.scheduleBlockTick(pos, this, delay);
	}

	/** Switches every panel inside the box on or off (generator started / failed). */
	public static int setPower(ServerWorld world, BlockBox box, boolean on) {
		int count = 0;
		BlockPos.Mutable pos = new BlockPos.Mutable();
		for (int x = box.getMinX(); x <= box.getMaxX(); x++) {
			for (int y = box.getMinY(); y <= box.getMaxY(); y++) {
				for (int z = box.getMinZ(); z <= box.getMaxZ(); z++) {
					BlockState state = world.getBlockState(pos.set(x, y, z));
					if (state.getBlock() instanceof MapBlock && state.get(MapBlock.LAMP)) {
						count++;
						if (state.get(MapBlock.POWERED) != on) {
							world.setBlockState(pos, state.with(MapBlock.POWERED, on), Block.NOTIFY_LISTENERS);
						}
						continue;
					}
					if (!(state.getBlock() instanceof CeilingLightBlock light)) {
						continue;
					}
					count++;
					if (state.get(POWERED) != on || state.get(LIT) != on) {
						world.setBlockState(pos, state.with(POWERED, on).with(LIT, on), Block.NOTIFY_LISTENERS);
					}
					if (on && state.get(FLICKER)) {
						world.scheduleBlockTick(pos.toImmutable(), light, 20 + world.random.nextInt(100));
					}
				}
			}
		}
		return count;
	}
}
