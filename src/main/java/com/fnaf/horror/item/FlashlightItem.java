package com.fnaf.horror.item;

import com.fnaf.horror.registry.ModSounds;
import net.minecraft.entity.Entity;
import net.minecraft.entity.LivingEntity;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.item.Item;
import net.minecraft.item.ItemStack;
import net.minecraft.sound.SoundCategory;
import net.minecraft.text.Text;
import net.minecraft.util.Formatting;
import net.minecraft.util.Hand;
import net.minecraft.util.TypedActionResult;
import net.minecraft.world.World;

/**
 * Flashlight: use to switch it on/off. While it is on and held, the battery (durability bar) drains one
 * point per second and {@link FlashlightLights} keeps a light source where the beam hits. Recharge it at a
 * running generator. It never breaks, an empty battery just switches it off.
 */
public class FlashlightItem extends Item {
	public static final int BATTERY_SECONDS = 600;
	private static final String ON = "On";

	public FlashlightItem(Settings settings) {
		super(settings.maxCount(1).maxDamage(BATTERY_SECONDS));
	}

	public static boolean isOn(ItemStack stack) {
		return stack.getItem() instanceof FlashlightItem && stack.hasNbt() && stack.getNbt().getBoolean(ON);
	}

	/** The lit flashlight the entity holds in either hand, or null. */
	public static ItemStack litIn(LivingEntity entity) {
		for (Hand hand : Hand.values()) {
			ItemStack s = entity.getStackInHand(hand);
			if (isOn(s)) {
				return s;
			}
		}
		return null;
	}

	private static boolean empty(ItemStack stack) {
		return stack.getDamage() >= stack.getMaxDamage() - 1;
	}

	@Override
	public TypedActionResult<ItemStack> use(World world, PlayerEntity user, Hand hand) {
		ItemStack stack = user.getStackInHand(hand);
		if (!world.isClient) {
			boolean on = !isOn(stack) && !empty(stack);
			stack.getOrCreateNbt().putBoolean(ON, on);
			world.playSound(null, user.getX(), user.getEyeY(), user.getZ(), ModSounds.FLASHLIGHT_CLICK, SoundCategory.PLAYERS, 0.8f,
					on ? 1.1f : 0.9f);
			if (!on && empty(stack)) {
				user.sendMessage(Text.translatable("message.fnaf.flashlight_empty").formatted(Formatting.RED), true);
			}
		}
		return TypedActionResult.success(stack, world.isClient);
	}

	@Override
	public void inventoryTick(ItemStack stack, World world, Entity entity, int slot, boolean selected) {
		if (world.isClient || !isOn(stack) || !(entity instanceof LivingEntity living) || world.getTime() % 20 != 0) {
			return;
		}
		if (living.getMainHandStack() != stack && living.getOffHandStack() != stack) {
			return;
		}
		stack.setDamage(stack.getDamage() + 1);
		if (empty(stack)) {
			stack.getOrCreateNbt().putBoolean(ON, false);
			world.playSound(null, entity.getX(), entity.getEyeY(), entity.getZ(), ModSounds.FLASHLIGHT_CLICK, SoundCategory.PLAYERS, 0.8f, 0.6f);
			if (entity instanceof PlayerEntity player) {
				player.sendMessage(Text.translatable("message.fnaf.flashlight_empty").formatted(Formatting.RED), true);
			}
		}
	}

	@Override
	public boolean allowNbtUpdateAnimation(PlayerEntity player, Hand hand, ItemStack oldStack, ItemStack newStack) {
		return false;
	}

	@Override
	public boolean canRepair(ItemStack stack, ItemStack ingredient) {
		return false;
	}
}
