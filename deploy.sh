#!/bin/bash

# deploy.sh - Deployment script for OpenTelemetry Lambda with OpenObserve
# Usage: ./deploy.sh [--profile PROFILE_NAME] [--region REGION]

set -e

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile|-p)
            AWS_PROFILE_ARG="$2"
            shift 2
            ;;
        --region|-r)
            AWS_REGION_ARG="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--profile PROFILE_NAME] [--region REGION]"
            echo "  --profile, -p    AWS profile to use"
            echo "  --region, -r     AWS region to deploy to"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown parameter: $1"
            exit 1
            ;;
    esac
done

echo "🚀 Deploying Lambda OpenTelemetry with OpenObserve integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

#!/bin/bash

# deploy.sh - Deployment script for OpenTelemetry Lambda with OpenObserve

set -e

echo "🚀 Deploying Lambda OpenTelemetry with OpenObserve integration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Get AWS profile configuration
get_aws_profile() {
    print_status "AWS Profile Configuration..."
    echo
    
    # Use command line argument if provided
    if [ -n "$AWS_PROFILE_ARG" ]; then
        export AWS_PROFILE="$AWS_PROFILE_ARG"
        print_status "Using profile from command line: $AWS_PROFILE"
    # Check if AWS_PROFILE is already set
    elif [ -n "$AWS_PROFILE" ]; then
        print_info "Using AWS_PROFILE environment variable: $AWS_PROFILE"
        read -p "Do you want to use this profile? (Y/n): " use_existing
        if [[ $use_existing =~ ^[Nn]$ ]]; then
            unset AWS_PROFILE
        else
            return 0
        fi
    fi
    
    # List available profiles
    print_info "Available AWS profiles:"
    aws configure list-profiles 2>/dev/null | sed 's/^/  - /' || {
        print_warning "No AWS profiles found or AWS CLI not configured"
        echo "  You can continue with default credentials or configure a profile first"
    }
    
    echo
    read -p "Enter AWS profile name (press Enter for default credentials): " AWS_PROFILE_INPUT
    
    if [ -n "$AWS_PROFILE_INPUT" ]; then
        # Validate the profile exists
        if aws configure list-profiles 2>/dev/null | grep -q "^${AWS_PROFILE_INPUT}$"; then
            export AWS_PROFILE="$AWS_PROFILE_INPUT"
            print_status "Using AWS profile: $AWS_PROFILE"
        else
            print_error "Profile '$AWS_PROFILE_INPUT' not found!"
            echo "Available profiles:"
            aws configure list-profiles 2>/dev/null | sed 's/^/  - /'
            exit 1
        fi
    else
        print_status "Using default AWS credentials"
    fi
    
    # Test AWS credentials
    print_status "Testing AWS credentials..."
    CURRENT_USER=$(aws sts get-caller-identity --query 'Arn' --output text 2>/dev/null) || {
        print_error "AWS credentials test failed!"
        print_error "Please ensure your AWS credentials are configured correctly"
        exit 1
    }
    
    print_status "✅ AWS credentials validated for: $CURRENT_USER"
    
    # Get region
    if [ -n "$AWS_REGION_ARG" ]; then
        AWS_REGION="$AWS_REGION_ARG"
        export AWS_DEFAULT_REGION="$AWS_REGION"
        print_status "Using region from command line: $AWS_REGION"
    else
        AWS_REGION=$(aws configure get region 2>/dev/null || echo "")
        if [ -z "$AWS_REGION" ]; then
            echo
            read -p "Enter AWS region (default: us-west-2): " AWS_REGION_INPUT
            AWS_REGION=${AWS_REGION_INPUT:-"us-west-2"}
            export AWS_DEFAULT_REGION="$AWS_REGION"
            print_status "Using AWS region: $AWS_REGION"
        else
            print_status "Using AWS region: $AWS_REGION"
        fi
    fi
}

# Check if required tools are installed
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    if ! command -v sam &> /dev/null; then
        print_error "AWS SAM CLI is not installed. Please install it first."
        echo "Installation guide: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html"
        exit 1
    fi
    
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command -v node &> /dev/null; then
        print_error "Node.js is not installed. Please install Node.js 18 or later."
        exit 1
    fi
    
    print_status "All prerequisites are satisfied!"
}

# Get user input for OpenObserve configuration
get_openobserve_config() {
    print_status "Getting OpenObserve configuration..."
    echo
    
    # Base endpoint
    echo "🌐 OpenObserve Base Endpoint"
    read -p "Enter your OpenObserve base endpoint (default: https://api.openobserve.ai): " OPENOBSERVE_BASE_ENDPOINT
    OPENOBSERVE_BASE_ENDPOINT=${OPENOBSERVE_BASE_ENDPOINT:-"https://api.openobserve.ai"}
    
    # Organization
    echo
    echo "🏢 OpenObserve Organization"
    echo "This is the organization name from your OpenObserve URL"
    echo "Example: prabhat_organization_2512_r6EinDy3fpExW1M"
    read -p "Enter your OpenObserve organization name: " OPENOBSERVE_ORGANIZATION
    
    # Stream name
    echo
    echo "📊 OpenObserve Stream"
    read -p "Enter your OpenObserve stream name (default: default): " OPENOBSERVE_STREAM
    OPENOBSERVE_STREAM=${OPENOBSERVE_STREAM:-"default"}
    
    # Username
    echo
    echo "👤 OpenObserve Credentials"
    read -p "Enter your OpenObserve username: " OPENOBSERVE_USERNAME
    
    # Password (hidden input)
    echo
    read -s -p "Enter your OpenObserve password: " OPENOBSERVE_PASSWORD
    echo
    
    # Validate required inputs
    if [ -z "$OPENOBSERVE_ORGANIZATION" ] || [ -z "$OPENOBSERVE_USERNAME" ] || [ -z "$OPENOBSERVE_PASSWORD" ]; then
        print_error "Organization name, username, and password are required!"
        exit 1
    fi
    
    echo
    print_status "✅ Configuration Summary:"
    echo "  Base Endpoint: $OPENOBSERVE_BASE_ENDPOINT"
    echo "  Organization: $OPENOBSERVE_ORGANIZATION"
    echo "  Stream: $OPENOBSERVE_STREAM"
    echo "  Username: $OPENOBSERVE_USERNAME"
    echo "  OTLP Endpoint: $OPENOBSERVE_BASE_ENDPOINT/api/$OPENOBSERVE_ORGANIZATION"
    echo "  Logs URL: $OPENOBSERVE_BASE_ENDPOINT/api/$OPENOBSERVE_ORGANIZATION/$OPENOBSERVE_STREAM/_json"
    echo
    
    read -p "Does this configuration look correct? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_warning "Configuration cancelled. Please run the script again."
        exit 0
    fi
}

# Deploy the stack
deploy_stack() {
    print_status "Building SAM application..."
    
    # Build with profile if set
    if [ -n "$AWS_PROFILE" ]; then
        sam build --profile "$AWS_PROFILE"
    else
        sam build
    fi
    
    print_status "Deploying SAM application..."
    
    # Check if this is first deployment
    STACK_NAME="lambda-opentelemetry-openobserve-demo"
    
    # Use profile for AWS CLI commands if set
    AWS_CLI_PROFILE=""
    if [ -n "$AWS_PROFILE" ]; then
        AWS_CLI_PROFILE="--profile $AWS_PROFILE"
    fi
    
    if aws cloudformation describe-stacks --stack-name "$STACK_NAME" $AWS_CLI_PROFILE &> /dev/null; then
        print_status "Stack exists, updating..."
        if [ -n "$AWS_PROFILE" ]; then
            sam deploy \
                --profile "$AWS_PROFILE" \
                --stack-name "$STACK_NAME" \
                --parameter-overrides \
                    OpenObserveEndpoint="$OPENOBSERVE_BASE_ENDPOINT" \
                    OpenObserveUsername="$OPENOBSERVE_USERNAME" \
                    OpenObservePassword="$OPENOBSERVE_PASSWORD" \
                    OpenObserveOrganization="$OPENOBSERVE_ORGANIZATION" \
                    OpenObserveStream="$OPENOBSERVE_STREAM" \
                --capabilities CAPABILITY_IAM \
                --no-confirm-changeset
        else
            sam deploy \
                --stack-name "$STACK_NAME" \
                --parameter-overrides \
                    OpenObserveEndpoint="$OPENOBSERVE_BASE_ENDPOINT" \
                    OpenObserveUsername="$OPENOBSERVE_USERNAME" \
                    OpenObservePassword="$OPENOBSERVE_PASSWORD" \
                    OpenObserveOrganization="$OPENOBSERVE_ORGANIZATION" \
                    OpenObserveStream="$OPENOBSERVE_STREAM" \
                --capabilities CAPABILITY_IAM \
                --no-confirm-changeset
        fi
    else
        print_status "First deployment, using guided mode..."
        if [ -n "$AWS_PROFILE" ]; then
            sam deploy \
                --guided \
                --profile "$AWS_PROFILE" \
                --stack-name "$STACK_NAME" \
                --parameter-overrides \
                    OpenObserveEndpoint="$OPENOBSERVE_BASE_ENDPOINT" \
                    OpenObserveUsername="$OPENOBSERVE_USERNAME" \
                    OpenObservePassword="$OPENOBSERVE_PASSWORD" \
                    OpenObserveOrganization="$OPENOBSERVE_ORGANIZATION" \
                    OpenObserveStream="$OPENOBSERVE_STREAM"
        else
            sam deploy \
                --guided \
                --stack-name "$STACK_NAME" \
                --parameter-overrides \
                    OpenObserveEndpoint="$OPENOBSERVE_BASE_ENDPOINT" \
                    OpenObserveUsername="$OPENOBSERVE_USERNAME" \
                    OpenObservePassword="$OPENOBSERVE_PASSWORD" \
                    OpenObserveOrganization="$OPENOBSERVE_ORGANIZATION" \
                    OpenObserveStream="$OPENOBSERVE_STREAM"
        fi
    fi
}

# Get stack outputs
get_outputs() {
    print_status "Getting stack outputs..."
    
    STACK_NAME="lambda-opentelemetry-openobserve-demo"
    
    # Use profile for AWS CLI commands if set
    AWS_CLI_PROFILE=""
    if [ -n "$AWS_PROFILE" ]; then
        AWS_CLI_PROFILE="--profile $AWS_PROFILE"
    fi
    
    API_URL=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`DemoApiUrl`].OutputValue' \
        --output text \
        $AWS_CLI_PROFILE)
    
    DEMO_FUNCTION=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`DemoFunctionName`].OutputValue' \
        --output text \
        $AWS_CLI_PROFILE)
    
    API_FUNCTION=$(aws cloudformation describe-stacks \
        --stack-name "$STACK_NAME" \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiFunctionName`].OutputValue' \
        --output text \
        $AWS_CLI_PROFILE)
    
    echo
    echo "🎉 Deployment completed successfully!"
    echo
    echo "📋 Stack Information:"
    echo "  Stack Name: $STACK_NAME"
    echo "  Demo Function: $DEMO_FUNCTION"
    echo "  API Function: $API_FUNCTION"
    echo "  API Endpoint: $API_URL"
    echo
    echo "🧪 Testing Commands:"
    echo "  Test API endpoint:"
    echo "    curl $API_URL"
    echo
    echo "  Invoke demo function directly:"
    echo "    aws lambda invoke --function-name $DEMO_FUNCTION --payload '{}' response.json"
    echo
    echo "  Watch logs:"
    echo "    sam logs --name $DEMO_FUNCTION --tail"
    echo "    sam logs --name $API_FUNCTION --tail"
    echo
    echo "📊 View in OpenObserve:"
    echo "  Login to: $OPENOBSERVE_BASE_ENDPOINT"
    echo "  Organization: $OPENOBSERVE_ORGANIZATION"
    echo "  Stream: $OPENOBSERVE_STREAM"
    echo "  Look for logs with service: lambda-openobserve-demo"
    echo
}

# Test the deployment
test_deployment() {
    print_status "Testing the deployment..."
    
    # Use profile for AWS CLI commands if set
    AWS_CLI_PROFILE=""
    if [ -n "$AWS_PROFILE" ]; then
        AWS_CLI_PROFILE="--profile $AWS_PROFILE"
    fi
    
    if [ -n "$API_URL" ]; then
        echo "Testing API endpoint..."
        response=$(curl -s -w "%{http_code}" "$API_URL")
        http_code="${response: -3}"
        
        if [ "$http_code" = "200" ]; then
            print_status "✅ API test passed!"
        else
            print_warning "⚠️  API test returned HTTP $http_code"
        fi
    fi
    
    if [ -n "$DEMO_FUNCTION" ]; then
        echo "Testing direct function invocation..."
        aws lambda invoke \
            --function-name "$DEMO_FUNCTION" \
            --payload '{"test": "deployment"}' \
            --cli-binary-format raw-in-base64-out \
            $AWS_CLI_PROFILE \
            /tmp/lambda-response.json > /dev/null
        
        if [ $? -eq 0 ]; then
            print_status "✅ Direct function test passed!"
        else
            print_warning "⚠️  Direct function test failed"
        fi
    fi
}

# Cleanup function
cleanup() {
    print_status "Cleaning up temporary files..."
    rm -f /tmp/lambda-response.json
}

# Main execution
main() {
    get_aws_profile
    check_prerequisites
    get_openobserve_config
    deploy_stack
    get_outputs
    test_deployment
    cleanup
    
    print_status "🎯 Deployment process completed!"
    echo
    echo "Next steps:"
    echo "1. Test the API endpoint with the provided curl command"
    echo "2. Check OpenObserve for traces and logs"
    echo "3. Monitor the CloudWatch logs for any issues"
    echo "4. Use the provided commands to invoke functions and view logs"
}

# Handle script termination
trap cleanup EXIT

# Run main function
main "$@"