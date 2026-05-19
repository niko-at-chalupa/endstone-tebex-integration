from endstone.plugin import Plugin
from endstone.event import event_handler

class TebexIntegrationPlugin(Plugin):
    def on_enable(self):
        self.register_events(self)