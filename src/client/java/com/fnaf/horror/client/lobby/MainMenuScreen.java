package com.fnaf.horror.client.lobby;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.client.night.NightClient;
import com.fnaf.horror.lobby.LobbyManager;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.client.networking.v1.ClientPlayNetworking;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.sound.PositionedSoundInstance;
import net.minecraft.client.sound.SoundInstance;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.text.Text;
import net.minecraft.util.Identifier;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * FNAF-style title screen shown while the player is in the lobby: a flickering Freddy face in static,
 * the title, and New Game / Continue / 6th Night (+ the free-roam pizzeria). New Game shows the
 * help-wanted newspaper first.
 */
public class MainMenuScreen extends Screen {
	private static final Identifier[] FACES = {FnafHorror.id("textures/gui/menu_freddy_0.png"), FnafHorror.id("textures/gui/menu_freddy_1.png")};
	private static final Identifier PAPER = FnafHorror.id("textures/gui/newspaper.png");
	private static final Random RANDOM = new Random();

	private record Item(String label, int mode) {
	}

	private final int beaten;
	private final List<Item> items = new ArrayList<>();
	private int selected;
	private int age;
	private int face;
	private int faceTicks;
	private float faceAlpha = 0.7f;
	private int faceShift;
	private int paperTicks = -1;
	private SoundInstance music;

	public MainMenuScreen(int beaten) {
		super(Text.literal("Five Nights at Freddy's"));
		this.beaten = beaten;
		items.add(new Item("New Game", LobbyManager.MODE_NEW_GAME));
		items.add(new Item("Continue", LobbyManager.MODE_CONTINUE));
		if (beaten >= 5) {
			items.add(new Item("6th Night", LobbyManager.MODE_SIXTH_NIGHT));
		}
		items.add(new Item("Free Roam", LobbyManager.MODE_FREE_ROAM));
		selected = beaten > 0 ? 1 : 0;
	}

	@Override
	public boolean shouldPause() {
		return false;
	}

	@Override
	public boolean shouldCloseOnEsc() {
		return false;
	}

	@Override
	public void tick() {
		age++;
		var sounds = MinecraftClient.getInstance().getSoundManager();
		if (music == null || !sounds.isPlaying(music)) {
			music = PositionedSoundInstance.master(ModSounds.MENU_MUSIC, 1.0f, 0.7f);
			sounds.play(music);
		}
		// the face flickers, sometimes twitches into another frame
		if (--faceTicks <= 0) {
			boolean twitch = RANDOM.nextInt(12) == 0;
			face = twitch ? 1 : 0;
			faceTicks = twitch ? 2 + RANDOM.nextInt(3) : 3 + RANDOM.nextInt(10);
			faceAlpha = 0.45f + RANDOM.nextFloat() * 0.4f;
			faceShift = RANDOM.nextInt(10) == 0 ? RANDOM.nextInt(9) - 4 : 0;
			if (twitch) {
				sounds.play(PositionedSoundInstance.master(ModSounds.CAM_SWITCH, 0.8f, 0.25f));
			}
		}
		if (paperTicks >= 0 && ++paperTicks > 200) {
			start(LobbyManager.MODE_NEW_GAME);
		}
	}

	@Override
	public void render(DrawContext ctx, int mouseX, int mouseY, float delta) {
		int w = width, h = height;
		ctx.fill(0, 0, w, h, 0xFF000000);
		if (paperTicks >= 0) {
			int size = Math.min(w, h) - 20;
			float a = Math.min(1f, paperTicks / 20f) * Math.min(1f, (200 - paperTicks) / 20f);
			ctx.setShaderColor(a, a, a, 1f);
			ctx.drawTexture(PAPER, (w - size) / 2, (h - size) / 2, 0, 0, size, size, size, size);
			ctx.setShaderColor(1f, 1f, 1f, 1f);
			return;
		}
		int fh = h;
		int fw = h;
		int fx = w - fw + faceShift * 3;
		ctx.setShaderColor(faceAlpha, faceAlpha, faceAlpha, 1f);
		ctx.drawTexture(FACES[face], fx, 0, 0, 0, fw, fh, fw, fh);
		ctx.setShaderColor(1f, 1f, 1f, 1f);
		for (int y = 0; y < h; y += 3) {
			ctx.fill(0, y, w, y + 1, 0x22000000);
		}
		NightClient.staticNoise(ctx, w, h, 1400, RANDOM.nextInt(30) == 0 ? 0xC0 : 0x50);

		String[] title = {"Five", "Nights", "at", "Freddy's"};
		for (int i = 0; i < title.length; i++) {
			ctx.getMatrices().push();
			ctx.getMatrices().translate(30, 30 + i * 26, 0);
			ctx.getMatrices().scale(2.6f, 2.6f, 1f);
			ctx.drawText(textRenderer, title[i], 0, 0, 0xFFFFFFFF, false);
			ctx.getMatrices().pop();
		}
		int y0 = h - 30 - items.size() * 22;
		for (int i = 0; i < items.size(); i++) {
			int y = y0 + i * 22;
			if (mouseX >= 20 && mouseX < 180 && mouseY >= y - 4 && mouseY < y + 16) {
				selected = i;
			}
			ctx.getMatrices().push();
			ctx.getMatrices().translate(50, y, 0);
			ctx.getMatrices().scale(1.6f, 1.6f, 1f);
			ctx.drawText(textRenderer, items.get(i).label(), 0, 0, 0xFFFFFFFF, false);
			ctx.getMatrices().pop();
			if (i == selected) {
				ctx.drawText(textRenderer, ">>", 28, y + 3, 0xFFFFFFFF, false);
				if (items.get(i).mode() == LobbyManager.MODE_CONTINUE) {
					ctx.drawText(textRenderer, "Night " + Math.max(1, Math.min(beaten + 1, 5)), 150, y + 3, 0xFFBBBBBB, false);
				}
			}
		}
		ctx.drawText(textRenderer, "C - cameras   click the red / white buttons for doors / lights", 10, h - 12, 0x80FFFFFF, false);
	}

	@Override
	public boolean mouseClicked(double mouseX, double mouseY, int button) {
		if (paperTicks >= 0) {
			if (paperTicks > 30) {
				start(LobbyManager.MODE_NEW_GAME);
			}
			return true;
		}
		int y0 = height - 30 - items.size() * 22;
		for (int i = 0; i < items.size(); i++) {
			int y = y0 + i * 22;
			if (mouseX >= 20 && mouseX < 180 && mouseY >= y - 4 && mouseY < y + 16) {
				choose(i);
				return true;
			}
		}
		return false;
	}

	@Override
	public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
		if (keyCode == 265) {             // up
			selected = (selected + items.size() - 1) % items.size();
			return true;
		}
		if (keyCode == 264) {             // down
			selected = (selected + 1) % items.size();
			return true;
		}
		if (keyCode == 257 || keyCode == 335 || keyCode == 32) {
			if (paperTicks >= 0) {
				start(LobbyManager.MODE_NEW_GAME);
			} else {
				choose(selected);
			}
			return true;
		}
		return false;
	}

	private void choose(int i) {
		Item item = items.get(i);
		if (item.mode() == LobbyManager.MODE_NEW_GAME) {
			paperTicks = 0;
			return;
		}
		start(item.mode());
	}

	private void start(int mode) {
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeInt(mode);
		ClientPlayNetworking.send(LobbyManager.START, buf);
		LobbyClient.leave();
		close();
	}

	@Override
	public void removed() {
		if (music != null) {
			MinecraftClient.getInstance().getSoundManager().stop(music);
		}
	}
}
