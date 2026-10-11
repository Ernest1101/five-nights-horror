package com.fnaf.horror.night;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.block.CeilingLightBlock;
import com.fnaf.horror.block.MapBlock;
import com.fnaf.horror.entity.AnimatronicEntity;
import com.fnaf.horror.lobby.LobbyManager;
import com.fnaf.horror.pizzeria.PizzeriaManager;
import com.fnaf.horror.registry.ModEntities;
import com.fnaf.horror.registry.ModSounds;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.PacketByteBufs;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayNetworking;
import net.minecraft.block.BlockState;
import net.minecraft.block.Blocks;
import net.minecraft.entity.Entity;
import net.minecraft.entity.EntityType;
import net.minecraft.network.PacketByteBuf;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.world.ServerWorld;
import net.minecraft.sound.SoundCategory;
import net.minecraft.sound.SoundEvent;
import net.minecraft.util.Identifier;
import net.minecraft.util.math.BlockPos;
import net.minecraft.util.math.Box;
import net.minecraft.util.math.Vec3d;
import net.minecraft.util.math.random.Random;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/**
 * A FNAF 1 night in the pizzeria: the clock runs from 12 AM to 6 AM, power drains with doors, hall lights
 * and the camera tablet, and the animatronics jump between route nodes on movement opportunities using the
 * original AI levels per night and hour. One shared night runs for everyone who started it.
 */
public final class NightManager {
	/** S2C: active, night, time, power, usage, blackout, disabled sides. */
	public static final Identifier STATE = FnafHorror.id("night_state");
	/** S2C: event type + argument (see EVENT_*). */
	public static final Identifier EVENT = FnafHorror.id("night_event");
	/** C2S: camera index the player looks through, -1 = tablet down. */
	public static final Identifier CAMERA = FnafHorror.id("night_camera");
	public static final int EVENT_START = 0, EVENT_WIN = 1, EVENT_GAME_OVER = 2, EVENT_CAM_GLITCH = 3, EVENT_BLACKOUT = 4;

	public static final int HOUR_TICKS = 89 * 20;
	public static final int NIGHT_TICKS = HOUR_TICKS * 6;
	private static final int INTRO_TICKS = 90;

	/** AI levels per night (Freddy, Bonnie, Chica, Foxy), as in FNAF 1; night 7 is unused for now. */
	private static final int[][] AI = {{0, 0, 0, 0}, {0, 0, 0, 0}, {0, 3, 1, 1}, {1, 0, 5, 2}, {1, 2, 4, 6}, {3, 5, 7, 5}, {4, 10, 12, 16}};

	private static final Map<String, String[]> BONNIE_ROUTE = Map.of(
			"stage_bonnie", new String[]{"dining_w", "backstage"},
			"dining_w", new String[]{"backstage", "w_hall"},
			"backstage", new String[]{"dining_w", "w_hall"},
			"w_hall", new String[]{"supply", "w_corner", "left_door"},
			"supply", new String[]{"w_hall", "left_door"},
			"w_corner", new String[]{"supply", "left_door"});
	private static final Map<String, String[]> CHICA_ROUTE = Map.of(
			"stage_chica", new String[]{"dining_e"},
			"dining_e", new String[]{"restrooms", "kitchen"},
			"restrooms", new String[]{"kitchen", "e_hall"},
			"kitchen", new String[]{"restrooms", "e_hall"},
			"e_hall", new String[]{"e_corner", "right_door", "kitchen"},
			"e_corner", new String[]{"right_door", "e_hall"});
	private static final String[] FREDDY_ROUTE = {"stage_freddy", "dining_c", "restrooms", "kitchen", "e_hall", "e_corner"};
	private static final String[] FOXY_STAGES = {"cove_in", "cove_peek", "cove_out"};

	/** Which camera shows each node. */
	private static final Map<String, String> NODE_CAMERA = new HashMap<>();

	static {
		for (String n : new String[]{"stage_freddy", "stage_bonnie", "stage_chica"}) {
			NODE_CAMERA.put(n, "1A");
		}
		for (String n : new String[]{"dining_w", "dining_c", "dining_e"}) {
			NODE_CAMERA.put(n, "1B");
		}
		for (String n : FOXY_STAGES) {
			NODE_CAMERA.put(n, "1C");
		}
		NODE_CAMERA.put("backstage", "5");
		NODE_CAMERA.put("supply", "3");
		NODE_CAMERA.put("w_hall", "2A");
		NODE_CAMERA.put("foxy_run", "2A");
		NODE_CAMERA.put("w_corner", "2B");
		NODE_CAMERA.put("e_hall", "4A");
		NODE_CAMERA.put("e_corner", "4B");
		NODE_CAMERA.put("kitchen", "6");
		NODE_CAMERA.put("restrooms", "7");
	}

	private enum Kind { FREDDY, BONNIE, CHICA, FOXY }

	private static final class Bot {
		final Kind kind;
		AnimatronicEntity entity;
		String node;
		int timer;
		final int interval;
		int officeTicks = -1;        // >= 0 while inside the office
		boolean leftSide;
		int foxyStage;
		int foxyWait;
		int runTicks = -1;           // >= 0 while Foxy sprints down the west hall
		UUID chase;                  // player it saw and runs after
		int lostTicks;               // ticks without seeing the chased player
		int chaseTicks;
		int returnTicks = -1;        // >= 0 while walking back to its node after a chase

		Bot(Kind kind, String node, int interval) {
			this.kind = kind;
			this.node = node;
			this.interval = interval;
			this.timer = interval;
		}
	}

	private static final class Session {
		int night;
		int time = -INTRO_TICKS;
		float power = 100f;
		int usage = 1;
		boolean blackout;
		int blackoutPhase;
		int blackoutTimer;
		int foxyBangs;
		int winTicks = -1;
		BlockPos generator;
		/** Where Freddy was before he came hunting in the blackout (he goes back when the power returns). */
		String freddyNode;
		MinecraftServer server;
		final Set<UUID> players = new HashSet<>();
		final Map<UUID, Integer> cams = new HashMap<>();
		final List<Bot> bots = new ArrayList<>();
	}

	private static Session session;

	public static void init() {
		ServerTickEvents.END_SERVER_TICK.register(NightManager::tick);
		net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback.EVENT.register((dispatcher, access, env) -> dispatcher.register(
				net.minecraft.server.command.CommandManager.literal("fnaf").requires(src -> src.hasPermissionLevel(2))
						.then(net.minecraft.server.command.CommandManager.literal("night")
								.then(net.minecraft.server.command.CommandManager.literal("start")
										.then(net.minecraft.server.command.CommandManager.argument("night",
												com.mojang.brigadier.arguments.IntegerArgumentType.integer(1, 6)).executes(ctx -> {
											if (session != null) {
												end(ctx.getSource().getServer());
											}
											return begin(ctx.getSource().getPlayerOrThrow(),
													com.mojang.brigadier.arguments.IntegerArgumentType.getInteger(ctx, "night")) ? 1 : 0;
										})))
								.then(net.minecraft.server.command.CommandManager.literal("skip").executes(ctx -> {
									if (session != null) {
										session.time = Math.max(session.time, NIGHT_TICKS - 60);
									}
									return 1;
								}))
								.then(net.minecraft.server.command.CommandManager.literal("power")
										.then(net.minecraft.server.command.CommandManager.argument("percent",
												com.mojang.brigadier.arguments.FloatArgumentType.floatArg(0, 100)).executes(ctx -> {
											if (session != null) {
												session.power = com.mojang.brigadier.arguments.FloatArgumentType.getFloat(ctx, "percent");
											}
											return 1;
										}))))));
		ServerPlayNetworking.registerGlobalReceiver(CAMERA, (server, player, handler, buf, responseSender) -> {
			int cam = buf.readInt();
			server.execute(() -> setCamera(player, cam));
		});
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (entity instanceof ServerPlayerEntity player && session != null && session.players.remove(player.getUuid())) {
				session.cams.remove(player.getUuid());
				sendEvent(player, EVENT_GAME_OVER, 0);
				sendState(player, false);
			}
		});
		ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> {
			if (session != null) {
				session.players.remove(handler.player.getUuid());
				session.cams.remove(handler.player.getUuid());
			}
		});
	}

	public static boolean isActive() {
		return session != null;
	}

	public static boolean isBlackout() {
		return session != null && session.blackout;
	}

	public static float power() {
		return session == null ? 0f : session.power;
	}

	/** Office buttons stop working in a blackout and on the side where an animatronic got in. */
	public static boolean buttonsBlocked(BlockPos button) {
		if (session == null) {
			return false;
		}
		if (session.blackout) {
			return true;
		}
		NightLayout.Node left = NightLayout.node("left_door");
		NightLayout.Node right = NightLayout.node("right_door");
		boolean leftSide = left != null && right != null
				&& Vec3d.ofCenter(button).squaredDistanceTo(left.pos()) < Vec3d.ofCenter(button).squaredDistanceTo(right.pos());
		for (Bot b : session.bots) {
			if (b.officeTicks >= 0 && b.leftSide == leftSide) {
				return true;
			}
		}
		return false;
	}

	// ------------------------------------------------------------------ start / stop

	/** Starts night `night` for the player (or lets them join the night that is already running). */
	public static boolean begin(ServerPlayerEntity player, int night) {
		MinecraftServer server = player.getServer();
		if (server == null || !PizzeriaManager.enter(player, false)) {
			return false;
		}
		ServerWorld world = server.getWorld(PizzeriaManager.WORLD);
		if (session == null) {
			session = new Session();
			session.night = Math.max(1, Math.min(6, night));
			session.server = server;
			reset(world);
		}
		session.players.add(player.getUuid());
		sendEvent(player, EVENT_START, session.night);
		sendState(player, true);
		return true;
	}

	/** Fresh building state: doors open, lights on, the four animatronics at their start positions. */
	private static void reset(ServerWorld world) {
		Box all = PizzeriaManager.clearBox();
		world.getEntitiesByClass(AnimatronicEntity.class, all, e -> true).forEach(Entity::discard);
		for (String door : new String[]{"left_door", "right_door"}) {
			List<BlockPos> cells = doorCells(door);
			if (!cells.isEmpty()) {
				MapBlock.setDoor(world, cells, false);
			}
		}
		CeilingLightBlock.setPower(world, PizzeriaManager.bounds(), true);
		Fuel.clearCans(world);
		session.generator = Fuel.placeGenerator(world);
		session.bots.add(spawn(world, new Bot(Kind.FREDDY, "stage_freddy", 60), ModEntities.FREDDY));
		session.bots.add(spawn(world, new Bot(Kind.BONNIE, "stage_bonnie", 99), ModEntities.BONNIE));
		session.bots.add(spawn(world, new Bot(Kind.CHICA, "stage_chica", 100), ModEntities.CHICA));
		session.bots.add(spawn(world, new Bot(Kind.FOXY, "cove_in", 100), ModEntities.FOXY));
	}

	private static Bot spawn(ServerWorld world, Bot bot, EntityType<AnimatronicEntity> type) {
		AnimatronicEntity e = type.create(world);
		if (e != null) {
			e.nightControlled = true;
			e.setPersistent();
			bot.entity = e;
			place(bot, bot.node);
			world.spawnEntity(e);
		}
		return bot;
	}

	private static void end(MinecraftServer server) {
		ServerWorld world = server.getWorld(PizzeriaManager.WORLD);
		if (world != null) {
			Fuel.clearCans(world);
			for (Bot b : session.bots) {
				if (b.entity != null && !b.entity.isJumpscaring()) {
					b.entity.discard();
				}
			}
		}
		for (UUID id : session.players) {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
			if (p != null) {
				sendState(p, false);
				clearNightItems(p);
			}
		}
		session = null;
	}

	// ------------------------------------------------------------------ tick

	private static void tick(MinecraftServer server) {
		if (session == null) {
			return;
		}
		ServerWorld world = server.getWorld(PizzeriaManager.WORLD);
		session.players.removeIf(id -> {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
			return p == null || p.getWorld() != world;
		});
		if (world == null || session.players.isEmpty() && session.winTicks < 0) {
			end(server);
			return;
		}
		if (session.winTicks >= 0) {
			if (++session.winTicks > 170) {
				for (UUID id : session.players) {
					ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
					if (p != null) {
						LobbyManager.sendToLobby(p);
					}
				}
				end(server);
			}
			return;
		}
		session.time++;
		if (session.time >= NIGHT_TICKS) {
			win(server, world);
			return;
		}
		if (session.time >= 0) {
			tickPower(world);
			for (Bot b : session.bots) {
				tickChase(server, world, b);
			}
			if (session.blackout) {
				tickBlackout(server, world);
			} else {
				for (Bot b : session.bots) {
					if (b.chase == null && b.returnTicks < 0) {
						tickBot(server, world, b);
					}
				}
			}
		}
		if (session.time % 10 == 0) {
			for (UUID id : session.players) {
				ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
				if (p != null) {
					sendState(p, true);
				}
			}
		}
	}

	private static int hour() {
		return Math.max(0, session.time) / HOUR_TICKS;
	}

	private static int aiLevel(Bot b, Random random) {
		int n = Math.min(session.night, 6);
		int level = AI[n][b.kind.ordinal()];
		if (n == 4 && b.kind == Kind.FREDDY) {
			level = 1 + random.nextInt(2);
		}
		int h = hour();
		if (b.kind != Kind.FREDDY) {
			if (h >= 2 && b.kind == Kind.BONNIE) {
				level++;
			}
			if (h >= 3) {
				level++;
			}
			if (h >= 4) {
				level++;
			}
		}
		return Math.min(20, level);
	}

	// ------------------------------------------------------------------ power

	private static void tickPower(ServerWorld world) {
		int usage = 1;
		for (String door : new String[]{"left_door", "right_door"}) {
			List<BlockPos> cells = doorCells(door);
			if (!cells.isEmpty() && world.getBlockState(cells.get(0)).get(MapBlock.CLOSED)) {
				usage++;
			}
			if (hallLit(world, door)) {
				usage++;
			}
		}
		if (session.cams.values().stream().anyMatch(c -> c >= 0)) {
			usage++;
		}
		session.usage = usage;
		if (session.blackout) {
			return;
		}
		float drain = usage / (9.6f * 20f) + (session.night - 1) * 7f / NIGHT_TICKS;
		session.power -= drain;
		if (session.power <= 0) {
			session.power = 0;
			startBlackout(world);
		}
	}

	private static boolean hallLit(ServerWorld world, String doorNode) {
		List<BlockPos> cells = doorCells(doorNode);
		NightLayout.Node n = NightLayout.node(doorNode);
		if (cells.isEmpty() || n == null) {
			return false;
		}
		BlockPos d = cells.get(0);
		int dx = Integer.signum((int) Math.floor(n.pos().x) - d.getX());
		BlockState s = world.getBlockState(d.add(dx, 0, 0));
		return s.isOf(Blocks.LIGHT) || s.getBlock() instanceof MapBlock && s.get(MapBlock.FLASH) > 0;
	}

	private static void startBlackout(ServerWorld world) {
		session.blackout = true;
		session.blackoutPhase = 0;
		session.blackoutTimer = 700 + world.random.nextInt(300);
		for (String door : new String[]{"left_door", "right_door"}) {
			List<BlockPos> cells = doorCells(door);
			if (!cells.isEmpty()) {
				MapBlock.setDoor(world, cells, false);
			}
		}
		CeilingLightBlock.setPower(world, PizzeriaManager.bounds(), false);
		session.cams.replaceAll((k, v) -> -1);
		if (session.generator != null && world.getBlockState(session.generator).isOf(com.fnaf.horror.registry.ModBlocks.GENERATOR)) {
			if (world.getBlockState(session.generator).get(com.fnaf.horror.block.GeneratorBlock.RUNNING)) {
				world.playSound(null, session.generator, ModSounds.GENERATOR_STOP, SoundCategory.BLOCKS, 1.0f, 1.0f);
			}
			world.setBlockState(session.generator, world.getBlockState(session.generator).with(com.fnaf.horror.block.GeneratorBlock.RUNNING, false));
		}
		Fuel.spawnCans(world, Fuel.CANS_PER_BLACKOUT, session.generator);
		for (UUID id : session.players) {
			ServerPlayerEntity p = world.getServer().getPlayerManager().getPlayer(id);
			if (p != null) {
				p.playSound(ModSounds.POWER_DOWN, SoundCategory.MASTER, 1.0f, 1.0f);
				sendEvent(p, EVENT_BLACKOUT, 0);
				if (p.getInventory().count(com.fnaf.horror.registry.ModItems.FLASHLIGHT) == 0) {
					net.minecraft.item.ItemStack light = new net.minecraft.item.ItemStack(com.fnaf.horror.registry.ModItems.FLASHLIGHT);
					if (p.getInventory().getMainHandStack().isEmpty()) {
						p.getInventory().setStack(p.getInventory().selectedSlot, light);
					} else {
						p.getInventory().offerOrDrop(light);
					}
				}
			}
		}
		Bot fr = bot(Kind.FREDDY);
		session.freddyNode = fr != null ? fr.node : "stage_freddy";
		// everyone but Freddy goes quiet; Freddy comes to the left door
		for (Bot b : session.bots) {
			if (b.kind != Kind.FREDDY && b.officeTicks >= 0) {
				b.officeTicks = -1;
				place(b, b.kind == Kind.BONNIE ? "dining_w" : b.kind == Kind.CHICA ? "e_hall" : "cove_in");
			}
		}
	}

	/** Power out: silence, then Freddy's music box at the left door, then darkness, then him. */
	private static void tickBlackout(MinecraftServer server, ServerWorld world) {
		if (--session.blackoutTimer > 0) {
			return;
		}
		Bot freddy = bot(Kind.FREDDY);
		switch (session.blackoutPhase) {
			case 0 -> {
				if (freddy != null && freddy.entity != null) {
					place(freddy, huntNode(server));
					world.playSoundFromEntity(null, freddy.entity, ModSounds.MUSIC_BOX, SoundCategory.HOSTILE, 1.5f, 1.0f);
				}
				session.blackoutPhase = 1;
				session.blackoutTimer = 300 + world.random.nextInt(100);
			}
			case 1 -> {
				if (freddy != null && freddy.entity != null) {
					freddy.entity.refreshPositionAndAngles(freddy.entity.getX(), freddy.entity.getY() - 50, freddy.entity.getZ(), 0, 0);
				}
				session.blackoutPhase = 2;
				session.blackoutTimer = 40 + world.random.nextInt(360);
			}
			default -> {
				if (freddy != null) {
					attack(server, freddy);
				}
				session.blackoutTimer = 1000;
			}
		}
	}

	/** Route node between 8 and 20 blocks from the nearest player: Freddy plays his tune somewhere close by. */
	private static String huntNode(MinecraftServer server) {
		String best = "left_door";
		double bestScore = Double.MAX_VALUE;
		for (String name : new String[]{"dining_w", "dining_c", "dining_e", "backstage", "supply", "w_hall", "w_corner",
				"e_hall", "e_corner", "restrooms", "kitchen", "left_door", "right_door"}) {
			NightLayout.Node n = NightLayout.node(name);
			if (n == null) {
				continue;
			}
			double d = Double.MAX_VALUE;
			for (UUID id : session.players) {
				ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
				if (p != null) {
					d = Math.min(d, Math.sqrt(p.squaredDistanceTo(n.pos())));
				}
			}
			double score = d < 8 ? 100 + (8 - d) : Math.abs(d - 12);
			if (score < bestScore) {
				bestScore = score;
				best = name;
			}
		}
		return best;
	}

	/** Fuel poured into the generator: power comes back (and the lights, if it was a blackout). */
	static void refuel(ServerWorld world, BlockPos generator, float amount, ServerPlayerEntity by) {
		if (session == null || amount <= 0) {
			return;
		}
		session.power = Math.min(100f, session.power + amount);
		BlockState g = world.getBlockState(generator);
		if (g.isOf(com.fnaf.horror.registry.ModBlocks.GENERATOR)) {
			world.setBlockState(generator, g.with(com.fnaf.horror.block.GeneratorBlock.RUNNING, true));
			world.playSound(null, generator, ModSounds.GENERATOR_START, SoundCategory.BLOCKS, 1.0f, 1.0f);
		}
		if (session.blackout) {
			endBlackout(world);
		}
		by.sendMessage(net.minecraft.text.Text.translatable("message.fnaf.generator_refuelled", (int) Math.ceil(session.power))
				.formatted(net.minecraft.util.Formatting.YELLOW), true);
	}

	private static void endBlackout(ServerWorld world) {
		session.blackout = false;
		session.blackoutPhase = 0;
		CeilingLightBlock.setPower(world, PizzeriaManager.bounds(), true);
		Bot freddy = bot(Kind.FREDDY);
		if (freddy != null && freddy.entity != null && !freddy.entity.isJumpscaring()) {
			place(freddy, session.freddyNode != null ? session.freddyNode : "stage_freddy");
			freddy.timer = freddy.interval;
		}
		for (UUID id : session.players) {
			ServerPlayerEntity p = world.getServer().getPlayerManager().getPlayer(id);
			if (p != null) {
				p.networkHandler.sendPacket(new net.minecraft.network.packet.s2c.play.StopSoundS2CPacket(
						ModSounds.MUSIC_BOX.getId(), SoundCategory.HOSTILE));
				sendState(p, true);
			}
		}
	}

	private static void clearNightItems(ServerPlayerEntity p) {
		var inv = p.getInventory();
		inv.remove(s -> s.isOf(Fuel.canItem()) || s.getItem() instanceof com.fnaf.horror.item.FlashlightItem, -1,
				p.playerScreenHandler.getCraftingInput());
	}

	// ------------------------------------------------------------------ chases

	/** Sight range: far with the hall lights on or a flashlight pointing around, short in the dark. */
	private static boolean sees(ServerWorld world, Bot b, ServerPlayerEntity p, boolean already) {
		AnimatronicEntity e = b.entity;
		if (!p.isAlive() || p.isSpectator() || p.isCreative() || inOffice(p) || p.getWorld() != world) {
			return false;
		}
		Vec3d to = p.getEyePos().subtract(e.getEyePos());
		double dist = to.length();
		int light = world.getLightLevel(p.getBlockPos());
		double range = com.fnaf.horror.item.FlashlightItem.litIn(p) != null ? 18 : light >= 6 ? 14 : 7;
		if (already) {
			range += 8;               // once it has you it does not let go so easily
		}
		if (dist > range) {
			return false;
		}
		if (!already && dist > 2.5) {
			Vec3d facing = Vec3d.fromPolar(0, e.getHeadYaw());
			if (facing.dotProduct(new Vec3d(to.x, 0, to.z).normalize()) < 0.3) {
				return false;         // behind its back
			}
		}
		return clearView(world, e, p);
	}

	/**
	 * Line of sight from chest height (the tall animatronics' eyes poke into the low ceiling, so the vanilla
	 * eye-to-eye check fails) to the player's head or body.
	 */
	private static boolean clearView(ServerWorld world, AnimatronicEntity e, ServerPlayerEntity p) {
		Vec3d from = e.getPos().add(0, Math.min(1.5, e.getHeight() * 0.7), 0);
		for (Vec3d to : new Vec3d[]{p.getEyePos(), p.getPos().add(0, 0.9, 0)}) {
			var hit = world.raycast(new net.minecraft.world.RaycastContext(from, to, net.minecraft.world.RaycastContext.ShapeType.COLLIDER,
					net.minecraft.world.RaycastContext.FluidHandling.NONE, e));
			if (hit.getType() == net.minecraft.util.hit.HitResult.Type.MISS) {
				return true;
			}
		}
		return false;
	}

	/** The security office itself (the doors and buttons keep things out there, FNAF style). */
	private static boolean inOffice(ServerPlayerEntity p) {
		double x = p.getX() - PizzeriaManager.ORIGIN.getX(), z = p.getZ() - PizzeriaManager.ORIGIN.getZ();
		return x > 22.8 && x < 28.2 && z > 37.5 && z < 45.5;
	}

	private static void tickChase(MinecraftServer server, ServerWorld world, Bot b) {
		AnimatronicEntity e = b.entity;
		if (e == null || e.isRemoved() || e.isJumpscaring() || b.officeTicks >= 0 || b.runTicks >= 0) {
			return;
		}
		// Freddy belongs to the blackout script; Foxy only once he is out of the cove
		boolean able = !(session.blackout && b.kind == Kind.FREDDY) && !(b.kind == Kind.FOXY && b.foxyStage < 2)
				&& e.getY() > PizzeriaManager.ORIGIN.getY() - 5;
		if (b.chase != null) {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(b.chase);
			if (p == null || !able || !session.players.contains(b.chase) || !p.isAlive()) {
				stopChase(b);
				return;
			}
			b.chaseTicks++;
			if (e.squaredDistanceTo(p) < 1.8 * 1.8 && Math.abs(e.getY() - p.getY()) < 1.5) {
				stopChase(b);
				b.entity.nightReturn = null;
				b.returnTicks = -1;
				attack(server, b);
				return;
			}
			if (inOffice(p)) {
				// you made it to the office: it waits at the door on its side, like in the game
				stopChase(b);
				String door = nearestDoor(e.getPos());
				if (door != null && e.getPos().distanceTo(NightLayout.node(door).pos()) < 14) {
					b.returnTicks = -1;
					e.nightReturn = null;
					e.getNavigation().stop();
					place(b, door);
					if (b.kind == Kind.FOXY) {
						b.foxyStage = 2;
					}
				}
				return;
			}
			b.lostTicks = sees(world, b, p, true) ? 0 : b.lostTicks + 1;
			if (b.lostTicks > 80 || b.chaseTicks > 600) {
				stopChase(b);
			}
			return;
		}
		if (!able) {
			return;
		}
		if (b.returnTicks >= 0) {
			NightLayout.Node home = NightLayout.node(b.node);
			if (++b.returnTicks > 300 || home == null || e.getPos().squaredDistanceTo(home.pos()) < 1.5 * 1.5) {
				b.returnTicks = -1;
				e.nightReturn = null;
				place(b, b.node);
			}
		}
		for (UUID id : session.players) {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
			if (p != null && sees(world, b, p, false)) {
				b.chase = id;
				b.lostTicks = 0;
				b.chaseTicks = 0;
				b.returnTicks = -1;
				e.nightReturn = null;
				e.nightChase = p;
				world.playSoundFromEntity(null, e, b.kind == Kind.FREDDY ? ModSounds.LAUGH : ModSounds.SERVO, SoundCategory.HOSTILE, 1.6f, 0.75f);
				p.playSound(ModSounds.STATIC, SoundCategory.HOSTILE, 0.5f, 1.3f);
				FnafHorror.LOGGER.debug("[night] {} chases {}", b.kind, p.getName().getString());
				return;
			}
		}
	}

	/** Lost the player: walk back to the route node it came from. */
	private static void stopChase(Bot b) {
		b.chase = null;
		b.lostTicks = 0;
		if (b.entity != null) {
			b.entity.nightChase = null;
			NightLayout.Node home = NightLayout.node(b.node);
			if (home != null) {
				b.entity.nightReturn = home.pos();
				b.returnTicks = 0;
			}
		}
	}

	private static String nearestDoor(Vec3d pos) {
		String best = null;
		double bestD = Double.MAX_VALUE;
		for (String d : new String[]{"left_door", "right_door"}) {
			NightLayout.Node n = NightLayout.node(d);
			if (n != null && n.pos().squaredDistanceTo(pos) < bestD) {
				bestD = n.pos().squaredDistanceTo(pos);
				best = d;
			}
		}
		return best;
	}

	// ------------------------------------------------------------------ animatronics

	private static void tickBot(MinecraftServer server, ServerWorld world, Bot b) {
		if (b.entity == null || b.entity.isRemoved()) {
			return;
		}
		if (b.officeTicks >= 0) {
			b.officeTicks++;
			// they strike when the tablet goes down (or after half a minute)
			if (b.officeTicks > 20 && session.cams.values().stream().noneMatch(c -> c >= 0) || b.officeTicks > 600) {
				attack(server, b);
			}
			return;
		}
		if (b.runTicks >= 0) {
			tickFoxyRun(server, world, b);
			return;
		}
		if (b.kind == Kind.FOXY && b.foxyStage == 2 && (++b.foxyWait > 500 || watching("2A"))) {
			startFoxyRun(world, b);
			return;
		}
		if (--b.timer > 0) {
			return;
		}
		b.timer = b.interval;
		int level = aiLevel(b, world.random);
		if (level <= 0 || 1 + world.random.nextInt(20) > level) {
			return;
		}
		switch (b.kind) {
			case FOXY -> {
				// Foxy only creeps out of the cove while nobody is looking at the cameras
				if (session.cams.values().stream().noneMatch(c -> c >= 0) && b.foxyStage < 2) {
					b.foxyStage++;
					move(b, FOXY_STAGES[b.foxyStage]);
				}
			}
			case FREDDY -> moveFreddy(server, b);
			default -> moveRoute(server, world, b);
		}
	}

	private static void moveRoute(MinecraftServer server, ServerWorld world, Bot b) {
		boolean bonnie = b.kind == Kind.BONNIE;
		String door = bonnie ? "left_door" : "right_door";
		if (b.node.equals(door)) {
			if (doorClosed(world, door)) {
				move(b, bonnie ? "dining_w" : "e_hall");
			} else {
				enterOffice(b, bonnie);
			}
			return;
		}
		String[] next = (bonnie ? BONNIE_ROUTE : CHICA_ROUTE).get(b.node);
		if (next != null) {
			move(b, next[world.random.nextInt(next.length)]);
		}
	}

	private static void moveFreddy(MinecraftServer server, Bot b) {
		String cam = NODE_CAMERA.get(b.node);
		if (cam != null && watching(cam)) {
			return;                    // Freddy never moves while you watch him
		}
		if (b.node.equals("stage_freddy") && (bot(Kind.BONNIE).node.startsWith("stage") || bot(Kind.CHICA).node.startsWith("stage"))) {
			return;                    // he waits until Bonnie and Chica have left the stage
		}
		ServerWorld world = server.getWorld(PizzeriaManager.WORLD);
		if (b.node.equals("e_corner")) {
			if (!doorClosed(world, "right_door") && !watching("4B")) {
				enterOffice(b, false);
			} else if (doorClosed(world, "right_door")) {
				move(b, "e_hall");
			}
			return;
		}
		for (int i = 0; i < FREDDY_ROUTE.length - 1; i++) {
			if (FREDDY_ROUTE[i].equals(b.node)) {
				move(b, FREDDY_ROUTE[i + 1]);
				if (world != null) {
					world.playSoundFromEntity(null, b.entity, ModSounds.LAUGH, SoundCategory.HOSTILE, 1.2f, 1.0f);
				}
				return;
			}
		}
	}

	private static void startFoxyRun(ServerWorld world, Bot b) {
		b.foxyWait = 0;
		b.runTicks = 0;
		move(b, "foxy_run");
		world.playSoundFromEntity(null, b.entity, ModSounds.FOXY_RUN, SoundCategory.HOSTILE, 2.0f, 1.0f);
	}

	private static void tickFoxyRun(MinecraftServer server, ServerWorld world, Bot b) {
		NightLayout.Node from = NightLayout.node("foxy_run");
		NightLayout.Node to = NightLayout.node("left_door");
		if (from == null || to == null) {
			b.runTicks = -1;
			return;
		}
		float t = Math.min(1f, ++b.runTicks / 45f);
		Vec3d p = from.pos().lerp(to.pos(), t);
		b.entity.refreshPositionAndAngles(p.x, p.y, p.z, 0, 0);
		b.entity.setHeadYaw(0);
		b.entity.setBodyYaw(0);
		if (t < 1f) {
			return;
		}
		b.runTicks = -1;
		if (doorClosed(world, "left_door")) {
			world.playSound(null, BlockPos.ofFloored(to.pos()), ModSounds.FOXY_BANG, SoundCategory.HOSTILE, 2.0f, 1.0f);
			session.power = Math.max(0, session.power - (1 + 5 * session.foxyBangs));
			session.foxyBangs++;
			b.foxyStage = world.random.nextInt(2);
			move(b, FOXY_STAGES[b.foxyStage]);
		} else {
			attack(server, b);
		}
	}

	private static void enterOffice(Bot b, boolean leftSide) {
		b.leftSide = leftSide;
		b.officeTicks = 0;
		move(b, leftSide ? "office_left" : "office_right");
	}

	private static void attack(MinecraftServer server, Bot b) {
		if (b.entity == null || b.entity.isJumpscaring()) {
			return;
		}
		for (Bot other : session.bots) {
			if (other.entity != null && other.entity.isJumpscaring()) {
				return;               // one jumpscare at a time
			}
		}
		ServerPlayerEntity victim = null;
		double best = Double.MAX_VALUE;
		for (UUID id : session.players) {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
			if (p != null && p.isAlive() && p.squaredDistanceTo(b.entity) < best) {
				best = p.squaredDistanceTo(b.entity);
				victim = p;
			}
		}
		b.officeTicks = -1;
		if (victim != null) {
			session.cams.put(victim.getUuid(), -1);
			b.entity.startJumpscare(victim);
		}
	}

	/** Moves an animatronic to a node, with a burst of static on cameras that show either end. */
	private static void move(Bot b, String node) {
		glitch(NODE_CAMERA.get(b.node));
		place(b, node);
		glitch(NODE_CAMERA.get(node));
		if (b.entity != null) {
			b.entity.getWorld().playSoundFromEntity(null, b.entity, ModSounds.STEP, SoundCategory.HOSTILE, 0.6f, 0.9f);
		}
	}

	private static void place(Bot b, String node) {
		FnafHorror.LOGGER.info("[night] {} -> {}", b.kind, node);
		NightLayout.Node n = NightLayout.node(node);
		b.node = node;
		b.chase = null;
		b.returnTicks = -1;
		if (b.entity != null) {
			b.entity.nightChase = null;
			b.entity.nightReturn = null;
			b.entity.getNavigation().stop();
		}
		if (n == null || b.entity == null) {
			return;
		}
		Vec3d p = n.pos();
		// two animatronics on one node stand side by side
		for (Bot other : session.bots) {
			if (other != b && node.equals(other.node)) {
				p = p.add(0.9, 0, 0.6);
			}
		}
		b.entity.refreshPositionAndAngles(p.x, p.y + 0.05, p.z, n.yaw(), 0);
		b.entity.setHeadYaw(n.yaw());
		b.entity.setBodyYaw(n.yaw());
		b.entity.setVelocity(Vec3d.ZERO);
	}

	private static Bot bot(Kind kind) {
		for (Bot b : session.bots) {
			if (b.kind == kind) {
				return b;
			}
		}
		return null;
	}

	// ------------------------------------------------------------------ cameras / doors

	private static void setCamera(ServerPlayerEntity player, int cam) {
		if (session == null || !session.players.contains(player.getUuid())) {
			return;
		}
		if (session.blackout || cam >= NightLayout.cameras().size()) {
			cam = -1;
		}
		session.cams.put(player.getUuid(), cam);
	}

	private static boolean watching(String camId) {
		int idx = NightLayout.cameraIndex(camId);
		return idx >= 0 && session.cams.containsValue(idx);
	}

	private static void glitch(String camId) {
		if (camId == null || session == null) {
			return;
		}
		int idx = NightLayout.cameraIndex(camId);
		for (Map.Entry<UUID, Integer> e : session.cams.entrySet()) {
			if (e.getValue() == idx) {
				ServerPlayerEntity p = session.server.getPlayerManager().getPlayer(e.getKey());
				if (p != null) {
					sendEvent(p, EVENT_CAM_GLITCH, idx);
				}
			}
		}
	}

	private static final Map<String, List<BlockPos>> DOORS = new HashMap<>();

	private static List<BlockPos> doorCells(String doorNode) {
		return DOORS.computeIfAbsent(doorNode, k -> {
			NightLayout.Node n = NightLayout.node(k);
			return n == null ? List.of() : MapBlock.nearestDoor(BlockPos.ofFloored(n.pos()));
		});
	}

	private static boolean doorClosed(ServerWorld world, String doorNode) {
		List<BlockPos> cells = doorCells(doorNode);
		return !cells.isEmpty() && world.getBlockState(cells.get(0)).getBlock() instanceof MapBlock
				&& world.getBlockState(cells.get(0)).get(MapBlock.CLOSED);
	}

	// ------------------------------------------------------------------ win

	private static void win(MinecraftServer server, ServerWorld world) {
		session.winTicks = 0;
		NightProgress progress = NightProgress.get(server);
		for (UUID id : session.players) {
			ServerPlayerEntity p = server.getPlayerManager().getPlayer(id);
			if (p == null) {
				continue;
			}
			progress.win(id, session.night);
			sendEvent(p, EVENT_WIN, session.night);
			play(p, ModSounds.NIGHT_CHIMES);
			play(p, ModSounds.NIGHT_CHEER);
		}
		for (Bot b : session.bots) {
			if (b.entity != null && !b.entity.isJumpscaring()) {
				b.entity.discard();
			}
		}
		session.bots.clear();
	}

	private static void play(ServerPlayerEntity p, SoundEvent sound) {
		p.playSound(sound, SoundCategory.MASTER, 1.0f, 1.0f);
	}

	// ------------------------------------------------------------------ packets

	private static void sendState(ServerPlayerEntity player, boolean active) {
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeBoolean(active && session != null);
		if (active && session != null) {
			buf.writeInt(session.night);
			buf.writeInt(session.time);
			buf.writeFloat(session.power);
			buf.writeInt(session.usage);
			buf.writeBoolean(session.blackout);
		}
		ServerPlayNetworking.send(player, STATE, buf);
	}

	private static void sendEvent(ServerPlayerEntity player, int type, int arg) {
		PacketByteBuf buf = PacketByteBufs.create();
		buf.writeInt(type);
		buf.writeInt(arg);
		ServerPlayNetworking.send(player, EVENT, buf);
	}

	private NightManager() {
	}
}
