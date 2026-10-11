package com.fnaf.horror.client.render;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import net.fabricmc.fabric.api.renderer.v1.Renderer;
import net.fabricmc.fabric.api.renderer.v1.RendererAccess;
import net.fabricmc.fabric.api.renderer.v1.material.BlendMode;
import net.fabricmc.fabric.api.renderer.v1.material.RenderMaterial;
import net.fabricmc.fabric.api.renderer.v1.mesh.MutableQuadView;
import net.fabricmc.fabric.api.renderer.v1.mesh.QuadEmitter;
import net.fabricmc.fabric.api.renderer.v1.model.FabricBakedModel;
import net.fabricmc.fabric.api.renderer.v1.render.RenderContext;
import net.fabricmc.fabric.api.util.TriState;
import net.minecraft.block.BlockState;
import net.minecraft.client.render.model.BakedModel;
import net.minecraft.client.render.model.BakedQuad;
import net.minecraft.client.render.model.Baker;
import net.minecraft.client.render.model.ModelBakeSettings;
import net.minecraft.client.render.model.UnbakedModel;
import net.minecraft.client.render.model.json.ModelOverrideList;
import net.minecraft.client.render.model.json.ModelTransformation;
import net.minecraft.client.texture.Sprite;
import net.minecraft.client.util.SpriteIdentifier;
import net.minecraft.screen.PlayerScreenHandler;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Direction;
import net.minecraft.util.math.random.Random;
import net.minecraft.world.BlockRenderView;
import org.jetbrains.annotations.Nullable;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.function.Supplier;
import java.util.zip.GZIPInputStream;

/**
 * Block model of fnaf:map_block: emits the triangles of the downloaded FNAF 1 map that lie inside the
 * block's cell (assets/fnaf/map/fnaf1.fmap, built by tools/pizzeria/build_map.py). Minecraft then meshes,
 * caches and lights them like any other block geometry.
 */
public class MapModel implements UnbakedModel, BakedModel, FabricBakedModel {
	public static final Identifier ID = FnafHorror.id("block/map_block");
	/** Set on the material index of triangles that belong to an office door (see build_map.py). */
	private static final int DOOR_BIT = 0x4000;

	/**
	 * Per cell: material index per quad, 4 vertices of packed (x y z) in 1/2048 block and (u v) in 1/65535
	 * (unsigned) as shorts, and the baked shade colour (ARGB) of every vertex.
	 */
	private record Cell(short[] mats, short[] verts, int[] colors) {
	}

	private static Map<Long, Cell> cells;
	private static String[] spriteIds = new String[0];
	private static int[] flags = new int[0];
	private Sprite[] sprites = new Sprite[0];
	private RenderMaterial[] materials = new RenderMaterial[0];

	/** Sprite id of a map material (shared with the door renderer). */
	public static String spriteId(int material) {
		load();
		return material >= 0 && material < spriteIds.length ? spriteIds[material] : "fnaf:block/map/palette";
	}

	private static synchronized void load() {
		if (cells != null) {
			return;
		}
		Map<Long, Cell> map = new HashMap<>();
		try (InputStream raw = MapModel.class.getResourceAsStream("/assets/fnaf/map/fnaf1.fmap")) {
			if (raw != null) {
				DataInputStream in = new DataInputStream(new GZIPInputStream(raw, 1 << 16));
				in.readInt();
				in.readInt();
				int nTex = in.readInt();
				spriteIds = new String[nTex];
				flags = new int[nTex];
				for (int i = 0; i < nTex; i++) {
					byte[] b = new byte[in.readShort()];
					in.readFully(b);
					spriteIds[i] = new String(b, java.nio.charset.StandardCharsets.UTF_8);
					flags[i] = in.readByte();
				}
				int n = in.readInt();
				for (int c = 0; c < n; c++) {
					int x = in.readShort(), y = in.readShort(), z = in.readShort();
					int quads = in.readInt();
					short[] mats = new short[quads];
					short[] verts = new short[quads * 20];
					int[] colors = new int[quads * 4];
					for (int t = 0; t < quads; t++) {
						mats[t] = in.readShort();
						for (int k = 0; k < 4; k++) {
							int o = t * 20 + k * 5;
							for (int j = 0; j < 5; j++) {
								verts[o + j] = in.readShort();
							}
							colors[t * 4 + k] = 0xFF000000 | in.readUnsignedByte() << 16 | in.readUnsignedByte() << 8 | in.readUnsignedByte();
						}
					}
					map.put(BlockPos.asLong(x, y, z), new Cell(mats, verts, colors));
				}
			}
		} catch (IOException e) {
			FnafHorror.LOGGER.error("Failed to read map geometry", e);
		}
		FnafHorror.LOGGER.info("Loaded map geometry for {} cells", map.size());
		cells = map;
	}

	// ---------------------------------------------------------------- unbaked

	@Override
	public Collection<Identifier> getModelDependencies() {
		return Collections.emptyList();
	}

	@Override
	public void setParents(Function<Identifier, UnbakedModel> modelLoader) {
	}

	@Nullable
	@Override
	public BakedModel bake(Baker baker, Function<SpriteIdentifier, Sprite> textureGetter, ModelBakeSettings rotationContainer, Identifier modelId) {
		load();
		sprites = new Sprite[spriteIds.length];
		materials = new RenderMaterial[spriteIds.length];
		Renderer renderer = RendererAccess.INSTANCE.getRenderer();
		for (int i = 0; i < spriteIds.length; i++) {
			sprites[i] = textureGetter.apply(new SpriteIdentifier(PlayerScreenHandler.BLOCK_ATLAS_TEXTURE, new Identifier(spriteIds[i])));
			boolean emissive = (flags[i] & 2) != 0;
			var finder = renderer.materialFinder().blendMode(BlendMode.CUTOUT_MIPPED);
			if (emissive) {
				finder.emissive(true).disableDiffuse(true).ambientOcclusion(TriState.FALSE);
			}
			materials[i] = finder.find();
		}
		return this;
	}

	// ---------------------------------------------------------------- baked

	@Override
	public boolean isVanillaAdapter() {
		return false;
	}

	@Override
	public void emitBlockQuads(BlockRenderView blockView, BlockState state, BlockPos pos, Supplier<Random> randomSupplier, RenderContext context) {
		BlockPos o = PizzeriaManager.ORIGIN;
		Cell cell = cells == null ? null : cells.get(BlockPos.asLong(pos.getX() - o.getX(), pos.getY() - o.getY(), pos.getZ() - o.getZ()));
		if (cell == null) {
			return;
		}
		QuadEmitter e = context.getEmitter();
		short[] v = cell.verts;
		boolean doorClosed = state.contains(com.fnaf.horror.block.MapBlock.CLOSED) && state.get(com.fnaf.horror.block.MapBlock.CLOSED);
		for (int t = 0; t < cell.mats.length; t++) {
			int m = cell.mats[t];
			if ((m & DOOR_BIT) != 0) {
				if (!doorClosed) {
					continue;            // open office doors are pulled up into the ceiling
				}
				m &= ~DOOR_BIT;
			}
			int b = t * 20;
			float x0 = v[b] / 2048f, y0 = v[b + 1] / 2048f, z0 = v[b + 2] / 2048f;
			float ax = v[b + 5] / 2048f - x0, ay = v[b + 6] / 2048f - y0, az = v[b + 7] / 2048f - z0;
			float bx = v[b + 10] / 2048f - x0, by = v[b + 11] / 2048f - y0, bz = v[b + 12] / 2048f - z0;
			float nx = ay * bz - az * by, ny = az * bx - ax * bz, nz = ax * by - ay * bx;
			float len = (float) Math.sqrt(nx * nx + ny * ny + nz * nz);
			if (len < 1e-9f) {
				continue;
			}
			nx /= len;
			ny /= len;
			nz /= len;
			for (int k = 0; k < 4; k++) {
				int i = b + k * 5;
				e.pos(k, v[i] / 2048f, v[i + 1] / 2048f, v[i + 2] / 2048f);
				e.uv(k, (v[i + 3] & 0xFFFF) / 65535f, (v[i + 4] & 0xFFFF) / 65535f);
				e.normal(k, nx, ny, nz);
			}
			e.spriteBake(sprites[m], MutableQuadView.BAKE_NORMALIZED);
			// baked shadows / lamp light (tools/blender/map_bake.py), emissive parts stay full bright
			int[] c = cell.colors;
			if ((flags[m] & 2) != 0) {
				e.color(-1, -1, -1, -1);
			} else {
				e.color(c[t * 4], c[t * 4 + 1], c[t * 4 + 2], c[t * 4 + 3]);
			}
			e.nominalFace(Direction.getFacing(nx, ny, nz));
			e.cullFace(null);
			e.material(materials[m]);
			e.emit();
		}
	}

	@Override
	public void emitItemQuads(net.minecraft.item.ItemStack stack, Supplier<Random> randomSupplier, RenderContext context) {
	}

	@Override
	public List<BakedQuad> getQuads(@Nullable BlockState state, @Nullable Direction face, Random random) {
		return Collections.emptyList();
	}

	@Override
	public boolean useAmbientOcclusion() {
		return true;
	}

	@Override
	public boolean hasDepth() {
		return false;
	}

	@Override
	public boolean isSideLit() {
		return true;
	}

	@Override
	public boolean isBuiltin() {
		return false;
	}

	@Override
	public Sprite getParticleSprite() {
		return sprites.length > 0 ? sprites[0] : null;
	}

	@Override
	public ModelTransformation getTransformation() {
		return ModelTransformation.NONE;
	}

	@Override
	public ModelOverrideList getOverrides() {
		return ModelOverrideList.EMPTY;
	}
}
