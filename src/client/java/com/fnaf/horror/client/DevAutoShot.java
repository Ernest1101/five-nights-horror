package com.fnaf.horror.client;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.lobby.LobbyManager;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.screen.TitleScreen;
import net.minecraft.client.util.ScreenshotRecorder;
import net.minecraft.server.MinecraftServer;

import java.io.File;
import java.util.ArrayDeque;
import java.util.Deque;

/**
 * Development helper: if run/fnaf_autoshot.txt exists, the client opens the world named in it, starts the
 * game, walks a camera tour through the pizzeria and saves screenshots (run/screenshots/fnaf_*.png), then quits.
 * Each line after the world name is either "shot <name>", "wait <ticks>", "hud <on|off>" or a server command.
 */
public final class DevAutoShot {
	private static final Deque<String> STEPS = new ArrayDeque<>();
	private static boolean started;
	private static int wait;
	private static net.minecraft.util.math.BlockPos genPos;

	public static void init() {
		File file = new File(MinecraftClient.getInstance().runDirectory, "fnaf_autoshot.txt");
		if (!file.isFile()) {
			return;
		}
		try {
			java.util.List<String> lines = java.nio.file.Files.readAllLines(file.toPath());
			file.delete();
			STEPS.addAll(lines);
		} catch (java.io.IOException e) {
			FnafHorror.LOGGER.error("autoshot", e);
			return;
		}
		ClientTickEvents.END_CLIENT_TICK.register(DevAutoShot::tick);
	}

	private static void tick(MinecraftClient client) {
		if (!started) {
			if (client.currentScreen instanceof TitleScreen) {
				started = true;
				client.options.pauseOnLostFocus = false;
				client.createIntegratedServerLoader().start(client.currentScreen, STEPS.poll());
				wait = 200;
			}
			return;
		}
		if (client.player == null || client.world == null) {
			return;
		}
		if (wait > 0) {
			wait--;
			return;
		}
		String step = STEPS.poll();
		if (step == null) {
			client.scheduleStop();
			return;
		}
		step = step.trim();
		FnafHorror.LOGGER.info("[autoshot] {}", step);
		if (step.isEmpty()) {
			return;
		}
		if (step.equals("start")) {
			ClientPlayNetworking.send(LobbyManager.START, PacketByteBufs.create());
			wait = 60;
		} else if (step.startsWith("wait ")) {
			wait = Integer.parseInt(step.substring(5).trim());
		} else if (step.startsWith("hud ")) {
			client.options.hudHidden = step.endsWith("off");
		} else if (step.startsWith("persp ")) {
			client.options.setPerspective(step.endsWith("front") ? net.minecraft.client.option.Perspective.THIRD_PERSON_FRONT
					: step.endsWith("back") ? net.minecraft.client.option.Perspective.THIRD_PERSON_BACK
					: net.minecraft.client.option.Perspective.FIRST_PERSON);
		} else if (step.startsWith("cam ")) {
			com.fnaf.horror.client.night.CameraScreen.debugOpen(Integer.parseInt(step.substring(4).trim()));
		} else if (step.equals("camclose")) {
			client.setScreen(null);
		} else if (step.startsWith("fps ")) {
			FnafHorror.LOGGER.info("[autoshot] FPS {} = {}", step.substring(4).trim(), client.getCurrentFps());
		} else if (step.startsWith("click ")) {
			String[] a = step.substring(6).trim().split(" ");
			net.minecraft.util.math.BlockPos bp = new net.minecraft.util.math.BlockPos(Integer.parseInt(a[0]), Integer.parseInt(a[1]), Integer.parseInt(a[2]));
			client.interactionManager.interactBlock(client.player, net.minecraft.util.Hand.MAIN_HAND,
					new net.minecraft.util.hit.BlockHitResult(net.minecraft.util.math.Vec3d.ofCenter(bp), net.minecraft.util.math.Direction.UP, bp, false));
			wait = 10;
		} else if (step.equals("gen")) {
			// walk up to the nearest generator (its spot is chosen at runtime) and use it
			net.minecraft.util.math.BlockPos me = client.player.getBlockPos();
			for (net.minecraft.util.math.BlockPos p : net.minecraft.util.math.BlockPos.iterateOutwards(me, 40, 3, 40)) {
				net.minecraft.block.BlockState st = client.world.getBlockState(p);
				if (st.isOf(com.fnaf.horror.registry.ModBlocks.GENERATOR)) {
					net.minecraft.util.math.Direction f = st.get(net.minecraft.block.HorizontalFacingBlock.FACING);
					net.minecraft.util.math.BlockPos stand = p.offset(f, 2);
					float yaw = f.getOpposite().asRotation();
					MinecraftServer server = client.getServer();
					String cmd = "execute in fnaf:pizzeria run tp " + client.player.getName().getString() + " " + (stand.getX() + 0.5) + " "
							+ stand.getY() + " " + (stand.getZ() + 0.5) + " " + yaw + " 35";
					FnafHorror.LOGGER.info("[autoshot] generator at {}", p);
					genPos = p.toImmutable();
					if (server != null) {
						server.execute(() -> server.getCommandManager().executeWithPrefix(server.getCommandSource(), cmd));
					}
					break;
				}
			}
			wait = 30;
		} else if (step.equals("clickgen") && genPos != null) {
			client.interactionManager.interactBlock(client.player, net.minecraft.util.Hand.MAIN_HAND,
					new net.minecraft.util.hit.BlockHitResult(net.minecraft.util.math.Vec3d.ofCenter(genPos), net.minecraft.util.math.Direction.UP, genPos, false));
			wait = 10;
		} else if (step.startsWith("hold ")) {
			com.fnaf.horror.client.night.RefuelScreen.debugHoldTicks = Integer.parseInt(step.substring(5).trim());
		} else if (step.startsWith("slot ")) {
			client.player.getInventory().selectedSlot = Integer.parseInt(step.substring(5).trim());
		} else if (step.startsWith("use")) {
			client.interactionManager.interactItem(client.player, net.minecraft.util.Hand.MAIN_HAND);
		} else if (step.startsWith("shot ")) {
			ScreenshotRecorder.saveScreenshot(client.runDirectory, "fnaf_" + step.substring(5).trim() + ".png",
					client.getFramebuffer(), text -> FnafHorror.LOGGER.info("[autoshot] {}", text.getString()));
			wait = 5;
		} else {
			MinecraftServer server = client.getServer();
			String name = client.player.getName().getString();
			String cmd = step.replace("@me", name);
			if (server != null) {
				server.execute(() -> server.getCommandManager().executeWithPrefix(server.getCommandSource(), cmd));
			}
			wait = 10;
		}
	}

	private DevAutoShot() {
	}
}
