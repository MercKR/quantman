"""로컬앱 설정 GUI (tkinter).

KIS 자격증명 입력 · 기기 페어링 · 자동매매 시작/중지 · 상태/로그 확인을
하나의 창에서 처리한다. 트레이 상주는 tray.py가 이 창을 감싼다.

UI는 웹앱과 같은 인디고 톤으로 맞추고, 상단 상태 히어로 + 1-2-3 단계
구성으로 초중급 사용자가 설정 순서를 헷갈리지 않도록 한다.
"""

from __future__ import annotations

import socket
import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

from . import pairing, secrets_store
from .config import EQUITY_PATH, LEDGER_PATH, PLATFORM_URL
from .logging_setup import setup_logging

_LOG_PATH_NAME = "logs/localapp.log"

# 웹앱과 통일한 색상 팔레트
BG = "#f4f5f7"
PANEL = "#ffffff"
BORDER = "#e3e5ea"
TEXT = "#1a1d23"
MUTED = "#6b7280"
ACCENT = "#4f46e5"
ACCENT_DARK = "#4338ca"
GREEN = "#15803d"
AMBER = "#b45309"
SLATE = "#475569"


def _read_json(path, default):
    import json
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


class SettingsApp:
    """로컬앱 메인 설정 창."""

    def __init__(self):
        setup_logging()
        self.scheduler = None
        self.on_close_to_tray = None     # tray.py가 주입

        self.root = tk.Tk()
        self.root.title("퀀트 플랫폼 — 로컬앱")
        self.root.geometry("560x740")
        self.root.resizable(False, True)
        self._apply_theme()
        self._build()
        self.refresh_status()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 테마 ──────────────────────────────────────────────────────────────────

    def _apply_theme(self):
        self.root.configure(bg=BG)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=TEXT,
                         font=("Segoe UI", 10))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=TEXT)
        style.configure("Muted.TLabel", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9))
        style.configure("TLabelframe", background=BG, bordercolor=BORDER,
                        relief="solid", borderwidth=1)
        style.configure("TLabelframe.Label", background=BG, foreground=TEXT,
                        font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground=PANEL, bordercolor=BORDER,
                        borderwidth=1, padding=4)

        style.configure("TButton", background=PANEL, foreground=TEXT,
                        bordercolor=BORDER, borderwidth=1, padding=(12, 7),
                        font=("Segoe UI", 10))
        style.map("TButton",
                  background=[("active", "#eef0f3"),
                              ("disabled", "#f0f1f3")],
                  foreground=[("disabled", "#a8abb3")])
        style.configure("Accent.TButton", background=ACCENT,
                        foreground="#ffffff", bordercolor=ACCENT,
                        padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", ACCENT_DARK),
                              ("disabled", "#c7c9d1")],
                  foreground=[("disabled", "#ffffff")])

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build(self):
        pad = {"padx": 12, "pady": (4, 6)}

        # 상태 히어로 — 한눈에 현재 상태를 보여준다
        self.hero = tk.Frame(self.root, bg=SLATE)
        self.hero.pack(fill="x", padx=12, pady=(12, 4))
        self.hero_label = tk.Label(self.hero, text="", bg=SLATE, fg="#ffffff",
                                   font=("Segoe UI", 14, "bold"))
        self.hero_label.pack(pady=(14, 2))
        self.hero_sub = tk.Label(self.hero, text="", bg=SLATE, fg="#e5e7eb",
                                 font=("Segoe UI", 9))
        self.hero_sub.pack(pady=(0, 14))

        # ① KIS 자격증명
        self.kf = ttk.LabelFrame(self.root, text="① KIS 모의투자 자격증명")
        self.kf.pack(fill="x", **pad)
        ttk.Label(self.kf, style="Muted.TLabel", wraplength=500, justify="left",
                  text="한국투자증권 모의투자 계좌의 App Key·Secret을 입력하세요. "
                       "키는 이 PC에만 저장되며 플랫폼 서버로 전송되지 않습니다."
                  ).pack(anchor="w", padx=12, pady=(8, 4))
        self.e_key = self._labeled_entry(self.kf, "App Key")
        self.e_secret = self._labeled_entry(self.kf, "App Secret", show="*")
        self.e_acct = self._labeled_entry(self.kf, "계좌번호 (예: 50001234-01)")
        ttk.Button(self.kf, text="자격증명 저장", style="Accent.TButton",
                   command=self._save_kis).pack(anchor="e", padx=12, pady=10)

        # ② 기기 페어링
        self.pf = ttk.LabelFrame(self.root, text="② 플랫폼 계정 연결")
        self.pf.pack(fill="x", **pad)
        ttk.Label(self.pf, style="Muted.TLabel",
                  text=f"플랫폼: {PLATFORM_URL}"
                  ).pack(anchor="w", padx=12, pady=(8, 2))
        ttk.Label(self.pf, style="Muted.TLabel", wraplength=500, justify="left",
                  text="‘기기 페어링 시작’을 누르면 브라우저가 열립니다. "
                       "플랫폼에 로그인한 뒤 승인하면 연결이 끝납니다."
                  ).pack(anchor="w", padx=12, pady=(0, 4))
        self.pair_code = tk.Label(self.pf, text="", bg=BG, fg=ACCENT,
                                  font=("Segoe UI", 19, "bold"))
        self.pair_code.pack(anchor="w", padx=12, pady=2)
        self.pair_msg = ttk.Label(self.pf, style="Muted.TLabel", text="")
        self.pair_msg.pack(anchor="w", padx=12, pady=2)
        self.btn_pair = ttk.Button(self.pf, text="기기 페어링 시작",
                                   style="Accent.TButton", command=self._pair)
        self.btn_pair.pack(anchor="e", padx=12, pady=10)

        # ③ 자동매매
        self.af = ttk.LabelFrame(self.root, text="③ 자동매매")
        self.af.pack(fill="x", **pad)
        ttk.Label(self.af, style="Muted.TLabel", wraplength=500, justify="left",
                  text="시작하면 평일 오전 8시 55분에 자동으로 매매합니다. "
                       "‘지금 한 번 실행’으로 즉시 테스트할 수 있습니다."
                  ).pack(anchor="w", padx=12, pady=(8, 4))
        row = ttk.Frame(self.af)
        row.pack(fill="x", padx=12, pady=8)
        self.btn_toggle = ttk.Button(row, text="자동매매 시작",
                                     style="Accent.TButton",
                                     command=self._toggle_auto)
        self.btn_toggle.pack(side="left")
        self.btn_cycle = ttk.Button(row, text="지금 한 번 실행",
                                    command=self._run_once)
        self.btn_cycle.pack(side="left", padx=8)
        self.cycle_msg = ttk.Label(self.af, style="Muted.TLabel", text="")
        self.cycle_msg.pack(anchor="w", padx=12, pady=(2, 8))

        # 활동 로그
        lf = ttk.LabelFrame(self.root, text="활동 로그")
        lf.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(lf, height=8, font=("Consolas", 8),
                                state="disabled", wrap="none",
                                bg=PANEL, fg=TEXT, relief="solid",
                                borderwidth=1, highlightthickness=0)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(10, 4))
        ttk.Button(lf, text="새로고침", command=self.refresh_status).pack(
            anchor="e", padx=12, pady=(0, 10))

    def _labeled_entry(self, parent, label, show=None):
        ttk.Label(parent, text=label).pack(anchor="w", padx=12, pady=(6, 1))
        e = ttk.Entry(parent, show=show or "", font=("Segoe UI", 10))
        e.pack(fill="x", padx=12)
        return e

    # ── 상태 갱신 ─────────────────────────────────────────────────────────────

    def _set_hero(self, text, sub, color):
        self.hero.configure(bg=color)
        self.hero_label.configure(text=text, bg=color)
        self.hero_sub.configure(text=sub, bg=color)

    def refresh_status(self):
        kis = secrets_store.load_kis()
        dev = secrets_store.load_device_token()
        running = bool(self.scheduler and self.scheduler.running)

        # 히어로 — 전체 상태 한 줄
        if not kis or not dev:
            missing = []
            if not kis:
                missing.append("KIS 자격증명")
            if not dev:
                missing.append("기기 페어링")
            self._set_hero("설정 미완료",
                           " · ".join(missing) + " 을(를) 완료하세요", AMBER)
        elif running:
            self._set_hero("자동매매 실행 중",
                           "평일 장 시작 전 자동으로 매매합니다", GREEN)
        else:
            self._set_hero("준비 완료 · 중지됨",
                           "‘자동매매 시작’을 누르면 가동됩니다", SLATE)

        # 단계 헤더에 진행 상태 표시
        self.kf.configure(
            text="① KIS 모의투자 자격증명        "
                 + ("✓ 등록됨" if kis else "입력 필요"))
        self.pf.configure(
            text="② 플랫폼 계정 연결        "
                 + ("✓ 완료" if dev else "미완료"))
        self.af.configure(
            text="③ 자동매매        " + ("실행 중" if running else "중지됨"))
        self.btn_toggle.config(text="자동매매 중지" if running else "자동매매 시작")

        if kis:
            self.e_key.delete(0, "end")
            self.e_key.insert(0, kis["app_key"])
            self.e_acct.delete(0, "end")
            self.e_acct.insert(0, kis["account_no"])

        eq = _read_json(EQUITY_PATH, [])
        led = _read_json(LEDGER_PATH, {})
        if eq:
            self.cycle_msg.config(
                text=f"최근 평가금액 {eq[-1]['value']:,}원 · 보유 {len(led)}종목"
                     f" · {eq[-1]['date']}")
        self._load_log_tail()

    def _load_log_tail(self):
        from .config import APP_DIR
        log_file = APP_DIR / _LOG_PATH_NAME
        text = ""
        if log_file.exists():
            lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
            text = "\n".join(lines[-200:])
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("1.0", text)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    # ── 백그라운드 작업 ───────────────────────────────────────────────────────

    def _run_bg(self, fn, on_done):
        def worker():
            try:
                res = fn()
                self.root.after(0, lambda: on_done(res, None))
            except Exception as e:
                self.root.after(0, lambda: on_done(None, e))
        threading.Thread(target=worker, daemon=True).start()

    # ── 동작 ──────────────────────────────────────────────────────────────────

    def _save_kis(self):
        key = self.e_key.get().strip()
        secret = self.e_secret.get().strip()
        acct = self.e_acct.get().strip()
        if not (key and secret and acct):
            messagebox.showwarning("입력 확인", "App Key/Secret/계좌번호를 모두 입력하세요.")
            return
        secrets_store.save_kis(key, secret, acct, virtual=True)
        self.e_secret.delete(0, "end")
        messagebox.showinfo("저장 완료",
                            "KIS 자격증명을 저장했습니다. 키는 이 PC를 떠나지 않습니다.")
        self.refresh_status()

    def _pair(self):
        self.btn_pair.config(state="disabled")
        self.pair_msg.config(text="페어링 코드 발급 중...")

        def start():
            return pairing.start_pairing(socket.gethostname() or "내 PC")

        def started(info, err):
            if err:
                self.pair_msg.config(text=f"오류: {err}")
                self.btn_pair.config(state="normal")
                return
            self.pair_code.config(text=info["user_code"])
            self.pair_msg.config(
                text="브라우저에서 로그인 후 승인 버튼을 누르세요. 승인 대기 중...")
            # 코드가 미리 채워진 URL로 연다(구버전 서버 대비 fallback)
            webbrowser.open(info.get("verification_uri_complete")
                            or info["verification_uri"])

            def poll():
                return pairing.poll_for_token(info["device_code"])

            def polled(_tok, e):
                self.btn_pair.config(state="normal")
                if e:
                    self.pair_msg.config(text=f"페어링 실패: {e}")
                else:
                    self.pair_code.config(text="")
                    self.pair_msg.config(text="페어링 완료.")
                    self.refresh_status()

            self._run_bg(poll, polled)

        self._run_bg(start, started)

    def _toggle_auto(self):
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
            self.refresh_status()
            return
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        self.scheduler = BackgroundScheduler(timezone="Asia/Seoul")
        self.scheduler.add_job(
            self._cycle_job,
            CronTrigger(day_of_week="mon-fri", hour=8, minute=55,
                        timezone="Asia/Seoul"),
            id="paper_cycle", misfire_grace_time=300)
        self.scheduler.start()
        self.refresh_status()

    def _cycle_job(self):
        from .runner import run_cycle
        run_cycle(use_mock=secrets_store.load_kis() is None)

    def _run_once(self):
        self.btn_cycle.config(state="disabled")
        self.cycle_msg.config(text="실행 중... (시세 수집에 시간이 걸릴 수 있습니다)")

        def job():
            from .runner import run_cycle
            return run_cycle(use_mock=secrets_store.load_kis() is None)

        def done(payload, err):
            self.btn_cycle.config(state="normal")
            if err:
                self.cycle_msg.config(text=f"오류: {err}")
            else:
                b = payload["balance"]
                self.cycle_msg.config(
                    text=f"완료 — 평가금액 {b['total_eval']:,}원 · "
                         f"보유 {len(payload['positions'])}종목 · "
                         f"체결 {len(payload['trades'])}건")
            self.refresh_status()

        self._run_bg(job, done)

    def _on_close(self):
        if self.on_close_to_tray:
            self.on_close_to_tray()        # 트레이로 숨김
        else:
            if self.scheduler and self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    SettingsApp().run()


if __name__ == "__main__":
    main()
