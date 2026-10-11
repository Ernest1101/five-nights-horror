package com.fnaf.horror.night;

import net.minecraft.nbt.NbtCompound;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.PersistentState;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Highest night each player has survived (saved with the world). */
public class NightProgress extends PersistentState {
	private final Map<UUID, Integer> beaten = new HashMap<>();

	public static NightProgress get(MinecraftServer server) {
		return server.getOverworld().getPersistentStateManager().getOrCreate(NightProgress::fromNbt, NightProgress::new, "fnaf_nights");
	}

	public int beaten(UUID player) {
		return beaten.getOrDefault(player, 0);
	}

	public void win(UUID player, int night) {
		if (night > beaten(player)) {
			beaten.put(player, Math.min(night, 6));
			markDirty();
		}
	}

	private static NightProgress fromNbt(NbtCompound nbt) {
		NightProgress p = new NightProgress();
		for (String key : nbt.getKeys()) {
			p.beaten.put(UUID.fromString(key), nbt.getInt(key));
		}
		return p;
	}

	@Override
	public NbtCompound writeNbt(NbtCompound nbt) {
		beaten.forEach((k, v) -> nbt.putInt(k.toString(), v));
		return nbt;
	}
}
