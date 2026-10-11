package com.fnaf.horror.client.render;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.entity.AnimatronicEntity;
import net.minecraft.client.render.VertexConsumer;
import net.minecraft.client.render.entity.EntityRendererFactory;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.MathHelper;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;
import org.joml.Vector4f;
import software.bernie.geckolib.cache.object.GeoBone;
import software.bernie.geckolib.constant.DataTickets;
import software.bernie.geckolib.core.animatable.model.CoreGeoBone;
import software.bernie.geckolib.core.animation.AnimationState;
import software.bernie.geckolib.model.DefaultedEntityGeoModel;
import software.bernie.geckolib.model.data.EntityModelData;
import software.bernie.geckolib.renderer.GeoEntityRenderer;
import software.bernie.geckolib.renderer.layer.AutoGlowingGeoLayer;

/**
 * Renders any animatronic from assets/fnaf/{geo,animations,textures}/entity/&lt;id&gt;.
 * GeckoLib still drives the skeleton and animations; when a realistic Blender mesh
 * (meshes/&lt;id&gt;.fmesh + textures/entity/&lt;id&gt;_hd.png) exists, each bone draws its mesh
 * part instead of its cubes. Eyes glow through the matching _glowmask texture.
 */
public class AnimatronicRenderer extends GeoEntityRenderer<AnimatronicEntity> {
	private final String id;
	private final Identifier hdTexture;
	private final Identifier glowTexture;
	/** Eye quads seen during this frame's pass, drawn emissive in renderFinal. */
	private final java.util.List<Object[]> pendingGlow = new java.util.ArrayList<>();
	private final Vector4f pos = new Vector4f();
	private final Vector3f normal = new Vector3f();

	public AnimatronicRenderer(EntityRendererFactory.Context ctx, String id, float shadowRadius) {
		super(ctx, new Model(id));
		this.id = id;
		this.hdTexture = FnafHorror.id("textures/entity/" + id + "_hd.png");
		this.shadowRadius = shadowRadius;
		this.glowTexture = FnafHorror.id("textures/entity/" + id + "_hd_glowmask.png");
	}

	@Override
	public Identifier getTextureLocation(AnimatronicEntity animatable) {
		return MeshModels.get(id) != null ? hdTexture : super.getTextureLocation(animatable);
	}

	@Override
	public void renderCubesOfBone(MatrixStack poseStack, GeoBone bone, VertexConsumer buffer, int packedLight,
								  int packedOverlay, float red, float green, float blue, float alpha) {
		MeshModels.Mesh mesh = MeshModels.get(id);
		if (mesh == null) {
			super.renderCubesOfBone(poseStack, bone, buffer, packedLight, packedOverlay, red, green, blue, alpha);
			return;
		}
		MeshModels.Part part = mesh.parts().get(bone.getName());
		if (part == null) {
			return;
		}
		MatrixStack.Entry entry = poseStack.peek();
		Matrix4f positionMatrix = entry.getPositionMatrix();
		Matrix3f normalMatrix = entry.getNormalMatrix();
		emit(buffer, positionMatrix, normalMatrix, part.vertices(), part.quads(), packedLight, packedOverlay, red, green, blue, alpha);
		if (part.glowQuads().length > 0) {
			pendingGlow.add(new Object[]{new Matrix4f(positionMatrix), new Matrix3f(normalMatrix), part});
		}
	}

	private void emit(VertexConsumer buffer, Matrix4f positionMatrix, Matrix3f normalMatrix, float[] v, int[] quads, int light, int overlay,
					  float red, float green, float blue, float alpha) {
		for (int q : quads) {
			int o = q * 8;
			positionMatrix.transform(pos.set(v[o], v[o + 1], v[o + 2], 1.0f));
			normalMatrix.transform(normal.set(v[o + 3], v[o + 4], v[o + 5]));
			buffer.vertex(pos.x, pos.y, pos.z, red, green, blue, alpha, v[o + 6], v[o + 7], overlay, light, normal.x, normal.y, normal.z);
		}
	}

	@Override
	public void preRender(MatrixStack poseStack, AnimatronicEntity animatable, software.bernie.geckolib.cache.object.BakedGeoModel model,
						  net.minecraft.client.render.VertexConsumerProvider bufferSource, VertexConsumer buffer, boolean isReRender,
						  float partialTick, int packedLight, int packedOverlay, float red, float green, float blue, float alpha) {
		pendingGlow.clear();
		super.preRender(poseStack, animatable, model, bufferSource, buffer, isReRender, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
	}

	/** Glowing eyes: only the quads that touch lit glowmask texels, full bright, after the main pass. */
	@Override
	public void renderFinal(MatrixStack poseStack, AnimatronicEntity animatable, software.bernie.geckolib.cache.object.BakedGeoModel model,
							net.minecraft.client.render.VertexConsumerProvider bufferSource, VertexConsumer buffer, float partialTick,
							int packedLight, int packedOverlay, float red, float green, float blue, float alpha) {
		super.renderFinal(poseStack, animatable, model, bufferSource, buffer, partialTick, packedLight, packedOverlay, red, green, blue, alpha);
		if (pendingGlow.isEmpty()) {
			return;
		}
		VertexConsumer glow = bufferSource.getBuffer(net.minecraft.client.render.RenderLayer.getEyes(glowTexture));
		for (Object[] g : pendingGlow) {
			MeshModels.Part part = (MeshModels.Part) g[2];
			emit(glow, (Matrix4f) g[0], (Matrix3f) g[1], part.vertices(), part.glowQuads(), 0xF000F0,
					net.minecraft.client.render.OverlayTexture.DEFAULT_UV, 1, 1, 1, 1);
		}
		pendingGlow.clear();
	}

	/**
	 * Head look is added on top of the animated/rest rotation instead of replacing it,
	 * so idle head twitches and posed heads (Golden Freddy's slump) survive.
	 */
	private static class Model extends DefaultedEntityGeoModel<AnimatronicEntity> {
		Model(String id) {
			super(FnafHorror.id(id), false);
		}

		@Override
		public void setCustomAnimations(AnimatronicEntity animatable, long instanceId, AnimationState<AnimatronicEntity> state) {
			super.setCustomAnimations(animatable, instanceId, state);
			CoreGeoBone head = getAnimationProcessor().getBone("head");
			EntityModelData data = state.getData(DataTickets.ENTITY_MODEL_DATA);
			if (head != null && data != null) {
				head.setRotX(head.getRotX() + data.headPitch() * MathHelper.RADIANS_PER_DEGREE);
				head.setRotY(head.getRotY() + data.netHeadYaw() * MathHelper.RADIANS_PER_DEGREE);
			}
		}
	}
}
