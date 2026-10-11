package com.fnaf.horror.client.night;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.night.NightLayout;
import com.fnaf.horror.night.NightManager;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.sound.PositionedSoundInstance;
import net.minecraft.entity.decoration.ArmorStandEntity;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.sound.SoundEvent;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.MathHelper;

import java.util.List;

/**
 * The security camera tablet. The game camera is moved to the chosen security camera (a client-only
 * invisible armor stand, slowly panning like the FNAF cams); the screen draws static, the recording dot,
 * the room name and the camera map with its buttons. The server is told which camera is watched.
 */
public class CameraScreen extends Screen {
	private static final Identifier MAP = FnafHorror.id("textures/gui/cam_map.png");
	private static int current;
	private ArmorStandEntity eye;
	private int glitchTicks = 8;
	private int age;

	public CameraScreen() {
		super(Text.literal("Cameras"));
	}

	@Override
	protected void init() {
		if (eye == null) {
			play(ModSounds.CAM_OPEN, 1f);
			select(current, false);
		}
	}

	@Override
	public boolean shouldPause() {
		return false;
	}

	public void glitch(int cam) {
		if (cam == current) {
			glitchTicks = 12;
			play(ModSounds.CAM_SWITCH, 0.6f);
		}
	}

	private void select(int cam, boolean sound) {
		List<NightLayout.Camera> cams = NightLayout.cameras();
		if (cams.isEmpty()) {
			return;
		}
		current = MathHelper.clamp(cam, 0, cams.size() - 1);
		glitchTicks = 8;
		if (sound) {
			play(ModSounds.CAM_SWITCH, 1f);
		}
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeInt(current);
		ClientPlayNetworking.send(NightManager.CAMERA, buf);
		MinecraftClient mc = MinecraftClient.getInstance();
		NightLayout.Camera c = cams.get(current);
		if (c.pos() == null || mc.world == null) {
			mc.setCameraEntity(mc.player);
			return;
		}
		if (eye == null) {
			eye = new ArmorStandEntity(mc.world, c.pos().x, c.pos().y, c.pos().z);
			eye.setInvisible(true);
		}
		aim(c, 0);
		mc.setCameraEntity(eye);
	}

	/** Positions the camera entity so its eyes sit at the camera, panning slowly left and right. */
	private void aim(NightLayout.Camera c, float tickDelta) {
		float pan = 18f * MathHelper.sin((age + tickDelta) * 0.012f);
		double y = c.pos().y - eye.getStandingEyeHeight();
		eye.refreshPositionAndAngles(c.pos().x, y, c.pos().z, c.yaw() + pan, c.pitch());
		eye.setHeadYaw(c.yaw() + pan);
		eye.prevYaw = eye.getYaw();
		eye.prevPitch = eye.getPitch();
	}

	@Override
	public void tick() {
		age++;
		if (glitchTicks > 0) {
			glitchTicks--;
		}
		if (!NightClient.active || NightClient.blackout) {
			close();
		}
	}

	@Override
	public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
		List<NightLayout.Camera> cams = NightLayout.cameras();
		if (cams.isEmpty()) {
			return;
		}
		NightLayout.Camera c = cams.get(current);
		if (c.pos() != null && eye != null) {
			aim(c, delta);
		}
		int w = width, h = height;
		if (c.pos() == null) {
			ctx.fill(0, 0, w, h, 0xFF000000);
			NightClient.big(ctx, textRenderer, "-CAMERA DISABLED-", w / 2, h / 2 - 20, 1.6f, 0xFFFFFFFF);
			NightClient.big(ctx, textRenderer, "AUDIO ONLY", w / 2, h / 2 + 4, 1.6f, 0xFFFFFFFF);
		}
		// tinted, scanlined, noisy camera image
		ctx.fill(0, 0, w, h, 0x18203018);
		for (int y = 0; y < h; y += 3) {
			ctx.fill(0, y, w, y + 1, 0x14000000);
		}
		NightClient.staticNoise(ctx, w, h, glitchTicks > 0 ? 2600 : 350, glitchTicks > 0 ? 0xD0 : 0x40);
		if (glitchTicks > 4) {
			ctx.fill(0, 0, w, h, 0x90000000);
			NightClient.staticNoise(ctx, w, h, 2600, 0xE0);
		}
		// frame + recording dot
		int b = 6;
		ctx.fill(b, b, w - b, b + 1, 0x90FFFFFF);
		ctx.fill(b, h - b - 1, w - b, h - b, 0x90FFFFFF);
		ctx.fill(b, b, b + 1, h - b, 0x90FFFFFF);
		ctx.fill(w - b - 1, b, w - b, h - b, 0x90FFFFFF);
		if ((age / 15) % 2 == 0) {
			ctx.fill(18, 18, 30, 30, 0xFFE02020);
		}
		ctx.drawTextWithShadow(textRenderer, "REC", 36, 20, 0xFFFFFFFF);
		// camera map with buttons
		int size = Math.min(170, h / 2);
		int mx = w - size - 14, my = h - size - 14;
		ctx.fill(mx - 4, my - 18, mx + size + 4, my + size + 4, 0x70000000);
		ctx.drawTexture(MAP, mx, my, 0, 0, size, size, size, size);
		NightClient.big(ctx, textRenderer, c.label(), mx + size / 2, my - 9, 1.3f, 0xFFFFFFFF);
		float scale = size / (float) NightLayout.mapSize();
		for (int i = 0; i < cams.size(); i++) {
			int[] r = button(cams.get(i), mx, my, scale);
			boolean sel = i == current;
			boolean hover = mouseX >= r[0] && mouseX < r[2] && mouseY >= r[1] && mouseY < r[3];
			ctx.fill(r[0], r[1], r[2], r[3], sel ? 0xE0A0C020 : hover ? 0xE0707070 : 0xE0404040);
			ctx.drawBorder(r[0], r[1], r[2] - r[0], r[3] - r[1], 0xFFFFFFFF);
			String label = "CAM " + cams.get(i).id();
			ctx.getMatrices().push();
			ctx.getMatrices().translate((r[0] + r[2]) / 2f, (r[1] + r[3]) / 2f, 0);
			ctx.getMatrices().scale(0.6f, 0.6f, 1f);
			ctx.drawText(textRenderer, label, -textRenderer.getWidth(label) / 2, -4, 0xFFFFFFFF, false);
			ctx.getMatrices().pop();
		}
		NightClient.hud(ctx, textRenderer, w, h);
		super.render(ctx, mouseX, mouseY, delta);
	}

	private static int[] button(NightLayout.Camera c, int mx, int my, float scale) {
		int x = mx + (int) (c.targetX() * scale), y = my + (int) (c.targetZ() * scale);
		return new int[]{x - 15, y - 6, x + 15, y + 6};
	}

	@Override
	public boolean mouseClicked(double mouseX, double mouseY, int button) {
		List<NightLayout.Camera> cams = NightLayout.cameras();
		int size = Math.min(170, height / 2);
		int mx = width - size - 14, my = height - size - 14;
		float scale = size / (float) NightLayout.mapSize();
		for (int i = 0; i < cams.size(); i++) {
			int[] r = button(cams.get(i), mx, my, scale);
			if (mouseX >= r[0] && mouseX < r[2] && mouseY >= r[1] && mouseY < r[3]) {
				if (i != current) {
					select(i, true);
				}
				return true;
			}
		}
		return super.mouseClicked(mouseX, mouseY, button);
	}

	@Override
	public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
		if (NightClient.cameraKey.matchesKey(keyCode, scanCode)) {
			close();
			return true;
		}
		// arrows / A-D cycle through the cameras
		if (keyCode == 262 || keyCode == 68) {
			select((current + 1) % NightLayout.cameras().size(), true);
			return true;
		}
		if (keyCode == 263 || keyCode == 65) {
			select((current + NightLayout.cameras().size() - 1) % NightLayout.cameras().size(), true);
			return true;
		}
		return super.keyPressed(keyCode, scanCode, modifiers);
	}

	@Override
	public void removed() {
		MinecraftClient mc = MinecraftClient.getInstance();
		mc.setCameraEntity(mc.player);
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeInt(-1);
		if (mc.getNetworkHandler() != null) {
			ClientPlayNetworking.send(NightManager.CAMERA, buf);
		}
		play(ModSounds.CAM_CLOSE, 1f);
		eye = null;
	}

	private static void play(SoundEvent sound, float volume) {
		MinecraftClient.getInstance().getSoundManager().play(PositionedSoundInstance.master(sound, 1.0f, volume));
	}

	/** Dev helper (autoshot): opens the tablet on a given camera. */
	public static void debugOpen(int cam) {
		current = cam;
		MinecraftClient mc = MinecraftClient.getInstance();
		if (mc.currentScreen instanceof CameraScreen open) {
			open.select(cam, true);
		} else {
			mc.setScreen(new CameraScreen());
		}
	}

	public static boolean isOpen() {
		return MinecraftClient.getInstance().currentScreen instanceof CameraScreen;
	}
}
