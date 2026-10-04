from django.contrib import admin
from .models import Group, ChatMessage, Decision, DecisionOption, Vote, SharedList, ListItem, BuddyMemory

admin.site.register(Group)
admin.site.register(ChatMessage)
admin.site.register(Decision)
admin.site.register(DecisionOption)
admin.site.register(Vote)
admin.site.register(SharedList)
admin.site.register(ListItem)
admin.site.register(BuddyMemory)