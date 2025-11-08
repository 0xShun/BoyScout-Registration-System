import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class EventAttendanceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # URL route should provide event_id as kwargs
        self.event_id = self.scope['url_route']['kwargs'].get('event_id')
        if self.scope['user'].is_anonymous:
            await self.close()
            return

        self.group_name = f'event_{self.event_id}_attendance'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # No incoming messages expected from clients for now
        pass

    async def attendance_update(self, event):
        # Forward attendance update payload to connected clients
        await self.send(text_data=json.dumps({
            'type': 'attendance.update',
            'event_id': event.get('event_id'),
            'user_id': event.get('user_id'),
            'user_full_name': event.get('user_full_name'),
            'timestamp': event.get('timestamp'),
            'status': event.get('status'),
        }))
