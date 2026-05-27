"""로컬앱 GUI 진입점 — 패키징(PyInstaller) 대상.

설정 창 + 트레이 상주. 단일 인스턴스만 허용한다.
개발 중에는 `python desktop.py`, 배포 시에는 빌드된 .exe로 실행된다.
"""

from __future__ import annotations

from localapp import single_instance
from localapp.logging_setup import setup_logging


def _enable_dpi_awareness() -> None:
    """Windows 고DPI 모니터에서 Tkinter 텍스트 흐림 해결.

    기본 Tkinter는 96 DPI 가정 → 4K·125%+ scaling 모니터에서 OS가 앱을 저해상도로
    렌더 후 stretching → blurry. Tk root 생성 *이전*에 process DPI awareness를
    설정해야 sharp 렌더. shcore.SetProcessDpiAwareness(1)=SYSTEM_AWARE (적당히
    호환 + 선명), (2)=PER_MONITOR_AWARE (멀티모니터 다른 DPI 시 더 정확하지만
    Tk 자체가 fully 지원 안 해 부작용 가능). 1로 선택.

    fallback: shcore 없는 구버전 Windows → user32.SetProcessDPIAware() 옛 API.
    """
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        # non-Windows 또는 라이브러리 부재 — 무시 (Tkinter는 그래도 동작)
        pass


def main():
    _enable_dpi_awareness()             # tkinter import 전에 호출 필수
    setup_logging(console=False)

    if not single_instance.acquire():
        import tkinter.messagebox as mb
        mb.showinfo("퀀트 플랫폼", "로컬앱이 이미 실행 중입니다.")
        return

    try:
        from localapp.tray import TrayApp
        TrayApp().run()
    finally:
        single_instance.release()


if __name__ == "__main__":
    main()
