import argparse
import os
from pathlib import Path
import sys
import mido
import tomllib
from dataclasses import dataclass, field

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "miniflow" / "config.toml"


@dataclass
class Trigger:
    type: str
    command: str = ""
    target: str = ""
    state: bool = False


@dataclass
class ControlConfig:
    path: str
    cc: int
    channel: int  # 0-indexed channel internally
    label: str = ""
    description: str = ""
    mode: str = "momentary"  # "momentary", "toggle", or "none"
    triggers: list[Trigger] = field(default_factory=list)


def parse_trigger(raw: dict, path_key: str) -> Trigger | None:
    if not isinstance(raw, dict):
        return None

    trig_type = raw.get("type")
    if not trig_type or not isinstance(trig_type, str):
        sys.exit(f"Fatal Error: Trigger in '{path_key}' missing valid 'type'.")

    trig_type = trig_type.lower()

    if trig_type == "applescript":
        command = raw.get("command")
        if not command or not isinstance(command, str):
            sys.exit(f"Fatal Error: 'applescript' trigger in '{path_key}' missing string 'command'.")
        return Trigger(type="applescript", command=command)

    elif trig_type == "set_toggle":
        target = raw.get("target")
        state = raw.get("state")
        if not target or not isinstance(target, str):
            sys.exit(f"Fatal Error: 'set_toggle' trigger in '{path_key}' missing string 'target'.")
        if not isinstance(state, bool):
            sys.exit(f"Fatal Error: 'set_toggle' trigger in '{path_key}' missing boolean 'state'.")
        return Trigger(type="set_toggle", target=target, state=state)

    else:
        sys.exit(f"Fatal Error: Unsupported trigger type '{trig_type}' in '{path_key}'.")


def load_config(config_file: Path) -> tuple[str, dict[tuple[int, int], ControlConfig], dict[str, ControlConfig]]:
    if not config_file.is_file():
        sys.exit(f"Fatal Error: Config file not found at {config_file}")

    try:
        with open(config_file, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        sys.exit(f"Fatal Error: Failed to parse TOML configuration in {config_file}: {e}")

    port_name = data.get("port_name")
    if not port_name or not isinstance(port_name, str):
        sys.exit(f"Fatal Error: 'port_name' key missing or invalid in {config_file}")

    raw_controls = data.get("controls")
    if not isinstance(raw_controls, dict) or not raw_controls:
        sys.exit(f"Fatal Error: 'controls' table missing or empty in {config_file}")

    controls_by_key: dict[tuple[int, int], ControlConfig] = {}
    controls_by_path: dict[str, ControlConfig] = {}
    valid_modes = {"momentary", "toggle", "none"}

    for path_key, v in raw_controls.items():
        if not isinstance(v, dict):
            continue

        raw_triggers = v.get("triggers", [])
        if not isinstance(raw_triggers, list) or not raw_triggers:
            continue

        cc = v.get("cc")
        channel = v.get("channel", 1)

        if not isinstance(cc, int) or not isinstance(channel, int):
            sys.exit(f"Fatal Error: Control '{path_key}' must specify integer 'cc' and 'channel'.")

        channel_0idx = channel - 1
        mode = str(v.get("mode", "momentary")).lower()
        if mode not in valid_modes:
            sys.exit(f"Fatal Error: Invalid mode '{mode}' for '{path_key}'. Must be one of {valid_modes}")

        parsed_triggers: list[Trigger] = []
        for item in raw_triggers:
            trig = parse_trigger(item, path_key)
            if trig:
                parsed_triggers.append(trig)

        if not parsed_triggers:
            continue

        cfg = ControlConfig(
            path=str(path_key),
            cc=cc,
            channel=channel_0idx,
            label=str(v.get("label", "")),
            description=str(v.get("description", "")),
            mode=mode,
            triggers=parsed_triggers,
        )

        controls_by_key[(channel_0idx, cc)] = cfg
        controls_by_path[str(path_key)] = cfg

    return port_name, controls_by_key, controls_by_path


def applescript(command: str) -> None:
    os.system(f"osascript -e '{command}'")


def send_cc(ioport: mido.ports.BasePort, channel: int, cc: int, value: int, verbose: bool = False) -> None:
    msg = mido.Message("control_change", channel=channel, control=cc, value=value)
    ioport.send(msg)
    if verbose:
        state_str = "ON" if value > 0 else "OFF"
        print(f"  └─> LED OUT Ch {channel + 1} CC {cc} -> {state_str}")


def execute_trigger(
    trigger: Trigger,
    ioport: mido.ports.BasePort,
    toggle_states: dict[str, bool],
    controls_by_path: dict[str, ControlConfig],
    verbose: bool = False,
) -> None:
    if trigger.type == "applescript":
        applescript(trigger.command)

    elif trigger.type == "set_toggle":
        if trigger.target in toggle_states:
            toggle_states[trigger.target] = trigger.state
            target_cfg = controls_by_path[trigger.target]
            val = 127 if trigger.state else 0
            send_cc(
                ioport,
                channel=target_cfg.channel,
                cc=target_cfg.cc,
                value=val,
                verbose=verbose,
            )


def main() -> None:
    if sys.platform != "darwin":
        sys.exit("Error: MiniFlow is currently supported on macOS only.")

    parser = argparse.ArgumentParser(description="MiniFlow: A minimal workflow system for creatives")
    parser.add_argument(
        "-c", "--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to config.toml file"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    args = parser.parse_args()

    port_name, controls_by_key, controls_by_path = load_config(args.config)

    input_ports = mido.get_input_names()
    matching = [p for p in input_ports if port_name.lower() in p.lower()]

    if not matching:
        sys.exit(f"Error: MIDI port containing '{port_name}' not found. Available: {input_ports}")

    target_port = matching[0]
    print(f"MiniFlow listening on: {target_port}")

    toggle_states: dict[str, bool] = {
        path: False for path, cfg in controls_by_path.items() if cfg.mode == "toggle"
    }

    try:
        with mido.open_ioport(target_port) as ioport:
            if toggle_states:
                if args.verbose:
                    print("Initializing toggle LEDs...")
                for path in toggle_states:
                    cfg = controls_by_path[path]
                    send_cc(ioport, channel=cfg.channel, cc=cfg.cc, value=0, verbose=args.verbose)

            for msg in ioport:
                if msg.type == "control_change" and msg.value > 0:
                    lookup_key = (msg.channel, msg.control)
                    ctrl = controls_by_key.get(lookup_key)

                    if ctrl:
                        if args.verbose:
                            name = ctrl.label or ctrl.path
                            print(f"[MIDI IN] {name} (Ch {msg.channel + 1}, CC {msg.control})")

                        for trigger in ctrl.triggers:
                            execute_trigger(
                                trigger=trigger,
                                ioport=ioport,
                                toggle_states=toggle_states,
                                controls_by_path=controls_by_path,
                                verbose=args.verbose,
                            )

                        if ctrl.mode == "momentary":
                            send_cc(ioport, msg.channel, msg.control, 0, verbose=args.verbose)

                        elif ctrl.mode == "toggle":
                            new_state = not toggle_states.get(ctrl.path, False)
                            toggle_states[ctrl.path] = new_state
                            val = 127 if new_state else 0
                            send_cc(ioport, msg.channel, msg.control, val, verbose=args.verbose)

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        sys.exit(f"Error handling MIDI stream: {e}")


if __name__ == "__main__":
    main()
