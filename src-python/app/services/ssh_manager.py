import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import asyncssh
from asyncssh.constants import (
    FILEXFER_TYPE_DIRECTORY,
    FILEXFER_TYPE_SYMLINK,
    FILEXFER_TYPE_UNKNOWN,
)

from app.models.types import (
    BashEnvironmentInfo,
    CommandCompletion,
    ConnectionInfo,
    SftpFileDetails,
    SftpFileInfo,
    SSHConnectionStatus,
    TerminalOutput,
)


class SSHManager:
    def __init__(self):
        self._connection: Optional[asyncssh.SSHClientConnection] = None
        self._sftp: Optional[asyncssh.SFTPClient] = None
        self._connection_info: Optional[ConnectionInfo] = None
        self._terminal_sessions: Dict[str, Any] = {}
        self._terminal_session_locks: Dict[str, asyncio.Lock] = {}
        self._connected = False
        self._host = ""
        self._port = 22
        self._username = ""

    async def _open_terminal_process(
        self, cols: int, rows: int
    ) -> Tuple[Any, Any, Any, Any]:
        term_size = asyncssh.TerminalSize(rows, cols, 0, 0)
        shell_candidates: List[Tuple[Optional[str], float]] = [
            (None, 2.5),
            ("bash --noprofile --norc -i", 2.0),
            ("sh -i", 2.0),
        ]
        last_timeout: Optional[Exception] = None

        for command, timeout in shell_candidates:
            try:
                process = await asyncio.wait_for(
                    self._connection.create_process(
                        command,
                        term_type="xterm-256color",
                        term_size=term_size,
                        encoding=None,
                    ),
                    timeout=timeout,
                )
                return process.channel, process.stdin, process.stdout, process.stderr
            except asyncio.TimeoutError as exc:
                last_timeout = exc
                continue

        if last_timeout is not None:
            raise TimeoutError("创建终端通道超时，请重试")
        raise RuntimeError("创建终端通道失败")

    async def connect(
        self,
        host: str,
        port: int,
        username: str,
        password: Optional[str] = None,
        private_key: Optional[str] = None,
        key_passphrase: Optional[str] = None,
    ) -> str:
        if self._connected:
            await self.disconnect()

        kwargs: Dict[str, Any] = {
            "host": host,
            "port": port,
            "username": username,
            "known_hosts": None,
            "connect_timeout": 8,
            "login_timeout": 8,
            "keepalive_interval": 20,
            "keepalive_count_max": 3,
        }

        if password:
            kwargs["password"] = password
        if private_key:
            if os.path.isfile(private_key):
                kwargs["client_keys"] = [private_key]
                if key_passphrase:
                    kwargs["passphrase"] = key_passphrase
            else:
                kwargs["client_keys"] = [private_key]

        self._connection = await asyncssh.connect(**kwargs)
        self._connected = True
        self._host = host
        self._port = port
        self._username = username
        self._connection_info = ConnectionInfo(
            host=host,
            port=port,
            username=username,
            auth_method="key" if private_key else "password",
        )
        return f"已连接到 {username}@{host}:{port}"

    async def disconnect(self) -> None:
        await self.close_all_terminal_sessions()
        if self._sftp:
            self._sftp.exit()
            self._sftp = None
        if self._connection:
            self._connection.close()
            await self._connection.wait_closed()
            self._connection = None
        self._connected = False
        self._connection_info = None

    def is_connected(self) -> bool:
        return self._connected and self._connection is not None

    async def execute_command(self, command: str) -> TerminalOutput:
        if not self.is_connected():
            raise ConnectionError("没有活动的 SSH 连接")
        try:
            result = await self._connection.run(command, check=False)
            return TerminalOutput.create(
                command=command, output=result.stdout, exit_code=result.exit_status
            )
        except Exception as e:
            return TerminalOutput.create(command=command, output=str(e), exit_code=-1)

    async def execute_dashboard_command(self, command: str) -> TerminalOutput:
        return await self.execute_command(command)

    async def execute_dashboard_command_as_user(
        self, command: str, username: Optional[str] = None
    ) -> TerminalOutput:
        if username and username != self._username:
            return await self.execute_command(f"sudo -u {username} {command}")
        return await self.execute_command(command)

    async def get_connection_status(self) -> Optional[SSHConnectionStatus]:
        if not self.is_connected():
            return None
        return SSHConnectionStatus(
            connected=True,
            host=self._host,
            port=self._port,
            username=self._username,
            last_activity=datetime.now(timezone.utc),
        )

    async def _ensure_sftp(self) -> asyncssh.SFTPClient:
        if not self.is_connected():
            raise ConnectionError("没有活动的 SSH 连接")
        if self._sftp is None:
            self._sftp = await self._connection.start_sftp_client()
        return self._sftp

    @staticmethod
    def _join_remote(path: str, name: str) -> str:
        if path == "/":
            return f"/{name}"
        return f"{path.rstrip('/')}/{name}"

    @staticmethod
    def _sftp_entry_filename(entry: Any) -> str:
        """asyncssh.SFTPName 字段为 filename（str 或 bytes），无 name 属性。"""
        raw = getattr(entry, "filename", None) or getattr(entry, "name", "") or ""
        if isinstance(raw, (bytes, bytearray)):
            return bytes(raw).decode("utf-8", errors="surrogateescape")
        return str(raw)

    @staticmethod
    def _perm_to_str(mode: Optional[int]) -> Optional[str]:
        if mode is None:
            return None
        perms = []
        file_type = "d" if (mode & 0o40000) else ("l" if (mode & 0o120000) else "-")
        perms.append(file_type)
        for shift in (6, 3, 0):
            p = (mode >> shift) & 0b111
            perms.append("r" if p & 0b100 else "-")
            perms.append("w" if p & 0b010 else "-")
            perms.append("x" if p & 0b001 else "-")
        return "".join(perms)

    @staticmethod
    def _epoch_to_iso(ts: Optional[int]) -> Optional[str]:
        """SFTP 时间戳在部分服务器上异常，fromtimestamp 可能抛 OSError/OverflowError。"""
        if ts is None:
            return None
        try:
            t = int(ts)
            if t <= 0:
                return None
            return datetime.fromtimestamp(t, tz=timezone.utc).isoformat()
        except (OSError, OverflowError, ValueError):
            return None

    @staticmethod
    def _classify_sftp_entry(attrs: Optional[asyncssh.SFTPAttrs]) -> Tuple[str, bool]:
        """结合 SFTPv4+ type 与 POSIX mode 判断目录/链接/文件。"""
        mode = attrs.permissions if attrs else None
        file_type = "file"
        is_dir = False
        if attrs is not None and attrs.type != FILEXFER_TYPE_UNKNOWN:
            if attrs.type == FILEXFER_TYPE_DIRECTORY:
                return "directory", True
            if attrs.type == FILEXFER_TYPE_SYMLINK:
                return "symlink", False
        if mode is not None:
            if mode & 0o40000:
                return "directory", True
            if mode & 0o120000:
                return "symlink", False
        return file_type, is_dir

    async def list_sftp_files(self, path: str) -> List[SftpFileInfo]:
        sftp = await self._ensure_sftp()
        out: List[SftpFileInfo] = []
        for entry in await sftp.readdir(path):
            fname = self._sftp_entry_filename(entry)
            attrs = entry.attrs
            mode = attrs.permissions if attrs else None
            file_type, is_dir = self._classify_sftp_entry(attrs)
            out.append(
                SftpFileInfo(
                    name=fname,
                    path=self._join_remote(path, fname),
                    file_type=file_type,
                    is_dir=is_dir,
                    size=(attrs.size if attrs and attrs.size is not None else 0),
                    modified=self._epoch_to_iso(attrs.mtime if attrs else None),
                    permissions=self._perm_to_str(mode),
                )
            )
        return out

    async def read_sftp_file(self, path: str) -> bytes:
        sftp = await self._ensure_sftp()
        async with sftp.open(path, "rb") as f:
            return await f.read()

    async def write_sftp_file(self, path: str, content: bytes) -> None:
        sftp = await self._ensure_sftp()
        async with sftp.open(path, "wb") as f:
            await f.write(content)

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        sftp = await self._ensure_sftp()
        await asyncssh.sftp_put(local_path, remote_path, sftp=sftp)

    async def download_file(self, remote_path: str, local_path: str) -> None:
        sftp = await self._ensure_sftp()
        await asyncssh.sftp_get(remote_path, local_path, sftp=sftp)

    async def create_directory(self, remote_path: str) -> None:
        sftp = await self._ensure_sftp()
        await sftp.mkdir(remote_path)

    async def chmod_sftp(self, path: str, mode: int) -> None:
        sftp = await self._ensure_sftp()
        await sftp.chmod(path, mode)

    async def get_file_details(self, path: str) -> SftpFileDetails:
        sftp = await self._ensure_sftp()
        attrs = await sftp.stat(path)
        mode = attrs.permissions if attrs else None
        file_type, _is_dir = self._classify_sftp_entry(attrs)
        crtime = getattr(attrs, "crtime", None) if attrs else None
        return SftpFileDetails(
            name=path.rsplit("/", 1)[-1],
            path=path,
            file_type=file_type,
            size=(attrs.size if attrs and attrs.size is not None else 0),
            permissions=self._perm_to_str(mode) or "",
            owner=str(attrs.uid) if attrs and attrs.uid is not None else None,
            group=str(attrs.gid) if attrs and attrs.gid is not None else None,
            created=self._epoch_to_iso(crtime),
            modified=self._epoch_to_iso(attrs.mtime if attrs else None),
            accessed=self._epoch_to_iso(attrs.atime if attrs else None),
        )

    async def compress_file(self, source_path: str, target_path: str, fmt: str) -> None:
        if fmt in ("tar.gz", "tgz"):
            cmd = f'tar -czf "{target_path}" -C "{source_path}" .'
        elif fmt == "tar":
            cmd = f'tar -cf "{target_path}" -C "{source_path}" .'
        elif fmt in ("tar.bz2", "tbz2"):
            cmd = f'tar -cjf "{target_path}" -C "{source_path}" .'
        elif fmt == "zip":
            cmd = f'cd "{source_path}" && zip -r "{target_path}" .'
        else:
            cmd = f'tar -czf "{target_path}" -C "{source_path}" .'
        result = await self.execute_command(cmd)
        if result.exit_code and result.exit_code != 0:
            raise RuntimeError(result.output)

    async def extract_file(self, archive_path: str, target_dir: str) -> None:
        if archive_path.endswith((".tar.gz", ".tgz")):
            cmd = f'mkdir -p "{target_dir}" && tar -xzf "{archive_path}" -C "{target_dir}"'
        elif archive_path.endswith((".tar.bz2", ".tbz2")):
            cmd = f'mkdir -p "{target_dir}" && tar -xjf "{archive_path}" -C "{target_dir}"'
        elif archive_path.endswith(".tar"):
            cmd = (
                f'mkdir -p "{target_dir}" && tar -xf "{archive_path}" -C "{target_dir}"'
            )
        elif archive_path.endswith(".zip"):
            cmd = f'mkdir -p "{target_dir}" && unzip -o "{archive_path}" -d "{target_dir}"'
        else:
            cmd = f'mkdir -p "{target_dir}" && tar -xzf "{archive_path}" -C "{target_dir}"'
        result = await self.execute_command(cmd)
        if result.exit_code and result.exit_code != 0:
            raise RuntimeError(result.output)

    async def create_terminal_session(
        self, terminal_id: str, cols: int = 80, rows: int = 24
    ) -> str:
        if not self.is_connected():
            raise ConnectionError("没有活动的 SSH 连接")

        lock = self._terminal_session_locks.setdefault(terminal_id, asyncio.Lock())
        async with lock:
            if terminal_id in self._terminal_sessions:
                return terminal_id

            channel, stdin, stdout, stderr = await self._open_terminal_process(
                cols, rows
            )

            self._terminal_sessions[terminal_id] = {
                "channel": channel,
                "stdin": stdin,
                "stdout": stdout,
                "stderr": stderr,
                "cols": cols,
                "rows": rows,
            }
            return terminal_id

    async def close_terminal_session(self, terminal_id: str) -> None:
        session = self._terminal_sessions.pop(terminal_id, None)
        self._terminal_session_locks.pop(terminal_id, None)
        if session:
            try:
                session["channel"].close()
            except Exception:
                pass

    async def close_all_terminal_sessions(self) -> None:
        for tid in list(self._terminal_sessions.keys()):
            await self.close_terminal_session(tid)

    async def send_terminal_input(self, terminal_id: str, data: bytes) -> None:
        session = self._terminal_sessions.get(terminal_id)
        if not session:
            raise ValueError(f"终端会话不存在: {terminal_id}")
        session["stdin"].write(data)
        await session["stdin"].drain()

    async def read_terminal_output(self, terminal_id: str) -> bytes:
        session = self._terminal_sessions.get(terminal_id)
        if not session:
            raise ValueError(f"终端会话不存在: {terminal_id}")
        try:
            data = await asyncio.wait_for(session["stdout"].read(4096), timeout=0.1)
            return data if data else b""
        except asyncio.TimeoutError:
            return b""
        except Exception:
            return b""

    async def resize_terminal(self, terminal_id: str, cols: int, rows: int) -> None:
        session = self._terminal_sessions.get(terminal_id)
        if not session:
            raise ValueError(f"终端会话不存在: {terminal_id}")
        session["cols"] = cols
        session["rows"] = rows
        session["channel"].change_terminal_size(asyncssh.TerminalSize(rows, cols, 0, 0))

    async def get_bash_environment_info(self) -> BashEnvironmentInfo:
        cmds = {
            "bash_version": "bash --version 2>/dev/null | head -1 || echo 'unknown'",
            "shell_type": "echo $SHELL 2>/dev/null || echo 'sh'",
            "ps1": "echo \"$PS1\" 2>/dev/null || echo '$ '",
            "pwd": "pwd",
            "home": "echo $HOME",
            "user": "whoami",
            "hostname": "hostname",
            "path": "echo $PATH",
        }
        out: Dict[str, str] = {}
        for k, cmd in cmds.items():
            try:
                r = await self.execute_command(cmd)
                out[k] = (r.output or "").strip()
            except Exception:
                out[k] = ""
        return BashEnvironmentInfo(**out)

    async def get_command_completion(self, input_text: str) -> CommandCompletion:
        words = input_text.split()
        completions: List[str] = []
        if not words or (len(words) == 1 and not input_text.endswith(" ")):
            common = [
                "ls",
                "cd",
                "pwd",
                "cat",
                "grep",
                "find",
                "ps",
                "top",
                "htop",
                "df",
                "du",
                "free",
                "uname",
                "whoami",
                "id",
                "groups",
                "chmod",
                "chown",
                "cp",
                "mv",
                "rm",
                "mkdir",
                "rmdir",
                "tar",
                "gzip",
                "gunzip",
                "zip",
                "unzip",
                "vim",
                "nano",
                "less",
                "more",
                "head",
                "tail",
                "ssh",
                "scp",
                "rsync",
                "wget",
                "curl",
                "systemctl",
                "service",
                "crontab",
                "history",
                "awk",
                "sed",
                "sort",
                "uniq",
                "wc",
                "tr",
            ]
            prefix = words[-1] if words else ""
            completions = [c for c in common if c.startswith(prefix)]
        else:
            last_word = words[-1]
            dir_path = "."
            if "/" in last_word:
                dir_path = last_word.rsplit("/", 1)[0] or "/"
            try:
                r = await self.execute_command(f"ls -1a {dir_path}")
                files = (r.output or "").split("\n")
                prefix = last_word.split("/")[-1]
                for f in files:
                    f = f.strip()
                    if f and f not in (".", "..") and f.startswith(prefix):
                        if "/" in last_word:
                            completions.append(
                                f"{last_word[: last_word.rfind('/') + 1]}{f}"
                            )
                        else:
                            completions.append(f)
            except Exception:
                pass
        return CommandCompletion(completions=completions, prefix=input_text)
