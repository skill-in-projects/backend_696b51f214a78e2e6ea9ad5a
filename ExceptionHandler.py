import os
import re
import traceback
import logging
import asyncio
from typing import Optional
from starlette.requests import Request
from starlette.responses import JSONResponse
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import httpx

logger = logging.getLogger(__name__)

def extract_board_id(request: Request) -> Optional[str]:
    """Extract boardId from request (route params, query string, headers, env, hostname)"""
    # Try route parameters
    if hasattr(request, 'path_params') and 'boardId' in request.path_params:
        return request.path_params['boardId']
    
    # Try query parameters
    if 'boardId' in request.query_params:
        return request.query_params['boardId']
    
    # Try headers
    if 'X-Board-Id' in request.headers:
        return request.headers['X-Board-Id']
    
    # Try environment variable
    board_id = os.getenv('BOARD_ID')
    if board_id:
        return board_id
    
    # Try to extract from hostname (Railway pattern: webapi{boardId}.up.railway.app - no hyphen)
    host = request.headers.get('host', '')
    if host:
        match = re.search(r'webapi([a-f0-9]{24})', host, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Try to extract from RUNTIME_ERROR_ENDPOINT_URL if it contains boardId pattern
    endpoint_url = os.getenv('RUNTIME_ERROR_ENDPOINT_URL', '')
    if endpoint_url:
        match = re.search(r'webapi([a-f0-9]{24})', endpoint_url, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None

async def send_error_to_endpoint(endpoint_url: str, board_id: Optional[str], request: Request, exception: Exception):
    """Send error details to runtime error endpoint (fire and forget)"""
    try:
        # Extract exception details
        exc_type = type(exception).__name__
        exc_message = str(exception) if exception else 'Unknown error'
        exc_traceback = ''.join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        
        # Get file and line from traceback
        tb_lines = traceback.extract_tb(exception.__traceback__)
        file_name = tb_lines[-1].filename if tb_lines else None
        line_number = tb_lines[-1].lineno if tb_lines else None
        
        # Build payload
        payload = {
            'boardId': board_id,
            'timestamp': None,  # Will be set by backend
            'file': file_name,
            'line': line_number,
            'stackTrace': exc_traceback,
            'message': exc_message,
            'exceptionType': exc_type,
            'requestPath': str(request.url.path),
            'requestMethod': request.method,
            'userAgent': request.headers.get('user-agent')
        }
        
        # Send in background (fire and forget)
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(endpoint_url, json=payload)
                logger.warning(f'[EXCEPTION HANDLER] Error endpoint response: {response.status_code}')
            except Exception as e:
                logger.error(f'[EXCEPTION HANDLER] Failed to send error to endpoint: {e}')
    except Exception as e:
        logger.error(f'[EXCEPTION HANDLER] Error in send_error_to_endpoint: {e}')

async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for all unhandled exceptions"""
    logger.error(f'[EXCEPTION HANDLER] Unhandled exception occurred: {exc}', exc_info=True)
    
    # Extract boardId
    board_id = extract_board_id(request)
    logger.warning(f'[EXCEPTION HANDLER] Extracted boardId: {board_id if board_id else "NULL"}')
    
    # Send error to runtime error endpoint if configured
    runtime_error_endpoint_url = os.getenv('RUNTIME_ERROR_ENDPOINT_URL')
    if runtime_error_endpoint_url:
        logger.warning(f'[EXCEPTION HANDLER] Sending error to endpoint: {runtime_error_endpoint_url}')
        # Fire and forget - don't await
        asyncio.create_task(send_error_to_endpoint(runtime_error_endpoint_url, board_id, request, exc))
    else:
        logger.warning('[EXCEPTION HANDLER] RUNTIME_ERROR_ENDPOINT_URL is not set - skipping error reporting')
    
    # Return error response
    return JSONResponse(
        status_code=500,
        content={
            'error': 'An error occurred while processing your request',
            'message': str(exc) if exc else 'Unknown error'
        }
    )

def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""
    # Handle all exceptions (most generic handler)
    app.add_exception_handler(Exception, global_exception_handler)
