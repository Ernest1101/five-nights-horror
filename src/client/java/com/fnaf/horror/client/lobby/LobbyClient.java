package com.fnaf.horror.client.lobby;

import com.fnaf.horror.lobby.LobbyManager;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.minecraft.client.MinecraftClient;

/** Client side of the lobby: while the player waits in it, the FNAF main menu is shown. */
public final class LobbyClient {
	private static boolean inLobby;
	private static int beaten;

	public static boolean isInLobby() {
		return inLobby;
	}

	/** Called by the menu once a mode was picked, so it is not reopened while the server moves the player. */
	public static void leave() {
		inLobby = false;
	}

	public static void init() {
		ClientPlayNetworking.registerGlobalReceiver(LobbyManager.SYNC, (client, handler, buf, responseSender) -> {
			boolean value = buf.readBoolean();
			int nights = buf.readableBytes() >= 4 ? buf.readInt() : 0;
			client.execute(() -> {
				inLobby = value;
				beaten = nights;
				if (!value && client.currentScreen instanceof MainMenuScreen menu) {
					menu.close();
				}
			});
		});
		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> inLobby = false);
		ClientTickEvents.END_CLIENT_TICK.register(LobbyClient::tick);
	}

	private static void tick(MinecraftClient client) {
		if (inLobby && client.world != null && client.player != null && client.currentScreen == null && client.getOverlay() == null) {
			client.setScreen(new MainMenuScreen(beaten));
		}
	}

	private LobbyClient() {
	}
}
