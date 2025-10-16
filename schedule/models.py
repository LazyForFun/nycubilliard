from django.db import models
from django.contrib.auth.models import User

class Tournament(models.Model):
    TYPE_CHOICES = [
        ("single_elim", "Single Elimination"),
        ("double_elim", "Double Elimination"),
        ("round_robin", "Round Robin"),
    ]
    name = models.CharField(max_length=20)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    semester = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    player_num = models.IntegerField()

    num_groups = models.IntegerField(null=True, blank=True)
    group_size = models.IntegerField(null=True, blank=True)
    advance_per_group = models.IntegerField(null=True, blank=True)


    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class Stage(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="stages")
    name = models.CharField(max_length=100)  # e.g. "Winners Bracket R1", "Losers Bracket", "Group A"
    order = models.PositiveIntegerField()  # 用來排序階段

    def __str__(self):
        return f"{self.tournament.name} - {self.name}"


class Player(models.Model):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    innings = models.IntegerField() #局數

    def __str__(self):
        return self.name


class Match(models.Model):
    stage = models.ForeignKey(Stage, on_delete=models.CASCADE, related_name="matches")
    player1 = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_player1")
    player2 = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_player2")
    winner = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_winner")
    loser = models.ForeignKey(Player, null=True, blank=True, on_delete=models.SET_NULL, related_name="match_loser")

    point1 = models.CharField(max_length=3, default='')
    point2 = models.CharField(max_length=3, default='')

    # 單/雙淘汰用：前一場的勝者 → 當作本場參賽者
    source_match1 = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="next_match_as_p1")
    source_match2 = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="next_match_as_p2")

    # match number
    match_number = models.IntegerField()

    #桌次
    table = models.IntegerField(default=0)

    # 雙敗淘汰需要 losers bracket，所以可以在 stage 層區分
    is_losers_bracket = models.BooleanField(default=False)

    # 循環賽用：不用連接 source_match，而是直接產生所有對戰
    round_number = models.PositiveIntegerField(null=True, blank=True)

    start_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Match {self.id} ({self.stage.name})"

    def get_player1_display(self):
        if self.player1:
            return self.player1.name
        elif self.source_match1:
            return f"Winner of Match #{self.source_match1.match_number}"
        return "-"

    def get_player2_display(self):
        if self.player2:
            return self.player2.name
        elif self.source_match2:
            return f"Winner of Match #{self.source_match2.match_number}"
        return '-'

class Announcement(models.Model):
    title = models.CharField(max_length=200)
    content = models.CharField(max_length=100000)