import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class GroupChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'chat_{self.group_id}'

        user = self.scope.get('user', AnonymousUser())
        if not user.is_authenticated:
            await self.close()
            return

        has_access = await self._check_membership(user)
        if not has_access:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '').strip()
        if not message:
            return

        user = self.scope['user']

        chat_msg = await self._save_message(user, message, is_ai=False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': user.username,
                'is_ai': False,
                'time': chat_msg.created_at.strftime('%H:%M'),
            }
        )

        if '@buddy' in message.lower() or '@ai' in message.lower():
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                }
            )

            ai_response = await self._get_ai_response()

            ai_msg = await self._save_message(None, ai_response, is_ai=True)

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': ai_response,
                    'username': 'Buddy',
                    'is_ai': True,
                    'time': ai_msg.created_at.strftime('%H:%M'),
                }
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'username': event['username'],
            'is_ai': event['is_ai'],
            'time': event['time'],
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing',
        }))

    @database_sync_to_async
    def _check_membership(self, user):
        from .models import Group
        try:
            group = Group.objects.get(id=self.group_id)
            return user in group.members.all()
        except Group.DoesNotExist:
            return False

    @database_sync_to_async
    def _save_message(self, user, content, is_ai):
        from .models import Group, ChatMessage
        group = Group.objects.get(id=self.group_id)
        msg = ChatMessage.objects.create(
            group=group,
            sender=user,
            content=content,
            is_ai=is_ai,
        )
        return msg

    async def _get_ai_response(self):
        from ai_engine.qwen import chat, SYSTEM_GROUP_CHAT
        from .models import Group

        group = await database_sync_to_async(Group.objects.get)(id=self.group_id)
        member_names = await database_sync_to_async(
            lambda: [m.username for m in group.members.all()]
        )()
        recent = await database_sync_to_async(
            lambda: list(group.messages.all().order_by('-created_at')[:20])
        )()

        messages = []
        system_text = SYSTEM_GROUP_CHAT + (
            f" Your group is called \"{group.name}\". "
            f"Members: {', '.join(member_names)}. "
            "You are part of this friend group."
        )
        messages.append({"role": "system", "content": system_text})

        for msg in reversed(recent):
            if msg.is_ai:
                messages.append({"role": "assistant", "content": msg.content})
            else:
                prefix = f"{msg.sender.username}: " if msg.sender else "Buddy: "
                messages.append({"role": "user", "content": prefix + msg.content})

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: chat(messages))
        return response