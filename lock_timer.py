# lock_timer.py
# 需要 Python 3.8+（建议使用 3.10 或更高）
# 依赖：标准库（tkinter, threading, time）
# 在 Windows 上运行时请使用系统自带的 Python（tkinter 应当随 Python 一起安装）

import tkinter as tk
from tkinter import messagebox
import threading
import time
import sys

DEFAULT_LOCK_SECONDS = 5 * 60  # 5分钟锁屏时长（秒）

class LockOverlay:
    def __init__(self, lock_seconds=DEFAULT_LOCK_SECONDS):
        self.lock_seconds = lock_seconds
        self.overlay = None
        self._stop_flag = False
        self._unlocked = threading.Event()

    def show(self):
        """在主线程调用以显示覆盖窗口"""
        if self.overlay:
            return
        root = tk.Tk()
        root.title("锁屏中")
        # make window full-screen and topmost
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        # remove decorations where available
        try:
            root.overrideredirect(True)
        except Exception:
            pass

        frame = tk.Frame(root, bg="black")
        frame.pack(fill="both", expand=True)

        lbl = tk.Label(frame, text="屏幕已锁定", font=("Arial", 48), fg="white", bg="black")
        lbl.pack(pady=40)

        self.count_label = tk.Label(frame, text="", font=("Arial", 36), fg="white", bg="black")
        self.count_label.pack(pady=20)

        btn = tk.Button(frame, text="立即解锁", font=("Arial", 24), command=self._on_force_unlock)
        btn.pack(pady=30)

        hint = tk.Label(frame, text="或等待倒计时结束自动解锁", font=("Arial", 14), fg="white", bg="black")
        hint.pack(side="bottom", pady=20)

        self.overlay = root
        self._stop_flag = False
        self._unlocked.clear()

        # start countdown in a thread (so UI stays responsive)
        t = threading.Thread(target=self._countdown_and_close, daemon=True)
        t.start()

        # block here until overlay is destroyed
        root.protocol("WM_DELETE_WINDOW", lambda: None)  # disable close
        root.mainloop()

    def _countdown_and_close(self):
        remaining = self.lock_seconds
        # update UI from main thread via after
        while remaining >= 0 and not self._stop_flag:
            mins, secs = divmod(remaining, 60)
            text = f"{mins:02d}:{secs:02d} 剩余自动解锁时间"
            try:
                # schedule label update on mainloop
                if self.overlay:
                    self.overlay.after(0, lambda t=text: self.count_label.config(text=t))
            except Exception:
                pass
            if remaining == 0:
                break
            time.sleep(1)
            remaining -= 1

        # 自动解锁（或被强制解锁）
        self._unlocked.set()
        try:
            if self.overlay:
                self.overlay.after(0, self._destroy_overlay)
        except Exception:
            pass

    def _on_force_unlock(self):
        # 强制解锁按钮
        self._stop_flag = True
        self._unlocked.set()
        self._destroy_overlay()

    def _destroy_overlay(self):
        try:
            if self.overlay:
                self.overlay.destroy()
        except Exception:
            pass
        self.overlay = None

    def wait_until_unlocked(self):
        """阻塞等待，直到解锁（自动或强制）"""
        self._unlocked.wait()


class TimerApp:
    def __init__(self, root):
        self.root = root
        root.title("定时锁屏闹铃")
        root.geometry("420x240")
        root.resizable(False, False)

        self.running = False
        self.thread = None
        self.stop_event = threading.Event()

        tk.Label(root, text="定时分钟 (例: 输入 30 即每 30 分钟触发一次)：").pack(pady=(12, 6))
        self.entry = tk.Entry(root, width=10, font=("Arial", 14))
        self.entry.pack()
        self.entry.insert(0, "30")

        self.status_label = tk.Label(root, text="状态：未运行", fg="blue")
        self.status_label.pack(pady=8)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=6)

        self.start_btn = tk.Button(btn_frame, text="Start", width=10, command=self.start)
        self.start_btn.grid(row=0, column=0, padx=8)

        self.stop_btn = tk.Button(btn_frame, text="Stop", width=10, command=self.stop, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=8)

        info = tk.Label(root, text="到点出现全屏锁定（5 分钟），可按“立即解锁”结束。", wraplength=380)
        info.pack(pady=(8, 4))

        # ensure clean exit
        root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start(self):
        if self.running:
            return
        try:
            minutes = float(self.entry.get())
            if minutes <= 0:
                raise ValueError()
        except Exception:
            messagebox.showerror("输入错误", "请输入正数的分钟数（例如 30）")
            return

        self.period_seconds = int(minutes * 60)
        self.running = True
        self.stop_event.clear()
        self.status_label.config(text=f"状态：运行中（每 {minutes} 分钟触发）", fg="green")
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        if not self.running:
            return
        self.running = False
        self.stop_event.set()
        self.status_label.config(text="状态：已停止", fg="red")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _run_loop(self):
        # 循环计时，直到手动 stop
        while not self.stop_event.is_set():
            # 等待周期（可被 stop_event 中断）
            waited = 0
            while waited < self.period_seconds and not self.stop_event.is_set():
                time.sleep(1)
                waited += 1
            if self.stop_event.is_set():
                break

            # 触发“锁屏”覆盖
            self.status_label.config(text="状态：触发锁定（覆盖窗口）", fg="orange")
            overlay = LockOverlay(lock_seconds=DEFAULT_LOCK_SECONDS)
            # show() 必须在主线程调用 tkinter；我们用 after 将其排入主事件循环
            evt = threading.Event()
            def show_overlay():
                try:
                    overlay.show()
                finally:
                    evt.set()
            self.root.after(0, show_overlay)
            # 等待 overlay 完成（自动解锁或强制解锁）
            evt.wait()
            overlay.wait_until_unlocked()

            # 解锁后继续循环（除非 stop）
            if self.stop_event.is_set():
                break
            self.status_label.config(text="状态：等待下一个周期", fg="green")

        # 退出循环
        self.running = False
        self.root.after(0, lambda: (self.start_btn.config(state="normal"),
                                     self.stop_btn.config(state="disabled"),
                                     self.status_label.config(text="状态：已停止", fg="red")))

    def on_close(self):
        # 尝试优雅退出
        if messagebox.askyesno("退出", "确认退出程序？程序正在运行时会停止定时任务。"):
            self.stop()
            # wait briefly for thread to wrap
            time.sleep(0.2)
            self.root.destroy()


def main():
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
