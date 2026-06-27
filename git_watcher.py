"""
이 모듈은 프로젝트 디렉토리 내의 파일 변경을 실시간으로 감지하여,
변경 사항이 발생할 때마다 자동으로 Git 스테이징(add), 커밋(commit), 그리고 푸시(push)를 수행하는 자동화 도구입니다.

주요 기능:
- watchdog 라이브러리를 사용한 파일 시스템 이벤트(생성, 수정, 삭제, 이름 변경) 실시간 감시
- .git, .venv, .agents 등 불필요한 시스템 디렉토리 감시 제외 필터링
- 디바운싱(debouncing) 적용을 통한 다수의 동시 파일 변경 동기화 에러 방지
- pythonw.exe를 활용한 윈도우 백그라운드 무음 상주 및 PID 락 파일을 이용한 중복 방지
- CLI 옵션을 통한 백그라운드 시작(--start), 종료(--stop), 상태 확인(--status) 제어
"""

import os
import sys
import time
import subprocess
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# 감시할 디렉토리 경로 지정 (현재 스크립트 위치 기준)
WORK_DIR = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(WORK_DIR, ".git-watcher-py.lock")

# 제외할 폴더 및 파일 패턴 정의
IGNORE_PATTERNS = [
    os.path.join(WORK_DIR, ".git"),
    os.path.join(WORK_DIR, ".venv"),
    os.path.join(WORK_DIR, ".agents"),
    LOCK_FILE,
]

def should_ignore(path):
    """지정된 경로가 감시 제외 대상인지 검증합니다."""
    for pattern in IGNORE_PATTERNS:
        if path.startswith(pattern) or path == pattern:
            return True
    # 추가적으로 임시 파일이나 스크립트 파일 자체 무시
    basename = os.path.basename(path)
    if basename in ["git_watcher.py", "git-watcher.ps1", "watcher-debug.log"]:
        return True
    return False

import threading
import re

class GitSyncHandler(FileSystemEventHandler):
    """파일 변경 이벤트를 처리하고 Git 동기화를 수행하는 핸들러 클래스입니다."""
    def __init__(self):
        super().__init__()
        self.timer = None
        self.lock = threading.Lock()
        # 지연 대기 시간 설정 (기본 300초 = 5분)
        self.wait_seconds = 300.0

    def on_any_event(self, event):
        # 제외 대상 경로인 경우 처리 건너뜀
        if should_ignore(event.src_path):
            return
        if hasattr(event, 'dest_path') and should_ignore(event.dest_path):
            return

        # 이벤트 발생 시마다 이전 타이머를 취소하고 새 타이머 설정 (5분 지연 동기화)
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
            self.timer = threading.Timer(self.wait_seconds, self.sync_git_changes, args=[event.event_type, os.path.basename(event.src_path)])
            self.timer.start()

    def has_security_leak(self):
        """변경된 코드 영역 내에 API Key, 패스워드 등 민감한 키워드 유출이 있는지 검사합니다."""
        try:
            # 커밋 전에 스테이징되지 않은 변경 차이점(diff) 조회
            diff_output = subprocess.check_output(["git", "diff"], cwd=WORK_DIR).decode('utf-8', errors='ignore')
            
            # API 키, 토큰, 비밀번호 등의 민감한 정보 매칭 정규식 패턴들
            patterns = [
                r'(?i)(api[_-]?key|secret|password|passwd|private[_-]?key)\s*[:=]\s*["\'][a-zA-Z0-9_\-+=/]{8,}["\']',
                r'(?i)(jwt|token|credential)\s*[:=]\s*["\'][a-zA-Z0-9_\.\-+=/]{16,}["\']',
                r'(?i)(aws_access_key_id|aws_secret_access_key)\s*[:=]'
            ]
            
            for pattern in patterns:
                if re.search(pattern, diff_output):
                    return True
        except Exception:
            pass
        return False

    def sync_git_changes(self, event_type, filename):
        """실제 Git add, commit, push 동기화를 안전하게 수행합니다."""
        with self.lock:
            self.timer = None

        try:
            # Git 변경 상태 확인
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=WORK_DIR).decode('utf-8').strip()
            if not status:
                return

            # 커밋 전 보안 유출 검사 수행
            if self.has_security_leak():
                print(f"[보안 차단] 민감 정보(API Key / 비밀번호 등) 감지! 자동 커밋 및 푸시를 일시 중지합니다.", flush=True)
                return

            print(f"[자동 동기화] {filename} 외 변경사항 감지됨 -> {int(self.wait_seconds)}초 지연 묶음 커밋 및 푸시 진행", flush=True)
            
            # Git 작업 순차 실행
            subprocess.run(["git", "add", "-A"], cwd=WORK_DIR, check=True)
            
            curr_date = time.strftime("%Y-%m-%d %H:%M:%S")
            commit_msg = f"Auto-commit: {curr_date} (Batch sync after {event_type} of {filename})"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=WORK_DIR, check=True)
            subprocess.run(["git", "push"], cwd=WORK_DIR, check=True)
            
        except Exception as e:
            print(f"Git 동기화 중 오류 발생: {e}", file=sys.stderr, flush=True)

def get_running_pid():
    """락 파일에 기록된 PID를 읽고, 해당 프로세스가 실제로 실행 중인지 검증하여 반환합니다."""
    if not os.path.exists(LOCK_FILE):
        return None

    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            pid = int(f.read().strip())
    except Exception:
        return None

    # 자기 자신 프로세스 번호는 제외
    if pid == os.getpid():
        return None

    # 윈도우 OpenProcess API를 사용한 생사 검증 (검증 완료된 안전한 방식)
    import ctypes
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_INFORMATION = 0x0400
    
    handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if handle != 0:
        kernel32.CloseHandle(handle)
        return pid
        
    return None

def start_background():
    """Start-Process 파워쉘 명령을 사용하여 자식 프로세스를 완벽히 독립된 백그라운드로 실행합니다."""
    pid = get_running_pid()
    if pid:
        print(f"git-watcher가 이미 실행 중입니다. (PID: {pid})")
        return

    # python.exe 경로 획득 (.venv 가상환경 내 경로 우선 적용)
    venv_python = os.path.join(WORK_DIR, ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else "python.exe"

    script_path = os.path.abspath(__file__)
    # 파워쉘의 Start-Process를 활용해 완벽하게 독립적인 백그라운드 프로세스로 구동
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-Command",
        f"Start-Process -FilePath '{python_exe}' -ArgumentList @('{script_path}', '--run-service') -WindowStyle Hidden -WorkingDirectory '{WORK_DIR}'"
    ]
    subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    print("git-watcher를 백그라운드에서 실행했습니다.")
    
    # 기동 대기
    time.sleep(1.0)
    pid = get_running_pid()
    if pid:
        print(f"백그라운드 PID: {pid}")

def stop_background():
    """백그라운드에서 실행 중인 프로세스를 찾아서 종료합니다."""
    pid = get_running_pid()
    if pid:
        try:
            # os.kill을 이용하여 프로세스 종료 (Windows에서 taskkill 호출)
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                os.kill(pid, 9)
            print(f"git-watcher 프로세스(PID: {pid})를 종료했습니다.")
        except Exception as e:
            print(f"프로세스 종료 실패: {e}")
        
        # 락 파일 제거
        if os.path.exists(LOCK_FILE):
            try:
                os.remove(LOCK_FILE)
            except Exception:
                pass
    else:
        print("실행 중인 git-watcher 프로세스를 찾을 수 없습니다.")

def print_status():
    """현재 프로세스의 실행 상태를 확인하여 출력합니다."""
    pid = get_running_pid()
    if pid:
        print(f"git-watcher가 실행 중입니다. (PID: {pid})")
    else:
        print("git-watcher가 실행 중이 아닙니다.")

def main():
    # pythonw.exe 등 표준 출력이 없는 환경 대응 (로그 파일로 리다이렉션)
    if sys.stdout is None:
        log_file = os.path.join(WORK_DIR, "watcher-debug.log")
        sys.stdout = open(log_file, "a", encoding="utf-8", buffering=1)
    if sys.stderr is None:
        log_file = os.path.join(WORK_DIR, "watcher-debug.log")
        sys.stderr = open(log_file, "a", encoding="utf-8", buffering=1)

    parser = argparse.ArgumentParser(description="Git Watcher CLI")
    parser.add_argument("--start", action="store_true", help="백그라운드 감시 시작")
    parser.add_argument("--stop", action="store_true", help="백그라운드 감시 종료")
    parser.add_argument("--status", action="store_true", help="감시 상태 확인")
    parser.add_argument("--run-service", action="store_true", help="백그라운드 서비스 실제 실행 (내부용)")
    args = parser.parse_args()

    # --run-service가 입력된 경우 무조건 로그 파일로 리다이렉션 (백그라운드 실행 시 출력/에러 유지 목적)
    if args.run_service:
        log_file = os.path.join(WORK_DIR, "watcher-debug.log")
        log_handle = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = log_handle
        sys.stderr = log_handle

    if args.start:
        start_background()
        sys.exit(0)
    elif args.stop:
        stop_background()
        sys.exit(0)
    elif args.status:
        print_status()
        sys.exit(0)

    # 락 파일 기록 및 중복 실행 확인
    pid = get_running_pid()
    if pid and pid != os.getpid():
        print(f"git-watcher가 이미 실행 중입니다. (PID: {pid})")
        sys.exit(0)

    with open(LOCK_FILE, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))

    # 감시자 프로세스 시작
    event_handler = GitSyncHandler()
    observer = Observer()
    
    # 실제 개발 작업이 일어나는 소스 디렉토리(yes24)만 선택하여 하위 감시(recursive=True)를 적용 (.venv 및 .git 유실 크래시 방지)
    target_src = os.path.join(WORK_DIR, "yes24")
    if os.path.exists(target_src):
        observer.schedule(event_handler, path=target_src, recursive=True)
    else:
        # yes24 디렉토리가 없으면 루트를 감시하되 안전을 위해 예외 처리
        observer.schedule(event_handler, path=WORK_DIR, recursive=True)
        
    observer.start()

    print(f"git-watcher가 시작되었습니다. (PID: {os.getpid()})")
    print(f"감시 대상 경로: {WORK_DIR}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
    
    # 종료 시 락 파일 제거
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
        except Exception:
            pass
    print("git-watcher가 종료되었습니다.")

if __name__ == "__main__":
    main()
