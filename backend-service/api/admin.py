
#  username = muqadaszahra
# password=smart1
# Register your models here.
# api/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, GeneratedImage, EditedImage, ImageScore, AuditLog, ForensicRequest

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra', {'fields': ('role', 'email_verified')}),
    )

admin.site.register(GeneratedImage)
admin.site.register(EditedImage)
admin.site.register(ImageScore)
admin.site.register(AuditLog)
admin.site.register(ForensicRequest)


