package com.fnaf.horror.pizzeria;

import com.fnaf.horror.FnafHorror;
import net.minecraft.block.Block;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.shape.VoxelShape;
import net.minecraft.util.shape.VoxelShapes;

import java.io.DataInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.GZIPInputStream;

/**
 * Collision boxes and special cells of the FNAF 1 map (data/fnaf/map/fnaf1.fcol, built by
 * tools/pizzeria/build_map.py), read from the mod jar so client and server see the same shapes.
 * Positions are absolute (the map sits at PizzeriaManager.ORIGIN).
 */
public final class MapCollision {
	public static final int DOOR = 1, DOOR_BUTTON = 2, LIGHT_BUTTON = 4, ROOM_DOOR = 8;

	private record Cell(int flags, VoxelShape open, VoxelShape closed) {
	}

	private static Map<Long, Cell> cells;
	private static final List<BlockPos> DOOR_CELLS = new ArrayList<>();

	public static VoxelShape shape(BlockPos pos, boolean doorClosed) {
		Cell c = cells().get(pos.asLong());
		return c == null ? VoxelShapes.empty() : doorClosed ? c.closed : c.open;
	}

	public static int flags(BlockPos pos) {
		Cell c = cells().get(pos.asLong());
		return c == null ? 0 : c.flags;
	}

	/** All cells holding a piece of an office door. */
	public static List<BlockPos> doorCells() {
		cells();
		return DOOR_CELLS;
	}

	private static synchronized Map<Long, Cell> cells() {
		if (cells != null) {
			return cells;
		}
		Map<Long, Cell> map = new HashMap<>();
		BlockPos o = PizzeriaManager.ORIGIN;
		try (InputStream raw = MapCollision.class.getResourceAsStream("/data/fnaf/map/fnaf1.fcol")) {
			if (raw != null) {
				DataInputStream in = new DataInputStream(new GZIPInputStream(raw, 1 << 16));
				in.readInt();
				in.readInt();
				int n = in.readInt();
				for (int i = 0; i < n; i++) {
					BlockPos pos = o.add(in.readShort(), in.readShort(), in.readShort());
					int flags = in.readByte();
					VoxelShape open = readBoxes(in);
					VoxelShape door = readBoxes(in);
					map.put(pos.asLong(), new Cell(flags, open, VoxelShapes.union(open, door).simplify()));
					if ((flags & DOOR) != 0) {
						DOOR_CELLS.add(pos);
					}
				}
			}
		} catch (IOException e) {
			FnafHorror.LOGGER.error("Failed to read map collision", e);
		}
		FnafHorror.LOGGER.info("Loaded map collision for {} cells ({} door cells)", map.size(), DOOR_CELLS.size());
		cells = map;
		return map;
	}

	private static VoxelShape readBoxes(DataInputStream in) throws IOException {
		int n = in.readByte();
		VoxelShape shape = VoxelShapes.empty();
		for (int b = 0; b < n; b++) {
			shape = VoxelShapes.union(shape, Block.createCuboidShape(in.readByte(), in.readByte(), in.readByte(),
					in.readByte(), in.readByte(), in.readByte()));
		}
		return shape.simplify();
	}

	private MapCollision() {
	}
}
