from django.contrib import admin
from django.contrib import admin
from .models import Material, MaterialPurchase


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'subject', 'level', 'uploader', 'download_count', 'is_approved', 'created_at')
    list_filter = ('subject', 'level', 'is_approved', 'file_type')
    search_fields = ('title', 'description', 'uploader__username')
    list_editable = ('is_approved',)
    actions = ['approve_materials']

    def approve_materials(self, request, queryset):
        queryset.update(is_approved=True)
    approve_materials.short_description = 'Approve selected materials'


@admin.register(MaterialPurchase)
class MaterialPurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'material', 'amount_paid', 'purchased_at')
    list_filter = ('purchased_at',)
    search_fields = ('user__username', 'material__title')
