package com.fnaf.horror.client.render;

import com.fnaf.horror.FnafHorror;
import net.fabricmc.fabric.api.resource.SimpleSynchronousResourceReloadListener;
import net.minecraft.client.texture.NativeImage;
import net.minecraft.resource.Resource;
import net.minecraft.resource.ResourceManager;
import net.minecraft.util.Identifier;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

/**
 * Loads the realistic meshes exported from Blender (assets/fnaf/meshes/&lt;id&gt;.fmesh).
 * Format (big endian): "FMSH", version, partCount, then per part: bone name (short + utf8),
 * vertexCount, vertices (x y z nx ny nz u v floats), indexCount, indices (ints).
 * Positions are already in GeckoLib model space (blocks, X mirrored like baked geo cubes).
 *
 * <p>For fast drawing the triangles are paired into quads at load time (two triangles sharing an edge
 * form one quad that the quad-based render layers split back into exactly those triangles), and the
 * quads that touch lit pixels of the entity's glowmask are listed separately so the glowing eyes do not
 * need a second pass over the whole model.
 */
public final class MeshModels implements SimpleSynchronousResourceReloadListener {
	/** quads: 4 vertex indices per quad; glowQuads: the subset drawn by the emissive eyes pass. */
	public record Part(float[] vertices, int[] quads, int[] glowQuads) {
	}

	public record Mesh(Map<String, Part> parts) {
	}

	private static final Map<String, Mesh> MESHES = new HashMap<>();

	public static Mesh get(String id) {
		return MESHES.get(id);
	}

	@Override
	public Identifier getFabricId() {
		return FnafHorror.id("meshes");
	}

	@Override
	public void reload(ResourceManager manager) {
		MESHES.clear();
		int quads = 0;
		for (Map.Entry<Identifier, Resource> entry : manager.findResources("meshes", id -> id.getPath().endsWith(".fmesh")).entrySet()) {
			Identifier id = entry.getKey();
			if (!id.getNamespace().equals(FnafHorror.MOD_ID)) {
				continue;
			}
			String name = id.getPath().substring("meshes/".length(), id.getPath().length() - ".fmesh".length());
			GlowMask glow = GlowMask.load(manager, FnafHorror.id("textures/entity/" + name + "_hd_glowmask.png"));
			try (InputStream in = entry.getValue().getInputStream()) {
				Mesh mesh = read(in, glow);
				MESHES.put(name, mesh);
				for (Part p : mesh.parts().values()) {
					quads += p.quads().length / 4;
				}
			} catch (IOException e) {
				FnafHorror.LOGGER.error("Failed to load mesh {}", id, e);
			}
		}
		FnafHorror.LOGGER.info("Loaded {} meshes ({} quads)", MESHES.size(), quads);
	}

	private static Mesh read(InputStream raw, GlowMask glow) throws IOException {
		DataInputStream in = new DataInputStream(new BufferedInputStream(raw, 1 << 16));
		byte[] magic = new byte[4];
		in.readFully(magic);
		if (magic[0] != 'F' || magic[1] != 'M' || magic[2] != 'S' || magic[3] != 'H') {
			throw new IOException("Not an FMSH file");
		}
		in.readInt();
		int partCount = in.readInt();
		Map<String, Part> parts = new HashMap<>();
		for (int p = 0; p < partCount; p++) {
			byte[] nameBytes = new byte[in.readShort()];
			in.readFully(nameBytes);
			float[] vertices = new float[in.readInt() * 8];
			for (int i = 0; i < vertices.length; i++) {
				vertices[i] = in.readFloat();
			}
			int[] indices = new int[in.readInt()];
			for (int i = 0; i < indices.length; i++) {
				indices[i] = in.readInt();
			}
			int[] quads = pairTriangles(indices);
			int[] glowQuads = glow == null ? new int[0] : glow.select(vertices, quads);
			parts.put(new String(nameBytes, java.nio.charset.StandardCharsets.UTF_8), new Part(vertices, quads, glowQuads));
		}
		return new Mesh(parts);
	}

	/**
	 * Greedy pairing: triangle (u, v, w) and a neighbour (v, u, x) across edge u-v become quad (v, w, u, x),
	 * which is drawn as triangles (v, w, u) and (u, x, v) — the original two. Leftovers become degenerate quads.
	 */
	static int[] pairTriangles(int[] idx) {
		int tris = idx.length / 3;
		Map<Long, Integer> edges = new HashMap<>(tris * 4);
		for (int t = 0; t < tris; t++) {
			for (int k = 0; k < 3; k++) {
				edges.putIfAbsent(edge(idx[t * 3 + k], idx[t * 3 + (k + 1) % 3]), t);
			}
		}
		boolean[] used = new boolean[tris];
		int[] out = new int[tris * 4];
		int n = 0;
		for (int t = 0; t < tris; t++) {
			if (used[t]) {
				continue;
			}
			used[t] = true;
			boolean paired = false;
			for (int k = 0; k < 3 && !paired; k++) {
				int u = idx[t * 3 + k], v = idx[t * 3 + (k + 1) % 3], w = idx[t * 3 + (k + 2) % 3];
				Integer s = edges.get(edge(v, u));
				if (s == null || used[s]) {
					continue;
				}
				int x = -1;
				for (int j = 0; j < 3; j++) {
					int a = idx[s * 3 + j];
					if (a != u && a != v) {
						x = a;
					}
				}
				if (x < 0) {
					continue;
				}
				used[s] = true;
				out[n++] = v;
				out[n++] = w;
				out[n++] = u;
				out[n++] = x;
				paired = true;
			}
			if (!paired) {
				out[n++] = idx[t * 3];
				out[n++] = idx[t * 3 + 1];
				out[n++] = idx[t * 3 + 2];
				out[n++] = idx[t * 3 + 2];
			}
		}
		return java.util.Arrays.copyOf(out, n);
	}

	private static long edge(int a, int b) {
		return ((long) a << 32) | (b & 0xffffffffL);
	}

	/** Which texels of a glowmask are lit, with a summed-area table for fast rectangle queries. */
	private record GlowMask(int w, int h, int[] sat) {
		static GlowMask load(ResourceManager manager, Identifier id) {
			Optional<Resource> res = manager.getResource(id);
			if (res.isEmpty()) {
				return null;
			}
			try (InputStream in = res.get().getInputStream(); NativeImage img = NativeImage.read(in)) {
				int w = img.getWidth(), h = img.getHeight();
				int[] sat = new int[(w + 1) * (h + 1)];
				for (int y = 0; y < h; y++) {
					for (int x = 0; x < w; x++) {
						int lit = (img.getColor(x, y) >>> 24) > 16 && !(x == w - 1 && y == h - 1) ? 1 : 0;
						sat[(y + 1) * (w + 1) + x + 1] = lit + sat[y * (w + 1) + x + 1] + sat[(y + 1) * (w + 1) + x] - sat[y * (w + 1) + x];
					}
				}
				return new GlowMask(w, h, sat);
			} catch (IOException e) {
				return null;
			}
		}

		int count(int x0, int y0, int x1, int y1) {
			x0 = Math.max(0, x0);
			y0 = Math.max(0, y0);
			x1 = Math.min(w, x1);
			y1 = Math.min(h, y1);
			if (x1 <= x0 || y1 <= y0) {
				return 0;
			}
			int W = w + 1;
			return sat[y1 * W + x1] - sat[y0 * W + x1] - sat[y1 * W + x0] + sat[y0 * W + x0];
		}

		/** Quads whose UV bounds cover any lit texel. */
		int[] select(float[] v, int[] quads) {
			int[] out = new int[quads.length];
			int n = 0;
			for (int q = 0; q < quads.length; q += 4) {
				float u0 = 1, v0 = 1, u1 = 0, v1 = 0;
				for (int k = 0; k < 4; k++) {
					int o = quads[q + k] * 8;
					u0 = Math.min(u0, v[o + 6]);
					u1 = Math.max(u1, v[o + 6]);
					v0 = Math.min(v0, v[o + 7]);
					v1 = Math.max(v1, v[o + 7]);
				}
				if (count((int) Math.floor(u0 * w), (int) Math.floor(v0 * h), (int) Math.ceil(u1 * w), (int) Math.ceil(v1 * h)) > 0) {
					System.arraycopy(quads, q, out, n, 4);
					n += 4;
				}
			}
			return java.util.Arrays.copyOf(out, n);
		}
	}
}
