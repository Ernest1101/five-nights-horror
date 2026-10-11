package com.fnaf.horror.block;

import net.minecraft.block.Block;
import net.minecraft.block.BlockState;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.block.ShapeContext;
import net.minecraft.item.ItemPlacementContext;
import net.minecraft.state.StateManager;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.world.BlockView;

import java.util.EnumMap;
import java.util.Map;

/**
 * Decoration that faces the player who placed it (CRT monitor, chairs, sinks ...). The outline box is
 * given for a south-facing block (pixels) and rotated with the model for the other directions.
 */
public class FacingDecorBlock extends HorizontalFacingBlock {
	private final Map<Direction, VoxelShape> shapes = new EnumMap<>(Direction.class);

	public FacingDecorBlock(Settings settings, VoxelShape shape) {
		super(settings);
		for (Direction d : Direction.Type.HORIZONTAL) {
			shapes.put(d, shape);
		}
	}

	/** box = {x1, y1, z1, x2, y2, z2} in pixels for the south-facing model. */
	public FacingDecorBlock(Settings settings, double... box) {
		super(settings);
		for (Direction d : Direction.Type.HORIZONTAL) {
			double[] a = rotate(box[0], box[2], d);
			double[] b = rotate(box[3], box[5], d);
			shapes.put(d, Block.createCuboidShape(Math.min(a[0], b[0]), box[1], Math.min(a[1], b[1]),
					Math.max(a[0], b[0]), box[4], Math.max(a[1], b[1])));
		}
	}

	/** Same rotation as the blockstate "y" values: south 0, west 90, north 180, east 270. */
	private static double[] rotate(double x, double z, Direction facing) {
		return switch (facing) {
			case WEST -> new double[]{16 - z, x};
			case NORTH -> new double[]{16 - x, 16 - z};
			case EAST -> new double[]{z, 16 - x};
			default -> new double[]{x, z};
		};
	}

	@Override
	protected void appendProperties(StateManager.Builder<Block, BlockState> builder) {
		builder.add(FACING);
	}

	@Override
	public BlockState getPlacementState(ItemPlacementContext ctx) {
		return getDefaultState().with(FACING, ctx.getHorizontalPlayerFacing().getOpposite());
	}

	@Override
	public VoxelShape getOutlineShape(BlockState state, BlockView world, BlockPos pos, ShapeContext context) {
		return shapes.get(state.get(FACING));
	}
}
