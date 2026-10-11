package com.fnaf.horror.client.mixin;

import com.fnaf.horror.client.lobby.LobbyClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.hud.InGameHud;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Hides the vanilla HUD in the main menu lobby and during FNAF nights. */
@Mixin(InGameHud.class)
public abstract class InGameHudMixin {
	@Inject(method = "renderHotbar", at = @At("HEAD"), cancellable = true)
	private void fnaf$hideHotbar(float tickDelta, DrawContext context, CallbackInfo ci) {
		// in a blackout the hotbar comes back: flashlight and petrol cans
		if (fnaf$hide() && !com.fnaf.horror.client.night.NightClient.blackout) ci.cancel();
	}

	@Inject(method = "renderStatusBars", at = @At("HEAD"), cancellable = true)
	private void fnaf$hideStatusBars(DrawContext context, CallbackInfo ci) {
		if (fnaf$hide()) ci.cancel();
	}

	@Inject(method = "renderExperienceBar", at = @At("HEAD"), cancellable = true)
	private void fnaf$hideExperience(DrawContext context, int x, CallbackInfo ci) {
		if (fnaf$hide()) ci.cancel();
	}

	@Inject(method = "renderCrosshair", at = @At("HEAD"), cancellable = true)
	private void fnaf$hideCrosshair(DrawContext context, CallbackInfo ci) {
		if (LobbyClient.isInLobby() || com.fnaf.horror.client.night.CameraScreen.isOpen()) ci.cancel();
	}

	/** No hotbar, hearts or XP in the lobby and during a night (FNAF has no inventory). */
	private static boolean fnaf$hide() {
		return LobbyClient.isInLobby() || com.fnaf.horror.client.night.NightClient.active;
	}
}
