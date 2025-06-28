from django.db import models
from telemetry.models import Beacon

class ErrorCluster(models.Model):
    """Represents a cluster of similar errors with pre-computed embedding"""
    cluster_hash = models.CharField(max_length=64, unique=True)
    error_signature = models.TextField()
    error_count = models.IntegerField()
    first_seen = models.DateTimeField()
    last_seen = models.DateTimeField()
    embedding = models.BinaryField()  # Pre-computed embedding for fast similarity search
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cluster_hash']),
        ]

class ConfigPattern(models.Model):
    """Stores configuration patterns that are statistically significant for error clusters"""
    cluster = models.ForeignKey(ErrorCluster, on_delete=models.CASCADE, related_name='config_patterns')
    config_key = models.CharField(max_length=100)  # e.g., 'python_ver', 'machine_arch', 'packages.numpy'
    config_value = models.TextField()
    occurrence_rate = models.FloatField()  # How often this config appears in this cluster (0.0-1.0)
    global_rate = models.FloatField()  # How often this config appears globally (0.0-1.0)
    significance_score = models.FloatField()  # occurrence_rate / global_rate (higher = more significant)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['cluster', 'significance_score']),
            models.Index(fields=['config_key', 'significance_score']),
        ]
        unique_together = ['cluster', 'config_key', 'config_value']

class ErrorAnalysis(models.Model):
    """Tracks analysis runs"""
    analysis_date = models.DateTimeField(auto_now_add=True)
    total_errors_analyzed = models.IntegerField()
    clusters_found = models.IntegerField()
    patterns_found = models.IntegerField()
    analysis_duration = models.FloatField()
    
    class Meta:
        ordering = ['-analysis_date']
