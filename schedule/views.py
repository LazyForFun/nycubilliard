from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView, DeleteView
from django.contrib import auth, messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

import csv, io, random
from .models import Tournament, Player, Announcement, Match
from .forms import PlayerImportForm, AnnouncementForm
from .utils import create_single_elimination_bracket, create_double_elimination_bracket, create_mixed_bracket, advance_from_round_robin_and_create_single_elim

# Create your views here.
class Home(View):
    def get(self, request):
        return render(request, 'Home.html')
    
class LoginView(View):

    def get(self, request):
        return render(request, 'Login.html')

    def post(self, request):
        if request.user.is_authenticated:
            return redirect(reverse('Home'))

        username = request.POST['username']
        password = request.POST['password']
        user = auth.authenticate(username=username, password=password)

        if user.is_active is True:
            auth.login(request, user)
            return redirect(reverse('Home'))
        else:
            return render(request, 'Login.html', locals())
        
class LogoutView(View):

    def post(self, request):
        auth.logout(request)
        return redirect(reverse('Home'))
    
class MatchDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        match = Match.objects.get(id=pk)
        return render(request, 'MatchDetail.html', {'match': match})
    
    def post(self, request, pk):
        match = Match.objects.get(id=pk)
        start_time = request.POST.get('start_time')
        if start_time != '':
            match.start_time = start_time
        match.table = request.POST.get('table')
        match.point1 = request.POST.get('point1')
        match.point2 = request.POST.get('point2')

        winner_field = request.POST.get("winner")
        if winner_field == "player1":
            match.winner = match.player1
            match.loser = match.player2
        elif winner_field == "player2":
            match.winner = match.player2
            match.loser = match.player1
        match.save()

        next_matches = Match.objects.filter(Q(source_match1=match) | Q(source_match2=match))

        for next_match in next_matches:
            if next_match.source_match1 == match:
                if 'Tie' in next_match.stage.name or 'Losers Round' in next_match.stage.name:
                    next_match.player1 = match.loser
                else:
                    next_match.player1 = match.winner
            else:
                if 'Tie' in next_match.stage.name or 'Losers' in next_match.stage.name:
                    next_match.player2 = match.loser
                else:
                    next_match.player2 = match.winner
            next_match.save()

        return redirect('TournamentDetailView', pk=match.stage.tournament.id)
    
class AnnouncementDeleteView(LoginRequiredMixin, DeleteView):
    model = Announcement
    template_name = "AnnouncementConfirmDelete.html"
    success_url = reverse_lazy("AnnouncementListView")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "公告已刪除")
        return super().delete(request, *args, **kwargs)
    
class AnnouncementCreateView(LoginRequiredMixin, CreateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = "AnnouncementForm.html"
    success_url = reverse_lazy("AnnouncementListView")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "公告已成功建立！")
        return response

class AnnouncementUpdateView(LoginRequiredMixin, UpdateView):
    model = Announcement
    form_class = AnnouncementForm
    template_name = "AnnouncementForm.html"  # 跟新增共用一個表單
    success_url = reverse_lazy("AnnouncementListView")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "公告已成功更新！")
        return response

class AnnouncementDetailView(View):
    def get(self, request, pk):
        announcement = Announcement.objects.get(id=pk)
        return render(request, 'AnnouncementDetail.html', {'announcement': announcement})
    
class AnnouncementListView(View):
    template_name = 'ListAnnouncement.html'

    def get(self, request):
        announcements = Announcement.objects.all().order_by('-id')
        return render(request, self.template_name, {'announcements': announcements})
    
class TournamentDeleteView(LoginRequiredMixin, DeleteView):
    model = Tournament
    template_name = "TournamentConfirmDelete.html"
    success_url = reverse_lazy("TournamentListView")

    def delete(self, request, *args, **kwargs):
        messages.success(request, "比賽已刪除")
        return super().delete(request, *args, **kwargs)

class TournamentCreateView(LoginRequiredMixin, View):
    template_name = "CreateTournament.html"

    def get(self, request):
        form = PlayerImportForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = PlayerImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES["file"]

            # ✅ 1. 檢查副檔名
            if not csv_file.name.endswith(".csv"):
                return render(request, self.template_name, {
                    "form": form,
                    "error": "請上傳 CSV 檔案"
                })

            # ✅ 2. 讀取 CSV 檔案內容
            decoded_file = csv_file.read().decode("utf-8-sig")  # 防止有 BOM
            io_string = io.StringIO(decoded_file)
            reader = csv.reader(io_string)

            # ✅ 3. 取得要讀取的玩家數量
            expected_count = form.cleaned_data["player_num"]

            # ✅ 4. 逐行讀取並限制最多讀取 expected_count 行
            player_names = []
            innings_list = []
            for i, row in enumerate(reader):
                if i >= expected_count:
                    break  # 超過輸入人數就停止

                if not row or not row[0].strip():
                    # 空行 → 空籤
                    name = f"-"
                    innings = 999
                else:
                    name = row[0].strip()
                    if len(row) > 1 and row[1].strip().isdigit():
                        innings = int(row[1].strip())
                    else:
                        innings = 999

                player_names.append(name)
                innings_list.append(innings)
            
            player_names = player_names + [''] * (expected_count - len(player_names))
            innings_list = innings_list + [999] * (expected_count - len(innings_list))
            # ✅ 7. 建立比賽
            t = form.cleaned_data["type"]
            tournament = Tournament.objects.create(
                type=t,
                name=form.cleaned_data["name"],
                semester=form.cleaned_data["semester"],
                player_num=expected_count,
                num_groups = form.cleaned_data["num_groups"],
                group_size = form.cleaned_data["group_size"],
                advance_per_group = form.cleaned_data["advance_per_group"],
            )

            # ✅ 8. 建立玩家（保留順序）
            players = [
                Player.objects.create(name=player_names[i], innings=innings_list[i])
                for i in range(expected_count)
            ]

            # ✅ 9. 依據賽制建立 bracket
            if t == 'single_elim':
                create_single_elimination_bracket(tournament, players)
            elif t == 'double_elim':
                create_double_elimination_bracket(tournament, players)
            elif t == 'round_robin':
                create_mixed_bracket(tournament, players, tournament.num_groups, tournament.group_size, tournament.advance_per_group)

            return redirect("TournamentDetailView", pk=tournament.id)

        return render(request, self.template_name, {"form": form})

    
class TournamentDetailView(View):
    def get(self, request, pk):
        return self.render_tournament(request, pk)

    def post(self, request, pk):
        # 判斷 POST 目的
        action = request.POST.get("action")

        # ✅ 如果是搜尋
        if action == "search":
            return self.render_tournament(request, pk, is_post=True)

        # ✅ 如果是生成單敗籤表（只允許循環賽）
        elif action == "generate_single_elim":
            tournament = get_object_or_404(Tournament, id=pk)

            if tournament.type != "round_robin":
                messages.error(request, "只有循環賽才能生成單敗籤表！")
                return redirect("TournamentDetailView", pk=pk)

            try:
                advance_from_round_robin_and_create_single_elim(tournament)
                messages.success(request, "單敗籤表已成功生成！")
            except Exception as e:
                messages.error(request, f"生成籤表時發生錯誤：{e}")

            return redirect("TournamentDetailView", pk=pk)

        # 其他未知情況就照舊顯示
        return self.render_tournament(request, pk)

    def render_tournament(self, request, pk, is_post=False):
        tournament = Tournament.objects.get(id=pk)

        # 搜尋功能（僅 POST 時啟用）
        name_query = None
        if is_post:
            getValue = request.POST
            if 'name' in getValue and getValue['name']:
                name_query = (
                    Q(player1__name__icontains=getValue['name']) |
                    Q(player2__name__icontains=getValue['name'])
                )

        # 取得所有 stage，依 order 排序
        stages = tournament.stages.all().order_by('order')

        # 分成兩組（Stage 1 / Final）
        group_stages = []  # 第一階段（雙敗或小組）
        final_stages = []  # 第二階段（單敗或晉級賽）

        # 根據 stage 名稱分類（可依照命名規則調整）
        for stage in stages:
            matches = stage.matches.all().order_by('id')
            if name_query:
                matches = matches.filter(name_query)

            data = {'stage': stage, 'matches': matches}
            if 'Round' in stage.name or 'Qualification' in stage.name:
                group_stages.append(data)
            else:
                final_stages.append(data)

        is_round_robin = tournament.type == 'round_robin'
        has_final_matches = bool(final_stages)

        context = {
            'tournament': tournament,
            'group_stage_matches': group_stages,
            'final_stage_matches': final_stages,
            'has_two_stages': tournament.type in ['double_elim', 'round_robin'],
            'show_generate_button': is_round_robin and not has_final_matches,
        }
        return render(request, 'ListStageAndMatch.html', context)

    
class TournamentListView(View):
    def get(self, request):
        tournaments = Tournament.objects.all()
        return render(request, 'ListTournament.html', {'tournaments': tournaments})
    
    def post(self, request):
        getValue = self.request.POST
        tournaments = Tournament.objects.all()
        if getValue:
            queryDict = {}
            if 'name' in getValue and getValue['name']:
                queryDict['name__icontains'] = getValue['name']
            if 'semester' in getValue and getValue['semester']:
                queryDict['semester__icontains'] = getValue['semester']
            tournaments = tournaments.filter(**queryDict)

        return render(request, 'ListTournament.html', {'tournaments': tournaments})