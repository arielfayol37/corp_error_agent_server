from django.test import TestCase
from django.utils import timezone
from analysis.models import ErrorCluster, ConfigPattern
from analysis.services import ConfigSuggestionService
import pickle
import numpy as np

class ConfigSuggestionServiceTest(TestCase):
    def setUp(self):
        self.service = ConfigSuggestionService()
        
        # Create test clusters with embeddings
        self.cluster1 = ErrorCluster.objects.create(
            cluster_hash="test_cluster_1",
            error_signature="TestError: division by zero",
            error_count=5,
            first_seen=timezone.now(),
            last_seen=timezone.now(),
            embedding=pickle.dumps(np.random.rand(384))  # Mock embedding
        )
        
        self.cluster2 = ErrorCluster.objects.create(
            cluster_hash="test_cluster_2", 
            error_signature="TestError: module not found",
            error_count=3,
            first_seen=timezone.now(),
            last_seen=timezone.now(),
            embedding=pickle.dumps(np.random.rand(384))  # Mock embedding
        )
        
        # Create config patterns for cluster1
        ConfigPattern.objects.create(
            cluster=self.cluster1,
            config_key="python_ver",
            config_value="3.8",
            occurrence_rate=0.8,
            global_rate=0.3,
            significance_score=2.67
        )
        
        ConfigPattern.objects.create(
            cluster=self.cluster1,
            config_key="packages.numpy",
            config_value="1.19.0",
            occurrence_rate=0.6,
            global_rate=0.2,
            significance_score=3.0
        )
        
        # Create config patterns for cluster2
        ConfigPattern.objects.create(
            cluster=self.cluster2,
            config_key="machine_arch",
            config_value="x86_64",
            occurrence_rate=0.9,
            global_rate=0.4,
            significance_score=2.25
        )
    
    def test_find_config_suggestion_returns_multiple_patterns(self):
        """Test that find_config_suggestion returns multiple patterns when available"""
        # Mock the model to return a predictable embedding
        mock_embedding = np.random.rand(384)
        self.service._model.encode = lambda x: [mock_embedding]
        
        # Set the cluster embedding to be similar to our mock
        self.cluster1.embedding = pickle.dumps(mock_embedding)
        self.cluster1.save()
        
        result = self.service.find_config_suggestion(
            error_sig="TestError: division by zero",
            threshold=0.1,  # Low threshold to ensure match
            max_suggestions=3
        )
        
        self.assertIsNotNone(result)
        self.assertIn('suggestions', result)
        self.assertGreaterEqual(len(result['suggestions']), 2)  # Should have both patterns
        
        # Check that suggestions are sorted by significance score
        significance_scores = [s['significance_score'] for s in result['suggestions']]
        self.assertEqual(significance_scores, sorted(significance_scores, reverse=True))
    
    def test_find_multiple_cluster_suggestions(self):
        """Test that find_multiple_cluster_suggestions works correctly"""
        # Mock the model to return a predictable embedding
        mock_embedding = np.random.rand(384)
        self.service._model.encode = lambda x: [mock_embedding]
        
        # Set both cluster embeddings to be similar to our mock
        self.cluster1.embedding = pickle.dumps(mock_embedding)
        self.cluster1.save()
        self.cluster2.embedding = pickle.dumps(mock_embedding)
        self.cluster2.save()
        
        result = self.service.find_multiple_cluster_suggestions(
            error_sig="TestError: some error",
            threshold=0.1,  # Low threshold to ensure matches
            max_clusters=2,
            max_suggestions_per_cluster=2
        )
        
        self.assertIsNotNone(result)
        self.assertIn('suggestions', result)
        self.assertIn('clusters_analyzed', result)
        self.assertIn('cluster_info', result)
        
        # Should have suggestions from both clusters
        self.assertGreaterEqual(len(result['suggestions']), 3)  # At least 3 total patterns
        self.assertEqual(result['clusters_analyzed'], 2)
    
    def test_no_suggestions_when_no_patterns(self):
        """Test that service returns None when no patterns exist"""
        # Create cluster without patterns
        empty_cluster = ErrorCluster.objects.create(
            cluster_hash="empty_cluster",
            error_signature="EmptyError",
            error_count=1,
            first_seen=timezone.now(),
            last_seen=timezone.now(),
            embedding=pickle.dumps(np.random.rand(384))
        )
        
        # Mock the model
        mock_embedding = np.random.rand(384)
        self.service._model.encode = lambda x: [mock_embedding]
        empty_cluster.embedding = pickle.dumps(mock_embedding)
        empty_cluster.save()
        
        result = self.service.find_config_suggestion(
            error_sig="EmptyError",
            threshold=0.1
        )
        
        self.assertIsNone(result)
    
    def test_package_parsing(self):
        """Test that package parsing works correctly with different formats"""
        from analysis.management.commands.run_analysis import Command
        
        command = Command()
        
        # Test dict format
        dict_packages = {
            "numpy": "1.19.0",
            "pandas": "1.3.0"
        }
        parsed = command._parse_packages(dict_packages)
        self.assertEqual(parsed, dict_packages)
        
        # Test list format with ==
        list_packages = [
            "build==1.2.2.post1",
            "certifi==2025.6.15",
            "numpy==2.2.6",
            "requests==2.32.4"
        ]
        parsed = command._parse_packages(list_packages)
        expected = {
            "build": "1.2.2.post1",
            "certifi": "2025.6.15", 
            "numpy": "2.2.6",
            "requests": "2.32.4"
        }
        self.assertEqual(parsed, expected)
        
        # Test list format with other operators
        list_packages_ops = [
            "numpy>=1.19.0",
            "pandas<=1.3.0",
            "requests>2.0.0",
            "urllib3<2.0.0"
        ]
        parsed = command._parse_packages(list_packages_ops)
        expected = {
            "numpy": ">=1.19.0",
            "pandas": "<=1.3.0",
            "requests": ">2.0.0",
            "urllib3": "<2.0.0"
        }
        self.assertEqual(parsed, expected)
        
        # Test empty/None cases
        self.assertEqual(command._parse_packages(None), {})
        self.assertEqual(command._parse_packages([]), {})
        self.assertEqual(command._parse_packages({}), {})
