package com.fnaf.horror.block;

import com.fnaf.horror.registry.ModBlocks;
import net.minecraft.block.Block;
import net.minecraft.block.BlockRenderType;
import net.minecraft.block.BlockState;
import net.minecraft.block.BlockWithEntity;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.block.ShapeContext;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.item.ItemPlacementContext;
import net.minecraft.state.StateManager;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.world.BlockView;

/** The office desk fan; its mesh and spinning blades are drawn by a block entity renderer. */
public class DeskFanBlock extends BlockWithEntity {
	private static final VoxelShape SHAPE = Block.createCuboidShape(3, 0, 3, 13, 9, 13);

	public DeskFanBlock(Settings settings) {
		super(settings);
		setDefaultState(getDefaultState().with(HorizontalFacingBlock.FACING, net.minecraft.util.math.Direction.SOUTH));
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(HorizontalFacingBlock.FACING);
	}

	@Override
	public BlockState getPlacementState(ItemPlacementContext ctx) {
		return getDefaultState().with(HorizontalFacingBlock.FACING, ctx.getHorizontalPlayerFacing().getOpposite());
	}

	@Override
	public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		return SHAPE;
	}

	@Override
	public <T extends BlockEntity> net.minecraft.block.entity.BlockEntityTicker<T> getTicker(net.minecraft.world.World world, BlockState state,
			net.minecraft.block.entity.BlockEntityType<T> type) {
		if (world.isClient) {
			return null;
		}
		// fan hum loop (8 s), staggered per fan
		return checkType(type, ModBlocks.DESK_FAN_ENTITY, (w, pos, s, be) -> {
			if ((w.getTime() + pos.hashCode()) % 160 == 0) {
				w.playSound(null, pos, com.fnaf.horror.registry.ModSounds.FAN_LOOP, net.minecraft.sound.SoundCategory.BLOCKS, 0.5f, 1.0f);
			}
		});
	}

	@Override
	public BlockRenderType getRenderType(BlockState state) {
		return BlockRenderType.ENTITYBLOCK_ANIMATED;
	}

	@Override
	public BlockEntity createBlockEntity(BlockPos pos, BlockState state) {
		return new PropBlockEntity(ModBlocks.DESK_FAN_ENTITY, pos, state);
	}
}
