# Python AWS Lambda OpenTelemetry with OpenObserve Integration

This project demonstrates comprehensive observability for Python AWS Lambda functions using OpenTelemetry and OpenObserve, including distributed tracing, custom metrics, and structured logging.

## Key Features

- **Distributed Tracing**: Full request tracing using OpenTelemetry Python
- **Custom Structured Logging**: Direct log shipping to OpenObserve
- **Custom Metrics**: Performance and business metrics collection  
- **Auto-Instrumentation**: AWS service instrumentation via OpenTelemetry layer
- **Error Handling**: Comprehensive error tracking and reporting
- **API Gateway Integration**: Complete HTTP request observability

## Project Structure

```
python-lambda-opentelemetry/
├── template.yaml              # SAM template for Python
├── python-deploy.sh          # Deployment script
├── README.md                 # This file
└── python_src/               # Python source code
    ├── lambda_function.py    # Main Lambda function
    ├── api_handler.py        # API Gateway handler
    └── requirements.txt      # Python dependencies
```

## Quick Start

### 1. Setup Project Structure

```bash
# Create project directory
mkdir python-lambda-opentelemetry
cd python-lambda-opentelemetry

# Create Python source directory
mkdir python_src

# Copy the provided files:
# - template.yaml (from python_sam_template artifact)
# - python_src/lambda_function.py (from python_lambda_function artifact)
# - python_src/api_handler.py (from python_api_handler artifact)
# - python_src/requirements.txt (from python_requirements artifact)
# - python-deploy.sh (from python_deploy_script artifact)
```

### 2. Make Deployment Script Executable

```bash
chmod +x python-deploy.sh
```

### 3. Deploy with Interactive Configuration

```bash
# Interactive deployment
./python-deploy.sh

# Or with command line arguments
./python-deploy.sh --profile your-aws-profile --region us-west-2
```

## Configuration Details

### OpenTelemetry Layer
The implementation uses the AWS OpenTelemetry Python layer:
```yaml
Layers:
  - !Sub "arn:aws:lambda:${AWS::Region}:615299751070:layer:AWSOpenTelemetryDistroPython:11"
```

### Environment Variables
```yaml
AWS_LAMBDA_EXEC_WRAPPER: /opt/otel-instrument
OTEL_LAMBDA_DISABLE_AWS_CONTEXT_PROPAGATION: "true"
OTEL_PROPAGATORS: "tracecontext"
OTEL_EXPORTER_OTLP_ENDPOINT: "https://api.openobserve.ai/api/your-org"
OTEL_SERVICE_NAME: "python-lambda-openobserve-demo"
OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED: "true"
```

## Observability Features

### 1. Distributed Tracing
Automatic tracing of:
- Lambda function execution
- AWS service calls (DynamoDB, S3, etc.)
- External HTTP requests
- Custom business logic spans

### 2. Custom Structured Logging
Direct log shipping to OpenObserve with:
- JSON structured format
- Request correlation IDs
- Custom metadata fields
- Error context and stack traces

### 3. Custom Metrics
Business and performance metrics:
- Request counters with labels
- Response time histograms
- Custom business KPIs

## Code Examples

### Custom Span Creation
```python
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("my-service", "1.0.0")

def my_business_function():
    span = tracer.start_span("business_operation")
    try:
        span.set_attributes({
            "operation.type": "data_processing",
            "user.id": user_id
        })
        # Your business logic
        span.set_status(Status(StatusCode.OK))
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
    finally:
        span.end()
```

### Custom Logging to OpenObserve
```python
openobserve_logger.send_logs({
    "level": "info",
    "message": "Operation completed successfully",
    "metadata": {
        "operation": "data_processing",
        "duration_ms": processing_time,
        "records_processed": record_count
    }
}, request_id)
```

### Custom Metrics
```python
from opentelemetry import metrics

meter = metrics.get_meter("my-service", "1.0.0")
counter = meter.create_counter("operations_total")
histogram = meter.create_histogram("processing_duration_ms")

# Usage
counter.add(1, {"operation": "success"})
histogram.record(processing_time, {"operation_type": "data_processing"})
```

## Testing Your Deployment

### 1. Test API Endpoint
```bash
# Get API URL from stack outputs
curl https://your-api-gateway-url/Prod/demo
```

### 2. Test Direct Function Invocation
```bash
aws lambda invoke \
  --function-name python-lambda-opentelemetry-openobserve-demo-python-demo-function \
  --payload '{"test": "manual"}' \
  --cli-binary-format raw-in-base64-out \
  --region us-west-2 \
  response.json
```

### 3. Monitor Logs
```bash
# Watch CloudWatch logs
sam logs --name your-function-name --tail --profile your-profile

# Check response
cat response.json
```

## OpenObserve Integration

### Viewing Data in OpenObserve

1. **Login to OpenObserve**
   - Navigate to your OpenObserve instance
   - Use your configured credentials

2. **View Traces**
   - Go to Traces section
   - Filter by service: `python-lambda-openobserve-demo`

3. **Query Logs**
   ```sql
   SELECT * FROM lambda 
   WHERE service = 'python-lambda-openobserve-demo' 
   ORDER BY timestamp DESC
   ```

4. **Create Dashboards**
   - Response time trends
   - Error rate monitoring
   - Request volume analysis

### Sample OpenObserve Queries

```sql
-- Error analysis
SELECT 
    level,
    COUNT(*) as count,
    function_name
FROM lambda 
WHERE service = 'python-lambda-openobserve-demo'
  AND timestamp > now() - INTERVAL 1 HOUR
GROUP BY level, function_name;

-- Performance monitoring
SELECT 
    function_name,
    AVG(processing_time_ms) as avg_processing_time,
    MAX(processing_time_ms) as max_processing_time
FROM lambda 
WHERE service = 'python-lambda-openobserve-demo'
  AND processing_time_ms IS NOT NULL
  AND timestamp > now() - INTERVAL 1 HOUR
GROUP BY function_name;

-- Request patterns
SELECT 
    DATE_TRUNC('minute', timestamp) as minute,
    COUNT(*) as requests_per_minute,
    AVG(processing_time_ms) as avg_response_time
FROM lambda 
WHERE service = 'python-lambda-openobserve-demo'
  AND timestamp > now() - INTERVAL 1 HOUR
GROUP BY minute
ORDER BY minute;
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - Ensure `requirements.txt` is in `python_src/` directory
   - Check SAM build output for dependency installation

2. **OpenTelemetry Layer Version**
   - Verify layer ARN for your region
   - Latest layers: https://aws-otel.github.io/docs/getting-started/lambda/lambda-python

3. **OpenObserve Connection Issues**
   - Verify credentials and organization name
   - Check CloudWatch logs for HTTP errors
   - Ensure network connectivity from Lambda

### Debug Commands

```bash
# Check Python version in Lambda
aws lambda invoke \
  --function-name your-function-name \
  --payload '{"action": "version_check"}' \
  response.json

# View function configuration
aws lambda get-function-configuration \
  --function-name your-function-name

# List available layers
aws lambda list-layers \
  --compatible-runtime python3.11 | grep -i otel
```

## Performance Considerations

### Cold Start Impact
- OpenTelemetry adds ~200-500ms to cold starts
- Consider provisioned concurrency for latency-sensitive functions
- Monitor cold start metrics in OpenObserve

### Memory Usage
- OpenTelemetry instrumentation adds ~50-100MB memory overhead
- Adjust Lambda memory allocation accordingly
- Monitor memory usage patterns

### Cost Optimization
- Use log sampling for high-volume functions
- Implement intelligent trace sampling
- Configure appropriate log retention

## Advanced Features

### Custom Instrumentation
```python
# Instrument custom libraries
from opentelemetry.instrumentation.requests import RequestsInstrumentor
RequestsInstrumentor().instrument()

# Custom context propagation
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
propagator = TraceContextTextMapPropagator()
```

### Sampling Configuration
```python
# Custom sampling rules
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
sampler = TraceIdRatioBased(0.1)  # Sample 10% of traces
```

## Deployment Commands Reference

```