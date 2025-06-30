from django.contrib import admin
from .models import EnvSnapshot, Beacon

@admin.register(EnvSnapshot)
class EnvSnapshotAdmin(admin.ModelAdmin):
    list_display = ('id', 'env_hash', 'machine_arch', 'python_ver', 'os_info', 'captured_at')
    list_filter = ('machine_arch', 'python_ver', 'captured_at')
    search_fields = ('env_hash', 'os_info')
    readonly_fields = ('captured_at',)
    ordering = ('-captured_at',)
    
    # Fields to show in the detail view - organized in logical groups
    fieldsets = (
        ('Basic Information', {
            'fields': ('env_hash', 'captured_at')
        }),
        ('System Information', {
            'fields': ('machine_arch', 'python_ver', 'os_info')
        }),
        ('Environment Data', {
            'fields': ('packages', 'env_vars'),
            'classes': ('collapse',)  # Makes this section collapsible
        }),
    )

@admin.register(Beacon)
class BeaconAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'env_hash', 'script_id', 'error_sig', 'ts')
    list_filter = ('kind', 'ts')
    search_fields = ('env_hash', 'script_id', 'error_sig')
    readonly_fields = ('ts',)
    ordering = ('-ts',)
