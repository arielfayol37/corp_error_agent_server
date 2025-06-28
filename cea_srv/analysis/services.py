import pickle
import numpy as np
from analysis.models import ErrorCluster, ConfigPattern
from sentence_transformers import SentenceTransformer

class ConfigSuggestionService:
    def __init__(self):
        # Only load the model when needed for new error encoding
        self._model = None
    
    def find_config_suggestion(self, error_sig, error_trace=None, threshold=0.7):
        """
        Find the most significant configuration pattern for a similar error
        Returns: dict with the most relevant configuration suggestion or None
        """
        if not error_sig and not error_trace:
            return None
            
        # Create error text for comparison
        error_text = ""
        if error_sig:
            error_text += error_sig + " "
        if error_trace:
            error_text += error_trace
            
        if not error_text.strip():
            return None
            
        # Get all existing clusters with their pre-computed embeddings
        clusters = ErrorCluster.objects.prefetch_related('config_patterns').all()
        
        if not clusters.exists():
            return None
            
        # Encode the new error (only time we need the model)
        if self._model is None:
            self._model = SentenceTransformer('all-MiniLM-L6-v2')
        
        new_error_embedding = self._model.encode([error_text.strip()])[0]
        
        # Find the most similar cluster using pre-computed embeddings
        best_match = None
        best_similarity = 0
        
        for cluster in clusters:
            # Load pre-computed embedding
            cluster_embedding = pickle.loads(cluster.embedding)
            
            # Calculate cosine similarity
            similarity = np.dot(new_error_embedding, cluster_embedding) / (
                np.linalg.norm(new_error_embedding) * np.linalg.norm(cluster_embedding)
            )
            
            if similarity > best_similarity and similarity >= threshold:
                best_similarity = similarity
                best_match = cluster
        
        if not best_match:
            return None
            
        # Get the most significant configuration pattern for this cluster
        best_pattern = best_match.config_patterns.order_by('-significance_score').first()
        
        if not best_pattern:
            return None
            
        # Format the suggestion
        confidence_percentage = int(best_similarity * 100)
        
        # Create a human-readable suggestion
        suggestion_text = self._format_config_suggestion(best_pattern, confidence_percentage)
        
        return {
            'similarity': best_similarity,
            'confidence_percentage': confidence_percentage,
            'total_similar_errors': best_match.error_count,
            'suggestion': suggestion_text,
            'config_key': best_pattern.config_key,
            'config_value': best_pattern.config_value,
            'significance_score': best_pattern.significance_score,
            'cluster_info': {
                'first_seen': best_match.first_seen,
                'last_seen': best_match.last_seen,
                'error_signature': best_match.error_signature
            }
        }
    
    def _format_config_suggestion(self, pattern, confidence_percentage):
        """Format the configuration pattern into a human-readable suggestion"""
        config_key = pattern.config_key
        config_value = pattern.config_value
        significance = pattern.significance_score
        
        # Create contextual suggestions based on config type
        if config_key == 'python_ver':
            return f"{confidence_percentage}% of similar errors occurred with Python {config_value}. Consider checking compatibility with this version."
        
        elif config_key == 'machine_arch':
            return f"{confidence_percentage}% of similar errors occurred on {config_value} architecture. This may be an architecture-specific issue."
        
        elif config_key.startswith('packages.'):
            package_name = config_key.replace('packages.', '')
            return f"{confidence_percentage}% of similar errors occurred with {package_name} version {config_value}. Consider updating or downgrading this package."
        
        elif config_key == 'os_info':
            return f"{confidence_percentage}% of similar errors occurred on {config_value}. This may be an OS-specific compatibility issue."
        
        else:
            return f"{confidence_percentage}% of similar errors had {config_key}={config_value} in common. This configuration may be related to the issue."
    
    def get_analysis_stats(self):
        """Get basic statistics about the analysis"""
        total_clusters = ErrorCluster.objects.count()
        total_patterns = ConfigPattern.objects.count()
        
        if total_clusters == 0:
            return None
            
        # Get most significant patterns across all clusters
        top_patterns = ConfigPattern.objects.order_by('-significance_score')[:5]
        
        return {
            'total_error_clusters': total_clusters,
            'total_config_patterns': total_patterns,
            'top_patterns': [
                {
                    'config_key': pattern.config_key,
                    'config_value': pattern.config_value,
                    'significance': pattern.significance_score,
                    'cluster_size': pattern.cluster.error_count
                }
                for pattern in top_patterns
            ]
        } 