package com.fnaf.horror.block;

import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModBlocks;
import com.fnaf.horror.registry.ModSounds;
import net.minecraft.block.BlockState;
import net.minecraft.block.entity.BlockEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.math.BlockBox;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.World;

public class GeneratorBlockEntity extends BlockEntity {
	/** Average running time in the pizzeria before it stalls, in ticks. */
	private static final int MEAN_RUN_TICKS = 20 * 60 * 4;
	private int soundTimer;
	private int pullCooldown;
	private int pulls;

	public GeneratorBlockEntity(BlockPos pos, BlockState state) {
		super(ModBlocks.GENERATOR_ENTITY, pos, state);
	}

	public static void serverTick(World world, BlockPos pos, BlockState state, GeneratorBlockEntity be) {
		if (be.pullCooldown > 0) {
			be.pullCooldown--;
		}
		if (!state.get(GeneratorBlock.RUNNING)) {
			return;
		}
		if (--be.soundTimer <= 0) {
			be.soundTimer = 118;
			world.playSound(null, pos, ModSounds.GENERATOR_RUN, SoundCategory.BLOCKS, 0.9f, 0.97f + world.random.nextFloat() * 0.06f);
		}
		if (GeneratorBlock.inPizzeria(world) && !com.fnaf.horror.night.NightManager.isActive() && world.random.nextInt(MEAN_RUN_TICKS) == 0) {
			be.stop(true);
		}
	}

	/** One pull of the starter cord: usually it only coughs, the fourth pull always catches. */
	public void pull(PlayerEntity player) {
		if (pullCooldown > 0 || world == null) {
			return;
		}
		pullCooldown = 30;
		pulls++;
		if (world.random.nextInt(3) == 0 || pulls >= 4) {
			pulls = 0;
			world.setBlockState(pos, getCachedState().with(GeneratorBlock.RUNNING, true));
			world.playSound(null, pos, ModSounds.GENERATOR_START, SoundCategory.BLOCKS, 1.0f, 1.0f);
			soundTimer = 60;
			CeilingLightBlock.setPower((ServerWorld) world, powerArea(), true);
			player.sendMessage(Text.translatable("message.fnaf.generator_started").formatted(Formatting.YELLOW), true);
		} else {
			world.playSound(null, pos, ModSounds.GENERATOR_PULL, SoundCategory.BLOCKS, 1.0f, 0.9f + world.random.nextFloat() * 0.2f);
		}
	}

	/** Stops the engine; a failure also plays the power-out sound to everyone in the dimension. */
	public void stop(boolean failure) {
		if (world == null) {
			return;
		}
		world.setBlockState(pos, getCachedState().with(GeneratorBlock.RUNNING, false));
		world.playSound(null, pos, ModSounds.GENERATOR_STOP, SoundCategory.BLOCKS, 1.0f, 1.0f);
		CeilingLightBlock.setPower((ServerWorld) world, powerArea(), false);
		if (failure) {
			// like in FNAF 1: in the dark, Freddy starts playing the Toreador March
			for (com.fnaf.horror.entity.AnimatronicEntity freddy : ((ServerWorld) world).getEntitiesByType(
					com.fnaf.horror.registry.ModEntities.FREDDY, e -> true)) {
				world.playSoundFromEntity(null, freddy, ModSounds.MUSIC_BOX, SoundCategory.HOSTILE, 1.4f, 1.0f);
			}
			for (ServerPlayerEntity p : ((ServerWorld) world).getPlayers()) {
				p.playSound(ModSounds.POWER_DOWN, SoundCategory.MASTER, 1.0f, 1.0f);
				p.sendMessage(Text.translatable("message.fnaf.power_out").formatted(Formatting.DARK_RED), true);
			}
		}
	}

	private BlockBox powerArea() {
		if (GeneratorBlock.inPizzeria(world)) {
			return PizzeriaManager.bounds();
		}
		return new BlockBox(pos.getX() - 24, pos.getY() - 4, pos.getZ() - 24, pos.getX() + 24, pos.getY() + 10, pos.getZ() + 24);
	}

	@Override
	protected void writeNbt(NbtCompound nbt) {
		super.writeNbt(nbt);
		nbt.putInt("Pulls", pulls);
	}

	@Override
	public void readNbt(NbtCompound nbt) {
		super.readNbt(nbt);
		pulls = nbt.getInt("Pulls");
	}
}
