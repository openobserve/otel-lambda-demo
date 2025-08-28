# python_src/lambda_function.py
import json
import os
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional
import urllib3
import boto3
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
tracer = trace.get_tracer("python-lambda-demo-service", "1.0.0")
meter = metrics.get_meter("python-lambda-demo-service", "1.0.0")

# Create custom metrics
request_counter = meter.create_counter(
    "demo_requests_total",
    description="Total number of demo requests"
)

processing_duration = meter.create_histogram(
    "demo_processing_duration_ms", 
    description="Duration of demo processing in milliseconds"
)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# HTTP client for OpenObserve
http = urllib3.PoolManager()


class OpenObserveLogger:
    """Custom logger for sending structured logs to OpenObserve"""
    
    def __init__(self):
        self.base_endpoint = os.environ.get('OPENOBSERVE_BASE_ENDPOINT')
        self.username = os.environ.get('OPENOBSERVE_USERNAME') 
        self.password = os.environ.get('OPENOBSERVE_PASSWORD')
        self.organization = os.environ.get('OPENOBSERVE_ORGANIZATION')
        self.stream = os.environ.get('OPENOBSERVE_STREAM', 'default')
        
        # Prepare auth header
        if self.username and self.password:
            import base64
            credentials = f"{self.username}:{self.password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            self.auth_header = f"Basic {encoded_credentials}"
        else:
            self.auth_header = None
    
    def send_logs(self, log_data: Dict[str, Any], request_id: str) -> None:
        """Send structured logs to OpenObserve"""
        span = tracer.start_span("send_logs_to_openobserve")
        
        try:
            if not all([self.base_endpoint, self.username, self.password, self.organization]):
                logger.info("OpenObserve credentials not configured, skipping custom log send")
                return
            
            # Construct URL: https://api.openobserve.ai/api/organization/stream/_json
            url = f"{self.base_endpoint}/api/{self.organization}/{self.stream}/_json"
            
            # Prepare log payload
            log_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": log_data.get("level", "info"),
                "message": log_data.get("message", ""),
                "service": "python-lambda-openobserve-demo",
                "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', ''),
                "request_id": request_id,
                **log_data.get("metadata", {})
            }
            
            payload = json.dumps([log_entry])
            logger.info(f"Sending logs to OpenObserve: {url}")
            
            # Send HTTP request
            response = http.request(
                'POST',
                url,
                body=payload.encode('utf-8'),
                headers={
                    'Authorization': self.auth_header,
                    'Content-Type': 'application/json'
                }
            )
            
            if response.status >= 200 and response.status < 300:
                logger.info("Successfully sent logs to OpenObserve")
                span.set_status(Status(StatusCode.OK))
            else:
                error_msg = f"Failed to send logs to OpenObserve: {response.status} {response.data.decode()}"
                logger.error(error_msg)
                span.set_status(Status(StatusCode.ERROR, error_msg))
                
        except Exception as e:
            error_msg = f"Error sending logs to OpenObserve: {str(e)}"
            logger.error(error_msg)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, error_msg))
        finally:
            span.end()


# Initialize OpenObserve logger
openobserve_logger = OpenObserveLogger()


def simulate_dynamodb_operation(request_id: str) -> Dict[str, Any]:
    """Simulate DynamoDB operation with tracing"""
    span = tracer.start_span("dynamodb_operation")
    
    try:
        span.set_attributes({
            "db.system": "dynamodb",
            "db.operation": "put_item", 
            "db.table": "demo-table",
            "request.id": request_id
        })
        
        logger.info("Simulating DynamoDB operation...")
        # Simulate processing time
        time.sleep(0.1)
        
        # Mock data
        result = {
            "item_id": f"item_{int(time.time())}",
            "request_id": request_id,
            "status": "created"
        }
        
        span.set_attributes({
            "db.item_id": result["item_id"],
            "db.operation.status": "success"
        })
        
        span.set_status(Status(StatusCode.OK))
        return result
        
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


def simulate_s3_operation(request_id: str) -> Dict[str, Any]:
    """Simulate S3 operation with tracing"""
    span = tracer.start_span("s3_operation")
    
    try:
        span.set_attributes({
            "aws.service": "s3",
            "aws.operation": "put_object",
            "aws.bucket": "demo-bucket",
            "request.id": request_id
        })
        
        logger.info("Simulating S3 operation...")
        # Simulate processing time
        time.sleep(0.15)
        
        # Mock data
        result = {
            "object_key": f"logs/{request_id}.json",
            "bucket": "demo-bucket",
            "size": 1024
        }
        
        span.set_attributes({
            "aws.s3.object_key": result["object_key"],
            "aws.s3.object_size": result["size"]
        })
        
        span.set_status(Status(StatusCode.OK))
        return result
        
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


def process_business_logic(request_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process business logic with comprehensive observability"""
    span = tracer.start_span("process_business_logic")
    start_time = time.time()
    
    try:
        # Add span attributes
        span.set_attributes({
            "request.id": request_id,
            "input.type": str(type(input_data).__name__),
            "input.size": len(json.dumps(input_data))
        })
        
        logger.info(f"Processing business logic for request: {request_id}")
        
        # Simulate DynamoDB operation
        db_result = simulate_dynamodb_operation(request_id)
        
        # Simulate S3 operation  
        s3_result = simulate_s3_operation(request_id)
        
        # Additional processing
        time.sleep(0.2)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Record metrics
        request_counter.add(1, {
            "status": "success",
            "function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
        })
        
        processing_duration.record(processing_time, {
            "operation": "business_logic"
        })
        
        # Send structured log to OpenObserve
        openobserve_logger.send_logs({
            "level": "info",
            "message": "Business logic processing completed successfully",
            "metadata": {
                "processing_time_ms": processing_time,
                "input_size": len(json.dumps(input_data)),
                "operations_completed": ["dynamodb", "s3", "processing"],
                "db_result": db_result,
                "s3_result": s3_result
            }
        }, request_id)
        
        span.set_attributes({
            "processing.duration_ms": processing_time,
            "processing.status": "success",
            "operations.count": 3
        })
        
        span.set_status(Status(StatusCode.OK))
        
        return {
            "request_id": request_id,
            "processing_time_ms": processing_time,
            "result": "Business logic completed successfully",
            "operations": ["dynamodb", "s3", "processing"],
            "db_result": db_result,
            "s3_result": s3_result
        }
        
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        
        # Record error metrics
        request_counter.add(1, {
            "status": "error", 
            "function": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
        })
        
        # Send error log to OpenObserve
        openobserve_logger.send_logs({
            "level": "error",
            "message": "Business logic processing failed",
            "metadata": {
                "error_message": str(e),
                "error_traceback": traceback.format_exc(),
                "processing_time_ms": processing_time
            }
        }, request_id)
        
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        
        raise
    finally:
        span.end()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler function"""
    span = tracer.start_span("lambda_handler")
    
    try:
        logger.info(f"Lambda function invoked with event: {json.dumps(event)}")
        
        # Add span attributes
        span.set_attributes({
            "faas.execution": context.aws_request_id,
            "faas.id": context.function_name,
            "faas.version": context.function_version,
            "cloud.account.id": context.invoked_function_arn.split(':')[4] if context.invoked_function_arn else '',
            "cloud.region": os.environ.get('AWS_REGION', '')
        })
        
        # Send startup log to OpenObserve
        openobserve_logger.send_logs({
            "level": "info",
            "message": "Lambda function invocation started",
            "metadata": {
                "function_name": context.function_name,
                "function_version": context.function_version,
                "remaining_time_ms": context.get_remaining_time_in_millis(),
                "event_source": event.get("source", "unknown"),
                "event_size": len(json.dumps(event))
            }
        }, context.aws_request_id)
        
        # Process the business logic
        result = process_business_logic(context.aws_request_id, event)
        
        # Send completion log to OpenObserve
        openobserve_logger.send_logs({
            "level": "info", 
            "message": "Lambda function execution completed successfully",
            "metadata": {
                "result": result,
                "execution_duration_ms": 30000 - context.get_remaining_time_in_millis()
            }
        }, context.aws_request_id)
        
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": context.aws_request_id
            },
            "body": json.dumps({
                "message": "Function executed successfully",
                "requestId": context.aws_request_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        }
        
        span.set_attributes({
            "lambda.execution.success": True,
            "response.status_code": response["statusCode"]
        })
        
        span.set_status(Status(StatusCode.OK))
        
        return response
        
    except Exception as e:
        logger.error(f"Lambda execution error: {str(e)}")
        
        # Send error log to OpenObserve
        openobserve_logger.send_logs({
            "level": "error",
            "message": "Lambda function execution failed", 
            "metadata": {
                "error_message": str(e),
                "error_traceback": traceback.format_exc(),
                "function_name": context.function_name
            }
        }, context.aws_request_id)
        
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        
        error_response = {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "X-Request-ID": context.aws_request_id
            },
            "body": json.dumps({
                "error": "Internal server error",
                "requestId": context.aws_request_id,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        }
        
        return error_response
        
    finally:
        span.end()