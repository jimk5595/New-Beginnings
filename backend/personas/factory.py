from personas.dropshipping.expert import DropshippingExpert
from personas.stocks.analyst import StockAnalyst
from personas.video.editor import VideoEditor
from personas.video.creator import VideoCreator
from personas.video.strategist import VideoStrategist
from personas.games.designer import GameDesigner
from personas.games.strategist import GameStrategist
from personas.games.analyst import GameAnalyst

PERSONA_REGISTRY = {
    "dropshipping_expert": DropshippingExpert,
    "stock_analyst": StockAnalyst,
    "video_editor": VideoEditor,
    "video_creator": VideoCreator,
    "video_strategist": VideoStrategist,
    "game_designer": GameDesigner,
    "game_strategist": GameStrategist,
    "game_analyst": GameAnalyst,
}

def create_persona(persona_name: str):
    cls = PERSONA_REGISTRY.get(persona_name)
    if cls is None:
        raise ValueError(f"Unknown persona: {persona_name}")
    return cls()
