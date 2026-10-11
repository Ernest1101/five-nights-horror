package com.fnaf.horror.registry;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.entity.AnimatronicEntity;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricDefaultAttributeRegistry;
import net.fabricmc.fabric.api.object.builder.v1.entity.FabricEntityTypeBuilder;
import net.minecraft.entity.EntityDimensions;
import net.minecraft.entity.EntityType;
import net.minecraft.entity.SpawnGroup;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;

import java.util.ArrayList;
import java.util.List;

public final class ModEntities {
	/** One entry per animatronic: id, hitbox, spawn egg colors. Model files share the id. */
	public record Animatronic(String id, EntityType<AnimatronicEntity> type, int eggPrimary, int eggSecondary) {
	}

	public static final List<Animatronic> ALL = new ArrayList<>();

	public static final EntityType<AnimatronicEntity> FREDDY = register("freddy", 0.8f, 2.4f, 0x6E4426, 0x1A1A1A);
	public static final EntityType<AnimatronicEntity> BONNIE = register("bonnie", 0.8f, 2.5f, 0x5252AC, 0xAF161A);
	public static final EntityType<AnimatronicEntity> CHICA = register("chica", 0.8f, 2.35f, 0xE2BE2A, 0xEE7C1E);
	public static final EntityType<AnimatronicEntity> FOXY = register("foxy", 0.7f, 2.35f, 0x9C2E22, 0xCC9674);
	public static final EntityType<AnimatronicEntity> GOLDEN_FREDDY = register("golden_freddy", 0.8f, 2.4f, 0xC49830, 0x18203E);

	private static EntityType<AnimatronicEntity> register(String id, float width, float height, int egg1, int egg2) {
		EntityType<AnimatronicEntity> type = Registry.register(Registries.ENTITY_TYPE, FnafHorror.id(id),
				FabricEntityTypeBuilder.<AnimatronicEntity>create(SpawnGroup.MONSTER, AnimatronicEntity::new)
						.dimensions(EntityDimensions.fixed(width, height))
						.trackRangeBlocks(80)
						.build());
		ALL.add(new Animatronic(id, type, egg1, egg2));
		return type;
	}

	public static void register() {
		for (Animatronic a : ALL) {
			FabricDefaultAttributeRegistry.register(a.type(), AnimatronicEntity.createAttributes());
		}
	}

	private ModEntities() {
	}
}
