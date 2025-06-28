from django.db import models

class EnvSnapshot(models.Model):
    id           = models.BigAutoField(primary_key=True)    
    env_hash     = models.CharField(max_length=12)
    machine_arch = models.CharField(max_length=20)          
    packages     = models.JSONField()
    python_ver   = models.CharField(max_length=20)
    os_info      = models.CharField(max_length=120)
    env_vars     = models.JSONField(null=True, blank=True)
    captured_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("env_hash", "machine_arch")


class Beacon(models.Model):
    KIND = [("error", "error"), ("success", "success")]
    kind       = models.CharField(max_length=7, choices=KIND)
    env_hash   = models.CharField(max_length=12)
    script_id  = models.CharField(max_length=12)
    error_sig  = models.TextField(null=True, blank=True)
    trace      = models.TextField(null=True, blank=True)
    ts         = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["error_sig", "env_hash"]),
        ]
