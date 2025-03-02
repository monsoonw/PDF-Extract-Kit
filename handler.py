import os
import sys
import json
import base64
import tempfile
import requests
from io import BytesIO
from typing import Dict, Any, List, Union
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from PIL import Image

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from pdf_extract_kit.utils.config_loader import load_config, initialize_tasks_and_models
from pdf_extract_kit.registry.registry import TASK_REGISTRY
from pdf_extract_kit.utils.data_preprocess import load_pdf

# Initialize FastAPI app
app = FastAPI()

# Global variables to store models
task_instances = None
pdf_extract_task = None

def initialize_models():
    """Initialize all models required for PDF processing."""
    global task_instances, pdf_extract_task
    
    # Load configuration
    config_path = os.environ.get("CONFIG_PATH", "project/pdf2markdown/configs/pdf2markdown.yaml")
    config = load_config(config_path)
    
    # Initialize task instances
    task_instances = initialize_tasks_and_models(config)
    
    # Get models
    layout_model = task_instances['layout_detection'].model if 'layout_detection' in task_instances else None
    mfd_model = task_instances['formula_detection'].model if 'formula_detection' in task_instances else None
    mfr_model = task_instances['formula_recognition'].model if 'formula_recognition' in task_instances else None
    ocr_model = task_instances['ocr'].model if 'ocr' in task_instances else None
    
    # Initialize PDF2MARKDOWN task
    pdf_extract_task = TASK_REGISTRY.get("pdf2markdown")(layout_model, mfd_model, mfr_model, ocr_model)
    
    return "Models initialized successfully"

@app.on_event("startup")
async def startup_event():
    """Initialize models on startup."""
    initialize_models()

@app.get("/")
async def root():
    """Root endpoint to check if the server is running."""
    return {"message": "PDF Extract Kit API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

async def process_pdf_file(file_path: str, save_dir: str = None, visualize: bool = False, merge2markdown: bool = True):
    """Process a PDF file and return the results."""
    global pdf_extract_task
    
    if pdf_extract_task is None:
        initialize_models()
    
    # Process the PDF
    results = pdf_extract_task.process(file_path, save_dir=save_dir, visualize=visualize, merge2markdown=merge2markdown)
    
    # Return the results
    return results

@app.post("/process")
async def process_pdf(
    file: UploadFile = File(None),
    url: str = Form(None),
    visualize: bool = Form(False),
    merge2markdown: bool = Form(True)
):
    """
    Process a PDF file and return the results.
    
    Args:
        file: The PDF file to process
        url: URL to a PDF file to process
        visualize: Whether to visualize the results
        merge2markdown: Whether to convert the results to markdown
        
    Returns:
        The processing results
    """
    if file is None and url is None:
        raise HTTPException(status_code=400, detail="Either file or url must be provided")
    
    # Create a temporary directory to store results
    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = None
        
        # Handle file upload
        if file:
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, "wb") as f:
                f.write(await file.read())
        
        # Handle URL
        elif url:
            try:
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Determine file extension from content type or URL
                content_type = response.headers.get("Content-Type", "")
                if "pdf" in content_type.lower():
                    ext = ".pdf"
                elif "image" in content_type.lower():
                    ext = ".png"
                else:
                    # Try to get extension from URL
                    ext = os.path.splitext(url)[1]
                    if not ext:
                        ext = ".pdf"  # Default to PDF
                
                file_path = os.path.join(temp_dir, f"downloaded{ext}")
                with open(file_path, "wb") as f:
                    f.write(response.content)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to download file from URL: {str(e)}")
        
        # Process the file
        results = await process_pdf_file(file_path, save_dir=temp_dir, visualize=visualize, merge2markdown=merge2markdown)
        
        # Read the markdown file if it was generated
        markdown_content = None
        if merge2markdown:
            basename = os.path.basename(file_path)[:-4]
            md_path = os.path.join(temp_dir, f"{basename}.md")
            if os.path.exists(md_path):
                with open(md_path, "r") as f:
                    markdown_content = f.read()
        
        # Read the visualization if it was generated
        visualization_data = None
        if visualize:
            basename = os.path.basename(file_path)[:-4]
            vis_path = os.path.join(temp_dir, f"{basename}.png")
            if not os.path.exists(vis_path) and file_path.endswith(".pdf"):
                vis_path = os.path.join(temp_dir, f"{basename}.pdf")
            
            if os.path.exists(vis_path):
                with open(vis_path, "rb") as f:
                    visualization_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Return the results
        response_data = {
            "success": True,
            "results": results,
        }
        
        if markdown_content:
            response_data["markdown"] = markdown_content
        
        if visualization_data:
            response_data["visualization"] = visualization_data
        
        return JSONResponse(content=response_data)

# RunPod handler function
def handler(event):
    """
    RunPod serverless handler function.
    
    Args:
        event: The event object containing the request data
        
    Returns:
        The response object
    """
    try:
        # Initialize models if not already initialized
        if task_instances is None or pdf_extract_task is None:
            initialize_models()
        
        # Get input data
        input_data = event.get("input", {})
        
        # Create a temporary directory to store results
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = None
            
            # Handle base64 encoded file
            if "file_base64" in input_data:
                file_data = base64.b64decode(input_data["file_base64"])
                file_path = os.path.join(temp_dir, "input.pdf")
                with open(file_path, "wb") as f:
                    f.write(file_data)
            
            # Handle URL
            elif "url" in input_data:
                url = input_data["url"]
                try:
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    
                    # Determine file extension from content type or URL
                    content_type = response.headers.get("Content-Type", "")
                    if "pdf" in content_type.lower():
                        ext = ".pdf"
                    elif "image" in content_type.lower():
                        ext = ".png"
                    else:
                        # Try to get extension from URL
                        ext = os.path.splitext(url)[1]
                        if not ext:
                            ext = ".pdf"  # Default to PDF
                    
                    file_path = os.path.join(temp_dir, f"downloaded{ext}")
                    with open(file_path, "wb") as f:
                        f.write(response.content)
                except Exception as e:
                    return {"error": f"Failed to download file from URL: {str(e)}"}
            
            else:
                return {"error": "Either file_base64 or url must be provided"}
            
            # Get options
            visualize = input_data.get("visualize", False)
            merge2markdown = input_data.get("merge2markdown", True)
            
            # Process the file
            results = pdf_extract_task.process(file_path, save_dir=temp_dir, visualize=visualize, merge2markdown=merge2markdown)
            
            # Read the markdown file if it was generated
            markdown_content = None
            if merge2markdown:
                basename = os.path.basename(file_path)[:-4]
                md_path = os.path.join(temp_dir, f"{basename}.md")
                if os.path.exists(md_path):
                    with open(md_path, "r") as f:
                        markdown_content = f.read()
            
            # Read the visualization if it was generated
            visualization_data = None
            if visualize:
                basename = os.path.basename(file_path)[:-4]
                vis_path = os.path.join(temp_dir, f"{basename}.png")
                if not os.path.exists(vis_path) and file_path.endswith(".pdf"):
                    vis_path = os.path.join(temp_dir, f"{basename}.pdf")
                
                if os.path.exists(vis_path):
                    with open(vis_path, "rb") as f:
                        visualization_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Return the results
            response_data = {
                "success": True,
                "results": results,
            }
            
            if markdown_content:
                response_data["markdown"] = markdown_content
            
            if visualization_data:
                response_data["visualization"] = visualization_data
            
            return response_data
    
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}

# For local testing
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000) 