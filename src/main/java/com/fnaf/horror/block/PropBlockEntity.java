package com.fnaf.horror.block;

import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.block.entity.BlockEntityType;
import net.minecraft.util.math.BlockPos;

/** Stateless block entity whose only job is to get a mesh prop drawn by its renderer. */
public class PropBlockEntity extends BlockEntity {
	public PropBlockEntity(BlockEntityType<?> type, BlockPos pos, BlockState state) {
		super(type, pos, state);
	}
}
