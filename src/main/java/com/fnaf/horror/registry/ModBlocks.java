package com.fnaf.horror.registry;

import com.fnaf.horror.FnafHorror;
import com.fnaf.horror.block.CeilingLightBlock;
import com.fnaf.horror.block.DecorBlock;
import com.fnaf.horror.block.DeskFanBlock;
import com.fnaf.horror.block.FacingDecorBlock;
import com.fnaf.horror.block.GeneratorBlock;
import com.fnaf.horror.block.GeneratorBlockEntity;
import com.fnaf.horror.block.LightButtonBlock;
import com.fnaf.horror.block.SpareHeadBlock;
import com.fnaf.horror.block.PropBlockEntity;
import net.minecraft.block.AbstractBlock;
import net.minecraft.block.Block;
import net.minecraft.block.BlockSetType;
import net.minecraft.block.DoorBlock;
import net.minecraft.block.LeverBlock;
import net.minecraft.block.RedstoneLampBlock;
import net.minecraft.block.SlabBlock;
import net.minecraft.block.MapColor;
import net.minecraft.block.entity.BlockEntityType;
import net.minecraft.block.piston.PistonBehavior;
import net.minecraft.item.BlockItem;
import net.minecraft.item.Item;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.sound.BlockSoundGroup;
import net.minecraft.sound.SoundEvents;

import java.util.ArrayList;
import java.util.List;

/** Pizzeria building blocks and props. Textures/models come from tools/pizzeria/gen_textures.py. */
public final class ModBlocks {
	public static final List<Block> ALL = new ArrayList<>();

	public static final Block CHECKER_FLOOR = register("checker_floor", new Block(stone(MapColor.WHITE)));
	public static final Block WALL_CHECKER = register("wall_checker", new Block(stone(MapColor.WHITE)));
	public static final Block WALL_PLASTER = register("wall_plaster", new Block(stone(MapColor.GRAY)));
	public static final Block WALL_RED = register("wall_red", new Block(stone(MapColor.RED)));
	public static final Block WALL_BASE = register("wall_base", new Block(stone(MapColor.BLACK)));
	public static final Block CONCRETE_WALL = register("concrete_wall", new Block(stone(MapColor.STONE_GRAY)));
	public static final Block CEILING_TILE = register("ceiling_tile", new Block(AbstractBlock.Settings.create()
			.mapColor(MapColor.WHITE_GRAY).strength(0.8f).sounds(BlockSoundGroup.WOOL)));
	public static final Block CEILING_LIGHT = register("ceiling_light", new CeilingLightBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.WHITE).strength(0.8f).sounds(BlockSoundGroup.GLASS)
			.luminance(s -> s.get(CeilingLightBlock.LIT) ? 13 : 0)));
	public static final Block STAGE_PLANKS = register("stage_planks", new Block(AbstractBlock.Settings.create()
			.mapColor(MapColor.BROWN).strength(2.0f).sounds(BlockSoundGroup.WOOD)));
	public static final Block STAR_CURTAIN = register("star_curtain", new Block(cloth(MapColor.BLACK)));
	public static final Block COVE_CURTAIN = register("cove_curtain", new Block(cloth(MapColor.PURPLE)));
	public static final Block RED_CURTAIN = register("red_curtain", new Block(cloth(MapColor.RED)));
	public static final Block BATH_TILE = register("bath_tile", new Block(stone(MapColor.WHITE)));
	public static final Block KITCHEN_TILE = register("kitchen_tile", new Block(stone(MapColor.TERRACOTTA_RED)));
	public static final Block DARK_TILE = register("dark_tile", new Block(stone(MapColor.DEEPSLATE_GRAY)));
	public static final Block PARTY_TABLE = register("party_table", new Block(cloth(MapColor.WHITE).strength(1.5f)));
	public static final Block PARTY_HAT = register("party_hat", new DecorBlock(decor().noCollision(),
			Block.createCuboidShape(5, 0, 5, 11, 12, 11)));
	public static final Block BALLOON = register("balloon", new DecorBlock(decor().noCollision().sounds(BlockSoundGroup.WOOL),
			Block.createCuboidShape(4, 0, 4, 12, 16, 12)));
	public static final Block CONFETTI = register("confetti", new DecorBlock(decor().noCollision().replaceable(),
			Block.createCuboidShape(0, 0, 0, 16, 0.5, 16)));
	public static final Block CRT_MONITOR = register("crt_monitor", new FacingDecorBlock(decor().sounds(BlockSoundGroup.METAL),
			Block.createCuboidShape(2, 0, 1, 14, 11, 13)));
	public static final Block ARCADE = register("arcade", new FacingDecorBlock(decor().sounds(BlockSoundGroup.WOOD).strength(2.0f),
			Block.createCuboidShape(1, 0, 1, 15, 16, 15)));
	public static final Block GENERATOR = register("generator", new GeneratorBlock(decor().sounds(BlockSoundGroup.METAL).strength(3.0f)));
	public static final Block DESK_FAN = register("desk_fan", new DeskFanBlock(decor().sounds(BlockSoundGroup.METAL)));

	/** Sounds of the steel office doors and the office buttons. */
	public static final BlockSetType SECURITY = new BlockSetType("fnaf_security", false, BlockSoundGroup.METAL,
			ModSounds.DOOR_CLOSE, ModSounds.DOOR_OPEN, SoundEvents.BLOCK_IRON_TRAPDOOR_CLOSE, SoundEvents.BLOCK_IRON_TRAPDOOR_OPEN,
			SoundEvents.BLOCK_METAL_PRESSURE_PLATE_CLICK_OFF, SoundEvents.BLOCK_METAL_PRESSURE_PLATE_CLICK_ON,
			ModSounds.BUTTON_CLICK, ModSounds.BUTTON_CLICK);
	public static final BlockSetType STALL = new BlockSetType("fnaf_stall", true, BlockSoundGroup.WOOD,
			SoundEvents.BLOCK_WOODEN_DOOR_CLOSE, SoundEvents.BLOCK_WOODEN_DOOR_OPEN, SoundEvents.BLOCK_WOODEN_TRAPDOOR_CLOSE,
			SoundEvents.BLOCK_WOODEN_TRAPDOOR_OPEN, SoundEvents.BLOCK_WOODEN_PRESSURE_PLATE_CLICK_OFF,
			SoundEvents.BLOCK_WOODEN_PRESSURE_PLATE_CLICK_ON, ModSounds.BUTTON_CLICK, ModSounds.BUTTON_CLICK);

	// furniture and fittings (tools/pizzeria/gen_decor.py)
	public static final Block CHAIR = register("chair", new FacingDecorBlock(decor().sounds(BlockSoundGroup.METAL), 2.5, 0, 2.5, 13.5, 21, 13.5));
	public static final Block PLATE = register("plate", new DecorBlock(decor().noCollision(), Block.createCuboidShape(2, 0, 2, 14, 1, 14)));
	public static final Block SODA_CUP = register("soda_cup", new DecorBlock(decor().noCollision(), Block.createCuboidShape(6, 0, 6, 10, 10, 10)));
	public static final Block STREAMER = register("streamer", new DecorBlock(decor().noCollision().sounds(BlockSoundGroup.WOOL),
			Block.createCuboidShape(2, 0, 2, 14, 16, 14)));
	public static final Block COBWEB = register("cobweb", new DecorBlock(decor().noCollision().sounds(BlockSoundGroup.WOOL),
			Block.createCuboidShape(0, 0, 0, 16, 16, 16)));
	public static final Block MIRROR = register("mirror", new FacingDecorBlock(decor().noCollision().sounds(BlockSoundGroup.GLASS), 1, 1, 0, 15, 15, 1));
	public static final Block OUT_OF_ORDER_SIGN = register("out_of_order_sign", new FacingDecorBlock(decor().noCollision(), 2, 3, 0, 14, 13, 1));
	public static final Block OFFICE_WINDOW = register("office_window", new FacingDecorBlock(decor().sounds(BlockSoundGroup.GLASS),
			0, 0, 7.5, 16, 16, 8.5));
	public static final Block CARDBOARD_BOX = register("cardboard_box", new Block(AbstractBlock.Settings.create()
			.mapColor(MapColor.BROWN).strength(0.6f).sounds(BlockSoundGroup.WOOL)));
	public static final Block SINK = register("sink", new FacingDecorBlock(decor().sounds(BlockSoundGroup.STONE), 1, 0, 1, 15, 17, 13));
	public static final Block TOILET = register("toilet", new FacingDecorBlock(decor().sounds(BlockSoundGroup.STONE), 2, 0, 0, 14, 17, 15));
	public static final Block COOKING_POT = register("cooking_pot", new DecorBlock(decor().sounds(BlockSoundGroup.METAL),
			Block.createCuboidShape(1, 0, 3, 15, 7, 13)));
	public static final Block OVEN = register("oven", new FacingDecorBlock(decor().sounds(BlockSoundGroup.METAL).strength(2.0f), 0, 0, 0, 16, 16, 16));
	public static final Block FRIDGE = register("fridge", new FacingDecorBlock(decor().sounds(BlockSoundGroup.METAL).strength(2.0f), 1, 0, 1, 15, 16, 15));
	public static final Block COUNTER = register("counter", new Block(AbstractBlock.Settings.create()
			.mapColor(MapColor.IRON_GRAY).strength(2.0f).sounds(BlockSoundGroup.METAL)));
	public static final Block METAL_SHELF = register("metal_shelf", new FacingDecorBlock(decor().sounds(BlockSoundGroup.METAL), 0.5, 0, 1, 15.5, 16, 15));
	public static final Block WORKBENCH = register("workbench", new FacingDecorBlock(decor().sounds(BlockSoundGroup.WOOD), 0, 0, 0, 16, 14, 16));
	public static final Block MOP_BUCKET = register("mop_bucket", new DecorBlock(decor(), Block.createCuboidShape(3, 0, 3, 13, 11, 13)));
	public static final Block TRASH_CAN = register("trash_can", new DecorBlock(decor(), Block.createCuboidShape(2.5, 0, 2.5, 13.5, 14, 13.5)));
	public static final Block OFFICE_DESK = register("office_desk", new FacingDecorBlock(decor().sounds(BlockSoundGroup.WOOD).strength(1.5f),
			0, 0, 0, 16, 16, 16));
	public static final Block OFFICE_CHAIR = register("office_chair", new FacingDecorBlock(decor(), 2, 0, 2, 14, 22, 14));
	public static final Block PAPERS = register("papers", new FacingDecorBlock(decor().noCollision().sounds(BlockSoundGroup.WOOL), 1, 0, 1, 15, 0.5, 15));
	public static final Block CUPCAKE = register("cupcake", new FacingDecorBlock(decor().noCollision().sounds(BlockSoundGroup.WOOL), 4.5, 0, 4.5, 11.5, 12, 11.5));
	public static final Block SPEAKER = register("speaker", new FacingDecorBlock(decor().sounds(BlockSoundGroup.WOOD).strength(1.5f), 0, 0, 0, 16, 16, 16));
	public static final Block STALL_WALL = register("stall_wall", new Block(AbstractBlock.Settings.create()
			.mapColor(MapColor.PALE_YELLOW).strength(1.0f).sounds(BlockSoundGroup.WOOD)));
	public static final Block STAGE_STEP = register("stage_step", new SlabBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.BROWN).strength(2.0f).sounds(BlockSoundGroup.WOOD)));
	public static final Block STALL_DOOR = register("stall_door", new DoorBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.PALE_YELLOW).strength(1.5f).nonOpaque().pistonBehavior(PistonBehavior.DESTROY), STALL));
	public static final Block SECURITY_DOOR = register("security_door", new DoorBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.IRON_GRAY).strength(5.0f).nonOpaque().pistonBehavior(PistonBehavior.DESTROY), SECURITY));
	public static final Block DOOR_BUTTON = register("door_button", new LeverBlock(AbstractBlock.Settings.create()
			.noCollision().strength(0.5f).sounds(BlockSoundGroup.METAL).pistonBehavior(PistonBehavior.DESTROY)));
	public static final Block LIGHT_BUTTON = register("light_button", new LightButtonBlock(AbstractBlock.Settings.create()
			.noCollision().strength(0.5f).pistonBehavior(PistonBehavior.DESTROY), SECURITY));
	public static final Block DOOR_LIGHT = register("door_light", new RedstoneLampBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.YELLOW).strength(0.3f).sounds(BlockSoundGroup.GLASS)
			.luminance(s -> s.get(RedstoneLampBlock.LIT) ? 15 : 0)));
	public static final Block MAP_BLOCK = register("map_block", new com.fnaf.horror.block.MapBlock(AbstractBlock.Settings.create()
			.mapColor(MapColor.GRAY).strength(-1.0f, 3600000.0f).nonOpaque().dropsNothing()
			.luminance(com.fnaf.horror.block.MapBlock::luminance).solidBlock((s, w, p) -> false)
			.suffocates((s, w, p) -> false).blockVision((s, w, p) -> false)));
	public static final Block GAS_CAN = register("gas_can", new com.fnaf.horror.block.GasCanBlock(decor().sounds(BlockSoundGroup.METAL)));
	public static final Block SPARE_HEAD = register("spare_head", new SpareHeadBlock(decor().sounds(BlockSoundGroup.WOOL)));

	public static final BlockEntityType<GeneratorBlockEntity> GENERATOR_ENTITY = Registry.register(Registries.BLOCK_ENTITY_TYPE,
			FnafHorror.id("generator"), BlockEntityType.Builder.create(GeneratorBlockEntity::new, GENERATOR).build(null));
	public static final BlockEntityType<PropBlockEntity> DESK_FAN_ENTITY = Registry.register(Registries.BLOCK_ENTITY_TYPE,
			FnafHorror.id("desk_fan"), BlockEntityType.Builder.<PropBlockEntity>create(
					(pos, state) -> new PropBlockEntity(ModBlocks.DESK_FAN_ENTITY, pos, state), DESK_FAN).build(null));

	public static final BlockEntityType<PropBlockEntity> SPARE_HEAD_ENTITY = Registry.register(Registries.BLOCK_ENTITY_TYPE,
			FnafHorror.id("spare_head"), BlockEntityType.Builder.<PropBlockEntity>create(
					(pos, state) -> new PropBlockEntity(ModBlocks.SPARE_HEAD_ENTITY, pos, state), SPARE_HEAD).build(null));

	private static AbstractBlock.Settings stone(MapColor color) {
		return AbstractBlock.Settings.create().mapColor(color).strength(1.5f, 6.0f).sounds(BlockSoundGroup.STONE);
	}

	private static AbstractBlock.Settings cloth(MapColor color) {
		return AbstractBlock.Settings.create().mapColor(color).strength(0.8f).sounds(BlockSoundGroup.WOOL);
	}

	private static AbstractBlock.Settings decor() {
		return AbstractBlock.Settings.create().strength(0.5f).nonOpaque().pistonBehavior(PistonBehavior.DESTROY);
	}

	private static Block register(String id, Block block) {
		Registry.register(Registries.BLOCK, FnafHorror.id(id), block);
		Registry.register(Registries.ITEM, FnafHorror.id(id), new BlockItem(block, new Item.Settings()));
		ALL.add(block);
		return block;
	}

	public static void register() {
		// class load registers the fields above
	}

	private ModBlocks() {
	}
}
