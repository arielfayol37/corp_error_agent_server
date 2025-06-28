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
    @csrf_exempt
    def post(self, request):
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

@method_decorator(csrf_exempt, name="dispatch")
class SuggestView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.suggestion_service = ConfigSuggestionService()
    
    @csrf_exempt
    def post(self, request):
        """Handle suggestion requests from the error agent client"""
        error_sig = request.data.get('error_sig')
        env_hash = request.data.get('env_hash')
        
        if not error_sig:
            return Response({"error": "error_sig required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Find configuration suggestion for this error
        config_suggestion = self.suggestion_service.find_config_suggestion(
            error_sig=error_sig,
            error_trace=None  # Client only sends error_sig
        )
        
        if not config_suggestion:
            return Response({"match": False})
        
        # Format response for the client
        return Response({
            "match": True,
            "confidence": config_suggestion["similarity"],
            "recommendation": config_suggestion["suggestion"],
            "docs": f"Config: {config_suggestion['config_key']}={config_suggestion['config_value']} (significance: {config_suggestion['significance_score']:.2f})"
        })
