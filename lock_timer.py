import tkinter as tk
import threading
import time
import os


# -------------------------
# 使用系统命令锁屏（更稳定）
# -------------------------
def lock_screen():
    os.system("rundll32.exe user32.dll,LockWorkStation")


# -------------------------
# 弹窗 GUI
# -------------------------
class TimerApp:

    def __init__(self, master):
        self.master = master
        self.master.title("定时锁屏闹钟 v1.1（已修复锁屏）")
        self.master.geometry("320x200")

        self.running = False
        self.timer_thread = None

        tk.Label(master, text="请输入间隔分钟数（例如 30）：").pack(pady=10)
        self.time_entry = tk.Entry(master)
        self.time_entry.pack()

        self.start_btn = tk.Button(master, text="开始定时循环", command=self.start_timer)
        self.start_btn.pack(pady=10)

        self.stop_btn = tk.Button(master, text="停止", command=self.stop_timer)
        self.stop_btn.pack()

        self.status_label = tk.Label(master, text="状态：未启动")
        self.status_label.pack(pady=10)

    # -----------------------------------
    def start_timer(self):
        if self.running:
            return

        minutes = self.time_entry.get()
        if not minutes.isdigit() or int(minutes) <= 0:
            self.status_label.config(text="请输入正确的分钟数！")
            return

        self.interval = int(minutes) * 60
        self.running = True
        self.status_label.config(text=f"已开启，每 {minutes} 分钟锁屏一次")

        self.timer_thread = threading.Thread(target=self.timer_loop)
        self.timer_thread.daemon = True
        self.timer_thread.start()

    # -----------------------------------
    def stop_timer(self):
        self.running = False
        self.status_label.config(text="状态：已停止")

    # -----------------------------------
    def timer_loop(self):
        while self.running:
            time.sleep(self.interval)

            if not self.running:
                break

            # 锁定屏幕（确保一定执行）
            lock_screen()

            # 等待 5 分钟后自动结束锁屏等待
            for i in range(5 * 60):
                if not self.running:  # 允许强制停止
                    break
                time.sleep(1)


# -------------------------
# 主逻辑
# -------------------------
if __name__ == "__main__":
    root = tk.Tk()
    app = TimerApp(root)
    root.mainloop()
