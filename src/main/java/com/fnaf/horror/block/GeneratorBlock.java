package com.fnaf.horror.block;

import com.fnaf.horror.item.FlashlightItem;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModBlocks;
import com.fnaf.horror.registry.ModSounds;
import net.minecraft.block.Block;
import net.minecraft.block.BlockRenderType;
import net.minecraft.block.BlockState;
import net.minecraft.block.BlockWithEntity;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.block.ShapeContext;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.block.entity.BlockEntityTicker;
import net.minecraft.block.entity.BlockEntityType;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.ItemPlacementContext;
import net.minecraft.item.ItemStack;
import net.minecraft.particle.ParticleTypes;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.state.StateManager;
import net.minecraft.state.property.BooleanProperty;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.util.math.Vec3d;
import net.minecraft.util.math.random.Random;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.world.BlockView;
import net.minecraft.world.World;

/**
 * Portable generator that powers the ceiling lights around it (the whole pizzeria when it stands inside it).
 * Use it to pull the starter cord (it takes a few tries), sneak-use to switch it off, use it with a
 * flashlight in hand to recharge the flashlight. In the pizzeria it stalls every few minutes.
 */
public class GeneratorBlock extends BlockWithEntity {
	public static final BooleanProperty RUNNING = BooleanProperty.of("running");
	private static final VoxelShape SHAPE = Block.createCuboidShape(0, 0, 0, 16, 12, 16);

	public GeneratorBlock(Settings settings) {
		super(settings);
		setDefaultState(getDefaultState().with(HorizontalFacingBlock.FACING, Direction.SOUTH).with(RUNNING, true));
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(HorizontalFacingBlock.FACING, RUNNING);
	}

	@Override
	public BlockState getPlacementState(ItemPlacementContext ctx) {
		return getDefaultState().with(HorizontalFacingBlock.FACING, ctx.getHorizontalPlayerFacing().getOpposite()).with(RUNNING, false);
	}

	@Override
	public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		return SHAPE;
	}

	@Override
	public BlockRenderType getRenderType(BlockState state) {
		return BlockRenderType.ENTITYBLOCK_ANIMATED;
	}

	@Override
	public BlockEntity createBlockEntity(BlockPos pos, BlockState state) {
		return new GeneratorBlockEntity(pos, state);
	}

	@Override
	public <T extends BlockEntity> BlockEntityTicker<T> getTicker(World world, BlockState state, BlockEntityType<T> type) {
		return world.isClient ? null : checkType(type, ModBlocks.GENERATOR_ENTITY, GeneratorBlockEntity::serverTick);
	}

	@Override
	public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, Hand hand, BlockHitResult hit) {
		if (world.isClient) {
			return ActionResult.SUCCESS;
		}
		if (!(world.getBlockEntity(pos) instanceof GeneratorBlockEntity generator)) {
			return ActionResult.PASS;
		}
		ItemStack held = player.getStackInHand(hand);
		boolean running = state.get(RUNNING);
		// during a FNAF night the generator only takes petrol (the refuel minigame)
		if (inPizzeria(world) && com.fnaf.horror.night.NightManager.isActive() && !(held.getItem() instanceof FlashlightItem && running)) {
			com.fnaf.horror.night.Fuel.useGenerator((net.minecraft.server.network.ServerPlayerEntity) player, pos);
			return ActionResult.CONSUME;
		}
		if (held.getItem() instanceof FlashlightItem) {
			if (running) {
				held.setDamage(0);
				world.playSound(null, pos, ModSounds.FLASHLIGHT_CLICK, SoundCategory.BLOCKS, 1.0f, 0.6f);
				player.sendMessage(Text.translatable("message.fnaf.flashlight_charged").formatted(Formatting.GREEN), true);
			} else {
				player.sendMessage(Text.translatable("message.fnaf.generator_off").formatted(Formatting.RED), true);
			}
			return ActionResult.CONSUME;
		}
		if (running) {
			if (player.isSneaking()) {
				generator.stop(false);
			} else {
				player.sendMessage(Text.translatable("message.fnaf.generator_running"), true);
			}
			return ActionResult.CONSUME;
		}
		generator.pull(player);
		return ActionResult.CONSUME;
	}

	@Override
	public void randomDisplayTick(BlockState state, World world, BlockPos pos, Random random) {
		if (!state.get(RUNNING)) {
			return;
		}
		// exhaust tip of the mesh, relative to the block centre for a south-facing generator
		Direction facing = state.get(HorizontalFacingBlock.FACING);
		Vec3d local = new Vec3d(0.06, 0.32, -0.26).rotateY(-facing.asRotation() * (float) (Math.PI / 180));
		for (int i = 0; i < 2; i++) {
			world.addParticle(random.nextInt(4) == 0 ? ParticleTypes.LARGE_SMOKE : ParticleTypes.SMOKE,
					pos.getX() + 0.5 + local.x, pos.getY() + local.y, pos.getZ() + 0.5 + local.z,
					(random.nextDouble() - 0.5) * 0.02, 0.04 + random.nextDouble() * 0.03, (random.nextDouble() - 0.5) * 0.02);
		}
	}

	static boolean inPizzeria(World world) {
		return world instanceof ServerWorld && world.getRegistryKey() == PizzeriaManager.WORLD;
	}
}
