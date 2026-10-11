package com.fnaf.horror.client.night;

import com.fnaf.horror.night.Fuel;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.sound.PositionedSoundInstance;
import net.minecraft.client.util.InputUtil;
import net.minecraft.entity.effect.StatusEffects;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.sound.SoundEvent;
import net.minecraft.text.Text;
import net.minecraft.util.math.MathHelper;
import net.minecraft.util.math.RotationAxis;
import org.lwjgl.glfw.GLFW;

import java.util.Random;

/**
 * Refuel minigame at the generator: hold the mouse button (or space) to tip the can. The flow needle has
 * to stay in the green band, which drifts around: too weak a stream dribbles past the funnel, too strong
 * a stream overflows it. Whatever reaches the tank becomes power (Fuel.POWER_PER_CAN per full can).
 */
public class RefuelScreen extends Screen {
	private static final float FLOW = 0.32f;          // cans per second at full tilt
	private final int cans;
	private final float startPower;
	private final Random random = new Random();

	private int can;
	private float canLeft = 1f;
	private float poured;
	private float needle, needleVel;
	private float zone = 0.5f, zoneVel;
	private float flow;
	private boolean inZone;
	private int state;                                 // 0 pouring, 1 done
	private int doneTicks;
	private boolean sent;
	private int pourCd, spillCd;
	private long last = -1;
	private float shake;
	/** Dev screenshots (DevAutoShot "hold <ticks>"): pretend the button is held. */
	public static int debugHoldTicks;

	public RefuelScreen(int cans, float power) {
		super(Text.translatable("screen.fnaf.refuel.title"));
		this.cans = Math.max(1, cans);
		this.startPower = power;
	}

	@Override
	public boolean shouldPause() {
		return false;
	}

	private float zoneWidth() {
		return 0.27f - 0.035f * Math.min(can, 3);
	}

	private boolean holding() {
		MinecraftClient mc = MinecraftClient.getInstance();
		long h = mc.getWindow().getHandle();
		if (debugHoldTicks > 0) {
			return true;
		}
		return InputUtil.isKeyPressed(h, GLFW.GLFW_KEY_SPACE) || GLFW.glfwGetMouseButton(h, GLFW.GLFW_MOUSE_BUTTON_LEFT) == GLFW.GLFW_PRESS;
	}

	private void step(float dt) {
		if (state != 0) {
			return;
		}
		// the needle: tipping the can speeds the stream up, letting go slows it down, with some inertia
		needleVel += (holding() ? 2.6f : -3.0f) * dt;
		needleVel *= Math.max(0f, 1f - 2.5f * dt);
		needle += needleVel * dt;
		if (needle < 0 || needle > 1) {
			needle = MathHelper.clamp(needle, 0, 1);
			needleVel = 0;
		}
		// the good band wanders
		float half = zoneWidth() / 2;
		zoneVel += (random.nextFloat() - 0.5f) * 2.4f * dt;
		zoneVel = MathHelper.clamp(zoneVel, -0.32f - 0.06f * can, 0.32f + 0.06f * can);
		zone += zoneVel * dt;
		if (zone < 0.25f + half || zone > 0.95f - half) {
			zone = MathHelper.clamp(zone, 0.25f + half, 0.95f - half);
			zoneVel = -zoneVel * 0.6f;
		}
		flow = needle < 0.05f ? 0f : needle * FLOW;
		inZone = Math.abs(needle - zone) <= half;
		float eff = inZone ? 1f : needle > zone ? 0.25f : 0.4f;
		float out = Math.min(canLeft, flow * dt);
		canLeft -= out;
		poured += out * eff;
		shake = !inZone && flow > 0 && needle > zone ? Math.min(1f, shake + dt * 4) : Math.max(0f, shake - dt * 3);
		if (canLeft <= 0f) {
			can++;
			if (can >= cans) {
				state = 1;
				doneTicks = 40;
				send();
			} else {
				canLeft = 1f;
				needle = 0;
				needleVel = 0;
				play(ModSounds.FUEL_PICKUP, 1f, 0.8f);
			}
		}
	}

	@Override
	public void tick() {
		if (debugHoldTicks > 0) {
			debugHoldTicks--;
		}
		MinecraftClient mc = MinecraftClient.getInstance();
		if (mc.player == null || !mc.player.isAlive() || !NightClient.active || mc.player.hasStatusEffect(StatusEffects.SLOWNESS)) {
			close();
			return;
		}
		if (state == 1) {
			if (--doneTicks <= 0) {
				close();
			}
			return;
		}
		if (flow > 0.01f && --pourCd <= 0) {
			pourCd = 15;
			play(ModSounds.FUEL_POUR, 0.8f + 0.4f * needle, 0.35f + 0.65f * needle);
		}
		if (flow > 0.04f && !inZone && --spillCd <= 0) {
			spillCd = 9;
			play(ModSounds.FUEL_SPILL, 0.9f + random.nextFloat() * 0.3f, 0.6f);
		}
	}

	private void play(SoundEvent sound, float pitch, float volume) {
		MinecraftClient.getInstance().getSoundManager().play(PositionedSoundInstance.master(sound, pitch, volume));
	}

	/** Cans that were opened are used up, the fuel that reached the tank counts. */
	private void send() {
		if (sent) {
			return;
		}
		sent = true;
		int used = Math.min(cans, can + (canLeft < 0.999f && can < cans ? 1 : 0));
		if (used == 0) {
			return;
		}
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeInt(used);
		buf.writeFloat(poured);
		ClientPlayNetworking.send(Fuel.POUR, buf);
	}

	@Override
	public void close() {
		send();
		super.close();
	}

	@Override
	public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
		long now = System.nanoTime();
		float dt = last < 0 ? 0 : Math.min(0.05f, (now - last) / 1e9f);
		last = now;
		step(dt);

		renderBackground(ctx);
		int w = width, h = height;
		int pw = 300, ph = 190;
		int x0 = (w - pw) / 2, y0 = (h - ph) / 2;
		ctx.fill(x0 - 2, y0 - 2, x0 + pw + 2, y0 + ph + 2, 0xFF3A2A12);
		ctx.fill(x0, y0, x0 + pw, y0 + ph, 0xF0101010);
		ctx.drawCenteredTextWithShadow(textRenderer, title, w / 2, y0 + 7, 0xFFE8C040);

		if (state == 1) {
			NightClient.big(ctx, textRenderer, Text.translatable("screen.fnaf.refuel.done").getString(), w / 2, y0 + ph / 2 - 6, 2f, 0xFFFFE070);
			ctx.drawCenteredTextWithShadow(textRenderer, Text.translatable("screen.fnaf.refuel.power",
					(int) Math.ceil(Math.min(100, startPower + poured * Fuel.POWER_PER_CAN))), w / 2, y0 + ph / 2 + 18, 0xFFFFFFFF);
			return;
		}

		// ---- tank gauge (left)
		int gx = x0 + 16, gy = y0 + 28, gh = 110;
		ctx.fill(gx - 1, gy - 1, gx + 19, gy + gh + 1, 0xFF8A8A8A);
		ctx.fill(gx, gy, gx + 18, gy + gh, 0xFF000000);
		float total = Math.min(100, startPower + poured * Fuel.POWER_PER_CAN) / 100f;
		float base = Math.min(100, startPower) / 100f;
		ctx.fill(gx, gy + gh - (int) (gh * total), gx + 18, gy + gh, 0xFFE0A020);
		ctx.fill(gx, gy + gh - (int) (gh * base), gx + 18, gy + gh, 0xFF9A6A14);
		ctx.drawCenteredTextWithShadow(textRenderer, (int) Math.ceil(total * 100) + "%", gx + 9, gy + gh + 4, 0xFFFFFFFF);

		// ---- picture: can tipping over a funnel into the generator
		int cx = x0 + pw / 2 + 4, funnelY = y0 + 86;
		// generator tank
		ctx.fill(cx - 46, funnelY + 16, cx + 46, funnelY + 40, 0xFF2E3A2A);
		ctx.fill(cx - 46, funnelY + 16, cx + 46, funnelY + 18, 0xFF55664E);
		ctx.drawCenteredTextWithShadow(textRenderer, "GENERATOR", cx, funnelY + 24, 0xFF9AAA90);
		// funnel
		for (int i = 0; i < 14; i++) {
			int half = 16 - i;
			ctx.fill(cx - half, funnelY + i, cx + half, funnelY + i + 1, i < 2 ? 0xFF9A9A9A : 0xFF6A6A6A);
		}
		ctx.fill(cx - 3, funnelY + 14, cx + 3, funnelY + 17, 0xFF6A6A6A);
		// can (rotates around its bottom corner)
		float tilt = 15 + needle * 75;
		float shakeX = shake * (random.nextFloat() - 0.5f) * 3;
		int pivotX = cx - 50, pivotY = y0 + 74;
		ctx.getMatrices().push();
		ctx.getMatrices().translate(pivotX + shakeX, pivotY, 0);
		ctx.getMatrices().multiply(RotationAxis.POSITIVE_Z.rotationDegrees(tilt));
		ctx.fill(-34, -26, 0, 0, 0xFFB02018);                       // body
		ctx.fill(-34, -26, 0, -24, 0xFFD04030);
		ctx.fill(-30, -22, -4, -4, 0xFF961A14);
		ctx.fill(-29, -21, -5, -5, 0xFFB02018);
		for (int i = 0; i < 22; i++) {                                // embossed X
			ctx.fill(-29 + i, -21 + (int) (i * 16 / 22f), -27 + i, -19 + (int) (i * 16 / 22f), 0xFFC83828);
			ctx.fill(-29 + i, -5 - (int) (i * 16 / 22f), -27 + i, -3 - (int) (i * 16 / 22f), 0xFFC83828);
		}
		ctx.fill(-28, -33, -10, -30, 0xFF7A1410);                     // handle
		ctx.fill(-28, -30, -25, -26, 0xFF7A1410);
		ctx.fill(-13, -30, -10, -26, 0xFF7A1410);
		ctx.fill(0, -30, 6, -22, 0xFF2A2A2A);                         // spout
		// fuel level inside, seen through a little window
		int level = (int) (16 * canLeft);
		ctx.fill(-33, -1 - level, -31, -1, 0xFFE0B030);
		ctx.getMatrices().pop();
		// spout tip in screen space
		double rad = Math.toRadians(tilt);
		double sx = pivotX + shakeX + 3 * Math.cos(rad) - (-26) * Math.sin(rad);
		double sy = pivotY + 3 * Math.sin(rad) + (-26) * Math.cos(rad);
		if (flow > 0.005f) {
			// stream: lands short of the funnel when weak, overshoots it when too strong
			float reach = (needle - zone) * 70f;
			int width = 1 + (int) (needle * 4);
			int tx = cx + (int) reach;
			int steps = 18;
			for (int i = 0; i < steps; i++) {
				float t = i / (float) steps;
				int px = (int) MathHelper.lerp(t, (float) sx, tx);
				int py = (int) MathHelper.lerp(t * t, (float) sy, funnelY + 2);
				ctx.fill(px - width / 2, py, px - width / 2 + width, py + 4, 0xC8E8B838);
			}
			if (!inZone) {
				for (int i = 0; i < 6; i++) {                             // splashes on the floor
					int px = tx + random.nextInt(24) - 12, py = funnelY + 10 + random.nextInt(30);
					ctx.fill(px, py, px + 2, py + 2, 0xB0E8C050);
				}
			}
		}

		// ---- cans left (right)
		int kx = x0 + pw - 30;
		for (int i = 0; i < cans; i++) {
			int ky = y0 + 30 + i * 30;
			int col = i < can ? 0xFF3A3A3A : 0xFFB02018;
			ctx.fill(kx, ky, kx + 16, ky + 22, col);
			ctx.fill(kx + 4, ky - 3, kx + 12, ky, i < can ? 0xFF2A2A2A : 0xFF7A1410);
			if (i == can) {
				int lv = (int) (20 * canLeft);
				ctx.fill(kx + 17, ky + 22 - lv, kx + 20, ky + 22, 0xFFE0B030);
				ctx.fill(kx - 3, ky + 9, kx - 1, ky + 13, 0xFFFFFFFF);
			}
		}

		// ---- flow bar
		int bx = x0 + 50, by = y0 + ph - 34, bw = pw - 100, bh = 10;
		float half = zoneWidth() / 2;
		int z1 = bx + (int) (bw * (zone - half)), z2 = bx + (int) (bw * (zone + half));
		ctx.fill(bx - 1, by - 1, bx + bw + 1, by + bh + 1, 0xFF8A8A8A);
		ctx.fill(bx, by, z1, by + bh, 0xFF5A4A18);
		ctx.fill(z1, by, z2, by + bh, inZone ? 0xFF40E040 : 0xFF2A9A2A);
		ctx.fill(z2, by, bx + bw, by + bh, 0xFF8A1A14);
		int nx = bx + (int) (bw * needle);
		ctx.fill(nx - 1, by - 4, nx + 1, by + bh + 4, 0xFFFFFFFF);
		ctx.fill(nx - 3, by - 6, nx + 3, by - 4, 0xFFFFFFFF);
		String status = flow <= 0.005f ? "screen.fnaf.refuel.tip" : inZone ? "screen.fnaf.refuel.good"
				: needle > zone ? "screen.fnaf.refuel.over" : "screen.fnaf.refuel.weak";
		int sc = inZone ? 0xFF60F060 : needle > zone ? ((System.currentTimeMillis() / 150) % 2 == 0 ? 0xFFFF4030 : 0xFFAA2018) : 0xFFE8C040;
		ctx.drawCenteredTextWithShadow(textRenderer, Text.translatable(status), w / 2, by - 14, sc);
		ctx.drawCenteredTextWithShadow(textRenderer, Text.translatable("screen.fnaf.refuel.hint"), w / 2, by + bh + 8, 0xFFAAAAAA);
	}

	@Override
	public boolean mouseClicked(double mouseX, double mouseY, int button) {
		return true;                   // holding is polled; swallow clicks so nothing behind reacts
	}
}
