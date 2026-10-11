package com.fnaf.horror.registry;

import com.fnaf.horror.FnafHorror;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.sound.SoundEvent;
import net.minecraft.util.Identifier;

/** Animatronic / pizzeria sounds: CC0 freesound recordings + procedural ones (tools/sounds/fnaf_sounds.py) (see tools/sounds/gen_sounds.py). */
public final class ModSounds {
	public static final SoundEvent STEP = register("animatronic.step");
	public static final SoundEvent SERVO = register("animatronic.servo");
	public static final SoundEvent HURT = register("animatronic.hurt");
	public static final SoundEvent DEATH = register("animatronic.death");
	public static final SoundEvent AMBIENT = register("animatronic.ambient");
	public static final SoundEvent STATIC = register("animatronic.static");
	public static final SoundEvent JUMPSCARE = register("animatronic.jumpscare");
	public static final SoundEvent GENERATOR_RUN = register("generator.run");
	public static final SoundEvent GENERATOR_PULL = register("generator.pull");
	public static final SoundEvent GENERATOR_START = register("generator.start");
	public static final SoundEvent GENERATOR_STOP = register("generator.stop");
	public static final SoundEvent POWER_DOWN = register("power.down");
	public static final SoundEvent FLASHLIGHT_CLICK = register("flashlight.click");
	public static final SoundEvent LAUGH = register("animatronic.laugh");
	public static final SoundEvent FOXY_RUN = register("foxy.run");
	public static final SoundEvent FOXY_BANG = register("foxy.bang");
	public static final SoundEvent KITCHEN_POTS = register("kitchen.pots");
	public static final SoundEvent MUSIC_BOX = register("music_box");
	public static final SoundEvent PIZZERIA_AMBIENCE = register("pizzeria.ambience");
	public static final SoundEvent FAN_LOOP = register("fan.loop");
	public static final SoundEvent DOOR_CLOSE = register("door.close");
	public static final SoundEvent DOOR_OPEN = register("door.open");
	public static final SoundEvent DOOR_LIGHT_BUZZ = register("door_light.buzz");
	public static final SoundEvent BUTTON_CLICK = register("button.click");
	public static final SoundEvent NIGHT_CHIMES = register("night.chimes");
	public static final SoundEvent NIGHT_CHEER = register("night.cheer");
	public static final SoundEvent CAM_OPEN = register("cam.open");
	public static final SoundEvent CAM_CLOSE = register("cam.close");
	public static final SoundEvent CAM_SWITCH = register("cam.switch");
	public static final SoundEvent MENU_MUSIC = register("menu.music");
	public static final SoundEvent FUEL_POUR = register("fuel.pour");
	public static final SoundEvent FUEL_SPILL = register("fuel.spill");
	public static final SoundEvent FUEL_PICKUP = register("fuel.pickup");

	private static SoundEvent register(String name) {
		Identifier id = FnafHorror.id(name);
		return Registry.register(Registries.SOUND_EVENT, id, SoundEvent.of(id));
	}

	public static void register() {
		// class load registers the fields above
	}

	private ModSounds() {
	}
}
