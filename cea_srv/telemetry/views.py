from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import EnvSnapshot, Beacon
from .serializers import EnvSnapshotIn, BeaconIn
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from analysis.services import ConfigSuggestionService

@method_decorator(csrf_exempt, name="dispatch")
class EnvView(APIView):
    def post(self, request):
        ser = EnvSnapshotIn(data=request.data)
        ser.is_valid(raise_exception=True)
        obj, created = EnvSnapshot.objects.get_or_create(
            env_hash     = ser.validated_data["env_hash"], # type: ignore
            machine_arch = ser.validated_data["machine_arch"], # type: ignore
            defaults     = ser.validated_data, # type: ignore
        )
        return Response({"stored": created})
    
@method_decorator(csrf_exempt, name="dispatch")
class BeaconView(APIView):
    def post(self, request):
        try:
            ser = BeaconIn(data=request.data)
            ser.is_valid(raise_exception=True)
            beacon = ser.save()                  

            # Tell the agent whether we still need /env
            need_env = not EnvSnapshot.objects.filter(env_hash=beacon.env_hash).exists() # type: ignore
            
            # Return appropriate status code
            if need_env:
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in BeaconView: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@method_decorator(csrf_exempt, name="dispatch")
class SuggestView(APIView):
    _suggestion_service = None  # Class-level singleton
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use singleton service instance
        if SuggestView._suggestion_service is None:
            SuggestView._suggestion_service = ConfigSuggestionService()
        self.suggestion_service = SuggestView._suggestion_service
    
    def post(self, request):
        """Handle suggestion requests from the error agent client"""
        try:
            error_sig = request.data.get('error_sig')
            env_hash = request.data.get('env_hash')
            use_multiple_clusters = request.data.get('use_multiple_clusters', False)
            format_response = request.data.get('format_response', True)
            
            if not error_sig:
                return Response({"error": "error_sig required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Find configuration suggestions for this error
            if use_multiple_clusters:
                config_suggestion = self.suggestion_service.find_multiple_cluster_suggestions(
                    error_sig=error_sig,
                    error_trace=None  # Client only sends error_sig
                )
            else:
                config_suggestion = self.suggestion_service.find_config_suggestion(
                    error_sig=error_sig,
                    error_trace=None  # Client only sends error_sig
                )
            
            if not config_suggestion:
                return Response({
                    "match": False,
                })
            
            # Ensure config_suggestion is a dictionary
            if not isinstance(config_suggestion, dict):
                print(f"Warning: config_suggestion is not a dict, it's {type(config_suggestion)}")
                return Response({
                    "match": False,
                    "error": "Invalid suggestion format"
                })
            
            # Format multiple suggestions for the client
            suggestions = config_suggestion.get("suggestions", [])
            if not isinstance(suggestions, list):
                print(f"Warning: suggestions is not a list, it's {type(suggestions)}")
                suggestions = []
            
            primary_suggestion = suggestions[0] if suggestions else None
            
            # Safe access to primary suggestion
            recommendation_text = "No specific recommendation available"
            if primary_suggestion and isinstance(primary_suggestion, dict):
                recommendation_text = primary_suggestion.get("suggestion", "No specific recommendation available")
            
            suggestion_data = {
                "match": True,
                "confidence": config_suggestion.get("similarity", 0.0) if "similarity" in config_suggestion else 0.0,  # Handle both single and multiple cluster responses
                "recommendation": recommendation_text,
                "docs": f"Found {len(suggestions)} relevant configuration patterns",
                "all_suggestions": [
                    {
                        "suggestion": suggestion.get("suggestion", ""),
                        "config_key": suggestion.get("config_key", "unknown"),
                        "config_value": suggestion.get("config_value", "unknown"),
                        "confidence_percentage": suggestion.get("confidence_percentage", 0),
                        "significance_score": suggestion.get("significance_score", 0.0)
                    }
                    for suggestion in suggestions
                    if isinstance(suggestion, dict)  # Only process dictionary suggestions
                ]
            }
            
            # Add cluster info if available (for multiple cluster mode)
            if "cluster_info" in config_suggestion:
                cluster_info = config_suggestion["cluster_info"]
                if isinstance(cluster_info, list):
                    suggestion_data["cluster_info"] = cluster_info
                    suggestion_data["clusters_analyzed"] = config_suggestion.get("clusters_analyzed", 1)
            
            if format_response: suggestion_data["formatted_text"] = self._build_formatted_text(suggestion_data)
            return Response(suggestion_data)
        except Exception as e:
            print(f"Error in SuggestView: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _build_formatted_text(self, h: dict) -> str:
        """Turn the JSON payload into a CLI‑friendly multiline string."""
        bar = "─" * 72
        lines = [f"\n{bar}"]
        
        # Safe confidence calculation
        confidence = h.get('confidence', 0.0)
        if confidence is None:
            confidence = 0.0
        lines.append(f"[INFO] corp-error-agent:  {int(confidence*100)}% match")
        
        if docs := h.get("docs"):
            lines.append(f"[INFO] {docs}")
        lines.append(bar)

        # Multi‑cluster summary
        if cinfo := h.get("cluster_info"):
            count = h.get("clusters_analyzed", len(cinfo))
            lines.append(f"[CLUSTERS] Analyzed {count} cluster(s):")
            for idx, c in enumerate(cinfo, 1):
                # Safe similarity calculation
                similarity = c.get("similarity", 0.0)
                if similarity is None:
                    similarity = 0.0
                sim = int(similarity * 100)
                
                cnt = c.get("error_count", "?")
                fs = c.get("first_seen", "unknown")
                ls = c.get("last_seen", "unknown")
                sig = c.get("error_signature", "").strip()
                
                # Format dates if they're datetime objects
                if hasattr(fs, 'strftime'):
                    fs = fs.strftime('%Y-%m-%d %H:%M')
                if hasattr(ls, 'strftime'):
                    ls = ls.strftime('%Y-%m-%d %H:%M')
                
                lines.append(
                    f"  [{idx}] {sim}% similar · {cnt} errors ·"
                    f" {fs} → {ls}\n"
                    f"       signature: {sig}"
                )
            lines.append(bar)

        # All suggestions
        if sugs := h.get("all_suggestions", []):
            lines.append(f"[SUGGESTIONS] Configuration suggestions ({len(sugs)}):")
            for i, sug in enumerate(sugs, 1):
                # Safe dictionary access with defaults
                txt = sug.get("suggestion", "").strip()
                key = sug.get("config_key", "unknown")
                val = sug.get("config_value", "unknown")
                pct = sug.get("confidence_percentage", 0)
                score = sug.get("significance_score", 0.0)
                
                lines.append(
                    f"{i:2}. {txt}\n"
                    f"       -> {key} = {val}  "
                    f"(conf: {pct}%, score: {score:.2f})"
                )
        else:
            # fallback single recommendation
            recommendation = h.get('recommendation', '').strip()
            lines.append(f"[SUGGESTION] {recommendation}")

        lines.append(bar)
        return "\n".join(lines)