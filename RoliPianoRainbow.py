# ROLI LUMI Scale Sync for Ableton Live 12
#
# Automatically syncs LUMI keyboard to Ableton's scale/key.
# When a Drum Rack is selected, switches to chromatic (all pads visible).

from ableton.v2.control_surface import ControlSurface
from ableton.v2.base import listens, liveobj_valid


class RoliPianoRainbow(ControlSurface):

    def __init__(self, c_instance):
        super(RoliPianoRainbow, self).__init__(c_instance)
        self._c_instance = c_instance

        self._last_root = None
        self._last_scale = None
        self._last_device = None

        # Listen to Live's scale settings
        self._on_root_note_changed.subject = self.song
        self._on_scale_name_changed.subject = self.song
        
        # Listen to selected track for drum rack detection
        self._on_selected_track_changed.subject = self.song.view

        # Initial sync after a short delay
        self.schedule_message(1, self._sync_from_live)

        self._log("[LUMI] LUMI Scale Sync loaded")

    def _log(self, msg):
        self._c_instance.log_message(str(msg))

    # --- Live listeners ---

    @listens("root_note")
    def _on_root_note_changed(self):
        self._sync_from_live()

    @listens("scale_name")
    def _on_scale_name_changed(self):
        self._sync_from_live()

    @listens("selected_track")
    def _on_selected_track_changed(self):
        self._sync_from_live()

    def _sync_from_live(self):
        """Sync LUMI to current scale/key or drum rack"""
        # Check if current device is a drum rack
        track = self.song.view.selected_track
        device = track.view.selected_device if liveobj_valid(track) else None
        
        is_drum_rack = (liveobj_valid(device) and 
                       hasattr(device, 'can_have_drum_pads') and 
                       device.can_have_drum_pads)
        
        if is_drum_rack:
            # Drum mode: just chromatic scale (keeps current color mode)
            if device != self._last_device:
                self._last_device = device
                self._log(f"[LUMI] Drum Rack: {device.name}")
                
                # Chromatic scale (all pads visible)
                chromatic_cmd = [0x10, 0x60, 0x42, 0x04, 0x00, 0x00, 0x00, 0x00]
                self._send_blocks_command(chromatic_cmd)
                
                # Root at C
                c_key_cmd = [0x10, 0x30, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00]
                self._send_blocks_command(c_key_cmd)
        else:
            # Scale mode: use Ableton's scale/key
            song = self.song
            root = int(getattr(song, "root_note", 0) or 0)
            scale_name = str(getattr(song, "scale_name", "") or "")

            # Debounce
            if root == self._last_root and scale_name == self._last_scale and device == self._last_device:
                return

            self._last_root = root
            self._last_scale = scale_name
            self._last_device = device

            self._log(f"[LUMI] Scale: {scale_name}, Root: {root}")
            
            # Send scale
            scale_cmd = self._get_scale_command(scale_name)
            self._send_blocks_command(scale_cmd)
            
            # Send key/root
            key_cmd = self._get_key_command(root)
            self._send_blocks_command(key_cmd)

    # --- BLOCKS Protocol ---

    def _blocks_checksum(self, command_bytes):
        """
        BLOCKS checksum algorithm:
        c = size
        for b in bytes:
            c = (c * 3 + b) & 0xFF
        return c & 0x7F
        """
        c = len(command_bytes)
        for b in command_bytes:
            c = (c * 3 + b) & 0xFF
        return c & 0x7F

    def _send_blocks_command(self, command_bytes):
        """Send BLOCKS-format command with broadcast selector 0x00"""
        header = [0xF0, 0x00, 0x21, 0x10, 0x77, 0x00]  # Device selector 0x00 (broadcast)
        chk = self._blocks_checksum(command_bytes)
        msg = tuple(header + command_bytes + [chk, 0xF7])
        
        self._send_midi(msg)

    def _get_scale_command(self, scale_name):
        """Get BLOCKS scale command (from SYSEX.txt)"""
        name = (scale_name or "").strip().lower()
        
        scales = {
            "major":               [0x10, 0x60, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00],
            "minor":               [0x10, 0x60, 0x22, 0x00, 0x00, 0x00, 0x00, 0x00],
            "harmonic minor":      [0x10, 0x60, 0x42, 0x00, 0x00, 0x00, 0x00, 0x00],
            "dorian":              [0x10, 0x60, 0x62, 0x01, 0x00, 0x00, 0x00, 0x00],
            "phrygian":            [0x10, 0x60, 0x02, 0x02, 0x00, 0x00, 0x00, 0x00],
            "lydian":              [0x10, 0x60, 0x22, 0x02, 0x00, 0x00, 0x00, 0x00],
            "mixolydian":          [0x10, 0x60, 0x42, 0x02, 0x00, 0x00, 0x00, 0x00],
            "blues":               [0x10, 0x60, 0x42, 0x01, 0x00, 0x00, 0x00, 0x00],
            "pentatonic major":    [0x10, 0x60, 0x02, 0x01, 0x00, 0x00, 0x00, 0x00],
            "pentatonic minor":    [0x10, 0x60, 0x22, 0x01, 0x00, 0x00, 0x00, 0x00],
            "chromatic":           [0x10, 0x60, 0x42, 0x04, 0x00, 0x00, 0x00, 0x00],
        }
        
        return scales.get(name, scales["major"])

    def _get_key_command(self, root_0_11):
        """
        Get BLOCKS key command (from SYSEX.txt)
        Pattern: val = 0x03 + 0x20*note, split into 7-bit bytes
        """
        val = 0x03 + (0x20 * int(root_0_11))
        b3 = val & 0x7F
        b4 = (val >> 7) & 0x7F
        return [0x10, 0x30, b3, b4, 0x00, 0x00, 0x00, 0x00]
