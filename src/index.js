// src/index.js
const { trace, metrics, logs } = require('@opentelemetry/api');
const https = require('https');
const AWS = require('aws-sdk');

// Initialize AWS services
const dynamodb = new AWS.DynamoDB.DocumentClient();
const s3 = new AWS.S3();

// Get tracer and meter
const tracer = trace.getTracer('lambda-demo-service', '1.0.0');
const meter = metrics.getMeter('lambda-demo-service', '1.0.0');

// Create custom metrics
const requestCounter = meter.createCounter('demo_requests_total', {
  description: 'Total number of demo requests'
});

const processingDuration = meter.createHistogram('demo_processing_duration_ms', {
  description: 'Duration of demo processing in milliseconds'
});

/**
 * Send custom logs to OpenObserve
 */
async function sendLogsToOpenObserve(logData) {
  const span = tracer.startSpan('send_logs_to_openobserve');
  
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
    
    console.log(`Sending logs to OpenObserve: ${url}`);
    
    const payload = JSON.stringify([{
      timestamp: new Date().toISOString(),
      level: logData.level || 'info',
      message: logData.message,
      service: 'lambda-openobserve-demo',
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
            console.log('Successfully sent logs to OpenObserve');
            resolve(data);
          } else {
            console.error('Failed to send logs to OpenObserve:', res.statusCode, data);
            reject(new Error(`HTTP ${res.statusCode}: ${data}`));
          }
        });
      });

      req.on('error', reject);
      req.write(payload);
      req.end();
    });

    span.setStatus({ code: 1 }); // OK
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
 * Simulate some business logic with OpenTelemetry instrumentation
 */
async function processBusinessLogic(requestId, inputData) {
  const span = tracer.startSpan('process_business_logic');
  const startTime = Date.now();
  
  try {
    // Add span attributes
    span.setAttributes({
      'request.id': requestId,
      'input.type': typeof inputData,
      'input.size': JSON.stringify(inputData).length
    });

    // Simulate DynamoDB operation
    const dbSpan = tracer.startSpan('dynamodb_operation', { parent: span });
    try {
      console.log('Simulating DynamoDB operation...');
      await new Promise(resolve => setTimeout(resolve, 100)); // Simulate DB delay
      
      dbSpan.setAttributes({
        'db.system': 'dynamodb',
        'db.operation': 'put_item',
        'db.table': 'demo-table'
      });
      
      dbSpan.setStatus({ code: 1 }); // OK
    } catch (dbError) {
      dbSpan.recordException(dbError);
      dbSpan.setStatus({ 
        code: 2, // ERROR
        message: dbError.message 
      });
      throw dbError;
    } finally {
      dbSpan.end();
    }

    // Simulate S3 operation
    const s3Span = tracer.startSpan('s3_operation', { parent: span });
    try {
      console.log('Simulating S3 operation...');
      await new Promise(resolve => setTimeout(resolve, 150)); // Simulate S3 delay
      
      s3Span.setAttributes({
        'aws.service': 's3',
        'aws.operation': 'put_object',
        'aws.bucket': 'demo-bucket'
      });
      
      s3Span.setStatus({ code: 1 }); // OK
    } catch (s3Error) {
      s3Span.recordException(s3Error);
      s3Span.setStatus({ 
        code: 2, // ERROR
        message: s3Error.message 
      });
      throw s3Error;
    } finally {
      s3Span.end();
    }

    // Simulate some processing time
    await new Promise(resolve => setTimeout(resolve, 200));

    const processingTime = Date.now() - startTime;
    
    // Record metrics
    requestCounter.add(1, { 
      status: 'success',
      function: process.env.AWS_LAMBDA_FUNCTION_NAME 
    });
    
    processingDuration.record(processingTime, {
      operation: 'business_logic'
    });

    // Send structured log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'info',
      message: 'Business logic processing completed successfully',
      requestId: requestId,
      metadata: {
        processing_time_ms: processingTime,
        input_size: JSON.stringify(inputData).length,
        operations_completed: ['dynamodb', 's3', 'processing']
      }
    });

    span.setAttributes({
      'processing.duration_ms': processingTime,
      'processing.status': 'success'
    });
    
    span.setStatus({ code: 1 }); // OK

    return {
      requestId,
      processingTime,
      result: 'Business logic completed successfully',
      operations: ['dynamodb', 's3', 'processing']
    };
    
  } catch (error) {
    const processingTime = Date.now() - startTime;
    
    // Record error metrics
    requestCounter.add(1, { 
      status: 'error',
      function: process.env.AWS_LAMBDA_FUNCTION_NAME 
    });
    
    // Send error log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'error',
      message: 'Business logic processing failed',
      requestId: requestId,
      metadata: {
        error_message: error.message,
        error_stack: error.stack,
        processing_time_ms: processingTime
      }
    });

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
 * Lambda handler function
 */
exports.handler = async (event, context) => {
  const span = tracer.startSpan('lambda_handler');
  
  try {
    console.log('Lambda function invoked with event:', JSON.stringify(event, null, 2));
    
    // Add span attributes
    span.setAttributes({
      'faas.execution': context.awsRequestId,
      'faas.id': context.functionName,
      'faas.version': context.functionVersion,
      'cloud.account.id': context.invokedFunctionArn.split(':')[4],
      'cloud.region': process.env.AWS_REGION
    });

    // Send startup log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'info',
      message: 'Lambda function invocation started',
      requestId: context.awsRequestId,
      metadata: {
        function_name: context.functionName,
        function_version: context.functionVersion,
        remaining_time_ms: context.getRemainingTimeInMillis(),
        event_source: event.source || 'unknown'
      }
    });

    // Process the business logic
    const result = await processBusinessLogic(context.awsRequestId, event);
    
    // Send completion log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'info',
      message: 'Lambda function execution completed successfully',
      requestId: context.awsRequestId,
      metadata: {
        result: result,
        execution_duration_ms: Date.now() - (context.getRemainingTimeInMillis() ? 
          30000 - context.getRemainingTimeInMillis() : 0)
      }
    });

    const response = {
      statusCode: 200,
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': context.awsRequestId
      },
      body: JSON.stringify({
        message: 'Function executed successfully',
        requestId: context.awsRequestId,
        result: result,
        timestamp: new Date().toISOString()
      })
    };

    span.setAttributes({
      'http.status_code': response.statusCode,
      'lambda.execution.success': true
    });

    span.setStatus({ code: 1 }); // OK
    
    return response;
    
  } catch (error) {
    console.error('Lambda execution error:', error);
    
    // Send error log to OpenObserve
    await sendLogsToOpenObserve({
      level: 'error',
      message: 'Lambda function execution failed',
      requestId: context.awsRequestId,
      metadata: {
        error_message: error.message,
        error_stack: error.stack,
        function_name: context.functionName
      }
    });

    span.recordException(error);
    span.setStatus({ 
      code: 2, // ERROR
      message: error.message 
    });

    const errorResponse = {
      statusCode: 500,
      headers: {
        'Content-Type': 'application/json',
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