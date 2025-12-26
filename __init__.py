from .RoliPianoRainbow import RoliPianoRainbow
from _Framework.Capabilities import (
    controller_id,
    inport,
    outport,
    CONTROLLER_ID_KEY,
    PORTS_KEY,
    NOTES_CC,
    SCRIPT,
    REMOTE,
    SYNC,
    TYPE_KEY,
    AUTO_LOAD_KEY,
)


def get_capabilities():
    # ROLI LUMI: VID 0x2AF4 (11012), PID 0x0F00 (3840)
    # Try two port pairs like Yaeltex does - maybe LUMI has multiple endpoints
    return {
        CONTROLLER_ID_KEY: controller_id(
            vendor_id=11012,
            product_ids=[3840],
            model_name="LUMI Keys"
        ),
        PORTS_KEY: [
            inport(props=[NOTES_CC, SCRIPT, REMOTE, SYNC]),
            inport(props=[]),
            outport(props=[NOTES_CC, SCRIPT, REMOTE, SYNC]),
            outport(props=[]),
        ],
        TYPE_KEY: "controller",
        AUTO_LOAD_KEY: False,
    }


def create_instance(c_instance):
    return RoliPianoRainbow(c_instance)
