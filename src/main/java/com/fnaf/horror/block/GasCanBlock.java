package com.fnaf.horror.block;

import com.fnaf.horror.registry.ModBlocks;
import com.fnaf.horror.registry.ModSounds;
import net.minecraft.block.BlockState;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.ItemStack;
import net.minecraft.sound.SoundCategory;
import net.minecraft.text.Text;
import net.minecraft.util.ActionResult;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;
import net.minecraft.util.hit.BlockHitResult;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

/**
 * A petrol can lying around the pizzeria after the power ran out. Use it to pick it up (works in
 * adventure mode), then pour it into the generator.
 */
public class GasCanBlock extends FacingDecorBlock {
	public GasCanBlock(Settings settings) {
		super(settings, 4.5, 0, 2.5, 11.5, 15.5, 13.5);
	}

	@Override
	public ActionResult onUse(BlockState state, World world, BlockPos pos, PlayerEntity player, Hand hand, BlockHitResult hit) {
		if (world.isClient) {
			return ActionResult.SUCCESS;
		}
		world.removeBlock(pos, false);
		player.getInventory().offerOrDrop(new ItemStack(ModBlocks.GAS_CAN));
		world.playSound(null, pos, ModSounds.FUEL_PICKUP, SoundCategory.PLAYERS, 1.0f, 0.9f + world.random.nextFloat() * 0.2f);
		int cans = player.getInventory().count(ModBlocks.GAS_CAN.asItem());
		player.sendMessage(Text.translatable("message.fnaf.gas_can_picked", cans).formatted(Formatting.GOLD), true);
		return ActionResult.CONSUME;
	}
}
