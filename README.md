# AWS Lambda OpenTelemetry with OpenObserve Integration

This project demonstrates how to implement comprehensive observability for AWS Lambda functions using OpenTelemetry and OpenObserve. It includes distributed tracing, custom metrics, and structured logging with automatic instrumentation.

## 🎯 Features

- **Distributed Tracing**: Full request tracing across Lambda functions and external services
- **Custom Metrics**: Performance and business metrics collection
- **Structured Logging**: Detailed logs sent to both CloudWatch and OpenObserve
- **Auto-Instrumentation**: Automatic AWS service instrumentation via OpenTelemetry layer
- **API Gateway Integration**: Complete HTTP request tracing
- **Error Handling**: Comprehensive error tracking and reporting

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- AWS SAM CLI installed
- Node.js 18+ installed
- OpenObserve instance (cloud or self-hosted)

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│   Lambda API     │───▶│  OpenObserve    │
│                 │    │   Function       │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          ▲
                              ▼                          │
                       ┌──────────────────┐              │
                       │   Lambda Demo    │──────────────┘
                       │   Function       │
                       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   CloudWatch     │
                       │   Logs           │
                       └──────────────────┘
```

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Create project directory
mkdir lambda-opentelemetry-openobserve
cd lambda-opentelemetry-openobserve

# Create source directory
mkdir src

# Copy the provided files:
# - template.yaml (SAM template)
# - src/index.js (main Lambda function)
# - src/api.js (API Gateway handler)
# - src/package.json (dependencies)
# - deploy.sh (deployment script)
```

### 2. Configure OpenObserve

Before deployment, ensure you have:
- OpenObserve instance URL
- Valid credentials (username/password)
- Organization name (default: "default")

### 3. Deploy

```bash
# Make deployment script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

The script will:
- Check prerequisites
- Prompt for OpenObserve configuration
- Build and deploy the SAM stack
- Test the deployment
- Provide testing commands

### 4. Manual Deployment (Alternative)

```bash
# Install dependencies
cd src && npm install && cd ..

# Build SAM application
sam build

# Deploy with parameters
sam deploy \
  --guided \
  --parameter-overrides \
    OpenObserveEndpoint="https://your-openobserve-instance.com" \
    OpenObserveUsername="your-username" \
    OpenObservePassword="your-password" \
    OpenObserveOrganization="your-org"
```

## 🧪 Testing

### Test API Endpoint
```bash
# Get API URL from CloudFormation outputs
API_URL=$(aws cloudformation describe-stacks \
  --stack-name lambda-opentelemetry-openobserve-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`DemoApiUrl`].OutputValue' \
  --output text)

# Test the endpoint
curl $API_URL
```

### Invoke Functions Directly
```bash
# Get function names
DEMO_FUNCTION=$(aws cloudformation describe-stacks \
  --stack-name lambda-opentelemetry-openobserve-demo \
  --query 'Stacks[0].Outputs[?OutputKey==`DemoFunctionName`].OutputValue' \
  --output text)

# Invoke demo function
aws lambda invoke \
  --function-name $DEMO_FUNCTION \
  --payload '{"test": "manual invocation"}' \
  response.json
```

### Monitor Logs
```bash
# Watch real-time logs
sam logs --name $DEMO_FUNCTION --tail

# Watch API function logs
sam logs --name $API_FUNCTION --tail
```

## 📊 Observability Features

### Traces
- **Automatic AWS Service Tracing**: DynamoDB, S3, and other AWS services
- **Custom Spans**: Business logic and external API calls
- **Error Tracking**: Automatic exception capture and span status
- **Request Context**: Full request lifecycle tracing

### Metrics
- **Request Counters**: Success/failure rates by function
- **Response Times**: Processing duration histograms
- **Custom Business Metrics**: Application-specific measurements
- **Resource Utilization**: Memory and timeout tracking

### Logs
- **Structured Logging**: JSON formatted logs with metadata
- **Request Correlation**: Logs linked to traces via request ID
- **Multiple Destinations**: CloudWatch and OpenObserve
- **Error Context**: Stack traces and error details

## 🔧 Configuration

### Environment Variables

The following environment variables are automatically configured:

```bash
# OpenTelemetry Configuration
AWS_LAMBDA_EXEC_WRAPPER=/opt/otel-handler
OTEL_LAMBDA_DISABLE_AWS_CONTEXT_PROPAGATION=true
OTEL_PROPAGATORS=tracecontext
OTEL_EXPORTER_OTLP_ENDPOINT=<your-openobserve-endpoint>
OTEL_SERVICE_NAME=lambda-openobserve-demo

# OpenObserve Configuration
OPENOBSERVE_ENDPOINT=<your-openobserve-endpoint>
OPENOBSERVE_USERNAME=<your-username>
OPENOBSERVE_PASSWORD=<your-password>
OPENOBSERVE_ORGANIZATION=<your-organization>
```

### Customization

#### Adding Custom Metrics
```javascript
const meter = metrics.getMeter('my-service', '1.0.0');
const customCounter = meter.createCounter('custom_operations_total');

// Use in your code
customCounter.add(1, { operation: 'business_logic' });
```

#### Custom Spans
```javascript
const span = tracer.startSpan('my_operation');
span.setAttributes({
  'operation.type': 'business_logic',
  'user.id': userId
});

try {
  // Your business logic
  span.setStatus({ code: trace.SpanStatusCode.OK });
} catch (error) {
  span.recordException(error);
  span.setStatus({ 
    code: trace.SpanStatusCode.ERROR, 
    message: error.message 
  });
} finally {
  span.end();
}
```

#### Custom Logs to OpenObserve
```javascript
await sendLogsToOpenObserve({
  level: 'info',
  message: 'Custom operation completed',
  requestId: context.awsRequestId,
  metadata: {
    operation: 'custom_business_logic',
    duration_ms: processingTime,
    user_id: userId
  }
});
```

## 📈 Monitoring in OpenObserve

### Accessing Data

1. **Login to OpenObserve**
   - Navigate to your OpenObserve instance
   - Use your configured credentials

2. **View Traces**
   - Go to Traces section
   - Filter by service: `lambda-openobserve-demo`
   - Explore request flows and dependencies

3. **Query Logs**
   ```sql
   SELECT * FROM default 
   WHERE service = 'lambda-openobserve-demo' 
   ORDER BY timestamp DESC
   ```

4. **Create Dashboards**
   - Response time trends
   - Error rate monitoring
   - Request volume analysis

### Sample Queries

```sql
-- Error rate by function
SELECT 
  function_name,
  COUNT(*) as total_requests,
  SUM(CASE WHEN level = 'error' THEN 1 ELSE 0 END) as errors,
  (SUM(CASE WHEN level = 'error' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as error_rate
FROM default 
WHERE service = 'lambda-openobserve-demo'
GROUP BY function_name;

-- Average response time
SELECT 
  function_name,
  AVG(response_time_ms) as avg_response_time
FROM default 
WHERE service = 'lambda-openobserve-demo' 
  AND response_time_ms IS NOT NULL
GROUP BY function_name;
```

## 🔍 Troubleshooting

### Common Issues

1. **Missing Traces in OpenObserve**
   - Check OpenObserve credentials in environment variables
   - Verify network connectivity from Lambda to OpenObserve
   - Check CloudWatch logs for OTLP export errors

2. **High Cold Start Times**
   - OpenTelemetry layer adds ~500ms to cold starts
   - Consider provisioned concurrency for latency-sensitive functions
   - Monitor via custom metrics

3. **Missing Custom Logs**
   - Verify OpenObserve endpoint configuration
   - Check for authentication errors in CloudWatch logs
   - Ensure organization name is correct

### Debug Commands

```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name lambda-opentelemetry-openobserve-demo

# View function configuration
aws lambda get-function-configuration \
  --function-name <function-name>

# Check layer information
aws lambda list-layers \
  --compatible-runtime nodejs18.x | grep otel
```

## 🧹 Cleanup

```bash
# Delete the CloudFormation stack
aws cloudformation delete-stack \
  --stack-name lambda-opentelemetry-openobserve-demo

# Verify deletion
aws cloudformation describe-stacks \
  --stack-name lambda-opentelemetry-openobserve-demo
```

## 📚 Additional Resources

- [AWS Lambda OpenTelemetry Layer](https://aws-otel.github.io/docs/getting-started/lambda)
- [OpenObserve Documentation](https://openobserve.ai/docs/)
- [OpenTelemetry JavaScript SDK](https://opentelemetry.io/docs/instrumentation/js/)
- [AWS SAM Documentation](https://docs.aws.amazon.com/serverless-application-model/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🏷️ Tags

`aws-lambda` `opentelemetry` `openobserve` `observability` `tracing` `logging` `metrics` `serverless` `sam` `cloudformation`