from django.contrib import admin
from emtools.emauth.models import Profile

class ProfileAdmin(admin.ModelAdmin):
    fieldsets = (
        ("MyBB Information", {'fields': ['mybb_uid', 'mybb_username']}),
        ("API Overrides", {'fields': ['usertitle']}),
        ("API Information", {'fields': ['name', 'characterid',
                                        'corp', 'corpid',
                                        'alliance', 'allianceid']}),
        ("Maintenance", {'fields': ['last_check', 'active']})
    )
    readonly_fields = ['mybb_uid', 'mybb_username']
    model = Profile
    max_num = 1
    can_delete = False

admin.site.register(Profile, ProfileAdmin)
