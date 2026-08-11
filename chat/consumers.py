import json
import uuid
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Q


class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = self.scope['user']

        print(f"🔌 WebSocket connect attempt: user={self.user.username if self.user.is_authenticated else 'Anonymous'}, conv={self.conversation_id}")

        if not self.user.is_authenticated:
            print("❌ User not authenticated, closing")
            await self.close()
            return

        if not await self.is_participant():
            print(f"❌ User {self.user.username} not participant of conversation {self.conversation_id}")
            await self.close()
            return

        self.room_group_name = f'dm_{self.conversation_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"✅ WebSocket connected: {self.user.username} joined {self.room_group_name}")
        await self.mark_messages_read()
        await self.send_pending_delivery_receipts()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            print("❌ Invalid JSON received")
            return

        msg_type = data.get('type', 'text')
        print(f"📨 Received: type={msg_type}, user={self.user.username}")

        if msg_type == 'text':
            # Plain text message
            content = data.get('message', '').strip()
            if not content:
                return
            try:
                message = await self.save_text_message(content)
                print(f"✅ Saved message id={message.id}, content={content[:30]}")
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type':            'chat_message',
                        'message_type':    'text',
                        'message':         content,
                        'sender_username': self.user.username,
                        'sender_avatar':   await self.get_avatar(),
                        'timestamp':       message.created_at.strftime('%H:%M'),
                        'message_id':      message.id,
                        'message_status':  'sent',
                    }
                )
                print(f"📤 Broadcasted to group: {self.room_group_name}")
            except Exception as e:
                print(f"❌ Error saving text message: {e}")

        elif msg_type in ('file', 'image', 'voice'):
            # File/Image/Voice — uploaded via HTTP first
            message_id   = data.get('message_id')
            file_url     = data.get('file_url')
            file_name    = data.get('file_name', '')
            file_size    = data.get('file_size', '')
            duration     = data.get('duration', 0)

            if not message_id or not file_url:
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'chat_message',
                    'message_type':    msg_type,
                    'message_id':      message_id,
                    'file_url':        file_url,
                    'file_name':       file_name,
                    'file_size':       file_size,
                    'duration':        duration,
                    'sender_username': self.user.username,
                    'sender_avatar':   await self.get_avatar(),
                    'timestamp':       data.get('timestamp', ''),
                    'message_status':  'sent',
                }
            )

        elif msg_type == 'typing':
            # Typing indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'typing_indicator',
                    'sender_username': self.user.username,
                    'is_typing':       data.get('is_typing', False),
                }
            )

        elif msg_type == 'voice_recording':
            # Voice recording indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'voice_recording_indicator',
                    'sender_username': self.user.username,
                    'is_recording':    data.get('is_recording', False),
                }
            )

        elif msg_type == 'message_delivered':
            # Message delivered receipt
            message_id = data.get('message_id')
            if message_id:
                await self.update_message_delivered(message_id)

        elif msg_type == 'message_read':
            # Message read receipt
            message_id = data.get('message_id')
            if message_id:
                await self.update_message_read(message_id)

        # WebRTC Video Call Signaling
        elif msg_type == 'call_offer':
            await self.handle_call_offer(data)

        elif msg_type == 'call_answer':
            await self.handle_call_answer(data)

        elif msg_type == 'ice_candidate':
            await self.handle_ice_candidate(data)

        elif msg_type == 'call_end':
            await self.handle_call_end(data)

        elif msg_type == 'call_rejected':
            await self.handle_call_rejected(data)

    async def chat_message(self, event):
        print(f"📥 Sending to {self.user.username}: {event.get('message', '')[:30]} (type: {event.get('message_type')})")
        await self.send(text_data=json.dumps(event))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps(event))

    async def voice_recording_indicator(self, event):
        await self.send(text_data=json.dumps(event))

    async def message_delivery_receipt(self, event):
        """Send delivery receipt to sender"""
        await self.send(text_data=json.dumps(event))

    async def message_read_receipt(self, event):
        """Send read receipt to sender"""
        await self.send(text_data=json.dumps(event))

    # WebRTC Signaling Handlers
    async def handle_call_offer(self, data):
        """Caller sends offer with SDP and optional call_id (UUID)"""
        call_id = data.get('call_id') or str(uuid.uuid4())
        offer = data.get('offer')
        call_type = data.get('call_type', 'direct')

        if not offer:
            return

        # Create or get VideoCall record
        call = await self.create_video_call(call_id, call_type, is_caller=True)

        # Broadcast offer to other participant(s) - EXCLUDE the caller
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':            'call_offer',
                'call_id':         call_id,
                'offer':           offer,
                'caller_username': self.user.username,
                'caller_avatar':   await self.get_avatar(),
                'call_type':       call_type,
                'exclude_sender':  True,  # Mark to exclude sender
            }
        )

    async def handle_call_answer(self, data):
        """Receiver answers with SDP answer"""
        call_id = data.get('call_id')
        answer = data.get('answer')

        if not call_id or not answer:
            return

        # Update call status to active
        await self.update_video_call_status(call_id, 'active')

        # Send answer back to caller
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':              'call_answer',
                'call_id':           call_id,
                'answer':            answer,
                'responder_username': self.user.username,
            }
        )

    async def handle_ice_candidate(self, data):
        """Relay ICE candidate to other peer(s)"""
        call_id = data.get('call_id')
        candidate = data.get('candidate')

        if not call_id or not candidate:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':           'ice_candidate',
                'call_id':        call_id,
                'candidate':      candidate,
                'sender_username': self.user.username,
            }
        )

    async def handle_call_end(self, data):
        """Either party ends the call"""
        call_id = data.get('call_id')

        if call_id:
            await self.end_video_call(call_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':            'call_end',
                'call_id':         call_id,
                'ended_by':        self.user.username,
            }
        )

    async def handle_call_rejected(self, data):
        """Receiver declines the call"""
        call_id = data.get('call_id')

        if call_id:
            await self.end_video_call(call_id, status='declined')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':              'call_rejected',
                'call_id':           call_id,
                'rejected_by':       self.user.username,
            }
        )

    # WebRTC Event Handlers (receive from channel layer)
    async def call_offer(self, event):
        """Incoming call offer - send to frontend (unless we're the caller)"""
        # Don't send call_offer back to the caller
        if event.get('caller_username') == self.user.username:
            return
        await self.send(text_data=json.dumps(event))

    async def call_answer(self, event):
        """Call answer received - send to frontend"""
        await self.send(text_data=json.dumps(event))

    async def ice_candidate(self, event):
        """ICE candidate received - send to frontend"""
        await self.send(text_data=json.dumps(event))

    async def call_end(self, event):
        """Call ended - send to frontend"""
        await self.send(text_data=json.dumps(event))

    async def call_rejected(self, event):
        """Call rejected - send to frontend"""
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_participant(self):
        from .models import DirectConversation
        return DirectConversation.objects.filter(
            id=self.conversation_id, participants=self.user
        ).exists()

    @database_sync_to_async
    def save_text_message(self, content):
        from .models import DirectMessage, DirectConversation
        from notifications.models import Notification

        conv = DirectConversation.objects.get(id=self.conversation_id)
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        message = DirectMessage.objects.create(
            conversation=conv, sender=self.user,
            message_type='text', content=content
        )

        # Notify the other participant
        recipient = conv.participants.exclude(id=self.user.id).first()
        if recipient:
            Notification.objects.create(
                recipient=recipient,
                actor=self.user,
                verb=f'{self.user.username} sent you a message',
                description=content[:100],
                notification_type='message',
            )

        return message

    @database_sync_to_async
    def mark_messages_read(self):
        from .models import DirectMessage
        DirectMessage.objects.filter(
            conversation_id=self.conversation_id, is_read=False
        ).exclude(sender=self.user).update(is_read=True)

    @database_sync_to_async
    def get_avatar(self):
        if self.user.avatar:
            return self.user.avatar.url
        return '/static/img/default_avatar.png'

    async def send_pending_delivery_receipts(self):
        """Send delivery receipts for messages that haven't been delivered yet"""
        from .models import DirectMessage
        # Get messages from others that are only 'sent' status
        undelivered = await database_sync_to_async(
            lambda: list(DirectMessage.objects.filter(
                conversation_id=self.conversation_id,
                message_status='sent'
            ).exclude(sender=self.user).values_list('id', flat=True))
        )()

        for msg_id in undelivered:
            # Send delivery receipt to sender
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_delivery_receipt',
                    'message_id': msg_id,
                    'status': 'delivered',
                }
            )

        # Update status to delivered
        if undelivered:
            await database_sync_to_async(
                lambda: DirectMessage.objects.filter(id__in=undelivered).update(message_status='delivered')
            )()

    @database_sync_to_async
    def update_message_delivered(self, message_id):
        from .models import DirectMessage
        DirectMessage.objects.filter(id=message_id, message_status='sent').update(message_status='delivered')

    @database_sync_to_async
    def update_message_read(self, message_id):
        from .models import DirectMessage
        DirectMessage.objects.filter(id=message_id).update(message_status='read', is_read=True)

    # VideoCall Database Operations
    @database_sync_to_async
    def create_video_call(self, call_id, call_type, is_caller=True):
        from .models import VideoCall, DirectConversation
        import uuid

        if call_type == 'direct':
            conv = DirectConversation.objects.get(id=self.conversation_id)
            other_participant = conv.participants.exclude(id=self.user.id).first()
            call = VideoCall.objects.create(
                id=uuid.UUID(call_id),
                call_type='direct',
                status='ringing',
                caller=self.user,
                receiver=other_participant,
                conversation=conv,
            )
        return call

    @database_sync_to_async
    def update_video_call_status(self, call_id, status):
        from .models import VideoCall
        import uuid

        try:
            call = VideoCall.objects.get(id=uuid.UUID(call_id))
            call.status = status
            if status == 'active' and not call.connected_at:
                call.connected_at = timezone.now()
            call.save(update_fields=['status', 'connected_at'])
        except VideoCall.DoesNotExist:
            pass

    @database_sync_to_async
    def end_video_call(self, call_id, status='ended'):
        from .models import VideoCall
        import uuid

        try:
            call = VideoCall.objects.get(id=uuid.UUID(call_id))
            call.status = status
            call.ended_at = timezone.now()
            if call.connected_at:
                call.duration = int((call.ended_at - call.connected_at).total_seconds())
            call.save(update_fields=['status', 'ended_at', 'duration'])
        except VideoCall.DoesNotExist:
            pass


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.user = self.scope['user']

        print(f"🔌 [Group] WebSocket connect attempt: user={self.user.username if self.user.is_authenticated else 'Anonymous'}, group={self.group_id}")

        if not self.user.is_authenticated:
            print("❌ [Group] User not authenticated, closing")
            await self.close()
            return

        if not await self.is_member():
            print(f"❌ [Group] User {self.user.username} not member of group {self.group_id}")
            await self.close()
            return

        self.room_group_name = f'group_chat_{self.group_id}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        print(f"✅ [Group] WebSocket connected: {self.user.username} joined {self.room_group_name}")
        await self.send_pending_delivery_receipts()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        msg_type = data.get('type', 'text')

        if msg_type == 'text':
            content = data.get('message', '').strip()
            if not content:
                return
            try:
                message = await self.save_text_message(content)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type':            'chat_message',
                        'message_type':    'text',
                        'message':         content,
                        'sender_username': self.user.username,
                        'sender_avatar':   await self.get_avatar(),
                        'timestamp':       message.created_at.strftime('%H:%M'),
                        'message_id':      message.id,
                        'message_status':  'sent',
                    }
                )
            except Exception as e:
                print(f"Error saving text message: {e}")

        elif msg_type in ('file', 'image', 'voice'):
            message_id = data.get('message_id')
            file_url   = data.get('file_url')
            if not message_id or not file_url:
                return
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'chat_message',
                    'message_type':    msg_type,
                    'message_id':      message_id,
                    'file_url':        file_url,
                    'file_name':       data.get('file_name', ''),
                    'file_size':       data.get('file_size', ''),
                    'duration':        data.get('duration', 0),
                    'sender_username': self.user.username,
                    'sender_avatar':   await self.get_avatar(),
                    'timestamp':       data.get('timestamp', ''),
                    'message_status':  'sent',
                }
            )

        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'typing_indicator',
                    'sender_username': self.user.username,
                    'is_typing':       data.get('is_typing', False),
                }
            )

        elif msg_type == 'voice_recording':
            # Voice recording indicator
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type':            'voice_recording_indicator',
                    'sender_username': self.user.username,
                    'is_recording':    data.get('is_recording', False),
                }
            )

        elif msg_type == 'message_delivered':
            # Message delivered receipt
            message_id = data.get('message_id')
            if message_id:
                await self.update_message_delivered(message_id)

        elif msg_type == 'message_read':
            # Message read receipt
            message_id = data.get('message_id')
            if message_id:
                await self.update_message_read(message_id)

        # WebRTC Video Call Signaling for Group Calls
        elif msg_type == 'call_offer':
            await self.handle_group_call_offer(data)

        elif msg_type == 'call_answer':
            await self.handle_group_call_answer(data)

        elif msg_type == 'ice_candidate':
            await self.handle_group_ice_candidate(data)

        elif msg_type == 'call_end':
            await self.handle_group_call_end(data)

    async def chat_message(self, event):
        print(f"📥 [Group] Sending to {self.user.username}: {event.get('message', '')[:30]} (type: {event.get('message_type')})")
        await self.send(text_data=json.dumps(event))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps(event))

    async def voice_recording_indicator(self, event):
        await self.send(text_data=json.dumps(event))

    async def message_delivery_receipt(self, event):
        """Send delivery receipt to sender"""
        await self.send(text_data=json.dumps(event))

    async def message_read_receipt(self, event):
        """Send read receipt to sender"""
        await self.send(text_data=json.dumps(event))

    # Group Video Call Signaling Handlers
    async def handle_group_call_offer(self, data):
        """Group call initiator sends offer"""
        call_id = data.get('call_id') or str(uuid.uuid4())
        offer = data.get('offer')

        if not offer:
            return

        # Create group video call record
        call = await self.create_group_video_call(call_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':            'call_offer',
                'call_id':         call_id,
                'offer':           offer,
                'caller_username': self.user.username,
                'caller_avatar':   await self.get_avatar(),
                'call_type':       'group',
            }
        )

    async def handle_group_call_answer(self, data):
        """Group member answers call"""
        call_id = data.get('call_id')
        answer = data.get('answer')

        if not call_id or not answer:
            return

        await self.update_group_video_call_status(call_id, 'active')

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':              'call_answer',
                'call_id':           call_id,
                'answer':            answer,
                'responder_username': self.user.username,
            }
        )

    async def handle_group_ice_candidate(self, data):
        """Relay ICE candidate in group call"""
        call_id = data.get('call_id')
        candidate = data.get('candidate')

        if not call_id or not candidate:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':           'ice_candidate',
                'call_id':        call_id,
                'candidate':      candidate,
                'sender_username': self.user.username,
            }
        )

    async def handle_group_call_end(self, data):
        """End group call"""
        call_id = data.get('call_id')

        if call_id:
            await self.end_group_video_call(call_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type':            'call_end',
                'call_id':         call_id,
                'ended_by':        self.user.username,
            }
        )

    # Group call event handlers
    async def call_offer(self, event):
        # Don't send call_offer back to the caller
        if event.get('caller_username') == self.user.username:
            return
        await self.send(text_data=json.dumps(event))

    async def call_answer(self, event):
        await self.send(text_data=json.dumps(event))

    async def ice_candidate(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_end(self, event):
        await self.send(text_data=json.dumps(event))

    async def call_rejected(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def is_member(self):
        from GROUPS.models import GroupMember
        return GroupMember.objects.filter(
            group_id=self.group_id, user=self.user, status='active'
        ).exists()

    @database_sync_to_async
    def save_text_message(self, content):
        from .models import GroupMessage
        from notifications.models import Notification
        from GROUPS.models import Group

        message = GroupMessage.objects.create(
            group_id=self.group_id, sender=self.user,
            message_type='text', content=content
        )

        # Notify other group members
        group = Group.objects.get(id=self.group_id)
        for member in group.memberships.filter(status='active').exclude(user=self.user):
            Notification.objects.create(
                recipient=member.user,
                actor=self.user,
                verb=f'{self.user.username} sent a message in {group.name}',
                description=content[:100],
                notification_type='group_message',
            )

        return message

    @database_sync_to_async
    def get_avatar(self):
        if self.user.avatar:
            return self.user.avatar.url
        return '/static/img/default_avatar.png'

    async def send_pending_delivery_receipts(self):
        """Send delivery receipts for messages that haven't been delivered yet"""
        from .models import GroupMessage
        # Get messages from others that are only 'sent' status
        undelivered = await database_sync_to_async(
            lambda: list(GroupMessage.objects.filter(
                group_id=self.group_id,
                message_status='sent'
            ).exclude(sender=self.user).values_list('id', flat=True))
        )()

        for msg_id in undelivered:
            # Send delivery receipt to sender
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'message_delivery_receipt',
                    'message_id': msg_id,
                    'status': 'delivered',
                }
            )

        # Update status to delivered
        if undelivered:
            await database_sync_to_async(
                lambda: GroupMessage.objects.filter(id__in=undelivered).update(message_status='delivered')
            )()

    @database_sync_to_async
    def update_message_delivered(self, message_id):
        from .models import GroupMessage
        GroupMessage.objects.filter(id=message_id, message_status='sent').update(message_status='delivered')

    @database_sync_to_async
    def update_message_read(self, message_id):
        from .models import GroupMessage
        GroupMessage.objects.filter(id=message_id).update(message_status='read')

    # Group VideoCall Database Operations
    @database_sync_to_async
    def create_group_video_call(self, call_id):
        from .models import VideoCall
        from GROUPS.models import Group
        import uuid

        group = Group.objects.get(id=self.group_id)
        call = VideoCall.objects.create(
            id=uuid.UUID(call_id),
            call_type='group',
            status='ringing',
            caller=self.user,
            group=group,
        )
        return call

    @database_sync_to_async
    def update_group_video_call_status(self, call_id, status):
        from .models import VideoCall
        import uuid

        try:
            call = VideoCall.objects.get(id=uuid.UUID(call_id))
            call.status = status
            if status == 'active' and not call.connected_at:
                call.connected_at = timezone.now()
            call.save(update_fields=['status', 'connected_at'])
        except VideoCall.DoesNotExist:
            pass

    @database_sync_to_async
    def end_group_video_call(self, call_id, status='ended'):
        from .models import VideoCall
        import uuid

        try:
            call = VideoCall.objects.get(id=uuid.UUID(call_id))
            call.status = status
            call.ended_at = timezone.now()
            if call.connected_at:
                call.duration = int((call.ended_at - call.connected_at).total_seconds())
            call.save(update_fields=['status', 'ended_at', 'duration'])
        except VideoCall.DoesNotExist:
            pass