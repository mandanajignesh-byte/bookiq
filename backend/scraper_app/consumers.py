import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ScrapeProgressConsumer(AsyncWebsocketConsumer):
    """
    WebSocket endpoint: ws://host/ws/scrape/<job_id>/
    Client connects → joins group → receives live progress events from Celery task.
    """

    async def connect(self):
        self.job_id = self.scope['url_route']['kwargs']['job_id']
        self.group_name = f'scrape_{self.job_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def scrape_progress(self, event):
        """Receive from channel layer and forward to WebSocket client."""
        await self.send(text_data=json.dumps({
            'current': event['current'],
            'total': event['total'],
            'percent': event['percent'],
            'message': event['message'],
            'status': event['status'],
        }))
