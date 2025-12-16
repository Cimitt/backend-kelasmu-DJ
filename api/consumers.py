import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .models import ClassChatMessage, DirectChatMessage, ChatAttachment
from api.models import Enrollment, Material

User = get_user_model()


@database_sync_to_async
def is_enrolled(user, material_id):
    material = Material.objects.select_related("classroom").get(id=material_id)
    return Enrollment.objects.filter(user=user, classroom=material.classroom).exists()


class MaterialChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.material_id = self.scope["url_route"]["kwargs"]["material_id"]
        self.room_group_name = f"material_{self.material_id}"

        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        allowed = await is_enrolled(user, self.material_id)
        if not allowed:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        user = self.scope["user"]

        # auth
        if not user.is_authenticated:
            await self.send(json.dumps({"error": "auth required"}))
            return

        event_type = data.get("type")

        # typing indicator
        if event_type == "typing":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "typing_event",
                    "user_id": user.id,
                    "is_typing": data.get("is_typing", False),
                },
            )
            return

        # read
        if event_type == "read":
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "read_event",
                    "user_id": user.id,
                    "message_ids": data.get("message_ids", []),
                },
            )
            return

        # 
        message = data.get("message")
        attachment_id = data.get("attachment_id")

        msg_obj = await database_sync_to_async(ClassChatMessage.objects.create)(
            material_id=self.material_id,
            sender=user,
            content=message,
        )

        if attachment_id:
            await database_sync_to_async(
                msg_obj.attachment_id.__setattr__("id", attachment_id)
            )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": user.username,
                "sender_id": user.id,
                "message_id": msg_obj.id,
            },
        )

    # event handler

    async def chat_message(self, event):
        await self.send(json.dumps({**event, "type": "message"}))

    async def typing_event(self, event):
        await self.send(json.dumps(event))

    async def read_event(self, event):
        await self.send(json.dumps(event))


class DirectChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        self.other_user_id = self.scope["url_route"]["kwargs"]["other_user_id"]
        me = str(user.id)
        ids = sorted([me, str(self.other_user_id)])
        self.room_group_name = f"direct_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.send(json.dumps({"error": "auth required"}))
            return

        message = data.get("message", "").strip()
        if not message:
            # ignore empty messages
            return

        recipient = await database_sync_to_async(User.objects.get)(id=self.other_user_id)

        msg = await database_sync_to_async(DirectChatMessage.objects.create)(
            sender=user,
            recipient=recipient,
            content=message,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "direct_message",
                "message": message,
                "sender": user.username,
                "sender_id": user.id,
                "recipient_id": recipient.id,
                "message_id": msg.id,
            },
        )

    async def direct_message(self, event):
        await self.send(json.dumps({**event, "type": "direct"}))
