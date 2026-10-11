package com.fnaf.horror.block;

import com.fnaf.horror.registry.ModSounds;
import net.minecraft.block.BlockSetType;
import net.minecraft.block.ButtonBlock;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.sound.SoundCategory;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.WorldAccess;
import org.jetbrains.annotations.Nullable;

/** Office hall-light button: lights the lamp outside the door for a few seconds, with the fluorescent buzz. */
public class LightButtonBlock extends ButtonBlock {
	public LightButtonBlock(Settings settings, BlockSetType type) {
		super(settings, type, 66, false);
	}

	@Override
	protected void playClickSound(@Nullable PlayerEntity player, WorldAccess world, BlockPos pos, boolean powered) {
		super.playClickSound(player, world, pos, powered);
		if (powered) {
			world.playSound(null, pos, ModSounds.DOOR_LIGHT_BUZZ, SoundCategory.BLOCKS, 0.8f, 1.0f);
		}
	}
}
