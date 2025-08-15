# Feature Flag Service (Local)

This problem requires designing an in-process feature flag (also known as a feature toggle) system. This service allows developers to modify system behavior without changing code, enabling practices like canary releases, A/B testing, and trunk-based development by decoupling feature deployment from code deployment.

### **1. System Overview & Scope Clarification**

We are building a library or component that an application can use to check if a feature is enabled for a given context (e.g., a specific user or request). The configuration for these flags will be loaded from a local source (like a JSON file) and must be reloadable at runtime without an application restart ("hot-reloading").

### **2. Detailed Design**

#### **2.1. Feature Flag Structure**

Each feature flag will have the following attributes:

- **Name**: A unique identifier for the feature flag.
- **Enabled**: A boolean indicating if the feature is enabled.
- **Rollout Percentage**: An optional field to specify a percentage of users for gradual rollouts.
- **Conditions**: Optional rules based on user attributes or request parameters.

#### **2.2. Configuration Storage**

Feature flags will be stored in a local JSON file with the following structure:

```json
{
  "featureFlags": [
    {
      "name": "newFeature",
      "enabled": true,
      "rolloutPercentage": 50,
      "conditions": {
        "userId": "12345"
      }
    }
  ]
}
```

The configuration file must be specified at service startup and cannot be changed without restarting the service.

#### **2.3. API**

The service will provide the following API:

- `isFeatureEnabled(featureName, context)`: Returns a boolean indicating if the feature is enabled for the given context.
- `getAllFeatures()`: Returns a list of all feature flags and their statuses.

#### **2.4. Hot-reloading**

The service will watch the configuration file for changes and automatically reload the feature flags without requiring a restart. This will be done using file system notifications.

### **3. Implementation**

#### **3.1. Data Structures**

```python
class FeatureFlag:
    def __init__(self, name, enabled, rollout_percentage=None, conditions=None):
        self.name = name
        self.enabled = enabled
        self.rollout_percentage = rollout_percentage
        self.conditions = conditions or {}

class FeatureFlagService:
    def __init__(self, config_file):
        self.config_file = config_file
        self.feature_flags = {}
        self.load_flags()

    def load_flags(self):
        with open(self.config_file, 'r') as f:
            config = json.load(f)
            for flag in config['featureFlags']:
                self.feature_flags[flag['name']] = FeatureFlag(**flag)
```

#### **3.2. API Implementation**

```python
from flask import Flask, request, jsonify

app = Flask(__name__)
service = FeatureFlagService('path/to/config.json')

@app.route('/feature-flag/<feature_name>', methods=['GET'])
def is_feature_enabled(feature_name):
    context = request.args.to_dict()
    enabled = service.is_feature_enabled(feature_name, context)
    return jsonify({"enabled": enabled})

@app.route('/feature-flags', methods=['GET'])
def get_all_features():
    flags = service.get_all_features()
    return jsonify(flags)
```

#### **3.3. Hot-reloading Implementation**

```python
import os
import time

class FeatureFlagService:
    # ... existing methods ...

    def watch_config_file(self):
        last_mtime = os.path.getmtime(self.config_file)
        while True:
            time.sleep(1)
            current_mtime = os.path.getmtime(self.config_file)
            if current_mtime != last_mtime:
                last_mtime = current_mtime
                self.load_flags()

    def start(self):
        import threading
        threading.Thread(target=self.watch_config_file, daemon=True).start()
```

### **4. Testing**

#### **4.1. Unit Tests**

- Test loading feature flags from the configuration file.
- Test the `is_feature_enabled` and `get_all_features` methods.
- Test the hot-reloading functionality.

#### **4.2. Integration Tests**

- Test the API endpoints with different scenarios (feature enabled/disabled, user in/out of rollout percentage, etc.).

### **5. Deployment**

- Package the service as a Docker container.
- Mount the configuration file as a read-only volume.
- Ensure the service has permission to read the configuration file and access the file system notifications.

### **6. Monitoring & Logging**

- Integrate with a logging framework to log feature flag evaluations and configuration reloads.
- Expose metrics (e.g., number of times a feature is enabled/disabled) to a monitoring system.

### **7. Security Considerations**

- Validate and sanitize all inputs to the API to prevent injection attacks.
- Ensure the configuration file is not accessible from the outside world and is protected from unauthorized access.

### **8. Future Enhancements**

- Support for nested conditions and more complex rules for feature enablement.
- Integration with a remote configuration service as an alternative to the local JSON file.
- A web-based dashboard for real-time monitoring and management of feature flags.
