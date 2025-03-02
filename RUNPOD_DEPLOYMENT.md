# Deploying PDF-Extract-Kit on RunPod Serverless

This guide provides step-by-step instructions for deploying the PDF-Extract-Kit project on RunPod's serverless platform using GitHub integration.

## Prerequisites

1. A [RunPod](https://www.runpod.io/) account
2. A GitHub account with the PDF-Extract-Kit repository

## Deployment Steps

### 1. Fork or Push the Repository to GitHub

Ensure your PDF-Extract-Kit repository is available on GitHub with the following files:

- `handler.py` - The serverless handler for RunPod
- `Dockerfile` - The Docker configuration for the serverless environment
- `runpod_requirements.txt` - Additional requirements for RunPod serverless

### 2. Set Up RunPod Serverless Endpoint

1. Log in to your RunPod account
2. Navigate to "Serverless" in the left sidebar
3. Click "New Endpoint"
4. Fill in the following details:
   - **Endpoint Name**: `pdf-extract-kit` (or your preferred name)
   - **Select Template**: `Custom`
   - **Container Configuration**:
     - Select "GitHub Repository"
     - Enter your GitHub repository URL
     - Select the branch (usually `main` or `master`)
     - Set the Docker build context to `/` (root)
   - **Advanced Options**:
     - **GPU**: Select an appropriate GPU (at least 16GB VRAM recommended)
     - **Container Disk**: At least 10GB
     - **Idle Timeout**: Set according to your needs (e.g., 5 minutes)
     - **Min Provisioned Workers**: 0 (or more if you expect constant traffic)
     - **Max Workers**: Set according to your expected load
5. Click "Deploy"

### 3. Wait for Deployment

The deployment process may take several minutes as RunPod builds the Docker image and provisions the serverless endpoint.

### 4. Test the Endpoint

Once the endpoint is deployed, you can test it using the RunPod API or with curl commands.

## API Usage

The serverless endpoint accepts the following input formats:

### 1. PDF URL

```json
{
  "input": {
    "url": "https://example.com/document.pdf",
    "visualize": true,
    "merge2markdown": true
  }
}
```

### 2. Base64 Encoded PDF

```json
{
  "input": {
    "file_base64": "BASE64_ENCODED_PDF_CONTENT",
    "visualize": true,
    "merge2markdown": true
  }
}
```

## Example Curl Commands

### Process PDF from URL

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "url": "https://arxiv.org/pdf/2303.08774.pdf",
      "visualize": true,
      "merge2markdown": true
    }
  }'
```

### Process PDF from Base64

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/run" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -d '{
    "input": {
      "file_base64": "'$(base64 -w 0 your_document.pdf)'",
      "visualize": true,
      "merge2markdown": true
    }
  }'
```

## Response Format

The API response will have the following structure:

```json
{
  "id": "request-id",
  "status": "COMPLETED",
  "output": {
    "success": true,
    "results": [...],  // Detailed extraction results
    "markdown": "...",  // Markdown content (if merge2markdown is true)
    "visualization": "..."  // Base64 encoded visualization (if visualize is true)
  }
}
```

## Monitoring and Logs

You can monitor your serverless endpoint and view logs in the RunPod dashboard:

1. Go to "Serverless" in the left sidebar
2. Select your endpoint
3. Click on "Logs" to view the execution logs

## Troubleshooting

If you encounter issues with your deployment:

1. Check the build logs in the RunPod dashboard
2. Ensure all dependencies are correctly specified in the requirements files
3. Verify that the GPU selected has enough memory for the models
4. Check that the handler function is correctly implemented

## Additional Resources

- [RunPod Serverless Documentation](https://docs.runpod.io/docs/serverless)
- [PDF-Extract-Kit Documentation](https://github.com/yourusername/PDF-Extract-Kit)
