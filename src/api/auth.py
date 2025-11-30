import logging
from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from src.auth import create_zoho_access_token

router = APIRouter()

logger = logging.getLogger(__name__)

@router.get("/auth")
async def authorize(user_id="1"):
    ...
    
@router.get("/authsuccess")
async def authsuccess():
    html = """
    <html>
        <head>
            <title>Logged In</title>
            <style>
                body {
                    margin: 0;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    background: #f0f0f0;
                    font-family: Arial, sans-serif;
                }
                .box {
                    background: white;
                    padding: 40px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    text-align: center;
                }
            </style>
        </head>
        <body>
            <div class="box">
                <h2>You are successfully logged in</h2>
                <p>You can close this page.</p>
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.get("/callback")
async def zoho_auth_callback(
    code:str, 
    location:str, 
    accounts_server:str = Query(..., alias="accounts-server")
):
    logger.info(f"got code={code}")
    await create_zoho_access_token(code)

    return RedirectResponse("/authsuccess", status_code=303)
