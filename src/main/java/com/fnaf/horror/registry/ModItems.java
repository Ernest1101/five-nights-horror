package com.fnaf.horror.registry;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.item.FlashlightItem;
import net.fabricmc.fabric.api.itemgroup.v1.FabricItemGroup;
import net.minecraft.item.Item;
import net.minecraft.item.ItemGroup;
import net.minecraft.item.ItemStack;
import net.minecraft.item.SpawnEggItem;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.text.Text;

import java.util.ArrayList;
import java.util.List;

public final class ModItems {
	public static final List<Item> SPAWN_EGGS = new ArrayList<>();
	public static final Item FLASHLIGHT = Registry.register(Registries.ITEM, FnafHorror.id("flashlight"), new FlashlightItem(new Item.Settings()));

	public static void register() {
		for (ModEntities.Animatronic a : ModEntities.ALL) {
			Item egg = new SpawnEggItem(a.type(), a.eggPrimary(), a.eggSecondary(), new Item.Settings());
			SPAWN_EGGS.add(Registry.register(Registries.ITEM, FnafHorror.id(a.id() + "_spawn_egg"), egg));
		}

		Registry.register(Registries.ITEM_GROUP, FnafHorror.id("main"), FabricItemGroup.builder()
				.icon(() -> new ItemStack(SPAWN_EGGS.get(0)))
				.displayName(Text.translatable("itemGroup.fnaf.main"))
				.entries((context, entries) -> {
					entries.add(FLASHLIGHT);
					ModBlocks.ALL.forEach(entries::add);
					SPAWN_EGGS.forEach(entries::add);
				})
				.build());
	}

	private ModItems() {
	}
}
