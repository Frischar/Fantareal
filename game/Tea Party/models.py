"""游戏数据模型 — 纯数据结构，无逻辑。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ═══════════════════════════════════════════
# 枚举
# ═══════════════════════════════════════════

class RoundType(Enum):
    """弹药类型"""
    LIVE = "live"    # 闪光彩带（实弹）
    BLANK = "blank"  # 柔软棉花（空包弹）

    def label(self) -> str:
        return "闪光彩带" if self == RoundType.LIVE else "柔软棉花"


class Target(Enum):
    """射击目标"""
    SELF = "self"
    OPPONENT = "opponent"


class ItemType(Enum):
    """派对道具"""
    CANDY_LENS = "candy_lens"            # 透视糖果
    BUBBLE_SODA = "bubble_soda"          # 气泡汽水
    CAT_PAW_RIBBON = "cat_paw_ribbon"    # 猫爪丝带
    DOUBLE_GLITTER = "double_glitter"    # 加倍闪粉管
    STRAWBERRY_CAKE = "strawberry_cake"  # 草莓蛋糕
    WHISPER_CONCH = "whisper_conch"      # 悄悄话海螺
    MIRACLE_WAND = "miracle_wand"        # 奇迹魔法棒
    PHANTOM_CAT_GLOVES = "phantom_cat_gloves"  # 怪盗猫爪手套
    KIWI_JUICE = "kiwi_juice"            # 浓缩猕猴桃汁

    def label(self) -> str:
        labels = {
            ItemType.CANDY_LENS: "透视糖果",
            ItemType.BUBBLE_SODA: "气泡汽水",
            ItemType.CAT_PAW_RIBBON: "猫爪丝带",
            ItemType.DOUBLE_GLITTER: "加倍闪粉管",
            ItemType.STRAWBERRY_CAKE: "草莓蛋糕",
            ItemType.WHISPER_CONCH: "悄悄话海螺",
            ItemType.MIRACLE_WAND: "奇迹魔法棒",
            ItemType.PHANTOM_CAT_GLOVES: "怪盗猫爪手套",
            ItemType.KIWI_JUICE: "浓缩猕猴桃汁",
        }
        return labels[self]

    def description(self) -> str:
        descs = {
            ItemType.CANDY_LENS: "看清礼炮内部，确认当前弹药是彩带还是棉花",
            ItemType.BUBBLE_SODA: "将当前弹药无害退膛，直接进入下一发",
            ItemType.CAT_PAW_RIBBON: "将对方手腕绑在椅子上，跳过对方下回合",
            ItemType.DOUBLE_GLITTER: "下一发实弹威力翻倍，击破2个气球",
            ItemType.STRAWBERRY_CAKE: "恢复1个心动气球",
            ItemType.WHISPER_CONCH: "悄悄告诉你礼炮内随机一发弹药的类型",
            ItemType.MIRACLE_WAND: "强行改变当前弹药的极性（彩带↔棉花）",
            ItemType.PHANTOM_CAT_GLOVES: "从对方道具区顺走一个道具并立即使用",
            ItemType.KIWI_JUICE: "50%几率恢复2个气球，50%几率扣除1个气球",
        }
        return descs[self]


class GamePhase(Enum):
    PLAYING = "playing"
    GAME_OVER = "game_over"


class GameMode(Enum):
    """游戏模式"""
    CLASSIC = "classic"  # 经典模式：AI 对手，限时回合
    PARTY = "party"      # 派对模式：AI 对手 + 聊天


# ═══════════════════════════════════════════
# 道具池
# ═══════════════════════════════════════════

ALL_ITEMS: list[ItemType] = list(ItemType)

# 怪盗猫爪手套偷到后无法使用的道具（会引起递归偷窃或逻辑混乱）
UNSTEALABLE = {ItemType.PHANTOM_CAT_GLOVES}

# 每个玩家最大道具槽位数
MAX_ITEM_SLOTS = 8


# ═══════════════════════════════════════════
# 数据类
# ═══════════════════════════════════════════

@dataclass
class PlayerState:
    """玩家状态"""
    name: str
    balloons: int
    items: list = field(default_factory=list)  # list[Optional[ItemType]], 8 slots
    skip_next_turn: bool = False
    double_damage_active: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "balloons": self.balloons,
            "items": [it.value if it is not None else None for it in self.items],
            "skip_next_turn": self.skip_next_turn,
            "double_damage_active": self.double_damage_active,
        }


@dataclass
class CannonState:
    """礼炮状态 — 弹药序列"""
    rounds: list[RoundType] = field(default_factory=list)
    current_index: int = 0

    @property
    def current_round(self) -> Optional[RoundType]:
        if self.current_index < len(self.rounds):
            return self.rounds[self.current_index]
        return None

    @property
    def remaining_rounds(self) -> list[RoundType]:
        return self.rounds[self.current_index:]

    @property
    def is_empty(self) -> bool:
        return self.current_index >= len(self.rounds)

    def advance(self) -> None:
        self.current_index += 1

    def to_dict(self) -> dict:
        return {
            "total": len(self.rounds),
            "remaining": len(self.remaining_rounds),
            "current_index": self.current_index,
            "live_count": sum(1 for r in self.rounds if r == RoundType.LIVE),
            "blank_count": sum(1 for r in self.rounds if r == RoundType.BLANK),
            "remaining_live": sum(1 for r in self.remaining_rounds if r == RoundType.LIVE),
            "remaining_blank": sum(1 for r in self.remaining_rounds if r == RoundType.BLANK),
            "current_round": self.current_round.value if self.current_round else None,
        }


@dataclass
class GameEvent:
    """描述一次游戏事件的轻量结构"""
    event_type: str
    data: dict = field(default_factory=dict)

    @staticmethod
    def of(event_type: str, **kwargs) -> GameEvent:
        return GameEvent(event_type=event_type, data=kwargs)


@dataclass
class ActionResult:
    """每次操作（使用道具 / 开火）的返回结果"""
    success: bool
    message: str
    events: list[GameEvent] = field(default_factory=list)
    phase: GamePhase = GamePhase.PLAYING
    winner: Optional[int] = None  # 0 或 1，仅在 GAME_OVER 时有值
    state: Optional[dict] = None  # 当前完整游戏状态快照


@dataclass
class ItemInfo:
    """道具可见信息（不暴露位置等隐藏信息）"""
    type: ItemType
    label: str
    description: str

    @staticmethod
    def from_type(it: ItemType) -> ItemInfo:
        return ItemInfo(type=it, label=it.label(), description=it.description())


@dataclass
class BattleLogEntry:
    """对战日志条目"""
    round_number: int       # 第几发
    round_type: str         # live / blank
    description: str        # 人类可读描述
    player: int             # 行动玩家
    timestamp: str = ""     # 时间戳（前端可忽略）


# 给 ActionResult 添加 to_dict 方法
def _action_result_to_dict(self) -> dict:
    return {
        "success": self.success,
        "message": self.message,
        "events": [{"type": e.event_type, **e.data} for e in self.events],
        "phase": self.phase.value,
        "winner": self.winner,
        "state": self.state,
    }


ActionResult.to_dict = _action_result_to_dict  # type: ignore[assignment]
