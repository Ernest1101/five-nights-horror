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
import net.minecraft.state.property.IntProperty;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.world.BlockView;

/**
 * A spare animatronic head on a backstage shelf. KIND picks the character (0 Freddy, 1 Bonnie, 2 Chica,
 * 3 Foxy); the head mesh of that animatronic is drawn by a block entity renderer.
 */
public class SpareHeadBlock extends BlockWithEntity {
	public static final IntProperty KIND = IntProperty.of("kind", 0, 3);
	public static final String[] IDS = {"freddy", "bonnie", "chica", "foxy"};
	private static final VoxelShape SHAPE = Block.createCuboidShape(2, 0, 2, 14, 12, 14);

	public SpareHeadBlock(Settings settings) {
		super(settings);
		setDefaultState(getDefaultState().with(HorizontalFacingBlock.FACING, Direction.SOUTH).with(KIND, 0));
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(HorizontalFacingBlock.FACING, KIND);
	}

	@Override
	public BlockState getPlacementState(ItemPlacementContext ctx) {
		return getDefaultState().with(HorizontalFacingBlock.FACING, ctx.getHorizontalPlayerFacing().getOpposite())
				.with(KIND, ctx.getWorld().random.nextInt(4));
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
		return new PropBlockEntity(ModBlocks.SPARE_HEAD_ENTITY, pos, state);
	}
}
