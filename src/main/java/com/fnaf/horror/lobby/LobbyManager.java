package com.fnaf.horror.lobby;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import net.fabricmc.fabric.api.entity.event.v1.ServerPlayerEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;
import net.minecraft.world.GameMode;
import net.minecraft.world.Heightmap;

import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Every player who joins (or respawns after dying) is put into a closed white box high
 * above the world. The client shows "TAB - START"; pressing it sends {@link #START} and the
 * player is released to the world spawn.
 */
public final class LobbyManager {
	/** S2C: one boolean, whether the receiving player is in the lobby. */
	public static final Identifier SYNC = FnafHorror.id("lobby_sync");
	/** C2S: the player picked a main menu entry (int mode, see MODE_*). */
	public static final Identifier START = FnafHorror.id("lobby_start");
	public static final int MODE_NEW_GAME = 0, MODE_CONTINUE = 1, MODE_SIXTH_NIGHT = 2, MODE_FREE_ROAM = 3;

	/** Box center, far from spawn so it never ends up under a heightmap lookup at spawn. */
	private static final BlockPos CENTER = new BlockPos(10_000, 300, 10_000);
	/** Interior is (2*HALF+1) x HEIGHT x (2*HALF+1). */
	private static final int HALF = 4;
	private static final int HEIGHT = 5;

	private static final Set<UUID> IN_LOBBY = ConcurrentHashMap.newKeySet();
	/** Players who just joined, with the ticks left before they are moved: teleporting on the join tick
	 * races the chunk packets of the dimension they logged out in. */
	private static final Map<UUID, Integer> PENDING = new java.util.HashMap<>();

	public static void init() {
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> PENDING.put(handler.player.getUuid(), 10));
		ServerTickEvents.END_SERVER_TICK.register(server -> {
			for (java.util.Iterator<Map.Entry<UUID, Integer>> it = PENDING.entrySet().iterator(); it.hasNext(); ) {
				Map.Entry<UUID, Integer> e = it.next();
				if (e.getValue() > 1) {
					e.setValue(e.getValue() - 1);
					continue;
				}
				it.remove();
				ServerPlayerEntity player = server.getPlayerManager().getPlayer(e.getKey());
				if (player != null) {
					sendToLobby(player);
				}
			}
		});
		ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
			IN_LOBBY.remove(handler.player.getUuid());
			PENDING.remove(handler.player.getUuid());
		});
		ServerPlayerEvents.AFTER_RESPAWN.register((oldPlayer, newPlayer, alive) -> {
			if (!alive) {
				sendToLobby(newPlayer);
			}
		});
		ServerPlayNetworking.registerGlobalReceiver(START, (server, player, handler, buf, responseSender) -> {
			int mode = buf.readableBytes() >= 4 ? buf.readInt() : MODE_CONTINUE;
			server.execute(() -> start(player, mode));
		});
	}

	public static boolean isInLobby(ServerPlayerEntity player) {
		return IN_LOBBY.contains(player.getUuid());
	}

	public static void sendToLobby(ServerPlayerEntity player) {
		MinecraftServer server = player.getServer();
		if (server == null) {
			return;
		}
		ServerWorld world = server.getOverworld();
		buildBox(world);
		IN_LOBBY.add(player.getUuid());
		player.changeGameMode(GameMode.ADVENTURE);
		player.teleport(world, CENTER.getX() + 0.5, CENTER.getY() + 1, CENTER.getZ() + 0.5, 180.0f, 0.0f);
		player.fallDistance = 0;
		sync(player, true);
	}

	private static void start(ServerPlayerEntity player, int mode) {
		if (!IN_LOBBY.remove(player.getUuid())) {
			return;
		}
		sync(player, false);
		int beaten = com.fnaf.horror.night.NightProgress.get(player.getServer()).beaten(player.getUuid());
		int night = switch (mode) {
			case MODE_NEW_GAME -> 1;
			case MODE_SIXTH_NIGHT -> beaten >= 5 ? 6 : Math.min(beaten + 1, 5);
			default -> Math.max(1, Math.min(beaten + 1, 5));
		};
		if (mode == MODE_FREE_ROAM ? PizzeriaManager.enter(player) : com.fnaf.horror.night.NightManager.begin(player, night)) {
			return;
		}
		// fallback: no pizzeria available, release the player at the overworld spawn
		MinecraftServer server = player.getServer();
		ServerWorld world = server.getOverworld();
		BlockPos spawn = world.getSpawnPos();
		BlockPos top = world.getTopPosition(Heightmap.Type.MOTION_BLOCKING_NO_LEAVES, spawn);
		player.changeGameMode(server.getDefaultGameMode());
		player.teleport(world, top.getX() + 0.5, top.getY(), top.getZ() + 0.5, player.getYaw(), 0.0f);
		player.fallDistance = 0;
	}

	private static void sync(ServerPlayerEntity player, boolean inLobby) {
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeBoolean(inLobby);
		buf.writeInt(player.getServer() == null ? 0 : com.fnaf.horror.night.NightProgress.get(player.getServer()).beaten(player.getUuid()));
		ServerPlayNetworking.send(player, SYNC, buf);
	}

	/** White concrete shell with invisible light blocks so the inside is evenly bright. */
	private static void buildBox(ServerWorld world) {
		BlockState wall = Blocks.WHITE_CONCRETE.getDefaultState();
		BlockState light = Blocks.LIGHT.getDefaultState();
		BlockState air = Blocks.AIR.getDefaultState();
		int r = HALF + 1;
		BlockPos.Mutable pos = new BlockPos.Mutable();
		for (int dx = -r; dx <= r; dx++) {
			for (int dz = -r; dz <= r; dz++) {
				for (int dy = 0; dy <= HEIGHT + 1; dy++) {
					boolean shell = Math.abs(dx) == r || Math.abs(dz) == r || dy == 0 || dy == HEIGHT + 1;
					boolean lamp = !shell && dy == HEIGHT && Math.abs(dx) % 3 == 0 && Math.abs(dz) % 3 == 0;
					BlockState state = shell ? wall : lamp ? light : air;
					pos.set(CENTER.getX() + dx, CENTER.getY() + dy, CENTER.getZ() + dz);
					if (world.getBlockState(pos) != state) {
						world.setBlockState(pos, state);
					}
				}
			}
		}
	}

	private LobbyManager() {
	}
}
