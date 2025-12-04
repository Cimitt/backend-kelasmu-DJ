from django.contrib import admin
from .models import User, Classroom, Material, Enrollment, Submission, ClassChatMessage, DirectChatMessage
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Extra", {"fields": ("is_teacher",)}),)

admin.site.register(Classroom)
admin.site.register(Material)
admin.site.register(Enrollment)
admin.site.register(Submission)
admin.site.register(ClassChatMessage)
admin.site.register(DirectChatMessage)
