import math
import random
from collections import defaultdict
from .models import Tournament, Stage, Match, Player
from django.db import transaction


def create_single_elimination_bracket(tournament: Tournament, players: list[Player], start_match_number=1):
    
    next_power_of_two = 2 ** math.ceil(math.log2(len(players)))

    stages = []
    total_rounds = int(math.log2(next_power_of_two))

    # 🏷 命名每個階段
    for i in range(total_rounds):
        remaining_players = next_power_of_two // (2 ** i)
        if remaining_players == 2:
            name = "Final"
        elif remaining_players == 4:
            name = "Semi-final"
        elif remaining_players == 8:
            name = 'Quarter-final'
        else:
            name = f"Last {remaining_players}"
        stage = Stage.objects.create(tournament=tournament, name=name, order=i + 1)
        stages.append(stage)

    match_counter = start_match_number
    players_queue = players
    matches_current_round = []

    # 🎯 第一輪
    for i in range(0, len(players_queue), 2):
        p1 = players_queue[i]
        p2 = players_queue[i + 1]
        match = Match.objects.create(
            stage=stages[0],
            player1=p1,
            player2=p2,
            match_number=match_counter
        )
        match.save()
        match_counter += 1
        matches_current_round.append(match)
    
    # 🔁 後續回合
    semifinal_matches = []  # 存下四強賽以建立季殿賽
    for round_index in range(1, total_rounds):
        matches_next_round = []
        num_matches = len(matches_current_round) // 2

        for i in range(num_matches):
            match = Match.objects.create(
                stage=stages[round_index],
                match_number=match_counter
            )
            match.source_match1 = matches_current_round[2 * i]
            match.source_match2 = matches_current_round[2 * i + 1]
            match.save()
            matches_next_round.append(match)
            match_counter += 1

        # 🔹 記錄四強賽 (Semi-final) 的比賽
        if stages[round_index].name == "Final" and len(matches_current_round) == 2:
            semifinal_matches = matches_current_round

        matches_current_round = matches_next_round

    # 🥉 建立季殿賽（由四強賽輸家對決）
    if semifinal_matches:
        tie_breaker_stage = Stage.objects.create(
            tournament=tournament,
            name="Tie Breaker",
            order=total_rounds + 1
        )
        tie_breaker = Match.objects.create(
            stage=tie_breaker_stage,
            match_number=match_counter,
            source_match1=semifinal_matches[0],
            source_match2=semifinal_matches[1],
        )

    return tournament

def create_double_elimination_bracket(tournament: Tournament, players: list[Player]):
    """
    建立四組，每組包含：
    - 第一輪 (Initial Round)
    - 敗部第一輪 (Losers Round 1)
    - 勝部第一輪 (Winners Round 1)
    - 敗部第二輪 (Losers Round 2)
    每組會產生兩位晉級者（勝部冠軍 + 敗部冠軍）
    """

    group_size = math.ceil(len(players) / 4)
    groups = [players[i:i + group_size] for i in range(0, len(players), group_size)]
    group_names = ["A", "B", "C", "D"]
    match_counter = 1

    # advancing_players_win = []
    # advancing_players_lose = []
    for g_idx, group_players in enumerate(groups):
        group_label = group_names[g_idx] if g_idx < len(group_names) else f"Group {g_idx+1}"

        # === 建立 Stages ===
        stages = {
            "initial": Stage.objects.create(
                tournament=tournament,
                name=f"Group {group_label} Initial Round",
                order=g_idx * 10 + 1
            ),
            "losers_r1": Stage.objects.create(
                tournament=tournament,
                name=f"Group {group_label} Losers Round 1",
                order=g_idx * 10 + 2
            ),
            "winners_qualification": Stage.objects.create(
                tournament=tournament,
                name=f"Group {group_label} Winners' Qualification",
                order=g_idx * 10 + 3
            ),
            "losers_qualification": Stage.objects.create(
                tournament=tournament,
                name=f"Group {group_label} Losers' Qualification",
                order=g_idx * 10 + 4
            ),
        }

        # === 第一輪 (Initial Round) ===
        initial_matches = []
        for i in range(0, len(group_players), 2):
            p1 = group_players[i]
            p2 = group_players[i + 1] if i + 1 < len(group_players) else None
            match = Match.objects.create(
                stage=stages["initial"],
                player1=p1,
                player2=p2,
                match_number=match_counter
            )
            match_counter += 1
            initial_matches.append(match)

        # === 敗部第一輪 (Losers Round 1) ===
        losers_r1_matches = []
        for i in range(0, len(initial_matches), 2):
            match = Match.objects.create(
                stage=stages["losers_r1"],
                source_match1=initial_matches[i],
                source_match2=initial_matches[i + 1] if i + 1 < len(initial_matches) else None,
                is_losers_bracket=True,
                match_number=match_counter
            )
            match_counter += 1
            losers_r1_matches.append(match)

        # === 勝部晉級賽 (Winners' Qulification) ===
        winners_qualification_matches = []
        for i in range(0, len(initial_matches), 2):
            match = Match.objects.create(
                stage=stages["winners_qualification"],
                source_match1=initial_matches[i],
                source_match2=initial_matches[i + 1] if i + 1 < len(initial_matches) else None,
                match_number=match_counter
            )
            match_counter += 1
            winners_qualification_matches.append(match)

        # === 敗部晉級賽 (Losers' Qulification) ===
        losers_qualification_matches = []
        # 將勝部晉級賽逆序排列（交叉配對）
        reversed_winners = list(reversed(winners_qualification_matches))

        for i in range(len(losers_r1_matches)):
            match = Match.objects.create(
                stage=stages["losers_qualification"],
                source_match1=losers_r1_matches[i],                       # 敗部第一輪的勝者
                source_match2=reversed_winners[i] if i < len(reversed_winners) else None,  # 勝部晉級賽的輸者
                is_losers_bracket=True,
                match_number=match_counter
            )
            match_counter += 1
            losers_qualification_matches.append(match)

        # advancing_players_win += [m.winner for m in winners_qualification_matches]  # 對應勝部第一輪勝者
        # advancing_players_lose += [m.winner for m in losers_qualification_matches]   # 對應敗部第二輪勝者

    # random.shuffle(advancing_players_win)
    # random.shuffle(advancing_players_lose)

    # advancing_players = []
    # for w_p, l_p in zip(advancing_players_win, advancing_players_lose):
    #     advancing_players.append(w_p)
    #     advancing_players.append(l_p)

    # if advancing_players:
    #     create_single_elimination_bracket(tournament, advancing_players, start_match_number=match_counter)

    return tournament

def advance_from_double_elim_and_create_single_elim(tournament):
    stages = Stage.objects.filter(tournament=tournament)

    advance_winners = []
    advance_losers = []
    for stage in stages:
        if 'Qualification' in stage.name:
            matches = Match.objects.filter(stage=stage)
            for match in matches:
                if 'Winner' in stage.name:
                    advance_winners.append(match.winner)
                elif 'Loser' in stage.name:
                    advance_losers.append(match.winner)
    random.shuffle(advance_winners)
    random.shuffle(advance_losers)

    advance_players = []
    for w, l in zip(advance_winners, advance_losers):
        advance_players.append(w)
        advance_players.append(l)

    create_single_elimination_bracket(tournament=tournament, players=advance_players)
    return tournament

@transaction.atomic
def create_mixed_bracket(
    tournament: Tournament,
    players: list[Player],
    num_groups: int,
    group_size: int,
    advance_per_group: int,
):
    """
    建立混合賽制（分組循環 + 後續單敗）

    參數：
        tournament: Tournament 物件
        players: 所有參賽 Player 物件 list
        num_groups: 要分成幾組
        group_size: 每組幾人
        advance_per_group: 每組晉級人數

    流程：
        1. 隨機打亂所有玩家
        2. 根據 num_groups / group_size 分組
        3. 為每組建立 Stage（循環賽）
        4. 為每組建立比賽（每人互打一次）
        5. 暫存晉級名單（目前先不生成單敗部分）
    """

    total_needed = num_groups * group_size
    if len(players) < total_needed:
        raise ValueError(f"需要至少 {total_needed} 名玩家（目前只有 {len(players)}）")

    if advance_per_group > group_size:
        raise ValueError("每組晉級人數不能大於該組人數")

    groups = []
    for i in range(num_groups):
        start = i * group_size
        end = start + group_size
        groups.append(players[start:end])

    advanced_players = []

    match_counter = 1

    # 為每組建立循環賽
    for group_index, group_players in enumerate(groups, start=1):
        stage = Stage.objects.create(
            tournament=tournament,
            name=f"Group {group_index} Round Robin",
            order=group_index,
        )

        # 建立所有對戰（循環）
        for i in range(len(group_players)):
            for j in range(i + 1, len(group_players)):
                Match.objects.create(
                    stage=stage,
                    player1=group_players[i],
                    player2=group_players[j],
                    match_number = match_counter
                )
                match_counter += 1

    return tournament

def advance_from_round_robin_and_create_single_elim(tournament):
    """
    循環賽 -> 單敗淘汰賽生成。
    - 比序：勝場 > 得局 > 失局少 > 得局率
    - 特殊情況：W = 該玩家 inning，FF = 0
    - 單敗籤表生成時避免同組首輪對戰
    """
    standings = get_round_robin_standings(tournament)
    advanced_players = []
    t = tournament.advance_per_group
    for group, players in standings.items():
        for player in players[:t]:
            advanced_players.append(player['player'])
    # group_stages = tournament.stages.filter(name__icontains="Group").order_by("order")
    # records = defaultdict(lambda: {"wins": 0, "games_for": 0, "games_against": 0})
    # group_advancers = defaultdict(list)  # {group_name: [players...]}

    # # === 統計循環賽數據 ===
    # for stage in group_stages:
    #     matches = stage.matches.all()
    #     for match in matches:
    #         p1, p2 = match.player1, match.player2
    #         if not p1 or not p2:
    #             continue

    #         point1, point2 = match.point1, match.point2
    #         if point1 is None or point2 is None:
    #             continue

    #         def convert_point(point, player):
    #             if isinstance(point, (int, float)):
    #                 return point
    #             if isinstance(point, str):
    #                 if point.upper() == "W":
    #                     return getattr(player, "inning", 1)
    #                 elif point.upper() == "FF":
    #                     return 0
    #             return 0

    #         p1_point = convert_point(point1, p1)
    #         p2_point = convert_point(point2, p2)

    #         records[p1]["games_for"] += p1_point
    #         records[p1]["games_against"] += p2_point
    #         records[p2]["games_for"] += p2_point
    #         records[p2]["games_against"] += p1_point

    #         if p1_point > p2_point:
    #             records[p1]["wins"] += 1
    #         elif p2_point > p1_point:
    #             records[p2]["wins"] += 1

    # # === 決定各組晉級 ===
    # for stage in group_stages:
    #     group_players = set()
    #     for match in stage.matches.all():
    #         if match.player1:
    #             group_players.add(match.player1)
    #         if match.player2:
    #             group_players.add(match.player2)

    #     group_records = []
    #     for p in group_players:
    #         rec = records[p]
    #         gf, ga = rec["games_for"], rec["games_against"]
    #         ratio = gf / (gf + ga) if (gf + ga) > 0 else 0
    #         group_records.append((p, rec["wins"], gf, ga, ratio))

    #     group_records.sort(key=lambda x: (x[1], x[2], -x[3], x[4]), reverse=True)

    #     advance_num = tournament.advance_per_group or 2
    #     group_advancers[stage.name] = [x[0] for x in group_records[:advance_num]]

    # # === 防同組對戰抽籤 ===
    # all_advancers = []
    # groups = list(group_advancers.values())

    # # 假設每組晉級相同人數（一般情況）
    # # 我們以「蛇形」分配到不同半區
    # for i in range(max(len(g) for g in groups)):
    #     for group in groups:
    #         if i < len(group):
    #             all_advancers.append(group[i])

    # # 若仍需隨機微調（例如組數太少），再隨機交換部分種子
    # random.shuffle(all_advancers)

    # # === 生成單敗籤表 ===
    random.shuffle(advanced_players)
    create_single_elimination_bracket(tournament, advanced_players)
    return tournament

def get_round_robin_standings(tournament):
    """
    即時計算循環賽各組積分表。
    回傳格式：
    {
        "Group A": [
            {"player": player, "wins": 3, "games_for": 21, "games_against": 10, "ratio": 0.677},
            ...
        ],
        ...
    }
    """
    group_stages = tournament.stages.filter(name__icontains="Group").order_by("order")
    records = defaultdict(lambda: {"wins": 0, "games_for": 0, "games_against": 0})
    group_standings = defaultdict(list)

    # === 統計數據 ===
    for stage in group_stages:
        matches = stage.matches.all()
        for match in matches:
            p1, p2 = match.player1, match.player2
            if not p1 or not p2:
                continue

            point1, point2 = match.point1, match.point2
            if point1 == '' or point2 == '':
                continue
            if point1 != 'W' and point1 != 'FF':
                point1 = int(point1)
            if point2 != 'W' and point2 != 'FF':
                point2 = int(point2)

            def convert_point(point, player):
                if isinstance(point, (int, float)):
                    return point
                if isinstance(point, str):
                    if point.upper() == "W":
                        return getattr(player, "inning", 1)
                    elif point.upper() == "FF":
                        return 0
                return 0

            p1_point = convert_point(point1, p1)
            p2_point = convert_point(point2, p2)

            records[p1]["games_for"] += p1_point
            records[p1]["games_against"] += p2_point
            records[p2]["games_for"] += p2_point
            records[p2]["games_against"] += p1_point

            if p1_point > p2_point:
                records[p1]["wins"] += 1
            elif p2_point > p1_point:
                records[p2]["wins"] += 1

    # === 各組排名 ===
    for stage in group_stages:
        group_players = set()
        for match in stage.matches.all():
            if match.player1:
                group_players.add(match.player1)
            if match.player2:
                group_players.add(match.player2)

        player_list = []
        for p in group_players:
            rec = records[p]
            gf, ga = rec["games_for"], rec["games_against"]
            ratio = gf / (gf + ga) if (gf + ga) > 0 else 0
            player_list.append({
                "player": p,
                "wins": rec["wins"],
                "games_for": gf,
                "games_against": ga,
                "ratio": round(ratio, 3),
            })

        player_list.sort(key=lambda x: (x["wins"], x["games_for"], -x["games_against"], x["ratio"]), reverse=True)
        group_standings[stage.name] = player_list

    return group_standings