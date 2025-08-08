# Telemetry - Error Analysis & Configuration Suggestion System

A Django-based telemetry system that collects error data from Python applications, performs intelligent clustering analysis, and provides configuration-based error resolution suggestions.

> **⚠️ Development Version**: This is a development/prototype version of the telemetry system. For production deployments, see the [Production Considerations](#production-considerations) section below.

## 🎯 Overview

This system helps developers quickly identify and resolve configuration-related errors by:

1. **Collecting telemetry data** from Python applications (environment snapshots and error beacons)
2. **Clustering similar errors** using machine learning (sentence embeddings + DBSCAN)
3. **Analyzing configuration patterns** that correlate with specific error types
4. **Providing intelligent suggestions** for configuration changes that may resolve errors

## 🏗️ Architecture

### Core Components

- **Telemetry App** (`telemetry/`): Handles data collection and API endpoints
- **Analysis App** (`analysis/`): Performs error clustering and pattern analysis
- **Django REST Framework**: Provides RESTful API endpoints
- **Sentence Transformers**: Generates embeddings for error similarity matching
- **Scikit-learn**: Performs DBSCAN clustering on error embeddings

### Data Models

#### Telemetry Models (`telemetry/models.py`)
- **EnvSnapshot**: Stores environment information (Python version, packages, OS, etc.)
- **Beacon**: Records error occurrences with signatures and traces

#### Analysis Models (`analysis/models.py`)
- **ErrorCluster**: Represents clusters of similar errors with pre-computed embeddings
- **ConfigPattern**: Stores statistically significant configuration patterns for error clusters
- **ErrorAnalysis**: Tracks analysis run statistics

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip
- SQLite (included with Python) or PostgreSQL (recommended for production)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd telemetry
   ```

2. **Install dependencies**
   ```bash
   cd cea_srv
   pip install -r requirements.txt
   ```

3. **Run migrations**
   ```bash
   python manage.py migrate
   ```

4. **Start the development server**
   ```bash
   python manage.py runserver
   ```

The API will be available at `http://localhost:8000/`





## 📡 API Endpoints

### Environment Data Collection

**POST** `/env`
```json
{
  "env_hash": "abc123def456",
  "machine_arch": "x86_64",
  "packages": {
    "numpy": "1.24.0",
    "pandas": "2.0.0"
  },
  "python_ver": "3.9.0",
  "os_info": "Linux-5.4.0-x86_64",
  "env_vars": {
    "PYTHONPATH": "/usr/local/lib/python3.9"
  }
}
```

### Error Beacon Submission

**POST** `/beacon`
```json
{
  "kind": "error",
  "env_hash": "abc123def456",
  "script_id": "script123",
  "error_sig": "ModuleNotFoundError: No module named 'numpy'",
  "trace": "Traceback (most recent call last):...",
  "ts": "2024-01-15T10:30:00Z"
}
```

### Configuration Suggestions

**POST** `/suggest`
```json
{
  "error_sig": "ModuleNotFoundError: No module named 'numpy'",
  "env_hash": "abc123def456",
  "use_multiple_clusters": false,
  "format_response": true
}
```

**Response:**
```json
{
  "match": true,
  "confidence": 0.95,
  "recommendation": "95% of similar errors occurred with numpy version 1.24.0. Consider updating or downgrading this package.",
  "docs": "Found 3 relevant configuration patterns",
  "all_suggestions": [
    {
      "suggestion": "95% of similar errors occurred with numpy version 1.24.0. Consider updating or downgrading this package.",
      "config_key": "packages.numpy",
      "config_value": "1.24.0",
      "confidence_percentage": 95,
      "significance_score": 3.2
    }
  ]
}
```

## 🔧 Analysis System

### Running Error Analysis

The system includes a management command to perform nightly error clustering and pattern analysis:

```bash
python manage.py run_analysis
```

This command:
1. **Clusters similar errors** using DBSCAN on sentence embeddings
2. **Analyzes configuration patterns** that correlate with error clusters
3. **Calculates significance scores** for configuration suggestions
4. **Stores results** for fast lookup during suggestion requests

### Analysis Process

1. **Error Deduplication**: Filters duplicate errors from the same environment
2. **Embedding Generation**: Uses SentenceTransformer to create error embeddings
3. **Clustering**: Groups similar errors using DBSCAN with cosine similarity
4. **Pattern Analysis**: Identifies configuration patterns that are statistically significant in error clusters
5. **Significance Scoring**: Calculates how much more common configurations are in error clusters vs. globally

## 🧪 Testing

A test script is included to verify package parsing functionality:

```bash
python test_package_parsing.py
```

This tests the package parsing logic that handles various package specification formats:
- Dictionary format: `{"numpy": "1.24.0"}`
- List format: `["numpy==1.24.0", "pandas>=2.0.0"]`
- Various operators: `==`, `>=`, `<=`, `>`, `<`

## 📊 Configuration Suggestion Types

The system provides contextual suggestions based on configuration type:

- **Python Version**: Compatibility issues with specific Python versions
- **Machine Architecture**: Architecture-specific problems
- **Package Versions**: Version conflicts or compatibility issues
- **Environment Variables**: Environment-specific configuration problems
- **OS Information**: Operating system compatibility issues

## 🔒 Security Considerations

- **CSRF Exempt**: API endpoints are CSRF exempt for client integration
- **Sensitive Data Filtering**: Environment variables with sensitive names are filtered out
- **Data Length Limits**: Very long configuration values are truncated
- **Error Handling**: Comprehensive error handling with detailed logging

## 🛠️ Development

### Project Structure
```
telemetry/
├── cea_srv/                    # Django project
│   ├── analysis/               # Error analysis and clustering
│   │   ├── management/commands/  # Django management commands
│   │   ├── models.py            # Analysis data models
│   │   └── services.py          # Configuration suggestion service
│   ├── telemetry/               # Data collection and API
│   │   ├── models.py           # Telemetry data models
│   │   ├── serializers.py      # API serializers
│   │   ├── views.py            # API endpoints
│   │   └── urls.py             # URL routing
│   ├── cea_srv/                # Django project settings
│   │   ├── settings.py         # Django configuration
│   │   └── urls.py             # Main URL routing
│   └── manage.py               # Django management script
└── test_package_parsing.py     # Package parsing tests
```

### Key Dependencies

#### Core Dependencies
- **Django 4.2+**: Web framework
- **Django REST Framework 3.14+**: API framework
- **Sentence Transformers 2.2+**: Text embedding generation
- **Scikit-learn 1.3+**: Machine learning clustering
- **NumPy 1.24+**: Numerical computing

#### Suggested Production Dependencies
- **PostgreSQL**: Replace SQLite for better performance
- **Redis**: Add caching layer for frequently accessed data
- **Celery**: Background task processing for analysis jobs
- **Gunicorn**: Production WSGI server instead of Django's development server

### Development Workflow

1. **Set up development environment**
   ```bash
   # Local development
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run tests**
   ```bash
   python test_package_parsing.py
   python manage.py test
   ```

3. **Run analysis**
   ```bash
   python manage.py run_analysis
   ```

4. **Monitor logs**
   ```bash
   # Local development
   tail -f logs/django.log
   ```

## 📈 Performance

- **Pre-computed Embeddings**: Error cluster embeddings are stored for fast similarity search
- **Database Indexing**: Optimized database indexes for query performance
- **Singleton Services**: ML models are loaded once and reused

⚠️ **Current limitations:** SQLite database, in-memory embedding storage, sequential processing

## 🏭 Production Considerations

This is a weekend project designed for development and learning. For production use, consider:

- **Vector Database**: Replace in-database embeddings with Pinecone/Weaviate
- **Production Database**: PostgreSQL with Redis caching
- **Containerization**: Docker/Kubernetes for deployment
- **Async Processing**: Celery for background analysis
- **Security**: Authentication, rate limiting, encryption
- **Monitoring**: Prometheus/Grafana for observability

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the existing issues
2. Create a new issue with detailed information
3. Include error logs and environment details



---

**⚠️ Development Version**: This is a weekend project designed for development and learning purposes. It uses SQLite and basic Django development server. For production use, implement the suggested improvements outlined above and ensure proper security measures, data retention policies, and monitoring are in place.
