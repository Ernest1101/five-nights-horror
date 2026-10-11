package com.fnaf.horror.registry;

import com.fnaf.horror.FnafHorror;
import net.minecraft.entity.decoration.painting.PaintingVariant;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;

/** Pizzeria posters and kids' drawings (textures in assets/fnaf/textures/painting, see tools/pizzeria/gen_paintings.py). */
public final class ModPaintings {
	public static void register() {
		variant("celebrate", 4, 3);
		variant("freddy_poster", 2, 3);
		variant("golden_poster", 2, 3);
		variant("rules", 2, 3);
		for (int i = 1; i <= 4; i++) {
			variant("drawing" + i, 1, 1);
		}
	}

	private static void variant(String name, int blocksWide, int blocksHigh) {
		Registry.register(Registries.PAINTING_VARIANT, FnafHorror.id(name), new PaintingVariant(blocksWide * 16, blocksHigh * 16));
	}

	private ModPaintings() {
	}
}
