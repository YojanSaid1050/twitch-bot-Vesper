# services/eventsub/registry.py
"""
Registro central de eventos EventSub.
"""

from services.eventsub.definitions import EventDefinition, ScopeOwner, TransportType

EVENTS: dict[str, EventDefinition] = {
    # ==========================================================
    # EVENTOS PÚBLICOS (sin scopes, App Token)
    # ==========================================================
    "stream.online": EventDefinition(
        type="stream.online",
        version="1",
        handler="stream_online",
        scope_owner=ScopeOwner.APP,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "stream.offline": EventDefinition(
        type="stream.offline",
        version="1",
        handler="stream_offline",
        scope_owner=ScopeOwner.APP,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.update": EventDefinition(
        type="channel.update",
        version="2",
        handler="channel_update",
        scope_owner=ScopeOwner.APP,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.raid": EventDefinition(
        type="channel.raid",
        version="1",
        handler="channel_raid",
        scope_owner=ScopeOwner.APP,
        condition_fields={"to_broadcaster_user_id": "broadcaster_id"},
    ),

    # ==========================================================
    # EVENTOS CON SCOPES (validación contra BROADCASTER)
    # ==========================================================
    "channel.subscribe": EventDefinition(
        type="channel.subscribe",
        version="1",
        handler="channel_subscribe",
        required_scopes=["channel:read:subscriptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.subscription.end": EventDefinition(
        type="channel.subscription.end",
        version="1",
        handler="channel_subscription_end",
        required_scopes=["channel:read:subscriptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.subscription.gift": EventDefinition(
        type="channel.subscription.gift",
        version="1",
        handler="channel_subscription_gift",
        required_scopes=["channel:read:subscriptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.subscription.message": EventDefinition(
        type="channel.subscription.message",
        version="1",
        handler="channel_subscription_message",
        required_scopes=["channel:read:subscriptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.cheer": EventDefinition(
        type="channel.cheer",
        version="1",
        handler="channel_cheer",
        required_scopes=["bits:read"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.vip.add": EventDefinition(
        type="channel.vip.add",
        version="1",
        handler="channel_vip_add",
        required_scopes=["channel:read:vips"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.vip.remove": EventDefinition(
        type="channel.vip.remove",
        version="1",
        handler="channel_vip_remove",
        required_scopes=["channel:read:vips"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.prediction.begin": EventDefinition(
        type="channel.prediction.begin",
        version="1",
        handler="channel_prediction_begin",
        required_scopes=["channel:read:predictions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.prediction.progress": EventDefinition(
        type="channel.prediction.progress",
        version="1",
        handler="channel_prediction_progress",
        required_scopes=["channel:read:predictions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.prediction.lock": EventDefinition(
        type="channel.prediction.lock",
        version="1",
        handler="channel_prediction_lock",
        required_scopes=["channel:read:predictions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.prediction.end": EventDefinition(
        type="channel.prediction.end",
        version="1",
        handler="channel_prediction_end",
        required_scopes=["channel:read:predictions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.poll.begin": EventDefinition(
        type="channel.poll.begin",
        version="1",
        handler="channel_poll_begin",
        required_scopes=["channel:read:polls"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.poll.progress": EventDefinition(
        type="channel.poll.progress",
        version="1",
        handler="channel_poll_progress",
        required_scopes=["channel:read:polls"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.poll.end": EventDefinition(
        type="channel.poll.end",
        version="1",
        handler="channel_poll_end",
        required_scopes=["channel:read:polls"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.goal.begin": EventDefinition(
        type="channel.goal.begin",
        version="1",
        handler="channel_goal_begin",
        required_scopes=["channel:read:goals"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.goal.progress": EventDefinition(
        type="channel.goal.progress",
        version="1",
        handler="channel_goal_progress",
        required_scopes=["channel:read:goals"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.goal.end": EventDefinition(
        type="channel.goal.end",
        version="1",
        handler="channel_goal_end",
        required_scopes=["channel:read:goals"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.hype_train.begin": EventDefinition(
        type="channel.hype_train.begin",
        version="2",
        handler="channel_hype_train_begin",
        required_scopes=["channel:read:hype_train"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.hype_train.progress": EventDefinition(
        type="channel.hype_train.progress",
        version="2",
        handler="channel_hype_train_progress",
        required_scopes=["channel:read:hype_train"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.hype_train.end": EventDefinition(
        type="channel.hype_train.end",
        version="2",
        handler="channel_hype_train_end",
        required_scopes=["channel:read:hype_train"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.channel_points_custom_reward_redemption.add": EventDefinition(
        type="channel.channel_points_custom_reward_redemption.add",
        version="1",
        handler="channel_channel_points_custom_reward_redemption_add",
        required_scopes=["channel:read:redemptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),
    "channel.channel_points_custom_reward_redemption.update": EventDefinition(
        type="channel.channel_points_custom_reward_redemption.update",
        version="1",
        handler="channel_channel_points_custom_reward_redemption_update",
        required_scopes=["channel:read:redemptions"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={"broadcaster_user_id": "broadcaster_id"},
    ),

    # ==========================================================
    # EVENTOS DE MODERACIÓN / CHAT
    # ==========================================================
    "channel.follow": EventDefinition(
        type="channel.follow",
        version="2",
        handler="channel_follow",
        required_scopes=["moderator:read:followers"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.moderator.add": EventDefinition(
        type="channel.moderator.add",
        version="1",
        handler="channel_moderator_add",
        required_scopes=["channel:manage:moderators"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.moderator.remove": EventDefinition(
        type="channel.moderator.remove",
        version="1",
        handler="channel_moderator_remove",
        required_scopes=["channel:manage:moderators"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.chat.message_delete": EventDefinition(
        type="channel.chat.message_delete",
        version="1",
        handler="channel_chat_message_delete",
        required_scopes=["moderator:manage:chat_messages"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "user_id": "user_id",
        },
    ),
    "channel.chat.clear": EventDefinition(
        type="channel.chat.clear",
        version="1",
        handler="channel_chat_clear",
        required_scopes=["moderator:manage:chat_messages"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "user_id": "user_id",
        },
    ),
    "channel.chat.clear_user_messages": EventDefinition(
        type="channel.chat.clear_user_messages",
        version="1",
        handler="channel_chat_clear_user_messages",
        required_scopes=["moderator:manage:chat_messages"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "user_id": "user_id",
        },
    ),
    "channel.shoutout.create": EventDefinition(
        type="channel.shoutout.create",
        version="1",
        handler="channel_shoutout_create",
        required_scopes=["moderator:manage:shoutouts"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.shoutout.receive": EventDefinition(
        type="channel.shoutout.receive",
        version="1",
        handler="channel_shoutout_receive",
        required_scopes=["moderator:manage:shoutouts"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),

    # ==========================================================
    # BAN / UNBAN - DESHABILITADOS (enabled=False)
    # ==========================================================
    "channel.ban": EventDefinition(
        type="channel.ban",
        version="1",
        handler="channel_ban",
        required_scopes=["moderator:manage:banned_users"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
        enabled=False,  # DESHABILITADO
    ),
    "channel.unban": EventDefinition(
        type="channel.unban",
        version="1",
        handler="channel_unban",
        required_scopes=["moderator:manage:banned_users"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
        enabled=False,  # DESHABILITADO
    ),

    # ==========================================================
    # RESTO DE EVENTOS DE MODERACIÓN (habilitados)
    # ==========================================================
    "channel.shield_mode.begin": EventDefinition(
        type="channel.shield_mode.begin",
        version="1",
        handler="channel_shield_mode_begin",
        required_scopes=["moderator:manage:shield_mode"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.shield_mode.end": EventDefinition(
        type="channel.shield_mode.end",
        version="1",
        handler="channel_shield_mode_end",
        required_scopes=["moderator:manage:shield_mode"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.unban_request.create": EventDefinition(
        type="channel.unban_request.create",
        version="1",
        handler="channel_unban_request_create",
        required_scopes=["moderator:manage:unban_requests"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.unban_request.resolve": EventDefinition(
        type="channel.unban_request.resolve",
        version="1",
        handler="channel_unban_request_resolve",
        required_scopes=["moderator:manage:unban_requests"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.suspicious_user.message": EventDefinition(
        type="channel.suspicious_user.message",
        version="1",
        handler="channel_suspicious_user_message",
        required_scopes=["moderator:read:suspicious_users"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "channel.suspicious_user.update": EventDefinition(
        type="channel.suspicious_user.update",
        version="1",
        handler="channel_suspicious_user_update",
        required_scopes=["moderator:read:suspicious_users"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "automod.message.hold": EventDefinition(
        type="automod.message.hold",
        version="1",
        handler="automod_message_hold",
        required_scopes=["moderator:manage:automod"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
    "automod.message.update": EventDefinition(
        type="automod.message.update",
        version="1",
        handler="automod_message_update",
        required_scopes=["moderator:manage:automod"],
        scope_owner=ScopeOwner.BROADCASTER,
        condition_fields={
            "broadcaster_user_id": "broadcaster_id",
            "moderator_user_id": "moderator_id",
        },
    ),
}