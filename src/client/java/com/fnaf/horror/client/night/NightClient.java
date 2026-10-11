package com.fnaf.horror.client.night;

import com.fnaf.horror.night.NightManager;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.font.TextRenderer;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import net.minecraft.util.math.MathHelper;
import org.lwjgl.glfw.GLFW;

import java.util.Random;

/**
 * Client side of a FNAF night: the synced clock/power state, the HUD (time, night, power, usage), the
 * full-screen "12:00 AM / 1st Night", "6 AM" and game-over cards, and the camera tablet key.
 */
public final class NightClient {
	public static boolean active;
	public static int night;
	public static int time;
	public static float power;
	public static int usage;
	public static boolean blackout;

	private static int introTicks;
	private static int winTicks;
	private static int gameOverTicks;
	private static int shownNight;
	private static final Random RANDOM = new Random();
	public static KeyBinding cameraKey;

	public static void init() {
		cameraKey = KeyBindingHelper.registerKeyBinding(new KeyBinding("key.fnaf.camera", InputUtil.Type.KEYSYM, GLFW.GLFW_KEY_C, "category.fnaf"));
		ClientPlayNetworking.registerGlobalReceiver(NightManager.STATE, (client, handler, buf, responseSender) -> {
			boolean a = buf.readBoolean();
			int n = a ? buf.readInt() : 0, t = a ? buf.readInt() : 0;
			float p = a ? buf.readFloat() : 0;
			int u = a ? buf.readInt() : 0;
			boolean b = a && buf.readBoolean();
			client.execute(() -> {
				active = a;
				night = n;
				time = t;
				power = p;
				usage = u;
				if (b && !blackout && client.currentScreen instanceof CameraScreen cs) {
					cs.close();
				}
				blackout = b;
			});
		});
		ClientPlayNetworking.registerGlobalReceiver(NightManager.EVENT, (client, handler, buf, responseSender) -> {
			int type = buf.readInt(), arg = buf.readInt();
			client.execute(() -> event(client, type, arg));
		});
		ClientPlayNetworking.registerGlobalReceiver(com.fnaf.horror.night.Fuel.OPEN, (client, handler, buf, responseSender) -> {
			buf.readBlockPos();
			int cans = buf.readInt();
			float p = buf.readFloat();
			client.execute(() -> client.setScreen(new RefuelScreen(cans, p)));
		});
		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> active = false);
		ClientTickEvents.END_CLIENT_TICK.register(NightClient::tick);
		HudRenderCallback.EVENT.register(NightClient::render);
		// the vanilla death screen cannot be closed while dead: cover it with the game-over card instead
		net.fabricmc.fabric.api.client.screen.v1.ScreenEvents.AFTER_INIT.register((client, screen, w, h) -> {
			if (screen instanceof net.minecraft.client.gui.screen.DeathScreen) {
				net.fabricmc.fabric.api.client.screen.v1.ScreenEvents.afterRender(screen).register((scr, ctx, mx, my, delta) -> {
					if (gameOverTicks > 0) {
						ctx.getMatrices().push();
						ctx.getMatrices().translate(0, 0, 500);   // above the death screen's own text
						render(ctx, delta);
						ctx.getMatrices().pop();
					}
				});
			}
		});
	}

	private static void event(MinecraftClient client, int type, int arg) {
		switch (type) {
			case NightManager.EVENT_START -> {
				shownNight = arg;
				introTicks = 100;
				winTicks = 0;
				gameOverTicks = 0;
				active = true;
				night = arg;
			}
			case NightManager.EVENT_WIN -> {
				shownNight = arg;
				winTicks = 170;
				if (client.currentScreen instanceof CameraScreen cs) {
					cs.close();
				}
			}
			case NightManager.EVENT_GAME_OVER -> {
				gameOverTicks = 70;
				if (client.currentScreen instanceof CameraScreen cs) {
					cs.close();
				}
			}
			case NightManager.EVENT_CAM_GLITCH -> {
				if (client.currentScreen instanceof CameraScreen cs) {
					cs.glitch(arg);
				}
			}
			case NightManager.EVENT_BLACKOUT -> {
				blackout = true;
				if (client.currentScreen instanceof CameraScreen cs) {
					cs.close();
				}
			}
			default -> {
			}
		}
	}

	private static void tick(MinecraftClient client) {
		// the night card only counts down once the pizzeria is on screen (not while terrain loads)
		if (introTicks > 0 && client.currentScreen == null) {
			introTicks--;
		}
		if (winTicks > 0) {
			winTicks--;
		}
		// FNAF-style death: no vanilla death screen, the game-over card plays and then we respawn into the menu
		if (gameOverTicks > 0 && --gameOverTicks == 0 && client.player != null && !client.player.isAlive()) {
			client.player.requestRespawn();
			client.setScreen(null);
		}
		// The key is polled directly: C is also the vanilla "save toolbar" key, and Minecraft hands a shared
		// key to only one of the bindings, so wasPressed() alone can miss it.
		boolean down = cameraKeyDown(client);
		boolean pressed = cameraKey.wasPressed() || down && !cameraKeyWasDown;
		while (cameraKey.wasPressed()) {
			// drain queued presses
		}
		cameraKeyWasDown = down;
		if (pressed && client.currentScreen == null && client.player != null) {
			if (active && !blackout && winTicks == 0 && introTicks == 0) {
				client.setScreen(new CameraScreen());
			} else if (!active) {
				client.player.sendMessage(net.minecraft.text.Text.translatable("message.fnaf.cameras_night_only"), true);
			}
		}
	}

	private static boolean cameraKeyWasDown;

	private static boolean cameraKeyDown(MinecraftClient client) {
		InputUtil.Key key = KeyBindingHelper.getBoundKeyOf(cameraKey);
		if (key.getCategory() != InputUtil.Type.KEYSYM || key.getCode() == InputUtil.UNKNOWN_KEY.getCode()) {
			return false;
		}
		return InputUtil.isKeyPressed(client.getWindow().getHandle(), key.getCode());
	}

	/** "12 AM", "1 AM" ... */
	public static String clock() {
		int hour = Math.max(0, time) / NightManager.HOUR_TICKS;
		return (hour == 0 ? 12 : hour) + " AM";
	}

	public static String ordinal(int n) {
		return n + switch (n) {
			case 1 -> "st";
			case 2 -> "nd";
			case 3 -> "rd";
			default -> "th";
		};
	}

	public static void render(DrawContext ctx, float tickDelta) {
		MinecraftClient client = MinecraftClient.getInstance();
		TextRenderer font = client.textRenderer;
		int w = ctx.getScaledWindowWidth(), h = ctx.getScaledWindowHeight();
		if (gameOverTicks > 0) {
			ctx.fill(0, 0, w, h, 0xFF000000);
			staticNoise(ctx, w, h, 900, 0x70);
			if (gameOverTicks < 40) {
				big(ctx, font, "GAME OVER", w / 2, h / 2 - 10, 3f, 0xFFFFFFFF);
			}
			return;
		}
		if (winTicks > 0) {
			ctx.fill(0, 0, w, h, 0xFF000000);
			// the "5" rolls up into a "6", then the cheering
			float t = 1f - (winTicks - 110) / 60f;
			int y = h / 2 - 12;
			ctx.enableScissor(0, y - 14, w, y + 30);
			if (winTicks > 110) {
				big(ctx, font, "5", w / 2 - 22, (int) (y - 30 * MathHelper.clamp(t, 0, 1)), 4f, 0xFFFFFFFF);
				big(ctx, font, "6", w / 2 - 22, (int) (y + 30 - 30 * MathHelper.clamp(t, 0, 1)), 4f, 0xFFFFFFFF);
			} else {
				big(ctx, font, "6", w / 2 - 22, y, 4f, 0xFFFFFFFF);
			}
			ctx.disableScissor();
			big(ctx, font, "AM", w / 2 + 26, y, 4f, 0xFFFFFFFF);
			return;
		}
		if (introTicks > 0) {
			int alpha = introTicks > 20 ? 255 : introTicks * 255 / 20;
			ctx.fill(0, 0, w, h, alpha << 24);
			if (introTicks > 10) {
				int a = Math.min(255, alpha) << 24;
				big(ctx, font, "12:00 AM", w / 2, h / 2 - 22, 3f, a | 0xFFFFFF);
				big(ctx, font, ordinal(shownNight) + " Night", w / 2, h / 2 + 12, 2.5f, a | 0xFFFFFF);
			}
			return;
		}
		if (!active || client.currentScreen instanceof CameraScreen) {
			return;
		}
		hud(ctx, font, w, h);
		if (blackout && !(client.currentScreen instanceof RefuelScreen) && client.player != null) {
			// power is out: go and find petrol for the generator
			int cans = client.player.getInventory().count(com.fnaf.horror.night.Fuel.canItem());
			boolean blink = (System.currentTimeMillis() / 500) % 2 == 0;
			ctx.drawCenteredTextWithShadow(font, net.minecraft.text.Text.translatable("hud.fnaf.blackout"), w / 2, h - 112,
					blink ? 0xFFFF5040 : 0xFFB02818);
			ctx.drawCenteredTextWithShadow(font, net.minecraft.text.Text.translatable(cans > 0 ? "hud.fnaf.blackout_go" : "hud.fnaf.blackout_find", cans),
					w / 2, h - 100, 0xFFE8C040);
		}
	}

	/** Time and night top right, power and usage bars bottom left (also drawn by the camera screen). */
	public static void hud(DrawContext ctx, TextRenderer font, int w, int h) {
		big(ctx, font, clock(), w - 40, 12, 2f, 0xFFFFFFFF);
		ctx.drawTextWithShadow(font, "Night " + night, w - 60, 30, 0xFFFFFFFF);
		ctx.drawTextWithShadow(font, "Power left: " + (int) Math.ceil(power) + "%", 10, h - 40, 0xFFFFFFFF);
		ctx.drawTextWithShadow(font, "Usage:", 10, h - 24, 0xFFFFFFFF);
		for (int i = 0; i < Math.min(usage, 5); i++) {
			int color = i < 2 ? 0xFF3FD13F : i < 4 ? 0xFFE8D020 : 0xFFE03020;
			ctx.fill(48 + i * 11, h - 27, 57 + i * 11, h - 15, color);
		}
	}

	public static void big(DrawContext ctx, TextRenderer font, String text, int cx, int cy, float scale, int color) {
		ctx.getMatrices().push();
		ctx.getMatrices().translate(cx, cy, 0);
		ctx.getMatrices().scale(scale, scale, 1f);
		ctx.drawTextWithShadow(font, text, -font.getWidth(text) / 2, -font.fontHeight / 2, color);
		ctx.getMatrices().pop();
	}

	/** Cheap animated TV static: random grey specks and a few torn horizontal bands. */
	public static void staticNoise(DrawContext ctx, int w, int h, int specks, int alpha) {
		for (int i = 0; i < specks; i++) {
			int x = RANDOM.nextInt(w), y = RANDOM.nextInt(h);
			int g = 80 + RANDOM.nextInt(176);
			int s = 1 + RANDOM.nextInt(3);
			ctx.fill(x, y, x + s, y + 1, (alpha << 24) | (g << 16) | (g << 8) | g);
		}
		for (int i = 0; i < 3; i++) {
			int y = RANDOM.nextInt(h);
			ctx.fill(0, y, w, y + 1 + RANDOM.nextInt(3), ((alpha / 3) << 24) | 0xFFFFFF);
		}
	}

	private NightClient() {
	}
}
