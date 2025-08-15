import click
import requests
import os
import time
import sys
from tqdm import tqdm
import io

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
        
        # Create progress bar optimized for smooth updates
        progress_bar = tqdm(
            total=file_size,
            unit='B',
            unit_scale=True,
            unit_divisor=1024,
            desc=f"Uploading {file_name}",
            ncols=80,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]',
            mininterval=0.01,     # Update every 0.01 seconds for ultra-smooth
            maxinterval=0.1,      # Force update every 0.1 seconds
            miniters=1,           # Update every iteration
            smoothing=0.0,        # No smoothing for immediate updates
            dynamic_ncols=True    # Adjust to terminal width
        )
        
        # Use requests-toolbelt for real progress monitoring
        from requests_toolbelt.multipart.encoder import MultipartEncoder
        
        # Create a custom progress callback with smooth incremental updates
        class ProgressMonitor:
            def __init__(self, progress_bar, total_size):
                self.progress_bar = progress_bar
                self.total_size = total_size
                self.bytes_read = 0
                self.last_update_time = time.time()
                # Calculate small increment size (1% of file size, minimum 1KB)
                self.increment_size = max(1024, total_size // 100)
                
            def __call__(self, monitor):
                bytes_read = monitor.bytes_read
                
                if bytes_read > self.bytes_read:
                    # Calculate how much we need to update
                    bytes_to_update = bytes_read - self.bytes_read
                    
                    # Break large updates into smaller increments
                    while bytes_to_update > 0:
                        # Determine how much to update in this step
                        update_amount = min(bytes_to_update, self.increment_size)
                        
                        # Update the progress bar
                        self.progress_bar.update(update_amount)
                        self.bytes_read += update_amount
                        bytes_to_update -= update_amount
                        
                        # Small delay to make progress visible
                        if update_amount >= self.increment_size:
                            time.sleep(0.005)  # 5ms delay for smooth animation
        
        progress_monitor = ProgressMonitor(progress_bar, file_size)
        
        # Create multipart encoder with progress monitoring
        encoder = MultipartEncoder(
            fields={'files': (file_name, file_handle, 'application/octet-stream')}
        )
        
        # Create a custom encoder that monitors progress
        class MonitoredEncoder:
            def __init__(self, encoder, callback):
                self.encoder = encoder
                self.callback = callback
                self.bytes_read = 0
                self.start_time = time.time()
                self.last_activity_time = time.time()
                
            def read(self, size=-1):
                try:
                    chunk = self.encoder.read(size)
                    if chunk:
                        self.bytes_read += len(chunk)
                        self.last_activity_time = time.time()
                        self.callback(self)
                    return chunk
                except Exception as e:
                    # Handle read errors gracefully
                    raise Exception(f"Error reading file chunk: {e}")
                
            def check_timeout(self, timeout_seconds=30):
                """Check if upload has been stuck for too long"""
                if time.time() - self.last_activity_time > timeout_seconds:
                    raise Exception(f"Upload appears to be stuck. No activity for {timeout_seconds} seconds.")
            
            @property
            def content_type(self):
                return self.encoder.content_type
            
            @property
            def len(self):
                return self.encoder.len
            
            def __len__(self):
                return self.encoder.len
        
        monitored_encoder = MonitoredEncoder(encoder, progress_monitor)
        
        # Make the request with real progress monitoring
        headers = {'Content-Type': encoder.content_type}
        
        # Add session with better timeout handling
        session = requests.Session()
        
        try:
            with session.post(
                f"{BASE_URL}/add", 
                data=monitored_encoder,
                headers=headers,
                timeout=(30, 1800)  # (connection timeout, read timeout)
            ) as r:
                # Check for HTTP errors immediately
                if r.status_code >= 400:
                    error_msg = f"HTTP {r.status_code}"
                    try:
                        error_detail = r.json().get("detail", r.text)
                        error_msg += f": {error_detail}"
                    except:
                        error_msg += f": {r.text}"
                    raise Exception(error_msg)
                
                response_data = r.json()
                
                # Close progress bar and clear the line
                progress_bar.close()
                # Clear the progress bar line using ANSI escape codes
                sys.stdout.write("\033[F")  # Move cursor up one line
                sys.stdout.write("\033[K")  # Clear the line
                sys.stdout.write("\n")      # Move to next line
                sys.stdout.flush()
                
                end_time = time.time()
                duration = end_time - start_time
                
                # --- Success Output ---
                click.echo(f"✔ Upload completed in {duration:.1f}s")
                click.echo(SUCCESS_BANNER)
                
                # Assuming single file upload, get the first result
                result = response_data.get("data", [])[0]
                ipfs_hash = result.get("Hash")
                
                click.echo("URL:")
                click.echo(f"https://{ipfs_hash}.ipfs.dweb.link")

        except requests.exceptions.HTTPError as e:
            try:
                detail = e.response.json().get("detail", e.response.text)
                if e.response.status_code == 413:
                    click.echo(f"🔥 File too large: {detail}", err=True)
                elif e.response.status_code == 500:
                    click.echo(f"🔥 Server error: {detail}", err=True)
                else:
                    click.echo(f"🔥 HTTP Error {e.response.status_code}: {detail}", err=True)
            except:
                click.echo(f"🔥 HTTP Error: {e}", err=True)
        except requests.exceptions.ConnectTimeout as e:
            click.echo(f"🔥 Connection timeout: Could not connect to the server within 30 seconds", err=True)
        except requests.exceptions.ReadTimeout as e:
            click.echo(f"🔥 Upload timeout: Server did not respond within 30 minutes", err=True)
        except requests.exceptions.ConnectionError as e:
            click.echo(f"🔥 Connection error: Could not connect to the server. Is it running?", err=True)
        except requests.exceptions.ChunkedEncodingError as e:
            click.echo(f"🔥 Transfer error: The connection was interrupted during upload", err=True)
        except requests.exceptions.RequestException as e:
            click.echo(f"🔥 Network error: {e}", err=True)
        except Exception as e:
            error_msg = str(e)
            if "stuck" in error_msg.lower():
                click.echo(f"🔥 Upload stuck: {error_msg}", err=True)
            elif "reading file chunk" in error_msg.lower():
                click.echo(f"🔥 File reading error: {error_msg}", err=True)
            else:
                click.echo(f"🔥 Unexpected error: {error_msg}", err=True)

    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", e.response.text)
            if e.response.status_code == 413:
                click.echo(f"🔥 File too large: {detail}", err=True)
            elif e.response.status_code == 500:
                click.echo(f"🔥 Server error: {detail}", err=True)
            else:
                click.echo(f"🔥 HTTP Error {e.response.status_code}: {detail}", err=True)
        except:
            click.echo(f"🔥 HTTP Error: {e}", err=True)
    except requests.exceptions.ConnectTimeout as e:
        click.echo(f"🔥 Connection timeout: Could not connect to the server within 30 seconds", err=True)
    except requests.exceptions.ReadTimeout as e:
        click.echo(f"🔥 Upload timeout: Server did not respond within 30 minutes", err=True)
    except requests.exceptions.ConnectionError as e:
        click.echo(f"🔥 Connection error: Could not connect to the server. Is it running?", err=True)
    except requests.exceptions.ChunkedEncodingError as e:
        click.echo(f"🔥 Transfer error: The connection was interrupted during upload", err=True)
    except requests.exceptions.RequestException as e:
        click.echo(f"🔥 Network error: {e}", err=True)
    except Exception as e:
        error_msg = str(e)
        if "stuck" in error_msg.lower():
            click.echo(f"🔥 Upload stuck: {error_msg}", err=True)
        elif "reading file chunk" in error_msg.lower():
            click.echo(f"🔥 File reading error: {error_msg}", err=True)
        else:
            click.echo(f"🔥 Unexpected error: {error_msg}", err=True)
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