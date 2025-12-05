import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Material, ClassChatMessage, DirectChatMessage

User = get_user_model()


class MaterialChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.material_id = self.scope["url_route"]["kwargs"]["material_id"]
        self.room_group_name = f"material_{self.material_id}"

        # optionally check if user is enrolled in the class for security
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        message = data.get("message")

        user = self.scope["user"]
        if not user.is_authenticated:
            await self.send(json.dumps({"error": "auth required"}))
            return

        # save message to DB
        await database_sync_to_async(ClassChatMessage.objects.create)(
            material_id=self.material_id, sender=user, content=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "message": message,
                "sender": user.username,
                "sender_id": user.id,
            },
        )

    async def chat_message(self, event):
        # forward to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                }
            )
        )


class DirectChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # url contains other_user_id
        self.other_user_id = self.scope["url_route"]["kwargs"]["other_user_id"]
        me = (
            str(self.scope["user"].id)
            if self.scope["user"].is_authenticated
            else "anon"
        )
        # canonical room: smallerid_biggerid
        ids = sorted([me, str(self.other_user_id)])
        self.room_group_name = f"direct_{ids[0]}_{ids[1]}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        message = data.get("message")
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.send(json.dumps({"error": "auth required"}))
            return

        recipient = await database_sync_to_async(User.objects.get)(
            id=self.other_user_id
        )
        await database_sync_to_async(DirectChatMessage.objects.create)(
            sender=user, recipient=recipient, content=message
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "direct.message",
                "message": message,
                "sender": user.username,
                "sender_id": user.id,
                "recipient_id": recipient.id,
            },
        )

    async def direct_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "message": event["message"],
                    "sender": event["sender"],
                    "sender_id": event["sender_id"],
                    "recipient_id": event["recipient_id"],
                }
            )
        )
