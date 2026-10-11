package com.fnaf.horror;

import com.fnaf.horror.item.FlashlightLights;
import com.fnaf.horror.lobby.LobbyManager;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModBlocks;
import com.fnaf.horror.registry.ModEntities;
import com.fnaf.horror.registry.ModItems;
import com.fnaf.horror.registry.ModPaintings;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.api.ModInitializer;
import net.minecraft.util.Identifier;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class FnafHorror implements ModInitializer {
	public static final String MOD_ID = "fnaf";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	public static Identifier id(String path) {
		return new Identifier(MOD_ID, path);
	}

	@Override
	public void onInitialize() {
		ModSounds.register();
		ModPaintings.register();
		ModEntities.register();
		ModBlocks.register();
		ModItems.register();
		FlashlightLights.init();
		LobbyManager.init();
		com.fnaf.horror.night.NightManager.init();
		com.fnaf.horror.night.Fuel.init();
		PizzeriaManager.registerCommands();
		LOGGER.info("It's me.");
	}
}
