package com.fnaf.horror.block;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.ShapeContext;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.world.BlockView;

/** Small decoration (party hat, floor litter) with a custom outline shape. */
public class DecorBlock extends Block {
	private final VoxelShape shape;

	public DecorBlock(Settings settings, VoxelShape shape) {
		super(settings);
		this.shape = shape;
	}

	@Override
	public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		return shape;
	}
}
