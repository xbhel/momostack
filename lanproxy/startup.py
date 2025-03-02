import subprocess
from typing import Dict


def parse_command_args() -> Dict[str, str]:
    from sys import argv

    args = argv[1:]
    if len(args) % 2:
        raise RuntimeError("Malformed parameter format.")
    return {k: v for k, v in zip(args[0::2], args[1::2])}


def exec_shell(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(command.split(), check=True, capture_output=True)


def download_frp(version: str, output_path: str) -> str:
    retries = 0
    while retries <= 3:
        url = f"https://github.com/fatedier/frp/releases/download/v{version}/frp_{version}_linux_amd64.tar.gz"
        status = exec_shell(f'curl -sfL -w %{{http_code}} -o {output_path} {url}').stdout
        if status == 200:
            break
        retries += 1
    if status != 200:
        raise RuntimeError("Failed to download frp.")
    return output_path


def build_docker_image(options: Dict[str, str]):
    mode = options["-m"]
    service = {"client": "frpc", "server": "frps"}[mode]
    tmp_archive_path = "./frp.tar.gz"
    local_archive_path = options.get("-f")

    if not local_archive_path:
        version = options.get("-v", "0.61.1")
        local_archive_path = download_frp(version, tmp_archive_path)

    exec_shell(f"cp {local_archive_path} {tmp_archive_path}")
    exec_shell(f"docker image build -f Dockerfile.{service} -t lanproxy:{mode} .")
    exec_shell(f"rm -rf build {tmp_archive_path}.")


if __name__ == "__main__":
    build_docker_image(parse_command_args())
