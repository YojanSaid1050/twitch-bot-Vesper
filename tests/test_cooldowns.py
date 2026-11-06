from utils.cooldowns import CooldownManager


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_global_cooldown():
    clock = FakeClock()
    cd = CooldownManager(clock)
    assert cd.try_use("cmd", global_seconds=10)
    assert not cd.try_use("cmd", global_seconds=10)
    clock.now += 9
    assert cd.remaining("cmd", global_seconds=10) == 1
    clock.now += 1
    assert cd.try_use("cmd", global_seconds=10)


def test_user_cooldown_is_per_user():
    clock = FakeClock()
    cd = CooldownManager(clock)
    assert cd.try_use("cmd", user_id="a", user_seconds=60)
    assert not cd.try_use("cmd", user_id="a", user_seconds=60)
    assert cd.try_use("cmd", user_id="b", user_seconds=60)


def test_zero_cooldown_never_blocks_and_reset():
    cd = CooldownManager(FakeClock())
    assert cd.try_use("cmd")
    assert cd.try_use("cmd")
    cd.trigger("x", "u")
    assert cd.remaining("x", global_seconds=5) > 0
    cd.reset("x")
    assert cd.remaining("x", global_seconds=5, user_id="u", user_seconds=5) == 0
