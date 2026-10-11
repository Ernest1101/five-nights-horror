package com.fnaf.horror.client;

import com.fnaf.horror.client.lobby.LobbyClient;
import com.fnaf.horror.client.render.AnimatronicRenderer;
import com.fnaf.horror.client.render.MeshModels;
import com.fnaf.horror.client.render.PropRenderers;
import com.fnaf.horror.registry.ModBlocks;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.blockrenderlayer.v1.BlockRenderLayerMap;
import net.fabricmc.fabric.api.client.rendering.v1.EntityRendererRegistry;
import net.fabricmc.fabric.api.resource.ResourceManagerHelper;
import net.minecraft.client.render.RenderLayer;
import net.minecraft.resource.ResourceType;
import com.fnaf.horror.registry.ModEntities;

public class FnafHorrorClient implements ClientModInitializer {
	@Override
	public void onInitializeClient() {
		for (ModEntities.Animatronic a : ModEntities.ALL) {
			float shadow = a.type().getWidth() * 0.6f;
			EntityRendererRegistry.register(a.type(), ctx -> new AnimatronicRenderer(ctx, a.id(), shadow));
		}
		ResourceManagerHelper.get(ResourceType.CLIENT_RESOURCES).registerReloadListener(new MeshModels());
		BlockRenderLayerMap.INSTANCE.putBlocks(RenderLayer.getCutout(), ModBlocks.PARTY_HAT, ModBlocks.CONFETTI, ModBlocks.PLATE,
				ModBlocks.STREAMER, ModBlocks.COBWEB, ModBlocks.PAPERS, ModBlocks.STALL_DOOR, ModBlocks.SECURITY_DOOR);
		BlockRenderLayerMap.INSTANCE.putBlocks(RenderLayer.getTranslucent(), ModBlocks.OFFICE_WINDOW);
		BlockRenderLayerMap.INSTANCE.putBlock(ModBlocks.MAP_BLOCK, RenderLayer.getCutoutMipped());
		net.fabricmc.fabric.api.client.model.loading.v1.ModelLoadingPlugin.register(ctx -> ctx.resolveModel().register(
				c -> c.id().equals(com.fnaf.horror.client.render.MapModel.ID) ? new com.fnaf.horror.client.render.MapModel() : null));
		PropRenderers.init();
		com.fnaf.horror.client.render.DoorRenderer.init();
		LobbyClient.init();
		com.fnaf.horror.client.night.NightClient.init();
		JumpscareClient.init();
		DevAutoShot.init();
	}
}
