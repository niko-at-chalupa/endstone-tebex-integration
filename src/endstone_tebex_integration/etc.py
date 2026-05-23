from endstone import Logger, Player
from endstone.plugin import Plugin
from endstone.map import MapRenderer, MapCanvas, MapView
from endstone.inventory import MapMeta, ItemStack
import numpy as np
from typing import cast, Any
import qrcode
from PIL import Image

async def generate_qr_map_array(data: str, target_size: int = 128) -> np.ndarray:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")

    pil_img_resized = pil_img.resize((target_size, target_size), resample=Image.Resampling.NEAREST)

    return np.array(pil_img_resized, dtype=np.uint8)

class ImageMapRenderer(MapRenderer):
    def __init__(self, image_array: np.ndarray) -> None:
        super().__init__(is_contextual=False)
        
        if image_array.shape[2] == 3:
            self.buffer = np.empty((128, 128, 4), dtype=np.uint8)
            self.buffer[:, :, :3] = image_array
            self.buffer[:, :, 3] = 255
        else:
            self.buffer = image_array

    def render(self, view: MapView, canvas: MapCanvas, player: Player) -> None:
        canvas.draw_image(0, 0, cast(Any, self.buffer))

def give_player_map_with_renderer(plugin: Plugin, player: Player, custom_renderer: MapRenderer):
    map_view = plugin.server.create_map(player.dimension)
    
    for renderer in list(map_view.renderers):
        map_view.remove_renderer(renderer)
    map_view.add_renderer(custom_renderer)
    
    item = ItemStack("minecraft:filled_map", 1)
    meta = item.item_meta
    
    if isinstance(meta, MapMeta):
        meta.map_view = map_view
        item.set_item_meta(meta)
        
    leftovers = player.inventory.add_item(item)
    
    if leftovers:
        for leftover_item in leftovers:
            if leftover_item and isinstance(leftover_item, ItemStack) and leftover_item.amount > 0:
                player.dimension.drop_item(player.location, leftover_item)
                
async def give_player_qr_code_map(plugin: Plugin, data: str, player: Player):
    map_view = ImageMapRenderer(await generate_qr_map_array(data=data))
    plugin.server.scheduler.run_task(plugin=plugin, task=lambda: give_player_map_with_renderer(plugin=plugin, player=player, custom_renderer=map_view))