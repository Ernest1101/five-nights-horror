package com.fnaf.horror.client.render;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.block.MapBlock;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import net.fabricmc.fabric.api.client.rendering.v1.WorldRenderContext;
import net.fabricmc.fabric.api.client.rendering.v1.WorldRenderEvents;
import net.minecraft.block.BlockState;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.render.OverlayTexture;
import net.minecraft.client.render.RenderLayer;
import net.minecraft.client.render.VertexConsumer;
import net.minecraft.client.render.WorldRenderer;
import net.minecraft.client.texture.Sprite;
import net.minecraft.client.texture.SpriteAtlasTexture;
import net.minecraft.client.util.math.MatrixStack;
import net.minecraft.client.world.ClientWorld;
import net.minecraft.screen.PlayerScreenHandler;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.RotationAxis;
import net.minecraft.util.math.Vec3d;
import org.joml.Matrix3f;
import org.joml.Matrix4f;
import org.joml.Vector3f;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.GZIPInputStream;

/**
 * The map's ordinary doors (assets/fnaf/map/fnaf1_doors.bin, built by tools/pizzeria/build_map.py): drawn
 * here instead of in the block mesh so they can swing on their hinge, with their signs and handles. Open
 * or closed comes from the CLOSED state of the door's map cells; the swing is animated on the client.
 */
public final class DoorRenderer {
	private static final class Door {
		BlockPos[] cells;
		float hingeX, hingeZ, openAngle;
		short[] mats;
		float[] verts;               // per triangle 3 x (x y z u v r g b), map coordinates + baked shade
		float angle = Float.NaN;     // current swing, NaN = not shown yet
	}

	private static List<Door> doors;
	private static long lastNanos;

	public static void init() {
		WorldRenderEvents.AFTER_ENTITIES.register(DoorRenderer::render);
	}

	private static synchronized void load() {
		if (doors != null) {
			return;
		}
		List<Door> list = new ArrayList<>();
		try (InputStream raw = DoorRenderer.class.getResourceAsStream("/assets/fnaf/map/fnaf1_doors.bin")) {
			if (raw != null) {
				DataInputStream in = new DataInputStream(new GZIPInputStream(raw, 1 << 16));
				in.readInt();
				in.readInt();
				int n = in.readInt();
				BlockPos o = PizzeriaManager.ORIGIN;
				for (int d = 0; d < n; d++) {
					Door door = new Door();
					door.cells = new BlockPos[in.readShort()];
					for (int i = 0; i < door.cells.length; i++) {
						door.cells[i] = o.add(in.readShort(), in.readShort(), in.readShort());
					}
					door.hingeX = in.readFloat();
					door.hingeZ = in.readFloat();
					door.openAngle = in.readFloat();
					int tris = in.readInt();
					door.mats = new short[tris];
					door.verts = new float[tris * 24];
					for (int t = 0; t < tris; t++) {
						door.mats[t] = in.readShort();
						for (int k = 0; k < 24; k++) {
							door.verts[t * 24 + k] = in.readFloat();
						}
					}
					list.add(door);
				}
			}
		} catch (IOException e) {
			FnafHorror.LOGGER.error("Failed to read map doors", e);
		}
		doors = list;
	}

	private static void render(WorldRenderContext ctx) {
		ClientWorld world = ctx.world();
		if (world == null || world.getRegistryKey() != PizzeriaManager.WORLD || ctx.consumers() == null) {
			return;
		}
		load();
		long now = System.nanoTime();
		float dt = lastNanos == 0 ? 0 : Math.min(0.1f, (now - lastNanos) / 1e9f);
		lastNanos = now;
		Vec3d cam = ctx.camera().getPos();
		MatrixStack ms = ctx.matrixStack();
		BlockPos o = PizzeriaManager.ORIGIN;
		var atlas = MinecraftClient.getInstance().getBakedModelManager().getAtlas(PlayerScreenHandler.BLOCK_ATLAS_TEXTURE);
		VertexConsumer vc = ctx.consumers().getBuffer(RenderLayer.getEntityCutoutNoCull(SpriteAtlasTexture.BLOCK_ATLAS_TEXTURE));
		Vector3f n = new Vector3f();
		Vector3f p = new Vector3f();
		Sprite[] sprites = new Sprite[64];
		for (Door door : doors) {
			BlockState s = world.getBlockState(door.cells[0]);
			if (!(s.getBlock() instanceof MapBlock)) {
				continue;
			}
			double hx = o.getX() + door.hingeX, hz = o.getZ() + door.hingeZ;
			if (cam.squaredDistanceTo(hx, cam.y, hz) > 64 * 64) {
				continue;
			}
			float target = s.get(MapBlock.CLOSED) ? 0f : door.openAngle;
			if (Float.isNaN(door.angle)) {
				door.angle = target;
			}
			float step = 150f * dt;                       // degrees per second
			door.angle += Math.max(-step, Math.min(step, target - door.angle));
			int light = WorldRenderer.getLightmapCoordinates(world, BlockPos.ofFloored(hx, o.getY() + 2, hz));
			ms.push();
			ms.translate(hx - cam.x, o.getY() - cam.y, hz - cam.z);
			ms.multiply(RotationAxis.POSITIVE_Y.rotationDegrees(door.angle));
			Matrix4f pose = ms.peek().getPositionMatrix();
			Matrix3f normal = ms.peek().getNormalMatrix();
			float[] v = door.verts;
			for (int t = 0; t < door.mats.length; t++) {
				int m = door.mats[t];
				Sprite sprite = m < sprites.length ? sprites[m] : null;
				if (sprite == null) {
					sprite = atlas.getSprite(new Identifier(MapModel.spriteId(m)));
					if (m < sprites.length) {
						sprites[m] = sprite;
					}
				}
				int b = t * 24;
				float ax = v[b + 8] - v[b], ay = v[b + 9] - v[b + 1], az = v[b + 10] - v[b + 2];
				float bx = v[b + 16] - v[b], by = v[b + 17] - v[b + 1], bz = v[b + 18] - v[b + 2];
				n.set(ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx);
				if (n.lengthSquared() < 1e-12f) {
					continue;
				}
				n.normalize();
				normal.transform(n);
				for (int k = 0; k < 4; k++) {
					int i = b + Math.min(k, 2) * 8;
					float x = v[i] - door.hingeX, y = v[i + 1], z = v[i + 2] - door.hingeZ;
					pose.transformPosition(x, y, z, p);
					float r = Math.min(1f, v[i + 5] * 0.89f), g = Math.min(1f, v[i + 6] * 0.89f), bl = Math.min(1f, v[i + 7] * 0.89f);
					vc.vertex(p.x, p.y, p.z, r, g, bl, 1f, sprite.getFrameU(v[i + 3] * 16), sprite.getFrameV(v[i + 4] * 16),
							OverlayTexture.DEFAULT_UV, light, n.x, n.y, n.z);
				}
			}
			ms.pop();
		}
	}

	private DoorRenderer() {
	}
}
