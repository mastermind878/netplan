"""Launch a real Uvicorn process, check HTTP, always stop it."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError


def main():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        port = probe.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app_final:app', '--host', '127.0.0.1', '--port', str(port)],
        cwd=Path(__file__).resolve().parents[1],
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    base = f'http://127.0.0.1:{port}'
    try:
        deadline = time.monotonic() + 15
        while True:
            if process.poll() is not None:
                raise RuntimeError('Uvicorn exited before becoming ready')
            try:
                with urlopen(base + '/health', timeout=1) as response:
                    assert json.load(response)['status'] == 'ok'
                break
            except (URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError('Uvicorn did not become ready in 15 seconds')
                time.sleep(0.1)
        with urlopen(base + '/networks/split?cidr=192.168.1.0%2F24&new_prefix=26') as response:
            assert json.load(response)['count'] == 4
        with urlopen(base + '/version') as response:
            assert json.load(response)['version'] == '1.0.0'
        with urlopen(base + '/docs') as response:
            assert response.status == 200
        print('HTTP smoke check passed: health, split, version, docs')
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == '__main__':
    main()
