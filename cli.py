import click
import requests
import os
import time

# The base URL of your running FastAPI service
# It's recommended to set this as an environment variable.
# Example: export BUNKER_API_URL="https://your-service.com/api/v2"
BASE_URL = os.environ.get("BUNKER_API_URL", "http://127.0.0.1:8000/api/v2")

# --- ASCII Art Banners ---
BUNKER_BANNER = r"""
  ____                    _
 | __ )   _   _   _ __   | | __   ___   _ __
 |  _ \  | | | | | '_ \  | |/ /  / _ \ | '__|
 | |_) | | |_| | | | | | |   <  |  __/ | |
 |____/   \__,_| |_| |_| |_|\_\  \___| |_|
                                             
"""

SUCCESS_BANNER = r"""
  ____                                              __           _ 
 / ___|   _   _    ___    ___    ___   ___   ___   / _|  _   _  | | 
 \___ \  | | | |  / __|  / __|  / _ \ / __| / __| | |_  | | | | | | 
  ___) | | |_| | | (__  | (__  |  __/ \__ \ \__ \ |  _| | |_| | | | 
 |____/   \__,_|  \___|  \___|  \___| |___/ |___/ |_|    \__,_| |_| 
"""

def format_size(size_bytes):
    """Converts bytes to KB, MB, GB, etc."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/1024**2:.2f} MB"
    else:
        return f"{size_bytes/1024**3:.2f} GB"

@click.group()
def cli():
    """
    A CLI to interact with Bunker, your personal IPFS Pinning Service.
    """
    pass

@cli.command()
@click.argument('file_path', type=click.Path(exists=True, dir_okay=False))
def upload(file_path):
    """
    Upload a single file to the IPFS node via Bunker.
    
    Example: python cli.py upload my_file.txt
    """
    click.echo(BUNKER_BANNER)
    click.echo(f"uploading {file_path} to ipfs...")
    
    # --- File Analysis ---
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    
    click.echo("\n File Upload Analysis:")
    click.echo(f"  File path: {os.path.abspath(file_path)}")
    click.echo(f"  File name: {file_name}")
    click.echo(f"  File size: {format_size(file_size)}")
    click.echo(f"  File exists: True")
    click.echo(f"  Is file: True\n")

    # Prepare file for upload
    file_handle = None
    start_time = time.time()

    try:
        file_handle = open(file_path, 'rb')
        upload_files = [
            ('files', (file_name, file_handle, 'application/octet-stream'))
        ]
        
        with requests.post(f"{BASE_URL}/add", files=upload_files, timeout=300) as r:
            r.raise_for_status()
            response_data = r.json()
            
            end_time = time.time()
            duration = end_time - start_time
            
            # --- Success Output ---
            click.echo(f"✔ Upload completed [████████████████████] 100% {duration:.0f}s")
            click.echo(SUCCESS_BANNER)
            
            # Assuming single file upload, get the first result
            result = response_data.get("data", [])[0]
            ipfs_hash = result.get("Hash")
            
            click.echo("URL:")
            click.echo(f"https://{ipfs_hash}.ipfs.dweb.link")

    except requests.exceptions.RequestException as e:
        click.echo(f"🔥 Error connecting to the pinning service: {e}", err=True)
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
    finally:
        # Correctly close the file handle
        if file_handle:
            file_handle.close()


@cli.command()
@click.argument('hash')
def remove(hash):
    """
    Unpin a file from the IPFS node by its hash.
    
    Example: python cli.py remove Qm...
    """
    try:
        response = requests.post(f"{BASE_URL}/unpin", json={"hash": hash})
        response.raise_for_status()
        click.echo(response.json().get("message"))
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
        except:
            detail = e.response.text
        click.echo(f"🔥 Error: {detail}", err=True)
    except requests.exceptions.RequestException as e:
        click.echo(f"🔥 Error connecting to the pinning service: {e}", err=True)


@cli.command('list')
def list_pins():
    """
    List all files pinned to the IPFS node.
    """
    try:
        response = requests.get(f"{BASE_URL}/pins")
        response.raise_for_status()
        data = response.json()
        pinned_files = data.get("pinned_files", [])
        
        if not pinned_files:
            click.echo("No files are currently pinned.")
            return
            
        click.echo("📌 Pinned Files:")
        for item in pinned_files:
            click.echo(f"  - Hash: {item['Hash']}, Type: {item['Type']}")
            
    except requests.exceptions.RequestException as e:
        click.echo(f"🔥 Error connecting to the pinning service: {e}", err=True)


if __name__ == "__main__":
    cli()
