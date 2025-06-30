from django.contrib import admin
from .models import ErrorCluster, ConfigPattern, ErrorAnalysis

@admin.register(ErrorCluster)
class ErrorClusterAdmin(admin.ModelAdmin):
    list_display = ('cluster_hash', 'error_signature', 'error_count', 'first_seen', 'last_seen', 'created_at')
    list_filter = ('first_seen', 'last_seen', 'created_at')
    search_fields = ('cluster_hash', 'error_signature')
    readonly_fields = ('created_at',)
    ordering = ('-last_seen',)

@admin.register(ConfigPattern)
class ConfigPatternAdmin(admin.ModelAdmin):
    list_display = ('cluster', 'config_key', 'config_value', 'occurrence_rate', 'global_rate', 'significance_score', 'created_at')
    list_filter = ('config_key', 'significance_score', 'created_at')
    search_fields = ('config_key', 'config_value')
    readonly_fields = ('created_at',)
    ordering = ('-significance_score',)

@admin.register(ErrorAnalysis)
class ErrorAnalysisAdmin(admin.ModelAdmin):
    list_display = ('analysis_date', 'total_errors_analyzed', 'clusters_found', 'patterns_found', 'analysis_duration')
    list_filter = ('analysis_date',)
    readonly_fields = ('analysis_date',)
    ordering = ('-analysis_date',)
