from rest_framework import serializers
from .models import EnvSnapshot, Beacon
from datetime import datetime, timezone as dt_timezone


class EnvSnapshotIn(serializers.ModelSerializer):
    class Meta:
        model  = EnvSnapshot
        fields = "__all__"
        read_only_fields = ("captured_at",) 

class BeaconIn(serializers.ModelSerializer):
    ts = serializers.DateTimeField()         # accept ISO‑8601 or epoch seconds

    class Meta:
        model  = Beacon
        fields = "__all__"

    def to_internal_value(self, data):
        data = data.copy()
        raw_ts = data.get("ts")
        if isinstance(raw_ts, (int, float)):
            data["ts"] = datetime.fromtimestamp(raw_ts, tz=dt_timezone.utc)
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs["kind"] == "error" and not (attrs.get("error_sig") or attrs.get("trace")):
            raise serializers.ValidationError(
                "For kind='error' you must supply error_sig or trace."
            )
        return attrs