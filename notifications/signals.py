from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

# We'll import the Notification model from this app to avoid circular imports
from .models import Notification


def create_notification(recipient, verb, description=None, notification_type='other', actor=None, target=None):
    """
    Helper function to create a notification.
    """
    notification = Notification(
        recipient=recipient,
        verb=verb,
        description=description,
        notification_type=notification_type,
        actor=actor,
    )
    if target:
        notification.target_content_type = ContentType.objects.get_for_model(target)
        notification.target_object_id = target.id
    notification.save()
    return notification


# Signal for DirectMessage
@receiver(post_save, sender='chat.DirectMessage')
def direct_message_notification(sender, instance, created, **kwargs):
    if not created:
        return

    # Get the conversation and participants
    conversation = instance.conversation
    # Exclude the sender
    recipients = conversation.participants.exclude(id=instance.sender.id)

    for recipient in recipients:
        create_notification(
            recipient=recipient,
            verb=f"You have a new message from {instance.sender.username}",
            description=instance.content[:100],  # Preview of the message
            notification_type='message',
            actor=instance.sender,
            target=instance  # The message itself
        )


# Signal for GroupMessage
@receiver(post_save, sender='chat.GroupMessage')
def group_message_notification(sender, instance, created, **kwargs):
    if not created:
        return

    # Get the group and its members (excluding the sender)
    group = instance.group
    # We assume there is a GroupMember model in the GROUPS app
    from GROUPS.models import GroupMember
    # Get active members of the group
    members = GroupMember.objects.filter(group=group, status='active').values_list('user', flat=True)
    # Exclude the sender
    recipients = [user_id for user_id in members if user_id != instance.sender.id]

    for recipient_id in recipients:
        try:
            recipient = settings.AUTH_USER_MODEL.objects.get(id=recipient_id)
            create_notification(
                recipient=recipient,
                verb=f"You have a new message in {group.name}",
                description=instance.content[:100],
                notification_type='group_message',
                actor=instance.sender,
                target=instance
            )
        except settings.AUTH_USER_MODEL.DoesNotExist:
            pass


# Signal for FriendRequest
@receiver(post_save, sender='friends.FriendRequest')
def friend_request_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Only notify on creation of a pending request
    if instance.status == 'pending':
        create_notification(
            recipient=instance.receiver,
            verb=f"You have a new friend request from {instance.sender.username}",
            notification_type='friend_request',
            actor=instance.sender,
            target=instance
        )


# Signal for GroupMember (for invitations)
@receiver(post_save, sender='GROUPS.GroupMember')
def group_invite_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Notify when status is 'invited'
    if instance.status == 'invited':
        create_notification(
            recipient=instance.user,
            verb=f"You have been invited to join the group {instance.group.name}",
            notification_type='group_invite',
            actor=instance.invited_by,  # The user who sent the invitation
            target=instance.group
        )


# Signal for Like (on Question)
@receiver(post_save, sender='forum.Like')
def question_like_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Only notify if the liker is not the author of the question
    if instance.user != instance.question.author:
        create_notification(
            recipient=instance.question.author,
            verb=f"{instance.user.username} liked your question \"{instance.question.title}\"",
            notification_type='like',
            actor=instance.user,
            target=instance.question
        )


# Signal for ReplyLike (on Reply)
@receiver(post_save, sender='forum.ReplyLike')
def reply_like_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Only notify if the liker is not the author of the reply
    if instance.user != instance.reply.author:
        create_notification(
            recipient=instance.reply.author,
            verb=f"{instance.user.username} liked your reply",
            notification_type='like',
            actor=instance.user,
            target=instance.reply
        )


# Signal for Reply (on Question) - new reply
@receiver(post_save, sender='forum.Reply')
def reply_notification(sender, instance, created, **kwargs):
    if not created:
        return
    # Only notify if the replier is not the author of the question
    if instance.author != instance.question.author:
        create_notification(
            recipient=instance.question.author,
            verb=f"{instance.author.username} replied to your question \"{instance.question.title}\"",
            notification_type='reply',
            actor=instance.author,
            target=instance.question
        )


# Signal for Subscription - we want to notify when trial is ending soon and when it expires
# We'll use a periodic task for this, but for simplicity, we can check on save.
# However, it's better to use a celery beat or a daily cron job.
# For now, we'll create a signal that checks on save if the trial is ending in 3 days or if it expired.
# But note: the trial_end and paid_until are set on save.
# We'll do it in the save method of Subscription model? But we are not allowed to modify other apps?
# We can still connect to the post_save of Subscription.

@receiver(post_save, sender='payment.Subscription')
def subscription_notification(sender, instance, created, **kwargs):
    # We'll check if the trial is ending in 3 days (from now) and if we haven't sent a reminder yet.
    # But we don't have a flag for whether we sent a reminder. We could add a field, but let's avoid modifying other apps.
    # Alternatively, we can send a notification every time the condition is met? That would be spammy.
    # Since we cannot modify the Subscription model, we'll skip this for now and note that it requires a periodic task.
    # However, we can still send a notification when the subscription status changes to 'expired' or when trial ends.
    # We'll check if the trial_end is in the past and the status is still 'trial' -> then it should have been updated to expired?
    # Actually, the save method of Subscription sets trial_end if not set, but doesn't update status.
    # We'll rely on the status field.

    # If the status changed to 'expired', we can notify.
    # But we don't have the old value. We can use the pre_save signal to capture the old state, but that's more complex.

    # For simplicity, we'll just note that this part needs improvement and for now, we'll not implement.
    pass