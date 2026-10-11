package com.fnaf.horror.night;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import net.minecraft.util.math.Vec3d;

import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Route nodes and security cameras of the FNAF 1 map (data/fnaf/pizzeria/night.json, written by
 * tools/pizzeria/night_layout.py). Read from the mod jar so client (camera tablet) and server agree.
 * All positions returned here are absolute (pizzeria origin added).
 */
public final class NightLayout {
	public record Node(String name, Vec3d pos, float yaw) {
	}

	/** pos == null: audio-only camera (the kitchen). target: map point the camera shows, for the cam map. */
	public record Camera(String id, String label, Vec3d pos, float yaw, float pitch, double targetX, double targetZ) {
	}

	private static Map<String, Node> nodes;
	private static List<Camera> cameras;
	private static int mapSize = 48;

	public static Node node(String name) {
		load();
		return nodes.get(name);
	}

	public static List<Camera> cameras() {
		load();
		return cameras;
	}

	public static int mapSize() {
		load();
		return mapSize;
	}

	public static int cameraIndex(String id) {
		List<Camera> cams = cameras();
		for (int i = 0; i < cams.size(); i++) {
			if (cams.get(i).id().equals(id)) {
				return i;
			}
		}
		return -1;
	}

	private static synchronized void load() {
		if (nodes != null) {
			return;
		}
		Map<String, Node> n = new HashMap<>();
		List<Camera> c = new ArrayList<>();
		Vec3d o = Vec3d.of(PizzeriaManager.ORIGIN);
		try (InputStream in = NightLayout.class.getResourceAsStream("/data/fnaf/pizzeria/night.json")) {
			if (in != null) {
				JsonObject root = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
				for (Map.Entry<String, JsonElement> e : root.getAsJsonObject("nodes").entrySet()) {
					JsonArray a = e.getValue().getAsJsonArray();
					n.put(e.getKey(), new Node(e.getKey(), o.add(a.get(0).getAsDouble(), a.get(1).getAsDouble(), a.get(2).getAsDouble()),
							a.get(3).getAsFloat()));
				}
				for (JsonElement e : root.getAsJsonArray("cameras")) {
					JsonObject cam = e.getAsJsonObject();
					JsonArray t = cam.getAsJsonArray("target");
					Vec3d pos = null;
					float yaw = 0, pitch = 0;
					if (cam.has("pos")) {
						JsonArray p = cam.getAsJsonArray("pos");
						pos = o.add(p.get(0).getAsDouble(), p.get(1).getAsDouble(), p.get(2).getAsDouble());
						yaw = cam.get("yaw").getAsFloat();
						pitch = cam.get("pitch").getAsFloat();
					}
					c.add(new Camera(cam.get("id").getAsString(), cam.get("label").getAsString(), pos, yaw, pitch,
							t.get(0).getAsDouble(), t.get(1).getAsDouble()));
				}
				if (root.has("map_size")) {
					mapSize = root.get("map_size").getAsInt();
				}
			}
		} catch (Exception e) {
			FnafHorror.LOGGER.error("Failed to read night layout", e);
		}
		nodes = n;
		cameras = c;
	}

	private NightLayout() {
	}
}
