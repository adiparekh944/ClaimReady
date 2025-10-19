#!/bin/bash

# Configuration
AWS_REGION="us-east-1"
REPOSITORY_NAME="claimready-frontend"
IMAGE_NAME="claimready-frontend"
TAG="latest"

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: Could not get AWS account ID. Make sure AWS CLI is configured."
    exit 1
fi

ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPOSITORY_NAME}"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "ECR URI: $ECR_URI"

# Create ECR repository if it doesn't exist
echo "Creating ECR repository..."
aws ecr create-repository --repository-name $REPOSITORY_NAME --region $AWS_REGION 2>/dev/null || echo "Repository already exists"

# Build Docker image
echo "Building Docker image..."
docker build -t $IMAGE_NAME:$TAG .

# Authenticate Docker with ECR
echo "Authenticating with ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_URI

# Tag image for ECR
echo "Tagging image for ECR..."
docker tag $IMAGE_NAME:$TAG $ECR_URI:$TAG

# Push image to ECR
echo "Pushing image to ECR..."
docker push $ECR_URI:$TAG

echo "Successfully pushed $ECR_URI:$TAG to ECR!"
echo "You can now use this image in ECS, EKS, or other AWS services."
echo ""
echo "To use this image in docker-compose, set these environment variables:"
echo "export AWS_ACCOUNT_ID=$AWS_ACCOUNT_ID"
echo "export AWS_REGION=$AWS_REGION"
echo "Then run: docker-compose -f docker-compose.ecr.yml up"
