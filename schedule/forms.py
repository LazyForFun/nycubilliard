from django import forms
from .models import Announcement, Tournament

class PlayerImportForm(forms.ModelForm):
    file = forms.FileField(
        label="上傳選手名單 (CSV)",
        help_text="CSV 檔案格式：每行一個玩家名稱"
    )

    TYPE_CHOICES = [
        ("single_elim", "單敗"),
        ("double_elim", "雙敗"),
        ("round_robin", "循環賽"),
    ]

    type = forms.ChoiceField(choices=TYPE_CHOICES, label="賽制")

    class Meta:
        model = Tournament
        fields = [
            'semester', 'name', 'player_num', 'type',
            'num_groups', 'group_size', 'advance_per_group'
        ]
        labels = {
            'name': '名稱',
            'semester': '學年',
            'player_num': '參賽人數',
            'num_groups': '組數',
            'group_size': '各組人數',
            'advance_per_group': '各組晉級人數',
        }

    def clean(self):
        cleaned_data = super().clean()
        tournament_type = cleaned_data.get('type')

        # 這三個欄位僅在「循環賽」時必填
        if tournament_type == 'round_robin':
            required_fields = ['num_groups', 'group_size', 'advance_per_group']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, f"當賽制為循環賽時，『{self.fields[field].label}』為必填欄位。")
        else:
            # 非循環賽時可清空以避免誤存
            cleaned_data['num_groups'] = None
            cleaned_data['group_size'] = None
            cleaned_data['advance_per_group'] = None

        return cleaned_data

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcement
        fields = ["title", "content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 15,
                "cols": 100,
                "style": "width:100%; resize:vertical;",
            }),
        }
