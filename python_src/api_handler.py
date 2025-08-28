# python_src/api_handler.py
import json
import os
import time
import logging
import traceback
from datetime import datetime
from typing import Dict, Any
import urllib3
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenTelemetry
tracer = trace.get_tracer("python-lambda-api-service", "1.0.0")
meter = metrics.get_meter("python-lambda-api-service", "1.0.0")

# Create custom metrics
api_request_counter = meter.create_counter(
    "api_requests_total",
    description="Total number of API requests"
)

api_response_time = meter.create_histogram(
    "api_response_time_ms",
    description="API response time in milliseconds"
)

# HTTP client for external calls and OpenObserve
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
        span = tracer.start_span("send_api_logs_to_openobserve")
        
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
                "service": "python-lambda-api-openobserve-demo",
                "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', ''),
                "request_id": request_id,
                **log_data.get("metadata", {})
            }
            
            payload = json.dumps([log_entry])
            logger.info(f"Sending API logs to OpenObserve: {url}")
            
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


def call_external_api(request_id: str) -> Dict[str, Any]:
    """Simulate external API call with tracing"""
    span = tracer.start_span("external_api_call")
    
    try:
        span.set_attributes({
            "http.method": "GET",
            "http.url": "https://api.example.com/data",
            "external.service": "example-api",
            "request.id": request_id
        })
        
        logger.info("Making external API call...")
        # Simulate API call delay
        time.sleep(0.3)
        
        # Mock external API response
        mock_data = {
            "id": int(time.time()) % 1000,
            "data": f"Sample data for request {request_id}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "status": "success"
        }
        
        span.set_attributes({
            "http.status_code": 200,
            "external.response.id": mock_data["id"],
            "external.response.status": mock_data["status"]
        })
        
        span.set_status(Status(StatusCode.OK))
        return mock_data
        
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


def process_api_request(request_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Process API request with tracing"""
    span = tracer.start_span("process_api_request")
    
    try:
        span.set_attributes({
            "processing.type": "api_business_logic",
            "request.id": request_id
        })
        
        logger.info(f"Processing API request: {request_id}")
        
        # Get external data
        external_data = call_external_api(request_id)
        
        # Simulate additional processing
        time.sleep(0.1)
        
        processing_result = {
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "external_data": external_data,
            "request_processed": True
        }
        
        span.set_attributes({
            "processing.success": True,
            "external.data.id": external_data["id"]
        })
        
        span.set_status(Status(StatusCode.OK))
        return processing_result
        
    except Exception as e:
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        raise
    finally:
        span.end()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """API Gateway Lambda handler"""
    start_time = time.time()
    span = tracer.start_span("api_gateway_handler")
    
    try:
        logger.info(f"API Gateway event: {json.dumps(event)}")
        
        # Extract request information
        method = event.get("httpMethod", "UNKNOWN")
        path = event.get("path", "/")
        query_params = event.get("queryStringParameters") or {}
        headers = event.get("headers") or {}
        user_agent = headers.get("User-Agent", "unknown")
        source_ip = event.get("requestContext", {}).get("identity", {}).get("sourceIp", "unknown")
        
        # Add span attributes
        span.set_attributes({
            "http.method": method,
            "http.route": path,
            "http.scheme": "https",
            "http.user_agent": user_agent,
            "http.client_ip": source_ip,
            "faas.execution": context.aws_request_id,
            "faas.id": context.function_name,
            "cloud.region": os.environ.get('AWS_REGION', '')
        })
        
        # Send request log to OpenObserve
        openobserve_logger.send_logs({
            "level": "info",
            "message": "API request received",
            "metadata": {
                "http_method": method,
                "http_path": path,
                "query_params": query_params,
                "user_agent": user_agent,
                "source_ip": source_ip,
                "api_gateway_request_id": event.get("requestContext", {}).get("requestId", ""),
                "headers_count": len(headers)
            }
        }, context.aws_request_id)
        
        # Process the request
        processing_result = process_api_request(context.aws_request_id, event)
        
        response_time = int((time.time() - start_time) * 1000)
        
        # Record metrics
        api_request_counter.add(1, {
            "method": method,
            "path": path,
            "status": "200"
        })
        
        api_response_time.record(response_time, {
            "method": method,
            "path": path
        })
        
        response = {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "X-Request-ID": context.aws_request_id,
                "X-Response-Time": f"{response_time}ms"
            },
            "body": json.dumps({
                "message": "API request processed successfully",
                "requestId": context.aws_request_id,
                "method": method,
                "path": path,
                "queryParams": query_params,
                "processingResult": processing_result,
                "responseTime": response_time,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        }
        
        # Send success log to OpenObserve
        openobserve_logger.send_logs({
            "level": "info",
            "message": "API request processed successfully",
            "metadata": {
                "response_time_ms": response_time,
                "status_code": 200,
                "external_data_id": processing_result["external_data"]["id"],
                "response_size": len(response["body"])
            }
        }, context.aws_request_id)
        
        span.set_attributes({
            "http.status_code": 200,
            "http.response_time_ms": response_time,
            "api.success": True
        })
        
        span.set_status(Status(StatusCode.OK))
        
        return response
        
    except Exception as e:
        response_time = int((time.time() - start_time) * 1000)
        logger.error(f"API Gateway error: {str(e)}")
        
        # Record error metrics
        api_request_counter.add(1, {
            "method": event.get("httpMethod", "UNKNOWN"),
            "path": event.get("path", "/"),
            "status": "500"
        })
        
        # Send error log to OpenObserve
        openobserve_logger.send_logs({
            "level": "error",
            "message": "API request failed",
            "metadata": {
                "error_message": str(e),
                "error_traceback": traceback.format_exc(),
                "response_time_ms": response_time,
                "http_method": event.get("httpMethod", "UNKNOWN"),
                "http_path": event.get("path", "/")
            }
        }, context.aws_request_id)
        
        span.record_exception(e)
        span.set_status(Status(StatusCode.ERROR, str(e)))
        
        error_response = {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
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