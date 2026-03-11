#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import queue
import os

class ControlPanel:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LeRobot 控制面板")
        self.root.geometry("1000x700")

        self.processes = []
        self.queue1 = queue.Queue()
        self.queue2 = queue.Queue()

        self.init_cmd = "source ~/miniconda3/bin/activate lerobot_alohamini && cd ~/lerobot_alohamini"

        # 按钮配置：[按钮文本, 命令1, 命令2, 等待时间]
        self.buttons_config = [
            ("轮臂遥操",
             "SKIP_CALIBRATION_PROMPT=1 PYTHONPATH='' python -m lerobot.robots.alohamini.lekiwi_host --arm_profile so-arm-5dof",
             "python examples/alohamini/teleoperate_bi.py --arm_profile so-arm-5dof",
             3),
            ("摄像头", "lerobot-find-cameras opencv", None, 0),
            ("录制",
             "SKIP_CALIBRATION_PROMPT=1 PYTHONPATH='' python -m lerobot.robots.alohamini.lekiwi_host --arm_profile so-arm-5dof",
             "python examples/alohamini/record_bi.py --dataset $HF_USER/so100_bi_test --num_episodes 1 --fps 30 --episode_time 45 --reset_time 8 --task_description \"pickup1\" --remote_ip 127.0.0.1 --leader_id so101_leader_bi --arm_profile so-arm-5dof",
             3)
        ]

        self._create_widgets()
        self._start_output_monitor()

    def _create_widgets(self):
        # 按钮区域
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)

        for config in self.buttons_config:
            text = config[0]
            btn = tk.Button(btn_frame, text=text, command=lambda c=config: self._run_commands(c),
                          width=15, height=2)
            btn.pack(side=tk.LEFT, padx=5)

        # 停止按钮
        stop_btn = tk.Button(btn_frame, text="停止所有", command=self._stop_all,
                           width=15, height=2, bg="red", fg="white")
        stop_btn.pack(side=tk.LEFT, padx=5)

        # 上方输出框
        tk.Label(self.root, text="命令1输出 (Host):").pack(anchor=tk.W, padx=10)
        self.output1 = scrolledtext.ScrolledText(self.root, height=15, width=120, font=("Monospace", 10))
        self.output1.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        # 下方输出框
        tk.Label(self.root, text="命令2输出 (Client):").pack(anchor=tk.W, padx=10)
        self.output2 = scrolledtext.ScrolledText(self.root, height=15, width=120, font=("Monospace", 10))
        self.output2.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

    def _run_commands(self, config):
        self._stop_all()
        self.output1.delete(1.0, tk.END)
        self.output2.delete(1.0, tk.END)

        text, cmd1, cmd2, wait_time = config

        # 启动第一个命令
        full_cmd1 = f"{self.init_cmd} && {cmd1}"
        self.output1.insert(tk.END, f">>> 执行: {cmd1}\n")

        if cmd2:
            # 如果有第二个命令，监控第一个命令的输出
            thread1 = threading.Thread(target=self._execute_command_with_trigger,
                                      args=(full_cmd1, self.queue1, cmd2))
            thread1.daemon = True
            thread1.start()
        else:
            # 没有第二个命令，正常执行
            thread1 = threading.Thread(target=self._execute_command, args=(full_cmd1, self.queue1))
            thread1.daemon = True
            thread1.start()

    def _execute_command_with_trigger(self, cmd1, output_queue, cmd2):
        """执行命令1，检测到启动成功后自动启动命令2"""
        try:
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'

            process = subprocess.Popen(
                f"echo '' | {cmd1}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, executable='/bin/bash', env=env
            )
            self.processes.append(process)

            cmd2_started = False
            for line in process.stdout:
                output_queue.put(line)

                # 检测到启动成功标志
                if not cmd2_started and ("Waiting for commands..." in line or "Lift axis homed to 0mm." in line):
                    cmd2_started = True
                    self.output2.insert(tk.END, f">>> Host已就绪，启动客户端\n")
                    self.output2.insert(tk.END, f">>> 执行: {cmd2}\n")

                    # 启动第二个命令
                    full_cmd2 = f"{self.init_cmd} && {cmd2}"
                    thread2 = threading.Thread(target=self._execute_command, args=(full_cmd2, self.queue2))
                    thread2.daemon = True
                    thread2.start()

            process.wait()
        except Exception as e:
            output_queue.put(f"错误: {str(e)}\n")

    def _execute_command(self, cmd, output_queue):
        try:
            process = subprocess.Popen(
                cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, executable='/bin/bash'
            )
            self.processes.append(process)

            for line in process.stdout:
                output_queue.put(line)

            process.wait()
        except Exception as e:
            output_queue.put(f"错误: {str(e)}\n")

    def _start_output_monitor(self):
        def monitor():
            try:
                while True:
                    line = self.queue1.get(timeout=0.01)
                    self.output1.insert(tk.END, line)
                    self.output1.see(tk.END)
            except queue.Empty:
                pass

            try:
                while True:
                    line = self.queue2.get(timeout=0.01)
                    self.output2.insert(tk.END, line)
                    self.output2.see(tk.END)
            except queue.Empty:
                pass

            self.root.after(100, monitor)

        monitor()

    def _stop_all(self):
        for p in self.processes:
            try:
                p.kill()  # 强制终止进程
            except:
                pass
        self.processes.clear()
        self.output1.delete(1.0, tk.END)
        self.output2.delete(1.0, tk.END)

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ControlPanel()
    app.run()
