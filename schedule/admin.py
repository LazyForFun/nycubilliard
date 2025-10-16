from django.contrib import admin

from .models import Tournament, Match, Stage, Player, Announcement

# Register your models here.
admin.site.register(Tournament)
admin.site.register(Match)
admin.site.register(Stage)
admin.site.register(Player)
admin.site.register(Announcement)