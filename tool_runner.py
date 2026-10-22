"""Execute the CDS analysis tools on Linux or Windows/WSL."""
from pathlib import Path
import os
import re
import subprocess
import uuid
from settings import TOOL_PATH, DATASETS_BIN, MAFFT_BIN, RAXML_BIN

def linux_path(path):
    path = Path(path).resolve()
    if os.name != 'nt':
        return str(path)
    if not re.fullmatch(r'[A-Za-z]:', path.drive):
        raise ValueError('解析保存先はWindowsのローカルドライブを指定してください。')
    return '/mnt/' + path.drive[0].lower() + path.as_posix()[2:]


def run_tool(args, cwd=None, output=None, timeout=3600):
    import shlex
    import tempfile
    # Linux-side files avoid WSL pipe /dev/stderr permission failures in MAFFT.
    temporary = tempfile.TemporaryDirectory(prefix="phylogpt_tool_") if cwd is None else None
    folder = Path(cwd if cwd is not None else temporary.name).resolve()
    token = uuid.uuid4().hex[:10]
    stdout_file = Path(output).resolve() if output is not None else folder / f"tool_{token}.stdout.log"
    stderr_file = folder / f"tool_{token}.stderr.log"
    prefix = ['wsl', '--exec', '/usr/bin/env'] if os.name == 'nt' else ['env']
    prefix += ['--chdir=' + linux_path(folder)]
    if TOOL_PATH:
        prefix.append('PATH=' + TOOL_PATH)
    command = shlex.join(['timeout', '--signal=TERM', '--kill-after=10s', str(timeout)] + list(args))
    command += ' > ' + shlex.quote(linux_path(stdout_file)) + ' 2> ' + shlex.quote(linux_path(stderr_file))
    flags = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
    try:
        result = subprocess.run(prefix + ['bash', '-c', command], capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=timeout + 30, **flags)
        stdout = stdout_file.read_text(encoding='utf-8', errors='replace') if output is None and stdout_file.exists() else ''
        stderr = stderr_file.read_text(encoding='utf-8', errors='replace') if stderr_file.exists() else ''
        if result.returncode:
            raise RuntimeError(f'{args[0]} の実行に失敗しました（終了コード {result.returncode}）。\n{(stderr or result.stderr or stdout)[-4000:]}')
        return stdout or (stderr if output is None else '')
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f'{args[0]} が制限時間を超えました。ログと実行環境を確認してください。') from exc
    finally:
        if temporary is not None:
            temporary.cleanup()


def check_tools():
    versions = {}
    for tool, flag in [(DATASETS_BIN, '--version'), (MAFFT_BIN, '--version'), (RAXML_BIN, '--version')]:
        # MAFFT writes its version to stderr, so probe with shell-free subprocess directly.
        try:
            versions[tool] = run_tool([tool, flag], timeout=60).strip() or '実行確認済み'
        except Exception as exc:
            versions[tool] = '未確認: ' + str(exc)
    return versions


