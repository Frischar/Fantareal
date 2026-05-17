"""派对彩带大对决 — 游戏引擎核心。

纯逻辑，无 I/O。所有公有方法返回 ActionResult。
"""

from __future__ import annotations

import random
from typing import Optional

from .models import (
    ALL_ITEMS,
    MAX_ITEM_SLOTS,
    UNSTEALABLE,
    ActionResult,
    BattleLogEntry,
    CannonState,
    GameEvent,
    GameMode,
    GamePhase,
    ItemType,
    PlayerState,
    RoundType,
    Target,
)

# ═══════════════════════════════════════════
# 难度配置
# ═══════════════════════════════════════════

DIFFICULTY_BALLOONS = {
    "easy": 6,
    "normal": 4,
    "hard": 2,
}


def _level_ammo(level: int) -> tuple[int, int]:
    """返回 (live_count, blank_count)"""
    if level == 1:
        return 2, 3
    if level == 2:
        return 3, 3
    return 4, 4


def _level_items_per_player(level: int) -> tuple[int, int]:
    """返回每回合每个玩家获得的道具数 (min, max)"""
    if level == 1:
        return 0, 1
    return 1, 2


# ═══════════════════════════════════════════
# PartyGame 引擎
# ═══════════════════════════════════════════

class PartyGame:
    """派对彩带大对决游戏引擎"""

    def __init__(
        self,
        p1_name: str = "玩家1",
        p2_name: str = "玩家2",
        difficulty: str = "normal",
        mode: GameMode = GameMode.CLASSIC,
        seed: Optional[int] = None,
    ):
        if difficulty not in DIFFICULTY_BALLOONS:
            raise ValueError(f"无效难度 '{difficulty}'，可选: {list(DIFFICULTY_BALLOONS)}")

        self._rng = random.Random(seed)
        self.mode = mode
        self.difficulty = difficulty
        self.level = 0
        self.phase = GamePhase.PLAYING
        self.winner: Optional[int] = None

        initial_balloons = DIFFICULTY_BALLOONS[difficulty]
        self.players: list[PlayerState] = [
            PlayerState(name=p1_name, balloons=initial_balloons, items=[None]*MAX_ITEM_SLOTS),
            PlayerState(name=p2_name, balloons=initial_balloons, items=[None]*MAX_ITEM_SLOTS),
        ]
        self.current_player: int = 0
        self.cannon = CannonState()
        self._items_distributed = False
        self._revealed_indices: set[int] = set()
        self._hint_owners: dict[int, int] = {}  # original_index → player_index (who revealed this hint)
        self._battle_log: list[BattleLogEntry] = []
        self._round_counter = 0
        self._level_start_counter = 0
        self._round_statuses: list[dict] = []
        self._level_initial_rounds: list[RoundType] = []

        self.start_new_level()

    # ── 公共属性 ────────────────────────────

    @property
    def current(self) -> PlayerState:
        return self.players[self.current_player]

    @property
    def opponent(self) -> PlayerState:
        return self.players[1 - self.current_player]

    def _other(self, player_index: int) -> PlayerState:
        return self.players[1 - player_index]

    # ═══════════════════════════════════════
    # 局数管理
    # ═══════════════════════════════════════

    def start_new_level(self) -> ActionResult:
        """开始新一局：生成弹药、洗牌装填、分配道具。"""
        if self.phase == GamePhase.GAME_OVER:
            return ActionResult(False, "游戏已结束，无法开始新局")

        self.level += 1
        live, blank = _level_ammo(self.level)
        rounds = [RoundType.LIVE] * live + [RoundType.BLANK] * blank
        self._rng.shuffle(rounds)
        self.cannon = CannonState(rounds=rounds, current_index=0)
        self._revealed_indices.clear()
        self._hint_owners.clear()
        self._level_start_counter = self._round_counter
        self._level_initial_rounds = rounds.copy()
        self._round_statuses = [{"type": r.value, "status": "unknown", "hint": None} for r in rounds]
        self.players[0].skip_next_turn = False
        self.players[1].skip_next_turn = False
        self._items_distributed = False

        events = [GameEvent.of("level_start", level=self.level, live=live, blank=blank)]

        dist_events = self._distribute_items()
        events.extend(dist_events)

        return ActionResult(
            success=True,
            message=f"第 {self.level} 局开始！装填了 {live} 发闪光彩带和 {blank} 发柔软棉花",
            events=events,
            state=self.get_state(),
        )

    # ═══════════════════════════════════════
    # 道具分配
    # ═══════════════════════════════════════

    def _distribute_items(self) -> list[GameEvent]:
        """为双方随机分配道具。填入第一个 None 槽位。"""
        if self._items_distributed:
            return []
        self._items_distributed = True

        min_n, max_n = _level_items_per_player(self.level)
        events: list[GameEvent] = []

        for pi in (0, 1):
            p = self.players[pi]
            none_slots = [i for i, it in enumerate(p.items) if it is None]
            if not none_slots:
                events.append(GameEvent.of("items_full", player=pi, message=f"{p.name} 道具已满！"))
                continue

            count = min(self._rng.randint(min_n, max_n), len(none_slots))
            if count == 0:
                continue
            new_items = self._rng.choices(ALL_ITEMS, k=count)
            for j, it in enumerate(new_items):
                p.items[none_slots[j]] = it
            events.append(GameEvent.of(
                "items_received", player=pi,
                items=[it.value for it in new_items],
                labels=[it.label() for it in new_items],
            ))

        return events

    # ═══════════════════════════════════════
    # 状态快照
    # ═══════════════════════════════════════

    def get_state(self) -> dict:
        """返回对前端可见的完整游戏状态（隐藏弹药顺序）。"""
        return {
            "phase": self.phase.value,
            "current_player": self.current_player,
            "level": self.level,
            "difficulty": self.difficulty,
            "mode": self.mode.value,
            "players": [p.to_dict() for p in self.players],
            "cannon": self.cannon.to_dict() if not self._should_hide_cannon() else None,
            "round_states": self._compute_round_states(),
            "level_live": sum(1 for rs in self._round_statuses if rs["type"] == "live"),
            "level_total": len(self._round_statuses),
            "turn_number": self.level,
            "items_distributed": self._items_distributed,
            "battle_log": [{"round_number": e.round_number, "round_type": e.round_type,
                            "description": e.description, "player": e.player}
                           for e in self._battle_log],
        }

    def get_sanitized_state(self) -> dict:
        """返回对 AI 安全的状态（隐藏弹药顺序、hint 状态对对手隐藏）。"""
        cannon = self.cannon
        if cannon.is_empty:
            cannon_info = None
        else:
            revealed_info = {}
            for idx in self._revealed_indices:
                if idx < len(cannon.rounds):
                    pos = idx - cannon.current_index + 1
                    revealed_info[str(pos)] = cannon.rounds[idx].value

            cannon_info = {
                "total_remaining": len(cannon.remaining_rounds),
                "live_count": sum(1 for r in cannon.remaining_rounds if r == RoundType.LIVE),
                "blank_count": sum(1 for r in cannon.remaining_rounds if r == RoundType.BLANK),
                "revealed": revealed_info,
            }

        # AI 看不到 hint 状态——全部替换为 unknown（保留 fired/ejected）
        safe_states = []
        for rs in self._compute_round_states():
            s = dict(rs)
            if s["status"].startswith("hint_"):
                s["status"] = "unknown"
            safe_states.append(s)

        return {
            "phase": self.phase.value,
            "current_player": self.current_player,
            "level": self.level,
            "mode": self.mode.value,
            "players": [p.to_dict() for p in self.players],
            "cannon": cannon_info,
            "round_states": safe_states,
            "battle_log": [{"round_number": e.round_number, "round_type": e.round_type,
                            "description": e.description, "player": e.player}
                           for e in self._battle_log],
        }

    def get_battle_log(self) -> list[dict]:
        """返回对战日志。"""
        return [{"round_number": e.round_number, "round_type": e.round_type,
                 "description": e.description, "player": e.player, "timestamp": e.timestamp}
                for e in self._battle_log]

    def _log_battle(self, description: str, round_type: str, player: int) -> None:
        self._round_counter += 1
        self._battle_log.append(BattleLogEntry(
            round_number=self._round_counter,
            round_type=round_type,
            description=description,
            player=player,
        ))

    def _should_hide_cannon(self) -> bool:
        return self.cannon.is_empty

    def _map_to_original(self, cannon_idx: int) -> int:
        """将 cannon.rounds 索引映射到 _round_statuses 原始索引。"""
        count = 0
        for i, rs in enumerate(self._round_statuses):
            if rs["status"] != "ejected":
                if count == cannon_idx:
                    return i
                count += 1
        return -1

    def _compute_round_states(self) -> list[dict]:
        """计算子弹圆圈所需的每发弹药状态。只显示当前玩家自己的 hint。"""
        states = []
        current_orig = self._map_to_original(self.cannon.current_index) if not self.cannon.is_empty else -1
        for i, rs in enumerate(self._round_statuses):
            st = rs["status"]
            if st == "fired":
                status = "fired_" + rs["type"]
            elif st == "ejected":
                status = "ejected"
            elif rs["hint"] and self._hint_owners.get(i) == self.current_player:
                status = "hint_" + rs["hint"]
            else:
                status = "unknown"
            states.append({"index": i + 1, "status": status, "current": i == current_orig})
        return states

    def _record_fired(self, orig_idx: int) -> None:
        if 0 <= orig_idx < len(self._round_statuses):
            self._round_statuses[orig_idx]["status"] = "fired"

    def _record_ejected(self, orig_idx: int) -> None:
        if 0 <= orig_idx < len(self._round_statuses):
            self._round_statuses[orig_idx]["status"] = "ejected"

    def _record_hint(self, orig_idx: int, round_type: str, player_index: int) -> None:
        if 0 <= orig_idx < len(self._round_statuses):
            self._round_statuses[orig_idx]["hint"] = round_type
            self._hint_owners[orig_idx] = player_index

    # ═══════════════════════════════════════
    # 公有方法：使用道具
    # ═══════════════════════════════════════

    def use_item(self, player_index: int, item_type_str: str, target_item: Optional[str] = None) -> ActionResult:
        """玩家使用道具。target_item：怪盗猫爪手套指定偷取的道具类型。"""
        if self.phase == GamePhase.GAME_OVER:
            return ActionResult(False, "游戏已结束")

        if player_index != self.current_player:
            return ActionResult(False, "现在不是你的回合")

        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            return ActionResult(False, f"无效道具类型 '{item_type_str}'")

        player = self.players[player_index]
        slot_idx = -1
        for i, it in enumerate(player.items):
            if it == item_type:
                slot_idx = i
                break
        if slot_idx == -1:
            return ActionResult(False, f"你没有「{item_type.label()}」")

        if self.cannon.is_empty and item_type in _ITEMS_NEED_CANNON:
            return ActionResult(False, "礼炮已空，无法使用此道具")

        player.items[slot_idx] = None
        events = self._apply_item_effect(player_index, item_type, target_item)

        self._log_battle(
            f"{player.name} 使用了「{item_type.label()}」",
            "item",
            player_index,
        )

        over = self._check_game_over()
        if over:
            over.events = events + over.events
            return over

        return ActionResult(
            success=True,
            message=f"使用了「{item_type.label()}」",
            events=events,
            state=self.get_state(),
        )

    def discard_item(self, player_index: int, item_type_str: str) -> ActionResult:
        """丢弃道具（不触发效果）。"""
        if self.phase == GamePhase.GAME_OVER:
            return ActionResult(False, "游戏已结束")

        try:
            item_type = ItemType(item_type_str)
        except ValueError:
            return ActionResult(False, f"无效道具类型 '{item_type_str}'")

        player = self.players[player_index]
        slot_idx = -1
        for i, it in enumerate(player.items):
            if it == item_type:
                slot_idx = i
                break
        if slot_idx == -1:
            return ActionResult(False, f"你没有「{item_type.label()}」")

        player.items[slot_idx] = None
        self._log_battle(
            f"{player.name} 丢弃了「{item_type.label()}」",
            "item",
            player_index,
        )

        return ActionResult(
            success=True,
            message=f"丢弃了「{item_type.label()}」",
            events=[GameEvent.of("item_discarded", player=player_index, item=item_type.value, label=item_type.label())],
            state=self.get_state(),
        )

    def _apply_item_effect(self, player_index: int, item_type: ItemType, target_item: Optional[str] = None) -> list[GameEvent]:
        """执行道具效果，返回事件列表。target_item 仅 phantom_cat_gloves 使用。"""
        player = self.players[player_index]
        opponent = self._other(player_index)

        if item_type == ItemType.CANDY_LENS:
            return self._effect_candy_lens(player_index)

        elif item_type == ItemType.BUBBLE_SODA:
            return self._effect_bubble_soda()

        elif item_type == ItemType.CAT_PAW_RIBBON:
            opponent.skip_next_turn = True
            return [GameEvent.of("cat_paw_ribbon", target=1 - player_index)]

        elif item_type == ItemType.DOUBLE_GLITTER:
            player.double_damage_active = True
            return [GameEvent.of("double_glitter_active", player=player_index)]

        elif item_type == ItemType.STRAWBERRY_CAKE:
            player.balloons = min(6, player.balloons + 1)
            return [GameEvent.of("heal", player=player_index, amount=1, new_balloons=player.balloons)]

        elif item_type == ItemType.WHISPER_CONCH:
            return self._effect_whisper_conch(player_index)

        elif item_type == ItemType.MIRACLE_WAND:
            return self._effect_miracle_wand()

        elif item_type == ItemType.PHANTOM_CAT_GLOVES:
            return self._effect_phantom_cat_gloves(player_index, target_item)

        elif item_type == ItemType.KIWI_JUICE:
            return self._effect_kiwi_juice(player_index)

        return []

    # ── 各道具效果实现 ─────────────────────

    def _effect_candy_lens(self, player_index: int) -> list[GameEvent]:
        cr = self.cannon.current_round
        if cr is None:
            return [GameEvent.of("candy_lens_empty")]
        orig_idx = self._map_to_original(self.cannon.current_index)
        self._revealed_indices.add(self.cannon.current_index)
        self._record_hint(orig_idx, cr.value, player_index)
        return [GameEvent.of("candy_lens", position=orig_idx+1)]

    def _effect_bubble_soda(self) -> list[GameEvent]:
        idx = self.cannon.current_index
        if idx >= len(self.cannon.rounds):
            return [GameEvent.of("bubble_soda_empty")]
        orig_idx = self._map_to_original(idx)
        removed = self.cannon.rounds.pop(idx)
        self._revealed_indices = {
            i - 1 if i > idx else i
            for i in self._revealed_indices
            if i != idx
        }
        self._record_ejected(orig_idx)
        events = [GameEvent.of("bubble_soda", ejected_round=removed.value, ejected_label=removed.label(), position=orig_idx+1)]
        if self.cannon.is_empty:
            events.append(GameEvent.of("cannon_empty"))
        return events

    def _effect_whisper_conch(self, player_index: int) -> list[GameEvent]:
        if self.cannon.is_empty:
            return [GameEvent.of("whisper_conch_empty")]
        options = list(range(self.cannon.current_index, len(self.cannon.rounds)))
        chosen = self._rng.choice(options)
        orig_idx = self._map_to_original(chosen)
        round_type = self.cannon.rounds[chosen]
        self._revealed_indices.add(chosen)
        self._record_hint(orig_idx, round_type.value, player_index)
        return [GameEvent.of("whisper_conch", position=orig_idx + 1)]

    def _effect_miracle_wand(self) -> list[GameEvent]:
        cr = self.cannon.current_round
        if cr is None:
            return [GameEvent.of("miracle_wand_empty")]
        new_type = RoundType.BLANK if cr == RoundType.LIVE else RoundType.LIVE
        self.cannon.rounds[self.cannon.current_index] = new_type
        return [GameEvent.of("miracle_wand")]

    def _effect_phantom_cat_gloves(self, player_index: int, target_item: Optional[str] = None) -> list[GameEvent]:
        opponent = self._other(player_index)
        stealable = [(i, it) for i, it in enumerate(opponent.items) if it is not None and it not in UNSTEALABLE]
        if not stealable:
            return [GameEvent.of("phantom_cat_gloves_no_target", target=1 - player_index)]

        if target_item:
            # 指定偷取某道具
            matched = [(i, it) for i, it in stealable if it.value == target_item]
            if matched:
                slot_idx, stolen = matched[0]
            else:
                return [GameEvent.of("phantom_cat_gloves_no_target", target=1 - player_index)]
        else:
            slot_idx, stolen = self._rng.choice(stealable)

        opponent.items[slot_idx] = None
        events = [GameEvent.of(
            "phantom_cat_gloves_steal",
            target=1 - player_index,
            stolen_item=stolen.value,
            stolen_label=stolen.label(),
        )]
        events.extend(self._apply_item_effect(player_index, stolen))
        return events

    def _effect_kiwi_juice(self, player_index: int) -> list[GameEvent]:
        player = self.players[player_index]
        if self._rng.random() < 0.5:
            player.balloons = min(6, player.balloons + 2)
            return [GameEvent.of("kiwi_juice_heal", player=player_index, amount=2, new_balloons=player.balloons)]
        else:
            player.balloons = max(0, player.balloons - 1)
            return [GameEvent.of("kiwi_juice_hurt", player=player_index, amount=1, new_balloons=player.balloons)]

    # ═══════════════════════════════════════
    # 公有方法：开火
    # ═══════════════════════════════════════

    def shoot(self, player_index: int, target_str: str) -> ActionResult:
        """玩家开火。"""
        if self.phase == GamePhase.GAME_OVER:
            return ActionResult(False, "游戏已结束")

        if player_index != self.current_player:
            return ActionResult(False, "现在不是你的回合")

        try:
            target = Target(target_str)
        except ValueError:
            return ActionResult(False, f"无效目标 '{target_str}'，可选: self, opponent")

        if self.cannon.is_empty:
            result = self.start_new_level()
            if not result.success:
                return result
            if self.cannon.is_empty:
                return ActionResult(False, "礼炮为空")

        round_type = self.cannon.current_round
        assert round_type is not None
        orig_idx = self._map_to_original(self.cannon.current_index)
        self.cannon.advance()
        fired_index = self.cannon.current_index - 1
        self._revealed_indices.discard(fired_index)
        self._record_fired(orig_idx)

        events = [GameEvent.of(
            "shot",
            player=player_index,
            target=target.value,
            round_type=round_type.value,
            round_label=round_type.label(),
        )]

        turn_switch = self._resolve_shot(player_index, target, round_type, events)

        target_name = "自己" if target == Target.SELF else self._other(player_index).name
        self._log_battle(
            f"{self.players[player_index].name} 向{target_name}开火 —— {round_type.label()}",
            round_type.value,
            player_index,
        )

        over = self._check_game_over()
        if over:
            over.events = events + over.events
            return over

        # 最后弹药打空 → 无论是否额外回合都开新局
        if self.cannon.is_empty:
            level_result = self.start_new_level()
            if level_result.success:
                events.extend(level_result.events)

        if turn_switch:
            switch_events = self._advance_turn()
            events.extend(switch_events)
            over = self._check_game_over()
            if over:
                over.events = events + over.events
                return over

        return ActionResult(
            success=True,
            message=f"向{'自己' if target == Target.SELF else '对方'}开火 —— {round_type.label()}",
            events=events,
            state=self.get_state(),
        )

    def skip_turn(self, player_index: int) -> ActionResult:
        """超时跳过回合：不射击，直接切换回合。"""
        if self.phase == GamePhase.GAME_OVER:
            return ActionResult(False, "游戏已结束")

        if player_index != self.current_player:
            return ActionResult(False, "现在不是你的回合")

        player_name = self.players[player_index].name
        events = [GameEvent.of("turn_timeout", player=player_index, message=f"{player_name} 超时，回合跳过！")]
        self._log_battle(f"{player_name} 超时，回合跳过", "timeout", player_index)

        switch_events = self._advance_turn()
        events.extend(switch_events)

        return ActionResult(
            success=True,
            message=f"{player_name} 超时，回合跳过",
            events=events,
            state=self.get_state(),
        )

    def _resolve_shot(
        self,
        player_index: int,
        target: Target,
        round_type: RoundType,
        events: list[GameEvent],
    ) -> bool:
        """解析射击结果。返回 True 表示需要切换回合。"""
        player = self.players[player_index]
        opponent = self._other(player_index)

        if target == Target.SELF:
            if round_type == RoundType.BLANK:
                events.append(GameEvent.of("self_blank", player=player_index))
                return False
            else:
                damage = 2 if player.double_damage_active else 1
                player.balloons = max(0, player.balloons - damage)
                player.double_damage_active = False
                events.append(GameEvent.of(
                    "self_live",
                    player=player_index,
                    damage=damage,
                    new_balloons=player.balloons,
                ))
                return True

        else:  # OPPONENT
            if round_type == RoundType.LIVE:
                damage = 2 if player.double_damage_active else 1
                opponent.balloons = max(0, opponent.balloons - damage)
                player.double_damage_active = False
                events.append(GameEvent.of(
                    "opponent_hit",
                    player=1 - player_index,
                    damage=damage,
                    double=damage == 2,
                    new_balloons=opponent.balloons,
                ))
            else:
                events.append(GameEvent.of("opponent_miss", player=player_index))
            return True

    # ═══════════════════════════════════════
    # 回合切换
    # ═══════════════════════════════════════

    def _advance_turn(self) -> list[GameEvent]:
        """推进回合到下一个玩家。处理跳过、空膛等逻辑。"""
        events: list[GameEvent] = []

        if self.cannon.is_empty:
            result = self.start_new_level()
            events.extend(result.events)

        self.current_player = 1 - self.current_player
        self._items_distributed = False

        if self.current.skip_next_turn:
            self.current.skip_next_turn = False
            events.append(GameEvent.of("turn_skipped", player=self.current_player))
            self.current_player = 1 - self.current_player
            self._items_distributed = True

        dist_events = self._distribute_items()
        events.extend(dist_events)

        events.append(GameEvent.of("turn_start", player=self.current_player))
        return events

    # ═══════════════════════════════════════
    # 游戏结束判定
    # ═══════════════════════════════════════

    def _check_game_over(self) -> Optional[ActionResult]:
        """检查是否有人的气球归零。返回 ActionResult 或 None。"""
        for i, p in enumerate(self.players):
            if p.balloons <= 0:
                self.phase = GamePhase.GAME_OVER
                self.winner = 1 - i
                return ActionResult(
                    success=True,
                    message=f"游戏结束！{self.players[self.winner].name} 获胜！",
                    events=[GameEvent.of(
                        "game_over",
                        winner=self.winner,
                        winner_name=self.players[self.winner].name,
                        loser=i,
                        loser_name=p.name,
                    )],
                    phase=GamePhase.GAME_OVER,
                    winner=self.winner,
                    state=self.get_state(),
                )
        return None


# ═══════════════════════════════════════════
# 空膛时不可使用的道具
# ═══════════════════════════════════════════

_ITEMS_NEED_CANNON: set[ItemType] = {
    ItemType.CANDY_LENS,
    ItemType.BUBBLE_SODA,
    ItemType.WHISPER_CONCH,
    ItemType.MIRACLE_WAND,
}

# ═══════════════════════════════════════════
# GameSession 单例管理
# ═══════════════════════════════════════════

# ═══════════════════════════════════════════
# 无AI模式 — 程序对手决策
# ═══════════════════════════════════════════

_NO_AI_DIALOGUES_HIT = [
    "打中了！嘿嘿~", "哇，运气真好！", "彩带飞出来啦~", "命中目标！",
    "哈哈，看来这发是实弹呢！", "砰！彩带满天飞~",
]
_NO_AI_DIALOGUES_MISS = [
    "啊，是棉花…", "呼，软绵绵的~", "空包弹呢…", "这发没中呢~",
    "运气不好喵…", "棉花球飘走了~",
]
_NO_AI_DIALOGUES_SELF_BLANK = [
    "安全！再来一次~", "棉花！赚到了！", "哈，果然是空包弹~",
    "运气不错，继续我的回合！",
]
_NO_AI_DIALOGUES_SELF_HIT = [
    "呃…打到自己了…", "好痛！我的气球！", "呜哇…失策了…",
    "怎么回事…居然打中自己了…",
]
_NO_AI_DIALOGUES_USE_ITEM = [
    "让我用个小道具~", "这个道具应该有用…", "试试这个！",
    "道具时间~", "嘿嘿，用这个~",
]
_NO_AI_DIALOGUES_TURN = [
    "轮到我了~", "让我想想…", "嗯…打哪里好呢？",
    "到我的回合了！", "好，看我的！",
]


def no_ai_decision(sanitized_state: dict) -> dict:
    """无AI模式的随机决策（不依赖 LLM）。"""
    import random as _rnd

    players = sanitized_state.get("players", [])
    p_self = players[1] if len(players) > 1 else {}  # AI 是 player 1
    p_opponent = players[0] if len(players) > 0 else {}

    self_items = [it for it in p_self.get("items", []) if it is not None]
    cannon = sanitized_state.get("cannon", {})
    live_count = cannon.get("live_count", 0)
    blank_count = cannon.get("blank_count", 0)
    total = cannon.get("total_remaining", 0)

    items_to_use = []

    # 策略：有透视糖果先看
    if "candy_lens" in self_items and total > 0:
        items_to_use.append("candy_lens")

    # 实弹比例高且对着对方时有加倍闪粉管
    if "double_glitter" in self_items and total > 0 and live_count >= blank_count:
        items_to_use.append("double_glitter")

    # 血量低时用草莓蛋糕
    if "strawberry_cake" in self_items and p_self.get("balloons", 0) <= 2:
        items_to_use.append("strawberry_cake")

    # 有机会就用悄悄话海螺
    if "whisper_conch" in self_items and total > 1:
        items_to_use.append("whisper_conch")

    # 想跳过对方时用猫爪丝带
    if "cat_paw_ribbon" in self_items and _rnd.random() < 0.4:
        items_to_use.append("cat_paw_ribbon")

    # 猕猴桃汁在血量低时试试
    if "kiwi_juice" in self_items and p_self.get("balloons", 0) <= 2:
        items_to_use.append("kiwi_juice")

    # 决定射击目标
    self_balloons = p_self.get("balloons", 0)
    opponent_balloons = p_opponent.get("balloons", 0)

    if total == 0:
        target = "self"
    elif self_balloons <= 1 and opponent_balloons > 1:
        target = "self" if _rnd.random() < 0.3 else "opponent"
    elif live_count > blank_count:
        target = "opponent" if _rnd.random() < 0.7 else "self"
    elif blank_count > live_count:
        target = "self" if _rnd.random() < 0.6 else "opponent"
    else:
        target = _rnd.choice(["self", "opponent"])

    # 对话
    if items_to_use:
        dialogue = _rnd.choice(_NO_AI_DIALOGUES_USE_ITEM)
    else:
        dialogue = _rnd.choice(_NO_AI_DIALOGUES_TURN)

    return {
        "items_to_use": items_to_use,
        "target": target,
        "dialogue": dialogue,
    }


def no_ai_reaction_dialogue(event_type: str) -> str:
    """根据事件类型返回预制反应对话。"""
    import random as _rnd
    mapping = {
        "opponent_hit": _NO_AI_DIALOGUES_HIT,
        "opponent_miss": _NO_AI_DIALOGUES_MISS,
        "self_blank": _NO_AI_DIALOGUES_SELF_BLANK,
        "self_live": _NO_AI_DIALOGUES_SELF_HIT,
    }
    options = mapping.get(event_type, _NO_AI_DIALOGUES_TURN)
    return _rnd.choice(options)


# ═══════════════════════════════════════════
# GameSession 单例管理
# ═══════════════════════════════════════════

_active_game: Optional[PartyGame] = None


def get_session() -> Optional[PartyGame]:
    """获取当前游戏实例。无活跃游戏返回 None。"""
    global _active_game
    return _active_game


def reset_session(
    mode: str = "classic",
    difficulty: str = "normal",
    p1_name: str = "玩家",
    p2_name: str = "对手",
) -> PartyGame:
    """创建新游戏并替换当前实例。"""
    global _active_game
    try:
        game_mode = GameMode(mode)
    except ValueError:
        game_mode = GameMode.CLASSIC
    _active_game = PartyGame(
        p1_name=p1_name,
        p2_name=p2_name,
        difficulty=difficulty,
        mode=game_mode,
    )
    return _active_game
