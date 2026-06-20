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

class GitSyncHandler(FileSystemEventHandler):
    """파일 변경 이벤트를 처리하고 Git 동기화를 수행하는 핸들러 클래스입니다."""
    def __init__(self):
        super().__init__()
        self.last_sync_time = 0

    def on_any_event(self, event):
        # 제외 대상 경로인 경우 처리 건너뜀
        if should_ignore(event.src_path):
            return
        if hasattr(event, 'dest_path') and should_ignore(event.dest_path):
            return

        # 디바운싱 처리 (3초 이내에 다수의 변경이 발생하면 한 번만 실행)
        current_time = time.time()
        if current_time - self.last_sync_time < 3:
            return
        self.last_sync_time = current_time

        # 파일 변경 직후 디스크 작업이 마무리되도록 대기
        time.sleep(2)

        # Git 변경 상태 확인
        try:
            status = subprocess.check_output(["git", "status", "--porcelain"], cwd=WORK_DIR).decode('utf-8').strip()
            if status:
                filename = os.path.basename(event.src_path)
                print(f"[{event.event_type.capitalize()}] {filename} 감지 -> Git 동기화 진행")
                
                # Git 작업 순차 실행
                subprocess.run(["git", "add", "-A"], cwd=WORK_DIR, check=True)
                curr_date = time.strftime("%Y-%m-%d %H:%M:%S")
                commit_msg = f"Auto-commit: {curr_date} [{event.event_type}] {filename}"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=WORK_DIR, check=True)
                subprocess.run(["git", "push"], cwd=WORK_DIR, check=True)
        except Exception as e:
            print(f"Git 동기화 중 오류 발생: {e}", file=sys.stderr)

def get_running_pid():
    """락 파일에서 현재 실행 중인 프로세스의 PID를 가져옵니다."""
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r", encoding="utf-8") as f:
                pid = int(f.read().strip())
                # 프로세스가 실제로 존재하는지 검증 (Windows 호환)
                import ctypes
                kernel32 = ctypes.windll.kernel32
                PROCESS_QUERY_INFORMATION = 0x0400
                handle = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
                if handle != 0:
                    kernel32.CloseHandle(handle)
                    return pid
        except Exception:
            pass
    return None

def start_background():
    """pythonw.exe를 이용하여 창이 없는 백그라운드 프로세스로 스크립트를 재실행합니다."""
    pid = get_running_pid()
    if pid:
        print(f"git-watcher가 이미 실행 중입니다. (PID: {pid})")
        return

    # pythonw.exe 경로 획득 (.venv 가상환경 내 경로 우선 적용)
    venv_pythonw = os.path.join(WORK_DIR, ".venv", "Scripts", "pythonw.exe")
    python_exe = venv_pythonw if os.path.exists(venv_pythonw) else "pythonw.exe"

    script_path = os.path.abspath(__file__)
    # 창 없이 실행하기 위한 인수 구성
    subprocess.Popen([python_exe, script_path], cwd=WORK_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
    print("git-watcher를 백그라운드에서 실행했습니다.")
    
    # 락 파일 생성 대기
    time.sleep(0.5)
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
    parser = argparse.ArgumentParser(description="Git Watcher CLI")
    parser.add_argument("--start", action="store_true", help="백그라운드 감시 시작")
    parser.add_argument("--stop", action="store_true", help="백그라운드 감시 종료")
    parser.add_argument("--status", action="store_true", help="감시 상태 확인")
    args = parser.parse_args()

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
