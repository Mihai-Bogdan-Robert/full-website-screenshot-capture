#!/usr/bin/env python3
"""
webcapture — CLI tool for website screenshot capture.

Communicates with the backend container via HTTP.
The backend must be running before you use this tool:

    docker-compose up -d          (from the website-capture folder)

Usage:
    webcapture capture <domain> [options]
    webcapture status  <job_id>
    webcapture cancel  <job_id>

Examples:
    webcapture capture example.com
    webcapture capture https://example.com --mode crawl --device mobile
    webcapture capture example.com --mode both --device both --max 50
    webcapture capture example.com --output ./my-screenshots
    webcapture status  3f2a1b...
    webcapture cancel  3f2a1b...

Environment:
    WEBCAPTURE_API    Backend URL (default: http://localhost:5000)
"""

import argparse
import base64
import os
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌  'requests' is not installed. Run:  pip install requests")
    sys.exit(1)

BACKEND_URL = os.environ.get('WEBCAPTURE_API', 'http://localhost:5000').rstrip('/')

# Terminal width for the progress bar
BAR_WIDTH = 35


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def _get(path, **kw):
    return requests.get(f"{BACKEND_URL}{path}", timeout=10, **kw)


def _post(path, **kw):
    return requests.post(f"{BACKEND_URL}{path}", timeout=10, **kw)


def check_backend():
    """Raise SystemExit if the backend is unreachable."""
    try:
        r = _get('/api/health')
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        print(f"\n❌  Cannot connect to the backend at {BACKEND_URL}")
        print("    Make sure the container is running:")
        print("        docker-compose up -d\n")
        sys.exit(1)
    except requests.exceptions.RequestException as exc:
        print(f"\n❌  Backend health check failed: {exc}\n")
        sys.exit(1)


def start_job(domain, modes, devices, max_pages):
    r = _post('/api/capture/start', json={
        'domain': domain,
        'max_pages': max_pages,
        'discovery_modes': modes,
        'devices': devices,
    })
    r.raise_for_status()
    return r.json()['job_id']


def get_progress(job_id):
    r = _get(f'/api/capture/progress/{job_id}')
    r.raise_for_status()
    return r.json()


def cancel_job(job_id):
    r = _post(f'/api/capture/cancel/{job_id}')
    r.raise_for_status()
    return r.json()


def download_zip(job_id, output_dir):
    """Stream the ZIP archive of screenshots to disk."""
    r = requests.get(
        f"{BACKEND_URL}/api/capture/download/{job_id}",
        stream=True,
        timeout=120,
    )
    r.raise_for_status()

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    zip_path = out / f"screenshots-{job_id[:8]}.zip"

    with open(zip_path, 'wb') as fh:
        for chunk in r.iter_content(chunk_size=8192):
            fh.write(chunk)

    return zip_path


def save_screenshots(job_data, output_dir):
    """Decode base64 screenshots from the progress payload and save to disk."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    for shot in job_data.get('screenshots_data', []):
        dest = out / shot['filename']
        dest.write_bytes(base64.b64decode(shot['data']))
        saved.append(dest)
    return saved


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------

def _draw_bar(percent, message):
    filled = int(BAR_WIDTH * percent / 100)
    bar = '█' * filled + '░' * (BAR_WIDTH - filled)
    label = message[:45].ljust(45)
    print(f'\r  [{bar}] {percent:3d}%  {label}', end='', flush=True)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_capture(args):
    modes   = ['sitemap', 'crawl'] if args.mode   == 'both' else [args.mode]
    devices = ['desktop', 'mobile'] if args.device == 'both' else [args.device]

    print()
    print(f"  🌐  Domain     : {args.domain}")
    print(f"  🔍  Discovery  : {', '.join(modes)}")
    print(f"  📱  Devices    : {', '.join(devices)}")
    print(f"  📄  Max pages  : {args.max_pages}")
    print(f"  📁  Output     : {args.output}")
    print()

    check_backend()

    # Start the job
    try:
        job_id = start_job(args.domain, modes, devices, args.max_pages)
    except requests.exceptions.RequestException as exc:
        print(f"❌  Failed to start job: {exc}\n")
        sys.exit(1)

    print(f"  Job ID  : {job_id}")
    print(f"  Track   : {BACKEND_URL}/api/capture/progress/{job_id}\n")
    print("  Progress:")

    # Poll until done
    try:
        while True:
            data = get_progress(job_id)
            status  = data.get('status', '')
            percent = data.get('progress', 0)
            message = data.get('message', '')

            _draw_bar(percent, message)

            if status == 'completed':
                print('\n')
                _print_summary(data)
                _save_and_report(data, job_id, args.output)
                print()
                break

            elif status == 'failed':
                print('\n')
                print(f"❌  Capture failed: {data.get('error', 'Unknown error')}\n")
                sys.exit(1)

            elif status == 'cancelled':
                print('\n')
                print("⏹️   Job was cancelled.\n")
                sys.exit(0)

            time.sleep(1)

    except KeyboardInterrupt:
        print('\n\n⚠️   Interrupted. Cancelling job...')
        try:
            cancel_job(job_id)
            print('    Job cancelled.\n')
        except Exception:
            pass
        sys.exit(130)


def _print_summary(data):
    print(f"  ✅  Capture complete!")
    print(f"      Screenshots : {data.get('screenshots', 0)}")
    print(f"      Failed      : {data.get('failed', 0)}")
    print(f"      URLs found  : {data.get('urls_found', 0)}")
    failed_urls = data.get('failed_urls', [])
    if failed_urls:
        print(f"\n  ⚠️   Failed URLs ({len(failed_urls)}):")
        for url in failed_urls[:10]:
            print(f"      • {url}")
        if len(failed_urls) > 10:
            print(f"      … and {len(failed_urls) - 10} more")


def _save_and_report(data, job_id, output_dir):
    shots = data.get('screenshots_data', [])
    if not shots:
        print("\n  ⚠️   No screenshot data in response.")
        return
    print(f"\n  💾  Saving {len(shots)} screenshots → {output_dir}")
    saved = save_screenshots(data, output_dir)
    print(f"      {len(saved)} file(s) written.")

    # Also offer a zip download via the dedicated endpoint
    try:
        zip_path = download_zip(job_id, output_dir)
        print(f"      ZIP archive  → {zip_path}")
    except Exception:
        pass  # ZIP endpoint is a convenience; failure is non-fatal


def cmd_status(args):
    check_backend()
    try:
        data = get_progress(args.job_id)
    except requests.exceptions.RequestException as exc:
        print(f"\n❌  {exc}\n")
        sys.exit(1)

    print()
    print(f"  Job ID    : {data['job_id']}")
    print(f"  Status    : {data['status']}")
    print(f"  Progress  : {data['progress']}%")
    print(f"  Message   : {data['message']}")
    print(f"  Captured  : {data.get('screenshots', 0)}")
    print(f"  Failed    : {data.get('failed', 0)}")
    if data.get('completed_at'):
        print(f"  Completed : {data['completed_at']}")
    print()


def cmd_cancel(args):
    check_backend()
    try:
        cancel_job(args.job_id)
        print(f"\n  ✅  Cancelled job {args.job_id}\n")
    except requests.exceptions.RequestException as exc:
        print(f"\n❌  {exc}\n")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        prog='webcapture',
        description='Website screenshot capture — CLI client for the logik backend',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest='command', required=True)

    # ---- capture ----
    cap = sub.add_parser('capture', help='Capture screenshots of a website')
    cap.add_argument('domain', help='Domain or URL to capture (e.g. example.com)')
    cap.add_argument(
        '--mode', choices=['sitemap', 'crawl', 'both'], default='sitemap',
        help='URL discovery method (default: sitemap)',
    )
    cap.add_argument(
        '--device', choices=['desktop', 'mobile', 'both'], default='desktop',
        help='Viewport/device type (default: desktop)',
    )
    cap.add_argument(
        '--max', dest='max_pages', type=int, default=200, metavar='N',
        help='Maximum pages to capture (default: 200)',
    )
    cap.add_argument(
        '--output', default='./screenshots', metavar='DIR',
        help='Output directory for screenshots (default: ./screenshots)',
    )
    cap.set_defaults(func=cmd_capture)

    # ---- status ----
    sta = sub.add_parser('status', help='Check the status of a capture job')
    sta.add_argument('job_id', help='Job ID returned by the capture command')
    sta.set_defaults(func=cmd_status)

    # ---- cancel ----
    can = sub.add_parser('cancel', help='Cancel a running capture job')
    can.add_argument('job_id', help='Job ID to cancel')
    can.set_defaults(func=cmd_cancel)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
