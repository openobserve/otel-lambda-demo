// src/api.js
const { trace, metrics } = require('@opentelemetry/api');
const https = require('https');

// Get tracer and meter
const tracer = trace.getTracer('lambda-api-service', '1.0.0');
const meter = metrics.getMeter('lambda-api-service', '1.0.0');

// Create metrics
const apiRequestCounter = meter.createCounter('api_requests_total', {
  description: 'Total number of API requests'
});

const apiResponseTime = meter.createHistogram('api_response_time_ms', {
  description: 'API response time in milliseconds'
});

/**
 * Send logs to OpenObserve
 */
async function sendLogsToOpenObserve(logData) {
  const span = tracer.startSpan('send_api_logs_to_openobserve');
  
  try {
    const baseEndpoint = process.env.OPENOBSERVE_BASE_ENDPOINT;
    const username = process.env.OPENOBSERVE_USERNAME;
    const password = process.env.OPENOBSERVE_PASSWORD;
    const organization = process.env.OPENOBSERVE_ORGANIZATION;
    const stream = process.env.OPENOBSERVE_STREAM || 'default';
    
    if (!baseEndpoint || !username || !password || !organization) {
      console.log('OpenObserve credentials not configured, skipping custom log send');
      return;
    }

    const auth = Buffer.from(`${username}:${password}`).toString('base64');
    // Construct URL: https://api.openobserve.ai/api/organization/stream/_json
    const url = `${baseEndpoint}/api/${organization}/${stream}/_json`;
    
    console.log(`Sending API logs to OpenObserve: ${url}`);
    
    const payload = JSON.stringify([{
      timestamp: new Date().toISOString(),
      level: logData.level || 'info',
      message: logData.message,
      service: 'lambda-api-openobserve-demo',
      function_name: process.env.AWS_LAMBDA_FUNCTION_NAME,
      request_id: logData.requestId,
      ...logData.metadata
    }]);

    await new Promise((resolve, reject) => {
      const options = {
        method: 'POST',
        headers: {
          'Authorization': `Basic ${auth}`,
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(payload)
        }
      };

      const req = https.request(url, options, (res) => {
        let data = '';
        res.on('data', (chunk) => data += chunk);
        res.on('end', () => {
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          }
        });
      });

      req.on('error', reject);
      req.write(payload);
      req.end();
    });

    span.setStatus({ code: trace.SpanStatusCode.OK });
  } catch (error) {
    span.recordException(error);
    span.setStatus({ 
      code: 2, // ERROR
      message: error.message 
    });
    console.error('Error sending logs to OpenObserve:', error);
  } finally {
    span.end();
  }
}

/**
 * Simulate external API call
 */
async function callExternalAPI(requestId) {
  const span = tracer.startSpan('external_api_call');
  
  try {
    // Simulate external API call
    console.log('Making external API call...');
    await new Promise(resolve => setTimeout(resolve, 300));
    
    span.setAttributes({
      'http.method': 'GET',
      'http.url': 'https://api.example.com/data',
      'http.status_code': 200,
      'external.service': 'example-api'
    });

    const mockData = {
      id: Math.floor(Math.random() * 1000),
      data: `Sample data for request ${requestId}`,
      timestamp: new Date().toISOString()
    };

    span.setStatus({ code: 1 }); // OK
    return mockData;
    
  } catch (error) {
    span.recordException(error);
    span.setStatus({ 
      code: 2, // ERROR
      message: error.message 
    });
    throw error;
  } finally {
    span.end();
  }
}

/**
 * API Gateway Lambda handler
 */
exports.handler = async (event, context) => {
  const startTime = Date.now();
  const span = tracer.startSpan('api_gateway_handler');
  
  try {
    console.log('API Gateway event:', JSON.stringify(event, null, 2));
    
    // Extract request information
    const method = event.httpMethod;
    const path = event.path;
    const queryParams = event.queryStringParameters || {};
    const headers = event.headers || {};
    const userAgent = headers['User-Agent'] || 'unknown';
    const sourceIp = event.requestContext?.identity?.sourceIp || 'unknown';

    // Add span attributes
    span.setAttributes({
      'http.method': method,
      'http.route': path,
      'http.scheme': 'https',
      'http.user_agent': userAgent,
      'http.client_ip': sourceIp,
      'faas.execution': context.awsRequestId,
      'faas.id': context.functionName,
      'cloud.region': process.env.AWS_REGION
    });

    // Send request log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'info',
      message: 'API request received',
      requestId: context.awsRequestId,
      metadata: {
        http_method: method,
        http_path: path,
        query_params: queryParams,
        user_agent: userAgent,
        source_ip: sourceIp,
        api_gateway_request_id: event.requestContext?.requestId
      }
    });

    // Simulate some business logic
    const externalData = await callExternalAPI(context.awsRequestId);
    
    // Simulate processing
    const processingSpan = tracer.startSpan('process_api_request');
    await new Promise(resolve => setTimeout(resolve, 100));
    processingSpan.setAttributes({
      'processing.type': 'api_business_logic',
      'data.external_id': externalData.id
    });
    processingSpan.end();

    const responseTime = Date.now() - startTime;
    
    // Record metrics
    apiRequestCounter.add(1, {
      method: method,
      path: path,
      status: '200'
    });
    
    apiResponseTime.record(responseTime, {
      method: method,
      path: path
    });

    const response = {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'X-Request-ID': context.awsRequestId,
        'X-Response-Time': `${responseTime}ms`
      },
      body: JSON.stringify({
        message: 'API request processed successfully',
        requestId: context.awsRequestId,
        method: method,
        path: path,
        queryParams: queryParams,
        externalData: externalData,
        responseTime: responseTime,
        timestamp: new Date().toISOString()
      })
    };

    // Send success log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'info',
      message: 'API request processed successfully',
      requestId: context.awsRequestId,
      metadata: {
        response_time_ms: responseTime,
        status_code: 200,
        external_data_id: externalData.id,
        response_size: JSON.stringify(response.body).length
      }
    });

    span.setAttributes({
      'http.status_code': 200,
      'http.response_time_ms': responseTime,
      'api.success': true
    });

    span.setStatus({ code: 1 }); // OK
    
    return response;
    
  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error('API Gateway error:', error);
    
    // Record error metrics
    apiRequestCounter.add(1, {
      method: event.httpMethod,
      path: event.path,
      status: '500'
    });

    // Send error log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'error',
      message: 'API request failed',
      requestId: context.awsRequestId,
      metadata: {
        error_message: error.message,
        error_stack: error.stack,
        response_time_ms: responseTime,
        http_method: event.httpMethod,
        http_path: event.path
      }
    });

    span.recordException(error);
    span.setStatus({ 
      code: trace.SpanStatusCode.ERROR, 
      message: error.message 
    });

    const errorResponse = {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'X-Request-ID': context.awsRequestId
      },
      body: JSON.stringify({
        error: 'Internal server error',
        requestId: context.awsRequestId,
        timestamp: new Date().toISOString()
      })
    };

    return errorResponse;
    
  } finally {
    span.end();
  }
};