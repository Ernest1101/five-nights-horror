package com.fnaf.horror.client.render;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.block.GeneratorBlock;
import com.fnaf.horror.block.GeneratorBlockEntity;
import com.fnaf.horror.block.PropBlockEntity;
import com.fnaf.horror.item.FlashlightItem;
import com.fnaf.horror.registry.ModBlocks;
import com.fnaf.horror.registry.ModItems;
import net.fabricmc.fabric.api.client.rendering.v1.BuiltinItemRendererRegistry;
import net.minecraft.block.BlockState;
import net.minecraft.block.HorizontalFacingBlock;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.render.LightmapTextureManager;
import net.minecraft.client.render.RenderLayer;
import net.minecraft.client.render.VertexConsumer;
import net.minecraft.client.render.VertexConsumerProvider;
import net.minecraft.client.render.block.entity.BlockEntityRenderer;
import net.minecraft.client.render.block.entity.BlockEntityRendererFactories;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.Direction;
import net.minecraft.util.math.RotationAxis;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import org.joml.Vector4f;

/**
 * Draws the Blender props (meshes/&lt;name&gt;.fmesh + textures/prop/&lt;name&gt;.png, see tools/blender/props.py):
 * generator and desk fan as block entities, flashlight / generator / fan as items. Mesh space is blocks with
 * the origin at the bottom centre and the front facing +Z (south).
 */
public final class PropRenderers {
	private static final Identifier GENERATOR_TEX = FnafHorror.id("textures/prop/generator.png");
	private static final Identifier FAN_TEX = FnafHorror.id("textures/prop/desk_fan.png");
	private static final Identifier FLASHLIGHT_TEX = FnafHorror.id("textures/prop/flashlight.png");
	/** Blade axis of the fan mesh (Minecraft y, z), see FAN_HUB in props.py. */
	private static final float FAN_HUB_Y = 0.34f, FAN_HUB_Z = 0.02f;

	public static void init() {
		BlockEntityRendererFactories.register(ModBlocks.GENERATOR_ENTITY, ctx -> new GeneratorRenderer());
		BlockEntityRendererFactories.register(ModBlocks.DESK_FAN_ENTITY, ctx -> new FanRenderer());
		BlockEntityRendererFactories.register(ModBlocks.SPARE_HEAD_ENTITY, ctx -> new HeadRenderer());
		BuiltinItemRendererRegistry.INSTANCE.register(ModBlocks.SPARE_HEAD, (stack, mode, matrices, vcp, light, overlay) -> {
			matrices.push();
			matrices.translate(0.5f, 0.1f, 0.5f);
			drawHead(matrices, vcp, 0, light, overlay);
			matrices.pop();
		});
		BuiltinItemRendererRegistry.INSTANCE.register(ModItems.FLASHLIGHT, (stack, mode, matrices, vcp, light, overlay) -> {
			matrices.push();
			matrices.translate(0.5f, 0.5f, 0.5f);
			boolean on = FlashlightItem.isOn(stack);
			VertexConsumer vc = vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(FLASHLIGHT_TEX));
			draw(matrices, vc, "flashlight", "main", light, overlay, 1.0f);
			draw(matrices, vc, "flashlight", "glow", on ? LightmapTextureManager.MAX_LIGHT_COORDINATE : light, overlay, on ? 1.0f : 0.45f);
			matrices.pop();
		});
		BuiltinItemRendererRegistry.INSTANCE.register(ModBlocks.GENERATOR, (stack, mode, matrices, vcp, light, overlay) -> {
			matrices.push();
			matrices.translate(0.5f, 0.15f, 0.5f);
			draw(matrices, vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(GENERATOR_TEX)), "generator", "main", light, overlay, 1.0f);
			matrices.pop();
		});
		BuiltinItemRendererRegistry.INSTANCE.register(ModBlocks.DESK_FAN, (stack, mode, matrices, vcp, light, overlay) -> {
			matrices.push();
			matrices.translate(0.5f, 0.25f, 0.5f);
			VertexConsumer vc = vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(FAN_TEX));
			draw(matrices, vc, "desk_fan", "main", light, overlay, 1.0f);
			draw(matrices, vc, "desk_fan", "spin", light, overlay, 1.0f);
			matrices.pop();
		});
	}

	/** Moves to the block's bottom centre and turns the model's front (+Z) to the block's facing. */
	private static void orient(MatrixStack matrices, BlockState state) {
		matrices.translate(0.5f, 0.0f, 0.5f);
		if (state.contains(HorizontalFacingBlock.FACING)) {
			Direction facing = state.get(HorizontalFacingBlock.FACING);
			matrices.multiply(RotationAxis.POSITIVE_Y.rotationDegrees(-facing.asRotation()));
		}
	}

	private static float time(float tickDelta) {
		MinecraftClient mc = MinecraftClient.getInstance();
		return mc.world == null ? 0 : (mc.world.getTime() % 24000L) + tickDelta;
	}

	static void draw(MatrixStack matrices, VertexConsumer buffer, String mesh, String part, int light, int overlay, float shade) {
		MeshModels.Mesh m = MeshModels.get(mesh);
		MeshModels.Part p = m == null ? null : m.parts().get(part);
		if (p == null) {
			return;
		}
		MatrixStack.Entry entry = matrices.peek();
		Matrix4f pose = entry.getPositionMatrix();
		Matrix3f normalMatrix = entry.getNormalMatrix();
		Vector4f pos = new Vector4f();
		Vector3f normal = new Vector3f();
		float[] v = p.vertices();
		for (int q : p.quads()) {
			int o = q * 8;
			pose.transform(pos.set(v[o], v[o + 1], v[o + 2], 1.0f));
			normalMatrix.transform(normal.set(v[o + 3], v[o + 4], v[o + 5]));
			buffer.vertex(pos.x, pos.y, pos.z, shade, shade, shade, 1.0f, v[o + 6], v[o + 7], overlay, light, normal.x, normal.y, normal.z);
		}
	}

	private static class GeneratorRenderer implements BlockEntityRenderer<GeneratorBlockEntity> {
		@Override
		public void render(GeneratorBlockEntity be, float tickDelta, MatrixStack matrices, VertexConsumerProvider vcp, int light, int overlay) {
			matrices.push();
			orient(matrices, be.getCachedState());
			if (be.getCachedState().get(GeneratorBlock.RUNNING)) {
				// engine vibration
				float t = time(tickDelta);
				matrices.translate(Math.sin(t * 2.9f) * 0.004f, Math.abs(Math.sin(t * 3.7f)) * 0.005f, Math.cos(t * 2.3f) * 0.003f);
			}
			draw(matrices, vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(GENERATOR_TEX)), "generator", "main", light, overlay, 1.0f);
			matrices.pop();
		}
	}

	private static class FanRenderer implements BlockEntityRenderer<PropBlockEntity> {
		@Override
		public void render(PropBlockEntity be, float tickDelta, MatrixStack matrices, VertexConsumerProvider vcp, int light, int overlay) {
			matrices.push();
			orient(matrices, be.getCachedState());
			VertexConsumer vc = vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(FAN_TEX));
			draw(matrices, vc, "desk_fan", "main", light, overlay, 1.0f);
			matrices.translate(0, FAN_HUB_Y, FAN_HUB_Z);
			matrices.multiply(RotationAxis.POSITIVE_Z.rotation(time(tickDelta) * 1.1f + be.getPos().hashCode()));
			matrices.translate(0, -FAN_HUB_Y, -FAN_HUB_Z);
			draw(matrices, vc, "desk_fan", "spin", light, overlay, 1.0f);
			matrices.pop();
		}
	}

	/** Bottom-centre offset and scale of each animatronic's head mesh (head + jaw bones), computed once. */
	private static final java.util.Map<String, float[]> HEAD_FIT = new java.util.HashMap<>();

	/** Draws the head of an animatronic (SpareHeadBlock.IDS[kind]) standing on its neck, face towards +Z. */
	static void drawHead(MatrixStack matrices, VertexConsumerProvider vcp, int kind, int light, int overlay) {
		String id = com.fnaf.horror.block.SpareHeadBlock.IDS[kind];
		MeshModels.Mesh mesh = MeshModels.get(id);
		if (mesh == null) {
			return;
		}
		float[] fit = HEAD_FIT.computeIfAbsent(id, k -> {
			float minX = Float.MAX_VALUE, minY = Float.MAX_VALUE, minZ = Float.MAX_VALUE;
			float maxX = -Float.MAX_VALUE, maxY = -Float.MAX_VALUE, maxZ = -Float.MAX_VALUE;
			for (String part : new String[]{"head", "jaw"}) {
				MeshModels.Part p = mesh.parts().get(part);
				if (p == null) {
					continue;
				}
				float[] v = p.vertices();
				for (int i = 0; i < v.length; i += 8) {
					minX = Math.min(minX, v[i]);
					maxX = Math.max(maxX, v[i]);
					minY = Math.min(minY, v[i + 1]);
					maxY = Math.max(maxY, v[i + 1]);
					minZ = Math.min(minZ, v[i + 2]);
					maxZ = Math.max(maxZ, v[i + 2]);
				}
			}
			float size = Math.max(maxX - minX, Math.max(maxY - minY, maxZ - minZ));
			float scale = size > 0.85f ? 0.85f / size : 1.0f;
			return new float[]{(minX + maxX) / 2, minY, (minZ + maxZ) / 2, scale};
		});
		matrices.push();
		// animatronic models look towards -Z; turn the face to the block's front (+Z)
		matrices.multiply(RotationAxis.POSITIVE_Y.rotationDegrees(180));
		matrices.scale(fit[3], fit[3], fit[3]);
		matrices.translate(-fit[0], -fit[1], -fit[2]);
		VertexConsumer vc = vcp.getBuffer(RenderLayer.getEntityCutoutNoCull(FnafHorror.id("textures/entity/" + id + "_hd.png")));
		draw(matrices, vc, id, "head", light, overlay, 0.9f);
		draw(matrices, vc, id, "jaw", light, overlay, 0.9f);
		matrices.pop();
	}

	private static class HeadRenderer implements BlockEntityRenderer<PropBlockEntity> {
		@Override
		public void render(PropBlockEntity be, float tickDelta, MatrixStack matrices, VertexConsumerProvider vcp, int light, int overlay) {
			matrices.push();
			orient(matrices, be.getCachedState());
			drawHead(matrices, vcp, be.getCachedState().get(com.fnaf.horror.block.SpareHeadBlock.KIND), light, overlay);
			matrices.pop();
		}
	}

	private PropRenderers() {
	}
}
