"""派对彩带大对决 — 手动验证脚本"""

import sys
sys.path.insert(0, '.')

from game import PartyGame, ItemType, Target, RoundType, GamePhase

passed = 0
failed = 0

def check(cond, msg):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {msg}")
    else:
        failed += 1
        print(f"  [FAIL] {msg}")

def pstate(g):
    s = g.get_state()
    p0, p1 = s['players'][0], s['players'][1]
    c = s['cannon']
    cp = s['current_player']
    return f"  P0[{p0['name']}] balloons={p0['balloons']} items={p0['items']} | P1[{p1['name']}] balloons={p1['balloons']} items={p1['items']} | turn=P{cp} | ammo={c['remaining']} (live={c['remaining_live']}/blank={c['remaining_blank']})"

def use(g, item_type, expect_ok=True):
    r = g.use_item(g.current_player, item_type.value)
    if r.success != expect_ok:
        print(f"  [FAIL] use_item({item_type.label()}): success={r.success}, msg={r.message}")
    elif r.success:
        for e in r.events:
            print(f"        event: {e.event_type} {e.data}")
    return r

def shoot(g, target, expect_ok=True):
    r = g.shoot(g.current_player, target.value)
    if r.success != expect_ok:
        print(f"  [FAIL] shoot({target.value}): success={r.success}, msg={r.message}")
    else:
        for e in r.events:
            print(f"        event: {e.event_type} {e.data}")
    return r


print("=" * 60)
print("Test 1: Create game & basic state")
print("=" * 60)
g = PartyGame(p1_name="Alice", p2_name="Bob", difficulty="normal", seed=42)
print(pstate(g))
check(g.level == 1, "level should be 1")
check(g.phase == GamePhase.PLAYING, "phase should be PLAYING")
check(g.players[0].balloons == 4, "P0 balloons should be 4")
check(g.players[1].balloons == 4, "P1 balloons should be 4")
check(len(g.cannon.rounds) == 5, "should have 5 rounds")
live_count = sum(1 for r in g.cannon.rounds if r == RoundType.LIVE)
check(live_count == 2, f"should have 2 live rounds, got {live_count}")

print()
print("=" * 60)
print("Test 2: Shoot self + blank => extra turn")
print("=" * 60)
g = PartyGame(seed=99)
cp = g.current_player
g.cannon.rounds[g.cannon.current_index] = RoundType.BLANK
r = shoot(g, Target.SELF)
print(pstate(g))
check(g.current_player == cp, f"should be same player (extra turn), got P{g.current_player}")

print()
print("=" * 60)
print("Test 3: Shoot self + live => lose balloon + switch turn")
print("=" * 60)
g = PartyGame(seed=99)
cp = g.current_player
old_balloons = g.players[cp].balloons
g.cannon.rounds[g.cannon.current_index] = RoundType.LIVE
r = shoot(g, Target.SELF)
print(pstate(g))
check(g.players[cp].balloons == old_balloons - 1, f"should lose 1 balloon, got {g.players[cp].balloons}")
check(g.current_player != cp, "should switch turn")

print()
print("=" * 60)
print("Test 4: Shoot opponent + live => opponent loses 1 balloon + switch")
print("=" * 60)
g = PartyGame(seed=99)
cp = g.current_player
opp = 1 - cp
old_opp = g.players[opp].balloons
g.cannon.rounds[g.cannon.current_index] = RoundType.LIVE
r = shoot(g, Target.OPPONENT)
print(pstate(g))
check(g.players[opp].balloons == old_opp - 1, f"opponent should lose 1 balloon, got {g.players[opp].balloons}")
check(g.current_player != cp, "should switch turn")

print()
print("=" * 60)
print("Test 5: Shoot opponent + blank => no damage + switch")
print("=" * 60)
g = PartyGame(seed=99)
cp = g.current_player
opp = 1 - cp
old_opp = g.players[opp].balloons
g.cannon.rounds[g.cannon.current_index] = RoundType.BLANK
r = shoot(g, Target.OPPONENT)
print(pstate(g))
check(g.players[opp].balloons == old_opp, f"opponent should not lose balloons, got {g.players[opp].balloons}")
check(g.current_player != cp, "should switch turn")

print()
print("=" * 60)
print("Test 6: Candy Lens - reveal current round type")
print("=" * 60)
g = PartyGame(seed=42)
g.players[g.current_player].items = [ItemType.CANDY_LENS]
r = use(g, ItemType.CANDY_LENS)
has_candy = any(e.event_type == "candy_lens" for e in r.events)
check(has_candy, "should have candy_lens event")

print()
print("=" * 60)
print("Test 7: Bubble Soda - eject current round")
print("=" * 60)
g = PartyGame(seed=42)
old_len = len(g.cannon.rounds)
old_idx = g.cannon.current_index
g.players[g.current_player].items = [ItemType.BUBBLE_SODA]
r = use(g, ItemType.BUBBLE_SODA)
new_len = len(g.cannon.rounds)
check(new_len == old_len - 1, f"rounds should decrease by 1, old={old_len} new={new_len}")
check(g.cannon.current_index == old_idx, f"index should stay same, got {g.cannon.current_index}")
print(f"  rounds: {old_len} -> {new_len}, index stays at {g.cannon.current_index}")

print()
print("=" * 60)
print("Test 8: Cat Paw Ribbon - skip opponent's next turn")
print("=" * 60)
g = PartyGame(seed=42)
cp = g.current_player
g.players[cp].items = [ItemType.CAT_PAW_RIBBON]
r = use(g, ItemType.CAT_PAW_RIBBON)
check(g.players[1 - cp].skip_next_turn, "opponent should have skip_next_turn=True")

g.cannon.rounds[g.cannon.current_index] = RoundType.BLANK
r = shoot(g, Target.OPPONENT)
print(pstate(g))
check(g.current_player == cp, f"should return to player {cp}, got P{g.current_player}")
check(not g.players[1 - cp].skip_next_turn, "skip flag should be cleared")

print()
print("=" * 60)
print("Test 9: Double Glitter - next live round deals 2x damage")
print("=" * 60)
g = PartyGame(seed=42)
cp = g.current_player
opp = 1 - cp
old_opp = g.players[opp].balloons
g.players[cp].items = [ItemType.DOUBLE_GLITTER]
r = use(g, ItemType.DOUBLE_GLITTER)
check(g.players[cp].double_damage_active, "double_damage should be active")

g.cannon.rounds[g.cannon.current_index] = RoundType.LIVE
r = shoot(g, Target.OPPONENT)
print(pstate(g))
check(g.players[opp].balloons == old_opp - 2, f"should deal 2 damage, old={old_opp} new={g.players[opp].balloons}")
check(not g.players[cp].double_damage_active, "double_damage should be cleared after use")

print()
print("=" * 60)
print("Test 10: Strawberry Cake - restore 1 balloon")
print("=" * 60)
g = PartyGame(seed=42)
cp = g.current_player
g.players[cp].balloons = 2
g.players[cp].items = [ItemType.STRAWBERRY_CAKE]
r = use(g, ItemType.STRAWBERRY_CAKE)
check(g.players[cp].balloons == 3, f"should restore to 3, got {g.players[cp].balloons}")
print(f"  balloons: 2 -> {g.players[cp].balloons}")

print()
print("=" * 60)
print("Test 11: Whisper Conch - reveal random remaining round")
print("=" * 60)
g = PartyGame(seed=42)
g.players[g.current_player].items = [ItemType.WHISPER_CONCH]
r = use(g, ItemType.WHISPER_CONCH)
has_whisper = any(e.event_type == "whisper_conch" for e in r.events)
check(has_whisper, "should have whisper_conch event")
for e in r.events:
    if e.event_type == "whisper_conch":
        print(f"  revealed position {e.data['position']}: {e.data['label']}")

print()
print("=" * 60)
print("Test 12: Miracle Wand - flip current round type")
print("=" * 60)
g = PartyGame(seed=42)
old_type = g.cannon.current_round
g.players[g.current_player].items = [ItemType.MIRACLE_WAND]
r = use(g, ItemType.MIRACLE_WAND)
new_type = g.cannon.current_round
check(old_type != new_type, f"should flip from {old_type} to opposite, got {new_type}")
print(f"  {old_type.label()} -> {new_type.label()}")

print()
print("=" * 60)
print("Test 13: Phantom Cat Gloves - steal & use opponent's item")
print("=" * 60)
g = PartyGame(seed=42)
cp = g.current_player
opp = 1 - cp
g.players[opp].items = [ItemType.STRAWBERRY_CAKE]
old_balloons = g.players[cp].balloons
g.players[cp].items = [ItemType.PHANTOM_CAT_GLOVES]
r = use(g, ItemType.PHANTOM_CAT_GLOVES)
check(ItemType.STRAWBERRY_CAKE not in g.players[opp].items, "cake should be stolen from opponent")
print(f"  balloons: {old_balloons} -> {g.players[cp].balloons}")
for e in r.events:
    print(f"        event: {e.event_type} {e.data}")

print()
print("=" * 60)
print("Test 14: Kiwi Juice - 50/50 chance (100 trials)")
print("=" * 60)
heal_count = 0
hurt_count = 0
for _ in range(100):
    g = PartyGame(seed=None)
    cp = g.current_player
    old_b = g.players[cp].balloons
    g.players[cp].items = [ItemType.KIWI_JUICE]
    r = use(g, ItemType.KIWI_JUICE)
    if g.players[cp].balloons > old_b:
        heal_count += 1
    else:
        hurt_count += 1
print(f"  100 trials: heal={heal_count}, hurt={hurt_count} (expected ~50/50)")
check(30 < heal_count < 70, f"probability seems off: heal={heal_count}/100")

print()
print("=" * 60)
print("Test 15: Game Over - balloons reach 0")
print("=" * 60)
g = PartyGame(seed=42)
g.players[1].balloons = 1
g.players[0].double_damage_active = True
g.cannon.rounds[g.cannon.current_index] = RoundType.LIVE
r = shoot(g, Target.OPPONENT)
check(g.phase == GamePhase.GAME_OVER, f"phase should be GAME_OVER, got {g.phase}")
check(g.winner == 0, f"winner should be P0, got P{g.winner}")
print(f"  {r.message}")

print()
print("=" * 60)
print("Test 16: Empty cannon auto-starts new level")
print("=" * 60)
g = PartyGame(seed=42)
while not g.cannon.is_empty:
    g.cannon.advance()
r = g.shoot(g.current_player, "self")
check(g.level == 2, f"should advance to level 2, got {g.level}")

print()
print("=" * 60)
print("Test 17: Invalid operations")
print("=" * 60)
g = PartyGame(seed=42)

r = g.use_item(1 - g.current_player, "strawberry_cake")
check(not r.success, f"wrong turn: {r.message}")

r = g.use_item(g.current_player, "nonexistent")
check(not r.success, f"invalid item: {r.message}")

g.players[1].balloons = 0
g._check_game_over()
r = g.shoot(g.current_player, "self")
check(not r.success, f"game over: {r.message}")

print()
print("=" * 60)
print("Test 18: Difficulty settings")
print("=" * 60)
g_easy = PartyGame(difficulty="easy")
check(g_easy.players[0].balloons == 6, f"easy should have 6 balloons, got {g_easy.players[0].balloons}")
g_normal = PartyGame(difficulty="normal")
check(g_normal.players[0].balloons == 4, f"normal should have 4 balloons, got {g_normal.players[0].balloons}")
g_hard = PartyGame(difficulty="hard")
check(g_hard.players[0].balloons == 2, f"hard should have 2 balloons, got {g_hard.players[0].balloons}")

print()
print("=" * 60)
print(f"Results: {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)

if failed > 0:
    sys.exit(1)
