#!/usr/bin/env python3

import sys
from subprocess import CompletedProcess, run
from typing import Dict, Optional

__author__ = "xbhel"


def exec_shell(command: str) -> CompletedProcess:
    kwargs: dict = {"check": True}
    if sys.version_info >= (3, 7):
        kwargs["capture_output"] = True
    return run(command.split(), **kwargs)


def parse_args() -> Dict[str, str]:
    _, *args = sys.argv
    if len(args) % 2:
        raise RuntimeError("Malformed parameter format.")
    return {k: v for k, v in zip(args[0::2], args[1::2])}


def download(version: str, output_path: Optional[str] = None) -> str:
    url = f"https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_linux_amd64.tar.gz"

    if not output_path:
        output_path = f"./{url.split('/')[-1]}"

    print(f"Starting download: {url} → {output_path}")

    for attempt in range(1, 4):
        resp = exec_shell(f"curl -fL -w %{{http_code}} -o {output_path} {url}")
        status_code = resp.stdout
        if status_code == 200:
            print(f"Successfully download FRP from {url} to location {output_path}.")
            return output_path

        print(f"Download failed (attempt {attempt}/3), retrying...")

    raise RuntimeError(f"Failed to download FRP from {url} after 3 attempts.")


def build_image(options: Dict[str, str]):
    service = options["--service"]
    image_name = options.get("--image-name", f"lanproxy:{service}")
    resp = exec_shell(f"docker images --filter reference={image_name}")
    has_image = len(resp.stdout.splitlines()) > 1

    if has_image:
        print(f"Skip to build the image of {image_name} due to it already exists.")
        return image_name

    version = options.get("--version", "0.61.1")
    archive_path = options.get("--archive")
    
    if not archive_path:
        archive_path = download(version)

    tmp_archive_path = "./frp.tar.gz"
    exec_shell(f"cp {archive_path} {tmp_archive_path}")
    exec_shell(f"docker image build -f dockerfiles/Dockerfile.{service} -t {image_name} .")
    exec_shell(f"rm -rf {tmp_archive_path}")
    print(f"The image '{image_name}' has been successfully build.")
    return image_name


if __name__ == '__main__':
    print(build_image(parse_args()))