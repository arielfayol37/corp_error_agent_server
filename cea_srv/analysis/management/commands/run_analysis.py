from django.core.management.base import BaseCommand
from telemetry.models import Beacon, EnvSnapshot
from analysis.models import ErrorCluster, ConfigPattern, ErrorAnalysis
from django.db.models import Count, Q, F
import json, math, hashlib, time, pickle
from sentence_transformers import SentenceTransformer
import sklearn.cluster
import numpy as np
from collections import defaultdict
import re

class Command(BaseCommand):
    help = "Nightly error clustering & configuration pattern analysis"

    def _parse_packages(self, packages):
        """
        Parse packages from either dict or list format
        Returns: dict of {package_name: version}
        """
        if not packages:
            return {}
        
        if isinstance(packages, dict):
            # Already in the right format
            return packages
        
        elif isinstance(packages, list):
            # Parse list format like ["build==1.2.2.post1", "certifi==2025.6.15", ...]
            parsed_packages = {}
            for pkg_spec in packages:
                if isinstance(pkg_spec, str) and '==' in pkg_spec:
                    # Handle "package==version" format
                    parts = pkg_spec.split('==', 1)
                    if len(parts) == 2:
                        pkg_name, pkg_version = parts
                        parsed_packages[pkg_name] = pkg_version
                elif isinstance(pkg_spec, str) and '>=' in pkg_spec:
                    # Handle "package>=version" format
                    parts = pkg_spec.split('>=', 1)
                    if len(parts) == 2:
                        pkg_name, pkg_version = parts
                        parsed_packages[pkg_name] = f">={pkg_version}"
                elif isinstance(pkg_spec, str) and '<=' in pkg_spec:
                    # Handle "package<=version" format
                    parts = pkg_spec.split('<=', 1)
                    if len(parts) == 2:
                        pkg_name, pkg_version = parts
                        parsed_packages[pkg_name] = f"<={pkg_version}"
                elif isinstance(pkg_spec, str) and '>' in pkg_spec:
                    # Handle "package>version" format
                    parts = pkg_spec.split('>', 1)
                    if len(parts) == 2:
                        pkg_name, pkg_version = parts
                        parsed_packages[pkg_name] = f">{pkg_version}"
                elif isinstance(pkg_spec, str) and '<' in pkg_spec:
                    # Handle "package<version" format
                    parts = pkg_spec.split('<', 1)
                    if len(parts) == 2:
                        pkg_name, pkg_version = parts
                        parsed_packages[pkg_name] = f"<{pkg_version}"
                elif isinstance(pkg_spec, str):
                    # Just package name without version
                    parsed_packages[pkg_spec] = "unknown"
            
            return parsed_packages
        
        return {}

    def handle(self, *args, **opts):
        start_time = time.time()
        self.stdout.write("Starting error analysis...")
        
        # Get all error beacons with their environment data
        error_beacons = Beacon.objects.filter(kind='error').select_related()
        
        if not error_beacons.exists():
            self.stdout.write("No error data to analyze")
            return
            
        total_beacons = error_beacons.count()
        self.stdout.write(f"Found {total_beacons} total error beacons")
        
        # Extract error signatures and get environment data
        error_texts = []
        beacon_env_data = []
        
        # Deduplicate beacons: same error_sig + env_hash = same error occurrence
        seen_errors = set()
        duplicates_filtered = 0
        
        for beacon in error_beacons:
            # Create unique key for this error + environment combination
            error_key = f"{beacon.error_sig or ''}:{beacon.env_hash}"
            
            if error_key in seen_errors:
                # Skip duplicate error from same environment
                duplicates_filtered += 1
                continue
            seen_errors.add(error_key)
            
            # Use error_sig directly since it's already the last line of the traceback
            text = beacon.error_sig or "unknown"
            
            if text.strip():
                error_texts.append(text.strip())
                
                # Get environment data for this beacon
                try:
                    env = EnvSnapshot.objects.get(env_hash=beacon.env_hash)
                    beacon_env_data.append({
                        'beacon': beacon,
                        'text': text.strip(),
                        'env': env
                    })
                except EnvSnapshot.DoesNotExist:
                    # Skip if no environment data
                    continue
        
        if not beacon_env_data:
            self.stdout.write("No error data with environment information")
            return
            
        self.stdout.write(f"Filtered out {duplicates_filtered} duplicate beacons")
        self.stdout.write(f"Processing {len(beacon_env_data)} unique errors")
        
        # Clear old analysis data
        ErrorCluster.objects.all().delete()
        ConfigPattern.objects.all().delete()
            
        # Automatic clustering using DBSCAN
        try:
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = model.encode(error_texts)
            
            # DBSCAN clustering
            clustering = sklearn.cluster.DBSCAN(
                eps=0.3,
                min_samples=2,
                metric='cosine'
            )
            cluster_labels = clustering.fit_predict(embeddings)
            
            # Process clusters and store embeddings
            clusters_created = 0
            patterns_created = 0
            
            # Calculate global configuration statistics
            global_config_stats = self._calculate_global_config_stats()
            
            for cluster_id in set(cluster_labels):
                if cluster_id == -1:  # Skip noise points
                    continue
                    
                # Get all beacons in this cluster
                cluster_data = [
                    beacon_env_data[i] 
                    for i, label in enumerate(cluster_labels) 
                    if label == cluster_id
                ]
                
                if len(cluster_data) < 2:
                    continue
                
                # Create cluster hash and store embedding
                representative_sig = cluster_data[0]['beacon'].error_sig or "Unknown Error"
                cluster_hash = hashlib.sha256(representative_sig.encode()).hexdigest()[:32]
                
                # Store the embedding for this cluster
                cluster_embedding = embeddings[error_texts.index(cluster_data[0]['text'])]
                embedding_bytes = pickle.dumps(cluster_embedding)
                
                # Calculate cluster statistics
                error_count = len(cluster_data)
                first_seen = min(data['beacon'].ts for data in cluster_data)
                last_seen = max(data['beacon'].ts for data in cluster_data)
                
                # Create ErrorCluster
                cluster_obj = ErrorCluster.objects.create(
                    cluster_hash=cluster_hash,
                    error_signature=representative_sig[:500],
                    error_count=error_count,
                    first_seen=first_seen,
                    last_seen=last_seen,
                    embedding=embedding_bytes
                )
                clusters_created += 1
                
                # Analyze configuration patterns for this cluster
                cluster_patterns = self._analyze_cluster_config_patterns(
                    cluster_data, global_config_stats, cluster_obj
                )
                patterns_created += len(cluster_patterns)
                    
        except Exception as e:
            self.stdout.write(f"Error during analysis: {e}")
            return
            
        # Record analysis results
        analysis_duration = time.time() - start_time
        ErrorAnalysis.objects.create(
            total_errors_analyzed=len(beacon_env_data),
            clusters_found=clusters_created,
            patterns_found=patterns_created,
            analysis_duration=analysis_duration
        )
        
        self.stdout.write(f"Analysis complete!")
        self.stdout.write(f"  - Analyzed {len(beacon_env_data)} unique errors (deduplicated)")
        self.stdout.write(f"  - Created {clusters_created} clusters")
        self.stdout.write(f"  - Found {patterns_created} significant config patterns")
        self.stdout.write(f"  - Duration: {analysis_duration:.2f} seconds")
    
    def _calculate_global_config_stats(self):
        """Calculate global configuration statistics across all environments"""
        all_envs = EnvSnapshot.objects.all()
        total_envs = all_envs.count()
        
        if total_envs == 0:
            return {}
        
        config_stats = defaultdict(lambda: defaultdict(int))
        
        for env in all_envs:
            # Python version
            config_stats['python_ver'][env.python_ver] += 1
            
            # Machine architecture
            config_stats['machine_arch'][env.machine_arch] += 1
            
            # OS info
            config_stats['os_info'][env.os_info] += 1
            
            # Package versions - parse both dict and list formats
            parsed_packages = self._parse_packages(env.packages)
            for pkg_name, pkg_version in parsed_packages.items():
                config_stats[f'packages.{pkg_name}'][str(pkg_version)] += 1
            
            # Environment variables - parse JSON field
            env_vars = env.env_vars
            if env_vars and isinstance(env_vars, dict):
                for env_var_name, env_var_value in env_vars.items():
                    # Skip very long values or sensitive data
                    if len(str(env_var_value)) > 200:
                        continue
                    # Skip common sensitive environment variables
                    if env_var_name.lower() in ['password', 'secret', 'key', 'token', 'auth']:
                        continue
                    config_stats[f'env_vars.{env_var_name}'][str(env_var_value)] += 1
        
        # Convert to rates
        global_rates = {}
        for config_key, value_counts in config_stats.items():
            global_rates[config_key] = {}
            for value, count in value_counts.items():
                global_rates[config_key][value] = count / total_envs
        
        return global_rates
    
    def _analyze_cluster_config_patterns(self, cluster_data, global_stats, cluster_obj):
        """Find configuration patterns that are statistically significant in this cluster"""
        patterns = []
        cluster_size = len(cluster_data)
        
        # Collect configuration data for this cluster
        cluster_configs = defaultdict(lambda: defaultdict(int))
        
        for data in cluster_data:
            env = data['env']
            
            # Python version
            cluster_configs['python_ver'][env.python_ver] += 1
            
            # Machine architecture
            cluster_configs['machine_arch'][env.machine_arch] += 1
            
            # OS info
            cluster_configs['os_info'][env.os_info] += 1
            
            # Package versions - parse both dict and list formats
            parsed_packages = self._parse_packages(env.packages)
            for pkg_name, pkg_version in parsed_packages.items():
                cluster_configs[f'packages.{pkg_name}'][str(pkg_version)] += 1
            
            # Environment variables - parse JSON field
            env_vars = env.env_vars
            if env_vars and isinstance(env_vars, dict):
                for env_var_name, env_var_value in env_vars.items():
                    # Skip very long values or sensitive data
                    if len(str(env_var_value)) > 200:
                        continue
                    # Skip common sensitive environment variables
                    if env_var_name.lower() in ['password', 'secret', 'key', 'token', 'auth']:
                        continue
                    cluster_configs[f'env_vars.{env_var_name}'][str(env_var_value)] += 1
        
        # Calculate significance scores
        for config_key, value_counts in cluster_configs.items():
            for value, count in value_counts.items():
                occurrence_rate = count / cluster_size
                
                # Get global rate for this config value
                # Default to 1% if not found globally - this ensures we can detect rare configurations
                global_rate = global_stats.get(config_key, {}).get(value, 0.01)
                
                # Calculate significance (how much more common this is in the cluster vs globally)
                # A high significance score means this config is much more common in error clusters
                significance_score = occurrence_rate / global_rate
                
                # Only store patterns that are significantly more common in this cluster
                if significance_score > 1.5 and occurrence_rate > 0.65:  # 50% more common and appears in 65%+ of cluster
                    ConfigPattern.objects.create(
                        cluster=cluster_obj,
                        config_key=config_key,
                        config_value=value,
                        occurrence_rate=occurrence_rate,
                        global_rate=global_rate,
                        significance_score=significance_score
                    )
                    patterns.append({
                        'config_key': config_key,
                        'config_value': value,
                        'significance': significance_score
                    })
        
        return patterns