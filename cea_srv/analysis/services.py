import pickle
import numpy as np
from analysis.models import ErrorCluster, ConfigPattern
from sentence_transformers import SentenceTransformer

class ConfigSuggestionService:
    _model = None  # Class-level singleton
    
    def __init__(self):
        # Load the model once for the entire class
        if ConfigSuggestionService._model is None:
            try:
                ConfigSuggestionService._model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
            except Exception as e:
                print(f"Error loading SentenceTransformer model: {e}")
                # Set a flag to indicate model loading failed
                ConfigSuggestionService._model = "ERROR"
        self._model = ConfigSuggestionService._model
    
    def find_config_suggestion(self, error_sig, error_trace=None, threshold=0.9, max_suggestions=3):
        """
        Find the most significant configuration patterns for a similar error
        Returns: dict with relevant configuration suggestions or None
        """
        if not error_sig and not error_trace:
            return None
            
        # Use error_sig directly since it's already the last line of the traceback
        error_text = error_sig or "unknown"
            
        if not error_text.strip():
            return None
        
        # Check if model loaded successfully
        if self._model == "ERROR" or self._model is None:
            print("SentenceTransformer model not available")
            return None
            
        # Get all existing clusters with their pre-computed embeddings
        clusters = ErrorCluster.objects.prefetch_related('config_patterns').all()
        
        if not clusters.exists():
            return None
            
        # Encode the new error (only time we need the model)
        try:
            new_error_embedding = self._model.encode([error_text.strip()])[0]
        except Exception as e:
            print(f"Error encoding error text: {e}")
            return None
        
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
            
        # Get multiple significant configuration patterns for this cluster
        significant_patterns = best_match.config_patterns.order_by('-significance_score')[:max_suggestions]
        
        if not significant_patterns.exists():
            return None
            
        # Create suggestions for each significant pattern
        suggestions = []
        for pattern in significant_patterns:
            confidence_percentage = int(pattern.occurrence_rate * 100)
            suggestion_text = self._format_config_suggestion(pattern, confidence_percentage)
            
            suggestions.append({
                'confidence_percentage': confidence_percentage,
                'suggestion': suggestion_text,
                'config_key': pattern.config_key,
                'config_value': pattern.config_value,
                'significance_score': pattern.significance_score,
            })
        
        return {
            'similarity': best_similarity,
            'total_similar_errors': best_match.error_count,
            'suggestions': suggestions,
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
        
        elif config_key.startswith('env_vars.'):
            env_var_name = config_key.replace('env_vars.', '')
            return f"{confidence_percentage}% of similar errors occurred with environment variable {env_var_name}={config_value}. Check if this environment setting is causing the issue."
        
        elif config_key == 'os_info':
            return f"{confidence_percentage}% of similar errors occurred on {config_value}. This may be an OS-specific compatibility issue."
        
        else:
            return f"{confidence_percentage}% of similar errors had {config_key}={config_value} in common. This configuration may be related to the issue."
    
    def find_multiple_cluster_suggestions(self, error_sig, error_trace=None, threshold=0.8, max_clusters=2, max_suggestions_per_cluster=2):
        """
        Find configuration suggestions from multiple similar clusters
        Returns: dict with suggestions from multiple clusters or None
        """
        if not error_sig and not error_trace:
            return None
            
        # Use error_sig directly since it's already the last line of the traceback
        error_text = error_sig or "unknown"
            
        if not error_text.strip():
            return None
        
        # Check if model loaded successfully
        if self._model == "ERROR" or self._model is None:
            print("SentenceTransformer model not available")
            return None
            
        # Get all existing clusters with their pre-computed embeddings
        clusters = ErrorCluster.objects.prefetch_related('config_patterns').all()
        
        if not clusters.exists():
            return None
            
        # Encode the new error (only time we need the model)
        try:
            new_error_embedding = self._model.encode([error_text.strip()])[0]
        except Exception as e:
            print(f"Error encoding error text: {e}")
            return None
        
        # Find multiple similar clusters using pre-computed embeddings
        similar_clusters = []
        
        for cluster in clusters:
            # Load pre-computed embedding
            cluster_embedding = pickle.loads(cluster.embedding)
            
            # Calculate cosine similarity
            similarity = np.dot(new_error_embedding, cluster_embedding) / (
                np.linalg.norm(new_error_embedding) * np.linalg.norm(cluster_embedding)
            )
            
            if similarity >= threshold:
                similar_clusters.append((cluster, similarity))
        
        # Sort by similarity and take top clusters
        similar_clusters.sort(key=lambda x: x[1], reverse=True)
        similar_clusters = similar_clusters[:max_clusters]
        
        if not similar_clusters:
            return None
            
        # Collect suggestions from all similar clusters
        all_suggestions = []
        cluster_info = []
        
        for cluster, similarity in similar_clusters:
            # Get significant patterns for this cluster
            significant_patterns = cluster.config_patterns.order_by('-significance_score')[:max_suggestions_per_cluster]
            
            cluster_suggestions = []
            for pattern in significant_patterns:
                confidence_percentage = int(pattern.occurrence_rate * 100)
                suggestion_text = self._format_config_suggestion(pattern, confidence_percentage)
                
                cluster_suggestions.append({
                    'confidence_percentage': confidence_percentage,
                    'suggestion': suggestion_text,
                    'config_key': pattern.config_key,
                    'config_value': pattern.config_value,
                    'significance_score': pattern.significance_score,
                })
            
            if cluster_suggestions:
                all_suggestions.extend(cluster_suggestions)
                cluster_info.append({
                    'similarity': similarity,
                    'error_count': cluster.error_count,
                    'first_seen': cluster.first_seen,
                    'last_seen': cluster.last_seen,
                    'error_signature': cluster.error_signature
                })
        
        if not all_suggestions:
            return None
            
        # Sort all suggestions by significance score
        all_suggestions.sort(key=lambda x: x['significance_score'], reverse=True)
        
        return {
            'suggestions': all_suggestions,
            'clusters_analyzed': len(cluster_info),
            'cluster_info': cluster_info
        }
    
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