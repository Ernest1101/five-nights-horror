package com.fnaf.horror.client;

import com.fnaf.horror.entity.AnimatronicEntity;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayConnectionEvents;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.client.rendering.v1.HudRenderCallback;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.network.ClientPlayerEntity;
import net.minecraft.client.sound.PositionedSoundInstance;
import net.minecraft.entity.Entity;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.Vec3d;
import net.minecraft.util.math.random.Random;

/**
 * Victim side of a jumpscare, FNAF 1 style: pre-rendered full-screen frames of the animatronic lunging at
 * you (textures/gui/jumpscare, rendered from the mod's models by tools/blender/jumpscares.py) over the
 * locked, shaking camera, with the scream.
 */
public final class JumpscareClient {
	private static final Random RANDOM = Random.create();
	private static int entityId = -1;
	private static int ticks;
	private static int total;
	private static String character;
	private static long startMs;
	private static final int FRAMES = 14, LUNGE = 8;

	public static void init() {
		ClientPlayNetworking.registerGlobalReceiver(AnimatronicEntity.JUMPSCARE_PACKET, (client, handler, buf, sender) -> {
			int id = buf.readVarInt();
			int duration = buf.readVarInt();
			client.execute(() -> {
				entityId = id;
				ticks = total = duration;
				startMs = System.currentTimeMillis();
				Entity e = client.world == null ? null : client.world.getEntityById(id);
				character = e == null ? null : net.minecraft.registry.Registries.ENTITY_TYPE.getId(e.getType()).getPath();
				client.getSoundManager().play(PositionedSoundInstance.master(ModSounds.JUMPSCARE, 1.0f, 1.0f));
			});
		});
		ClientPlayConnectionEvents.DISCONNECT.register((handler, client) -> ticks = 0);
		ClientTickEvents.END_CLIENT_TICK.register(JumpscareClient::tick);
		HudRenderCallback.EVENT.register(JumpscareClient::render);
	}

	private static void tick(MinecraftClient client) {
		if (ticks <= 0) {
			return;
		}
		ticks--;
		ClientPlayerEntity player = client.player;
		Entity e = client.world == null ? null : client.world.getEntityById(entityId);
		if (player == null || e == null) {
			return;
		}
		Vec3d face = e.getPos().add(0, (e instanceof com.fnaf.horror.entity.AnimatronicEntity a ? a.modelHeight() : e.getHeight()) * 0.86, 0);
		Vec3d d = face.subtract(player.getEyePos());
		float yaw = (float) (MathHelper.atan2(d.z, d.x) * (180 / Math.PI)) - 90f;
		float pitch = (float) -(MathHelper.atan2(d.y, Math.sqrt(d.x * d.x + d.z * d.z)) * (180 / Math.PI));
		float shake = ticks > total / 3 ? 2.5f : 5f;
		yaw += (RANDOM.nextFloat() - 0.5f) * shake;
		pitch += (RANDOM.nextFloat() - 0.5f) * shake;
		player.setYaw(yaw);
		player.setPitch(pitch);
		player.prevYaw = yaw;
		player.prevPitch = pitch;
		player.setHeadYaw(yaw);
	}

	private static void render(DrawContext ctx, float tickDelta) {
		if (ticks <= 0) {
			return;
		}
		int w = ctx.getScaledWindowWidth();
		int h = ctx.getScaledWindowHeight();
		if (character != null) {
			// lunge frames at 25 fps, then the shaking, chomping hold loops
			long ms = System.currentTimeMillis() - startMs;
			int f = (int) (ms / 40);
			if (f >= LUNGE) {
				f = LUNGE + (int) ((ms - LUNGE * 40) / 55) % (FRAMES - LUNGE);
			}
			ctx.fill(0, 0, w, h, 0x90000000);
			// cover the screen (frames are 16:9), with a hard shake
			float scale = Math.max(w / 800f, h / 450f) * 1.06f;
			int dw = (int) (800 * scale), dh = (int) (450 * scale);
			int sx = (int) ((RANDOM.nextFloat() - 0.5f) * w * 0.025f), sy = (int) ((RANDOM.nextFloat() - 0.5f) * h * 0.025f);
			com.mojang.blaze3d.systems.RenderSystem.enableBlend();
			ctx.drawTexture(new net.minecraft.util.Identifier("fnaf", "textures/gui/jumpscare/" + character + "_" + f + ".png"),
					(w - dw) / 2 + sx, (h - dh) / 2 + sy, dw, dh, 0, 0, 800, 450, 800, 450);
			com.mojang.blaze3d.systems.RenderSystem.disableBlend();
		}
		if (ticks % 4 < 2) {
			ctx.fill(0, 0, w, h, 0x20B00000);
		}
		for (int i = 0; i < 25; i++) {
			int y = RANDOM.nextInt(h);
			int x = RANDOM.nextInt(w);
			int len = 10 + RANDOM.nextInt(w / 3);
			int g = 120 + RANDOM.nextInt(120);
			ctx.fill(x, y, Math.min(w, x + len), y + 1, (0x50 << 24) | (g << 16) | (g << 8) | g);
		}
		if (ticks < 5) {
			int a = (int) ((5 - ticks) / 5.0f * 255);
			ctx.fill(0, 0, w, h, a << 24);
		}
	}

	private JumpscareClient() {
	}
}
