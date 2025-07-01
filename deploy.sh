#!/bin/bash

# Real-time Video Processing Deployment Script
# This script deploys the entire infrastructure to AWS

set -e

# Configuration
PROJECT_NAME="real-time-video-processing"
ENVIRONMENT=${1:-development}
REGION=${2:-us-east-1}
STACK_NAME="$PROJECT_NAME-$ENVIRONMENT"

echo "🚀 Deploying Real-time Video Processing Platform"
echo "Project: $PROJECT_NAME"
echo "Environment: $ENVIRONMENT"
echo "Region: $REGION"
echo "Stack: $STACK_NAME"
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

echo "✅ AWS CLI configured"

# Create deployment package for Lambda
echo "📦 Creating Lambda deployment package..."
mkdir -p temp/lambda
cp lambda_functions/video_processor.py temp/lambda/
cd temp/lambda

# Install dependencies
pip install opencv-python-headless pillow numpy -t .

# Create zip file
zip -r ../../lambda-deployment.zip .
cd ../..
rm -rf temp

echo "✅ Lambda package created"

# Upload Lambda package to S3
DEPLOYMENT_BUCKET="$PROJECT_NAME-deployments-$ENVIRONMENT"
echo "📤 Creating deployment bucket: $DEPLOYMENT_BUCKET"

# Create deployment bucket if it doesn't exist
aws s3api head-bucket --bucket $DEPLOYMENT_BUCKET 2>/dev/null || aws s3 mb s3://$DEPLOYMENT_BUCKET --region $REGION

# Upload Lambda package
aws s3 cp lambda-deployment.zip s3://$DEPLOYMENT_BUCKET/lambda/video_processor.zip

echo "✅ Lambda package uploaded"

# Deploy CloudFormation stack
echo "☁️ Deploying CloudFormation stack..."

aws cloudformation deploy \
    --template-file infrastructure/cloudformation-template.yaml \
    --stack-name $STACK_NAME \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        ProjectName=$PROJECT_NAME \
        Environment=$ENVIRONMENT \
    --region $REGION \
    --no-fail-on-empty-changeset

echo "✅ CloudFormation stack deployed"

# Update Lambda function code
echo "🔄 Updating Lambda function code..."
FUNCTION_NAME="$PROJECT_NAME-processor-$ENVIRONMENT"

aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --s3-bucket $DEPLOYMENT_BUCKET \
    --s3-key lambda/video_processor.zip \
    --region $REGION

echo "✅ Lambda function updated"

# Get stack outputs
echo "📋 Getting deployment information..."
OUTPUTS=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs' \
    --output json)

echo "🎉 Deployment completed successfully!"
echo ""
echo "📊 Deployment Information:"
echo "========================="

# Parse and display outputs
echo "$OUTPUTS" | jq -r '.[] | "- \(.OutputKey): \(.OutputValue)"'

echo ""
echo "🔗 Next Steps:"
echo "1. Update your .env file with the deployment outputs"
echo "2. Configure your application to use the deployed resources"
echo "3. Test the video upload functionality"
echo "4. Monitor the CloudWatch dashboard for metrics"

# Create .env file with deployment outputs
echo ""
echo "📝 Creating deployment.env file..."

cat > deployment.env << EOF
# Auto-generated deployment configuration
# Environment: $ENVIRONMENT
# Stack: $STACK_NAME
# Deployed: $(date)

$(echo "$OUTPUTS" | jq -r '.[] | "\(.OutputKey)=\(.OutputValue)"')
AWS_REGION=$REGION
STACK_NAME=$STACK_NAME
DEPLOYMENT_BUCKET=$DEPLOYMENT_BUCKET
EOF

echo "✅ deployment.env file created"
echo ""
echo "🚀 Your Real-time Video Processing Platform is now deployed!"

# Cleanup
rm -f lambda-deployment.zip
