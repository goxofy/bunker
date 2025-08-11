import aioipfs
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from typing import List

# --- Configuration ---
# This is the address of the IPFS RPC API.
IPFS_API_ADDR = '/ip4/127.0.0.1/tcp/5001'

# --- Pydantic Models ---
class PinRequest(BaseModel):
    """Request model for unpinning an item by its IPFS hash."""
    hash: str

# --- FastAPI App Initialization ---
app = FastAPI(
    title="My Pinning Service",
    description="A Python-based API to pin, unpin, and list files on a local IPFS node.",
    version="1.3.0", # Version bump for new feature
)

@app.get("/")
def read_root():
    """A simple root endpoint to check if the service is running."""
    return {"message": "Welcome to your personal IPFS Pinning Service!"}


# Mimicking the path from the original service
@app.post("/api/v2/add")
async def upload_to_ipfs(files: List[UploadFile] = File(...)):
    """
    Receives one or more files, adds them to the local IPFS node,
    and returns their IPFS details.
    """
    results = []
    client = None  # Initialize client to None
    try:
        # aioipfs uses an async context manager for connections
        client = aioipfs.AsyncIPFS(maddr=IPFS_API_ADDR)
        
        for file in files:
            try:
                file_content = await file.read()
                
                # Add the file content to IPFS.
                # The library handles pinning by default when adding.
                res = await client.add_bytes(file_content)
                
                # The result 'res' is a dictionary, e.g., {'Name': '...', 'Hash': '...', 'Size': '...'}
                results.append({
                    "Name": file.filename,
                    "Hash": res['Hash'],
                    "Size": res['Size']
                })

            except Exception as e:
                # It's better to raise the exception to the outer handler
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload file '{file.filename}'. Error: {e}"
                )
            finally:
                await file.close()

    except Exception as e:
        # General connection error or other issues
        raise HTTPException(
            status_code=503,
            detail=f"An error occurred with the IPFS daemon. Is it running? Error: {e}"
        )
    finally:
        # Ensure the client session is closed
        if client:
            await client.close()

    return {"data": results}


@app.post("/api/v2/unpin")
async def remove_from_ipfs(request: PinRequest):
    """
    Unpins a file from the local IPFS node based on its hash.
    """
    client = None
    try:
        client = aioipfs.AsyncIPFS(maddr=IPFS_API_ADDR)
        
        # The `rm` method on the `pin` object is used to unpin.
        unpinned_hash = await client.pin.rm(request.hash)

        # The command returns the hash of the unpinned item.
        # We can check if it matches the requested hash.
        if unpinned_hash.get('Pins', [])[0] != request.hash:
             raise HTTPException(
                status_code=404,
                detail=f"Hash '{request.hash}' was not pinned or could not be unpinned."
            )

        return {"message": f"Successfully unpinned hash: {request.hash}"}

    except Exception as e:
        # Handle cases where the hash is invalid, not found, or daemon is down
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unpin hash '{request.hash}'. Error: {e}"
        )
    finally:
        if client:
            await client.close()


@app.get("/api/v2/pins")
async def list_pinned_files():
    """
    Lists all files currently pinned to the local IPFS node.
    """
    client = None
    try:
        client = aioipfs.AsyncIPFS(maddr=IPFS_API_ADDR)
        
        # `ls` returns the raw, complex dictionary from the IPFS daemon.
        raw_pins = await client.pin.ls()
        
        # The raw response is like: {"Keys": {"<hash>": {"Type": ...}, ...}}
        # We need to parse this into a simple list of dicts for the client.
        formatted_pins = []
        if "Keys" in raw_pins and isinstance(raw_pins["Keys"], dict):
            for pin_hash, details in raw_pins["Keys"].items():
                formatted_pins.append({
                    "Hash": pin_hash,
                    "Type": details.get("Type", "N/A")
                })
        
        return {"pinned_files": formatted_pins}

    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not list pinned files. Is the IPFS daemon running? Error: {e}"
        )
    finally:
        if client:
            await client.close()


# --- Main execution block ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

