import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, simpledialog
import threading
import time
import requests
import json
import os
import re
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import webbrowser
import subprocess
import sys
import uuid
import random
import zipfile
import winreg
import shutil
import tempfile
from typing import List, Dict

# 获取临时解压目录
base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

# 定义需要复制的文件列表
files_to_copy = ['ffmpeg.exe']

# 复制文件到当前运行目录
for file in files_to_copy:
    source_file = os.path.join(base_path, file)
    destination_file = os.path.join(os.getcwd(), file)
    # 检查目标文件是否已经存在
    if os.path.exists(destination_file):
        print(f"文件 {file} 已存在，跳过复制。")
    else:
        try:
            shutil.copy2(source_file, destination_file)
            print(f"成功复制文件: {file}")
        except Exception as e:
            print(f"复制文件时出错: {e}")

def get_app_directory():
    """获取应用程序目录（适用于EXE和脚本环境）"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的EXE，使用EXE所在目录
        return os.path.dirname(sys.executable)
    else:
        # 如果是脚本，使用脚本所在目录
        return os.path.dirname(os.path.abspath(__file__))

#---------------------------以下是配置管理器--------------------------------------
class StreamerManager:
    def __init__(self, config_file="streamer_monitor_config.json"):
        self.config_file = config_file
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            messagebox.showerror("错误", f"配置文件 {self.config_file} 不存在")
            self.config = {
                "app_token": "",
                "user_id": "",
                "streamers": [],
                "douyin_cookie": "",
                "auto_cookie": True,
                "automations": [],
                "wxpusher_enabled": True,
                "wecom_enabled": True,
                "wecom_webhook": "",
                "notification_groups": [],
                "default_notification_group": "默认组"
            }
        except json.JSONDecodeError:
            messagebox.showerror("错误", "配置文件格式错误")
            self.config = {
                "app_token": "",
                "user_id": "",
                "streamers": [],
                "douyin_cookie": "",
                "auto_cookie": True,
                "automations": [],
                "wxpusher_enabled": True,
                "wecom_enabled": True,
                "wecom_webhook": "",
                "notification_groups": [],
                "default_notification_group": "默认组"
            }

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {str(e)}")
            return False

    def get_streamers(self) -> List[Dict]:
        """获取主播列表"""
        return self.config.get("streamers", [])

    def update_streamers(self, streamers: List[Dict]):
        """更新主播列表"""
        self.config["streamers"] = streamers

    def get_notification_groups(self) -> List[Dict]:
        """获取通知组列表"""
        return self.config.get("notification_groups", [])

    def update_notification_groups(self, groups: List[Dict]):
        """更新通知组列表"""
        self.config["notification_groups"] = groups

    def get_automations(self) -> List[Dict]:
        """获取自动化任务列表"""
        return self.config.get("automations", [])

    def update_automations(self, automations: List[Dict]):
        """更新自动化任务列表"""
        self.config["automations"] = automations


class StreamerManagerApp:
    def __init__(self, parent_window):  # 修改参数名
        self.root = parent_window  # 使用传入的窗口作为根窗口
        self.root.title("配置管理器")
        self.root.geometry("1000x700")

        self.manager = StreamerManager()

        # 创建选项卡
        self.notebook = ttk.Notebook(self.root)  # 使用self.root
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # 其他初始化代码保持不变...
        self.streamer_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.streamer_frame, text="主播管理")

        self.group_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.group_frame, text="通知组设置")

        self.automation_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.automation_frame, text="自动化任务")

        self.setup_streamer_tab()
        self.setup_group_tab()
        self.setup_automation_tab()

        # 底部按钮
        self.button_frame = ttk.Frame(self.root)  # 使用self.root
        self.button_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(self.button_frame, text="保存配置", command=self.save_config).pack(side='right', padx=5)
        ttk.Button(self.button_frame, text="重新加载", command=self.reload_config).pack(side='right', padx=5)

        self.load_data()

    def load_data(self):
        """加载数据到界面"""
        self.load_streamers()
        self.load_groups()
        self.load_automations()

    def reload_config(self):
        """重新加载配置"""
        self.manager.load_config()
        self.load_data()
        messagebox.showinfo("成功", "配置已重新加载")

    def save_config(self):
        """保存配置"""
        if self.manager.save_config():
            messagebox.showinfo("成功", "配置已保存")

    def setup_streamer_tab(self):
        """设置主播管理选项卡"""
        # 工具栏
        toolbar = ttk.Frame(self.streamer_frame)
        toolbar.pack(fill='x', pady=5)

        ttk.Button(toolbar, text="添加主播", command=self.add_streamer).pack(side='left', padx=5)
        ttk.Button(toolbar, text="编辑主播", command=self.edit_streamer).pack(side='left', padx=5)
        ttk.Button(toolbar, text="删除主播", command=self.delete_streamer).pack(side='left', padx=5)
        ttk.Button(toolbar, text="上移", command=self.move_streamer_up).pack(side='left', padx=5)
        ttk.Button(toolbar, text="下移", command=self.move_streamer_down).pack(side='left', padx=5)

        # 主播列表
        columns = ("名称", "平台", "ID", "状态", "分组")
        self.streamer_tree = ttk.Treeview(self.streamer_frame, columns=columns, show='headings', height=20)

        for col in columns:
            self.streamer_tree.heading(col, text=col)
            self.streamer_tree.column(col, width=150)

        self.streamer_tree.pack(fill='both', expand=True)

        # 绑定双击事件
        self.streamer_tree.bind('<Double-1>', lambda e: self.edit_streamer())

    def load_streamers(self):
        """加载主播列表"""
        self.streamer_tree.delete(*self.streamer_tree.get_children())
        streamers = self.manager.get_streamers()

        for streamer in streamers:
            self.streamer_tree.insert('', 'end', values=(
                streamer.get('name', ''),
                streamer.get('platform', ''),
                streamer.get('id', ''),
                streamer.get('status', ''),
                streamer.get('group', '')
            ))

    def add_streamer(self):
        """添加主播"""
        dialog = StreamerDialog(self.root, "添加主播")
        if dialog.result:
            streamers = self.manager.get_streamers()
            streamers.append(dialog.result)
            self.manager.update_streamers(streamers)
            self.load_streamers()

    def edit_streamer(self):
        """编辑主播"""
        selection = self.streamer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的主播")
            return

        item = selection[0]
        values = self.streamer_tree.item(item, 'values')
        index = self.streamer_tree.index(item)

        streamers = self.manager.get_streamers()
        if index < len(streamers):
            original_streamer = streamers[index]
            dialog = StreamerDialog(self.root, "编辑主播", original_streamer)
            if dialog.result:
                streamers[index] = dialog.result
                self.manager.update_streamers(streamers)
                self.load_streamers()

    def delete_streamer(self):
        """删除主播"""
        selection = self.streamer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的主播")
            return

        if messagebox.askyesno("确认", "确定要删除选中的主播吗？"):
            indices = [self.streamer_tree.index(item) for item in selection]
            # 从大到小排序，避免删除时索引变化
            indices.sort(reverse=True)

            streamers = self.manager.get_streamers()
            for index in indices:
                if index < len(streamers):
                    # 从通知组中移除该主播
                    groups = self.manager.get_notification_groups()
                    for group in groups:
                        if streamers[index]['name'] in group.get('streamers', []):
                            group['streamers'].remove(streamers[index]['name'])
                    self.manager.update_notification_groups(groups)

                    # 从自动化任务中移除该主播
                    automations = self.manager.get_automations()
                    automations = [auto for auto in automations if auto.get('streamer') != streamers[index]['name']]
                    self.manager.update_automations(automations)

                    # 删除主播
                    del streamers[index]

            self.manager.update_streamers(streamers)
            self.load_streamers()
            self.load_groups()
            self.load_automations()

    def move_streamer_up(self):
        """上移主播"""
        selection = self.streamer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要移动的主播")
            return

        item = selection[0]
        index = self.streamer_tree.index(item)
        if index > 0:
            streamers = self.manager.get_streamers()
            streamers[index], streamers[index - 1] = streamers[index - 1], streamers[index]
            self.manager.update_streamers(streamers)
            self.load_streamers()
            self.streamer_tree.selection_set(self.streamer_tree.get_children()[index - 1])

    def move_streamer_down(self):
        """下移主播"""
        selection = self.streamer_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要移动的主播")
            return

        item = selection[0]
        index = self.streamer_tree.index(item)
        streamers = self.manager.get_streamers()
        if index < len(streamers) - 1:
            streamers[index], streamers[index + 1] = streamers[index + 1], streamers[index]
            self.manager.update_streamers(streamers)
            self.load_streamers()
            self.streamer_tree.selection_set(self.streamer_tree.get_children()[index + 1])

    def setup_group_tab(self):
        """设置通知组选项卡"""
        # 工具栏
        toolbar = ttk.Frame(self.group_frame)
        toolbar.pack(fill='x', pady=5)

        ttk.Button(toolbar, text="添加通知组", command=self.add_group).pack(side='left', padx=5)
        ttk.Button(toolbar, text="编辑通知组", command=self.edit_group).pack(side='left', padx=5)
        ttk.Button(toolbar, text="删除通知组", command=self.delete_group).pack(side='left', padx=5)

        # 通知组列表
        columns = ("名称", "主播数量", "WxPusher", "企业微信")
        self.group_tree = ttk.Treeview(self.group_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.group_tree.heading(col, text=col)
            self.group_tree.column(col, width=150)

        self.group_tree.pack(fill='both', expand=True)

        # 绑定双击事件
        self.group_tree.bind('<Double-1>', lambda e: self.edit_group())

    def load_groups(self):
        """加载通知组列表"""
        self.group_tree.delete(*self.group_tree.get_children())
        groups = self.manager.get_notification_groups()

        for group in groups:
            streamer_count = len(group.get('streamers', []))
            wxpusher = "是" if group.get('notify_methods', {}).get('wxpusher', False) else "否"
            wecom = "是" if group.get('notify_methods', {}).get('wecom', False) else "否"

            self.group_tree.insert('', 'end', values=(
                group.get('name', ''),
                streamer_count,
                wxpusher,
                wecom
            ))

    def add_group(self):
        """添加通知组"""
        dialog = GroupDialog(self.root, "添加通知组", self.manager.get_streamers())
        if dialog.result:
            groups = self.manager.get_notification_groups()
            groups.append(dialog.result)
            self.manager.update_notification_groups(groups)
            self.load_groups()

    def edit_group(self):
        """编辑通知组"""
        selection = self.group_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的通知组")
            return

        item = selection[0]
        values = self.group_tree.item(item, 'values')
        index = self.group_tree.index(item)

        groups = self.manager.get_notification_groups()
        if index < len(groups):
            original_group = groups[index]
            dialog = GroupDialog(self.root, "编辑通知组", self.manager.get_streamers(), original_group)
            if dialog.result:
                groups[index] = dialog.result
                self.manager.update_notification_groups(groups)
                self.load_groups()

    def delete_group(self):
        """删除通知组"""
        selection = self.group_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的通知组")
            return

        if messagebox.askyesno("确认", "确定要删除选中的通知组吗？"):
            indices = [self.group_tree.index(item) for item in selection]
            # 从大到小排序，避免删除时索引变化
            indices.sort(reverse=True)

            groups = self.manager.get_notification_groups()
            for index in indices:
                if index < len(groups):
                    # 检查是否是默认通知组
                    if groups[index].get('name') == self.manager.config.get('default_notification_group'):
                        messagebox.showwarning("警告", "不能删除默认通知组")
                        continue

                    # 将使用该组的主播移动到默认组
                    group_name = groups[index].get('name')
                    streamers = self.manager.get_streamers()
                    for streamer in streamers:
                        if streamer.get('group') == group_name:
                            streamer['group'] = self.manager.config.get('default_notification_group', '默认组')
                    self.manager.update_streamers(streamers)

                    # 删除通知组
                    del groups[index]

            self.manager.update_notification_groups(groups)
            self.load_groups()
            self.load_streamers()

    def setup_automation_tab(self):
        """设置自动化任务选项卡"""
        # 工具栏
        toolbar = ttk.Frame(self.automation_frame)
        toolbar.pack(fill='x', pady=5)

        ttk.Button(toolbar, text="添加自动化任务", command=self.add_automation).pack(side='left', padx=5)
        ttk.Button(toolbar, text="编辑自动化任务", command=self.edit_automation).pack(side='left', padx=5)
        ttk.Button(toolbar, text="删除自动化任务", command=self.delete_automation).pack(side='left', padx=5)

        # 自动化任务列表
        columns = ("主播", "触发条件", "脚本路径")
        self.automation_tree = ttk.Treeview(self.automation_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.automation_tree.heading(col, text=col)
            self.automation_tree.column(col, width=200)

        self.automation_tree.pack(fill='both', expand=True)

        # 绑定双击事件
        self.automation_tree.bind('<Double-1>', lambda e: self.edit_automation())

    def load_automations(self):
        """加载自动化任务列表"""
        self.automation_tree.delete(*self.automation_tree.get_children())
        automations = self.manager.get_automations()

        for automation in automations:
            self.automation_tree.insert('', 'end', values=(
                automation.get('streamer', ''),
                automation.get('trigger', ''),
                automation.get('script', '')
            ))

    def add_automation(self):
        """添加自动化任务"""
        dialog = AutomationDialog(self.root, "添加自动化任务", self.manager.get_streamers())
        if dialog.result:
            automations = self.manager.get_automations()
            automations.append(dialog.result)
            self.manager.update_automations(automations)
            self.load_automations()

    def edit_automation(self):
        """编辑自动化任务"""
        selection = self.automation_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要编辑的自动化任务")
            return

        item = selection[0]
        values = self.automation_tree.item(item, 'values')
        index = self.automation_tree.index(item)

        automations = self.manager.get_automations()
        if index < len(automations):
            original_automation = automations[index]
            dialog = AutomationDialog(self.root, "编辑自动化任务", self.manager.get_streamers(), original_automation)
            if dialog.result:
                automations[index] = dialog.result
                self.manager.update_automations(automations)
                self.load_automations()

    def delete_automation(self):
        """删除自动化任务"""
        selection = self.automation_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的自动化任务")
            return

        if messagebox.askyesno("确认", "确定要删除选中的自动化任务吗？"):
            indices = [self.automation_tree.index(item) for item in selection]
            # 从大到小排序，避免删除时索引变化
            indices.sort(reverse=True)

            automations = self.manager.get_automations()
            for index in indices:
                if index < len(automations):
                    del automations[index]

            self.manager.update_automations(automations)
            self.load_automations()


class StreamerDialog(simpledialog.Dialog):
    def __init__(self, parent, title, streamer=None):
        self.streamer = streamer or {}
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="名称:").grid(row=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(master, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="平台:").grid(row=1, sticky='w', pady=5)
        self.platform_combo = ttk.Combobox(master, values=["抖音", "哔哔哩哔哔哩"], width=27)
        self.platform_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(master, text="ID/链接:").grid(row=2, sticky='w', pady=5)
        self.id_entry = ttk.Entry(master, width=30)
        self.id_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(master, text="状态:").grid(row=3, sticky='w', pady=5)
        self.status_combo = ttk.Combobox(master, values=["未开播", "直播中"], width=27)
        self.status_combo.grid(row=3, column=1, padx=5, pady=5)

        ttk.Label(master, text="分组:").grid(row=4, sticky='w', pady=5)
        self.group_entry = ttk.Entry(master, width=30)
        self.group_entry.grid(row=4, column=1, padx=5, pady=5)

        # 填充现有数据
        if self.streamer:
            self.name_entry.insert(0, self.streamer.get('name', ''))
            self.platform_combo.set(self.streamer.get('platform', ''))
            self.id_entry.insert(0, self.streamer.get('id', ''))
            self.status_combo.set(self.streamer.get('status', '未开播'))
            self.group_entry.insert(0, self.streamer.get('group', '默认组'))

        return self.name_entry  # 初始焦点

    def validate(self):
        name = self.name_entry.get().strip()
        platform = self.platform_combo.get().strip()
        id_val = self.id_entry.get().strip()

        if not name:
            messagebox.showwarning("警告", "请输入主播名称")
            return False

        if not platform:
            messagebox.showwarning("警告", "请选择平台")
            return False

        if not id_val:
            messagebox.showwarning("警告", "请输入ID或链接")
            return False

        return True

    def apply(self):
        self.result = {
            "name": self.name_entry.get().strip(),
            "platform": self.platform_combo.get().strip(),
            "id": self.id_entry.get().strip(),
            "status": self.status_combo.get().strip(),
            "group": self.group_entry.get().strip() or "默认组"
        }


class GroupDialog(simpledialog.Dialog):
    def __init__(self, parent, title, streamers, group=None):
        self.streamers = streamers
        self.group = group or {}
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="组名:").grid(row=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(master, width=30)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # 通知方式
        ttk.Label(master, text="通知方式:").grid(row=1, sticky='w', pady=5)
        notify_frame = ttk.Frame(master)
        notify_frame.grid(row=1, column=1, sticky='w', padx=5, pady=5)

        self.wxpusher_var = tk.BooleanVar()
        self.wecom_var = tk.BooleanVar()

        ttk.Checkbutton(notify_frame, text="WxPusher", variable=self.wxpusher_var).pack(side='left')
        ttk.Checkbutton(notify_frame, text="企业微信", variable=self.wecom_var).pack(side='left', padx=10)

        # 主播列表
        ttk.Label(master, text="包含的主播:").grid(row=2, sticky='w', pady=5)

        # 创建框架包含列表和按钮
        list_frame = ttk.Frame(master)
        list_frame.grid(row=3, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)

        # 可用主播列表
        ttk.Label(list_frame, text="可用主播").grid(row=0, column=0, sticky='w')
        self.available_listbox = tk.Listbox(list_frame, width=25, height=10, selectmode='multiple')
        self.available_listbox.grid(row=1, column=0, padx=5, pady=5)

        # 按钮
        button_frame = ttk.Frame(list_frame)
        button_frame.grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(button_frame, text=">", command=self.add_selected).pack(pady=5)
        ttk.Button(button_frame, text=">>", command=self.add_all).pack(pady=5)
        ttk.Button(button_frame, text="<", command=self.remove_selected).pack(pady=5)
        ttk.Button(button_frame, text="<<", command=self.remove_all).pack(pady=5)

        # 已选主播列表
        ttk.Label(list_frame, text="已选主播").grid(row=0, column=2, sticky='w')
        self.selected_listbox = tk.Listbox(list_frame, width=25, height=10, selectmode='multiple')
        self.selected_listbox.grid(row=1, column=2, padx=5, pady=5)

        # 填充数据
        if self.group:
            self.name_entry.insert(0, self.group.get('name', ''))
            notify_methods = self.group.get('notify_methods', {})
            self.wxpusher_var.set(notify_methods.get('wxpusher', False))
            self.wecom_var.set(notify_methods.get('wecom', False))

            # 填充已选主播
            selected_streamers = self.group.get('streamers', [])
            for streamer in self.streamers:
                name = streamer.get('name', '')
                self.available_listbox.insert('end', name)
                if name in selected_streamers:
                    # 从可用列表中移除并添加到已选列表
                    index = self.available_listbox.get(0, 'end').index(name)
                    self.available_listbox.delete(index)
                    self.selected_listbox.insert('end', name)
        else:
            # 新组，添加所有主播到可用列表
            for streamer in self.streamers:
                self.available_listbox.insert('end', streamer.get('name', ''))

        return self.name_entry

    def add_selected(self):
        """添加选中的主播到已选列表"""
        selected_indices = self.available_listbox.curselection()
        for index in reversed(selected_indices):  # 反向遍历避免索引变化
            item = self.available_listbox.get(index)
            self.available_listbox.delete(index)
            self.selected_listbox.insert('end', item)

    def add_all(self):
        """添加所有主播到已选列表"""
        items = self.available_listbox.get(0, 'end')
        for item in reversed(items):
            self.available_listbox.delete(0)
            self.selected_listbox.insert('end', item)

    def remove_selected(self):
        """从已选列表中移除选中的主播"""
        selected_indices = self.selected_listbox.curselection()
        for index in reversed(selected_indices):
            item = self.selected_listbox.get(index)
            self.selected_listbox.delete(index)
            self.available_listbox.insert('end', item)

    def remove_all(self):
        """从已选列表中移除所有主播"""
        items = self.selected_listbox.get(0, 'end')
        for item in reversed(items):
            self.selected_listbox.delete(0)
            self.available_listbox.insert('end', item)

    def validate(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("警告", "请输入组名")
            return False
        return True

    def apply(self):
        selected_streamers = list(self.selected_listbox.get(0, 'end'))

        self.result = {
            "name": self.name_entry.get().strip(),
            "streamers": selected_streamers,
            "notify_methods": {
                "wxpusher": self.wxpusher_var.get(),
                "wecom": self.wecom_var.get()
            }
        }


class AutomationDialog(simpledialog.Dialog):
    def __init__(self, parent, title, streamers, automation=None):
        self.streamers = streamers
        self.automation = automation or {}
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="主播:").grid(row=0, sticky='w', pady=5)
        self.streamer_combo = ttk.Combobox(master, width=27)
        self.streamer_combo['values'] = [s.get('name', '') for s in self.streamers]
        self.streamer_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(master, text="触发条件:").grid(row=1, sticky='w', pady=5)
        self.trigger_combo = ttk.Combobox(master, values=["直播中", "未开播"], width=27)
        self.trigger_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(master, text="脚本路径:").grid(row=2, sticky='w', pady=5)
        path_frame = ttk.Frame(master)
        path_frame.grid(row=2, column=1, sticky='ew', padx=5, pady=5)

        self.script_entry = ttk.Entry(path_frame, width=25)
        self.script_entry.pack(side='left', fill='x', expand=True)
        ttk.Button(path_frame, text="浏览", command=self.browse_script).pack(side='right', padx=5)

        # 填充现有数据
        if self.automation:
            self.streamer_combo.set(self.automation.get('streamer', ''))
            self.trigger_combo.set(self.automation.get('trigger', ''))
            self.script_entry.insert(0, self.automation.get('script', ''))

        return self.streamer_combo

    def browse_script(self):
        """浏览选择脚本文件"""
        filename = filedialog.askopenfilename(
            title="选择脚本文件",
            filetypes=[("Python文件", "*.py"), ("批处理文件", "*.bat"), ("所有文件", "*.*")]
        )
        if filename:
            self.script_entry.delete(0, 'end')
            self.script_entry.insert(0, filename)

    def validate(self):
        streamer = self.streamer_combo.get().strip()
        trigger = self.trigger_combo.get().strip()
        script = self.script_entry.get().strip()

        if not streamer:
            messagebox.showwarning("警告", "请选择主播")
            return False

        if not trigger:
            messagebox.showwarning("警告", "请选择触发条件")
            return False

        if not script:
            messagebox.showwarning("警告", "请输入脚本路径")
            return False

        if not os.path.exists(script):
            messagebox.showwarning("警告", "脚本文件不存在")
            return False

        return True

    def apply(self):
        self.result = {
            "id": self.automation.get('id') or str(hash(f"{self.streamer_combo.get()}_{self.trigger_combo.get()}")),
            "streamer": self.streamer_combo.get().strip(),
            "trigger": self.trigger_combo.get().strip(),
            "script": self.script_entry.get().strip()
        }

#---------------------------------以下为添加录播任务--------------------------------------

class ScriptGenerator:
    #----------------模板文件起------------------------
    def _get_or4_template(self):
        """获取原画模板 (文档5)"""
        return r'''import re
import subprocess
import time
import requests
import os
import sys
import random
import json
from datetime import datetime
import psutil
# 获取当前脚本所在目录作为基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_single_instance():
    """检查是否已有相同脚本在运行"""
    try:
        # 基于脚本路径和主播名称创建唯一标识
        script_name = os.path.basename(__file__)
        if 'SPECIFIED_NAME' in globals():
            instance_id = f"{script_name}_{SPECIFIED_NAME}"
        else:
            instance_id = script_name

        # 获取当前进程的PID
        current_pid = os.getpid()

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue

                # 检查命令行参数中是否包含实例标识
                cmdline = proc.info.get('cmdline', [])
                if instance_id in ' '.join(cmdline):
                    print(f"已经有一个实例在运行: {instance_id}")
                    sys.exit(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"检查单实例时出错: {e}")

# 配置参数
LIVE_ID = 1234567890
LIVE_URL = f"https://live.douyin.com/{LIVE_ID}"
ARIA2_BAT_PATH = "aria2.bat"  # 使用相对路径
ARIA2_RPC_URL = "http://localhost:6800/jsonrpc"
SPEED_THRESHOLD = 100  # KB/s
MAX_EMPTY_RETRIES = 3
SPECIFIED_NAME = "主播名字"  # 可以修改为您想要的名称，如果为空则使用默认命名
LOG_INTERVAL = 30  # 日志输出间隔，单位秒（将在生成时替换）
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
]

random_ua = random.choice(ua_list)

# 使用程序目录下的cookie文件
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.txt')
with open(COOKIE_FILE, 'r', encoding='utf-8') as file:
    cookies2 = file.read()

# 请求头
HEADERS = {
    "User-Agent": f"{random_ua}",
    "Cookie": f"{cookies2}",
    "Referer": f"https://live.douyin.com/{LIVE_ID}",
    "authority": "live.douyin.com",
    "method": "GET",
    "path": f"/{LIVE_ID}"
}

def get_current_datetime_string():
    """获取当前日期时间字符串，格式为YYYYMMDD_HHMMSS"""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def generate_filename(quality_suffix=""):
    """生成文件名，保存在当前工作目录下"""
    datetime_str = get_current_datetime_string()

    if SPECIFIED_NAME and SPECIFIED_NAME.strip():
        if quality_suffix:
            return f"{SPECIFIED_NAME}_{datetime_str}_{quality_suffix}.flv"  # 返回相对路径
        else:
            return f"{SPECIFIED_NAME}_{datetime_str}.flv"
    else:
        if quality_suffix:
            return f"live_{datetime_str}_{quality_suffix}.flv"
        else:
            return f"live_{datetime_str}.flv"

def check_aria2_running():
    """检查 Aria2 是否已经在运行"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "aria2.getVersion",
            "id": "1"
        }
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_stream_url(url: str) -> str:
    """返回第一条可用的 flv；若无 flv 则返回第一条 m3u8"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 1. 优先 flv
        flv_pattern = re.compile(r'"(https?://[^"]+\.flv[^"]*)"')
        flv_urls = flv_pattern.findall(resp.text)
        if flv_urls:
            return flv_urls[0]

        # 2. 退回 m3u8
        m3u8_pattern = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
        m3u8_urls = m3u8_pattern.findall(resp.text)
        if m3u8_urls:
            return m3u8_urls[0]

        return ""
    except Exception as e:
        print(f"[find_stream_url] 获取直播流时出错: {e}")
        return ""

def start_aria2():
    """启动 Aria2 下载器（如果未运行）"""
    # 先检查 Aria2 是否已经在运行
    if check_aria2_running():
        print("Aria2 已经在运行中，跳过启动。")
        return

    try:
        print("正在启动 Aria2...")
        subprocess.Popen([ARIA2_BAT_PATH], shell=True)
        time.sleep(5)  # 等待 Aria2 启动

        # 验证 Aria2 是否成功启动
        if check_aria2_running():
            print("Aria2 启动完成")
        else:
            print("Aria2 可能未正确启动，将继续尝试...")
    except Exception as e:
        print(f"启动 Aria2 时出错: {e}")

# 在所有录播脚本模板的 submit_to_aria2 函数中修改：

def submit_to_aria2(url, filename=None):
    headers = {'Content-Type': 'application/json'}
    
    # 先定义options
    options = {}
    if filename:
        options["out"] = filename

    # 设置下载目录为当前工作目录（EXE所在目录）
    options["dir"] = BASE_DIR

    # 添加User-Agent和其他头信息
    aria2_headers = {
        "User-Agent": random_ua,
        "Referer": f"https://live.douyin.com/{LIVE_ID}"
    }

    # 添加header选项
    header_list = []
    for key, value in aria2_headers.items():
        header_list.append(f"{key}: {value}")
    options["header"] = header_list

    # 构建参数
    params = [[url], options]

    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": "1",
        "params": params
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[submit_to_aria2] 成功添加下载任务，任务 ID: {result['result']}")
                if filename:
                    print(f"[submit_to_aria2] 文件将保存为: {os.path.join(BASE_DIR, filename)}")
                return result['result']  # 返回任务ID
            else:
                print(f"[submit_to_aria2] 添加下载任务失败: {result}")
                return None
        else:
            print(f"[submit_to_aria2] 请求失败，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[submit_to_aria2] 网络请求出错: {e}")
        # 尝试启动 Aria2 并重新提交
        start_aria2()
        time.sleep(3)
        return submit_to_aria2(url, filename)

def get_aria2_speed():
    """获取 Aria2 当前所有任务的总下载速度（KB/s）"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.getGlobalStat",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                # 下载速度是字节/秒，转换为KB/s
                download_speed = int(result['result'].get('downloadSpeed', 0)) / 1024
                return download_speed
        return 0
    except Exception as e:
        print(f"[get_aria2_speed] 获取速度时出错: {e}")
        return 0

def get_active_tasks():
    """获取活跃的下载任务列表"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.tellActive",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        return []
    except Exception as e:
        print(f"[get_active_tasks] 获取任务列表时出错: {e}")
        return []

def stop_aria2_task(gid):
    """停止指定的下载任务"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.remove",
        "id": "1",
        "params": [gid]
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[stop_aria2_task] 成功停止任务: {gid}")
                return True
        return False
    except Exception as e:
        print(f"[stop_aria2_task] 停止任务时出错: {e}")
        return False

def get_quality_from_url(url):
    """从URL中提取质量标识"""
    if "sd.flv" in url:
        return "sd"
    elif "ld.flv" in url:
        return "ld"
    elif "hd.flv" in url:
        return "hd"
    elif "md.flv" in url:
        return "md"
    elif "or4.flv" in url:
        return "or4"
    elif "uhd.flv" in url:
        return "uhd"
    else:
        return "unknown"

def is_high_quality(url):
    """判断是否为高质量链接"""
    return "or4.flv" in url

def is_acceptable_quality(url):
    """判断是否为可接受的质量链接（保持录播完整性）"""
    return "sd.flv" in url or "ld.flv" in url or "hd.flv" in url or "uhd.flv" in url or "or4.flv" in url


def get_quality_priority(quality):
    """获取画质优先级，数值越大表示画质越好"""
    quality_priority = {
        "or4": 5,
        "uhd": 4,
        "hd": 3,
        "ld": 2,
        "sd": 1,
        "unknown": 0
    }
    return quality_priority.get(quality, 0)


def is_better_quality(new_quality, current_quality):
    """判断新画质是否比当前画质更好"""
    return get_quality_priority(new_quality) > get_quality_priority(current_quality)


def main():
    try:
        empty_retries = 0
        # 初始化变量
        current_task_id = None
        current_quality = ""
        found_high_quality = False
        last_log_time = 0  # 上次日志输出时间
        
        while True:
            print("[main] 开始抓取直播流链接...")
            
            # 获取直播流链接
            raw_url = find_stream_url(LIVE_URL)

            if not raw_url:
                empty_retries += 1
                print(f"[main] 第 {empty_retries} 次获取到空链接")
    
                if empty_retries >= MAX_EMPTY_RETRIES:
                    print(f"[main] 空链接超过 {MAX_EMPTY_RETRIES} 次，程序退出")
                    return
    
                time.sleep(random.uniform(3, 5))
                continue

            # 重置空链接计数器
            empty_retries = 0

            # 清洗链接：替换Unicode转义字符并去除末尾的反斜杠
            clean_url = raw_url.replace(r"\u0026", "&").rstrip('\\')
            quality = get_quality_from_url(clean_url)
            
            # 控制日志输出频率
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                print(f"[main] 获取到直播流: {clean_url} (质量: {quality})")
                last_log_time = current_time
    
            # 检查是否为可接受的质量（保持录播完整性）
            if not is_acceptable_quality(clean_url):
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 链接质量不可接受，等待重试...")
                time.sleep(random.uniform(3, 4))
                continue
    
            # 如果是第一次找到可接受质量的链接，或者找到了更高质量的链接
            if current_task_id is None or (is_better_quality(quality, current_quality) and not found_high_quality):
                # 生成文件名（包含质量标识）
                filename = generate_filename(quality)
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 生成文件名: {filename}")
    
                # 提交到 Aria2
                task_id = submit_to_aria2(clean_url, filename)
    
                if task_id:
                    # 如果之前有任务在运行，并且找到了更高质量的链接，则停止之前的任务
                    if current_task_id is not None and is_better_quality(quality, current_quality) and not found_high_quality:
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 找到更高质量链接 ({quality} > {current_quality})，停止之前的任务: {current_task_id}")
                        stop_aria2_task(current_task_id)
    
                    # 更新当前任务信息
                    current_task_id = task_id
                    current_quality = quality
    
                    # 如果是最高质量链接（or4），标记为已找到
                    if quality == "or4":
                        found_high_quality = True
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print("[main] 最高质量链接（or4）已找到并开始下载")
                else:
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print("[main] 下载任务提交失败，重新开始...")
                    time.sleep(2)
                    continue
    
            # 如果已经找到最高质量链接（or4），则只监控下载速度
            if found_high_quality:
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 最高质量链接下载中，开始监控下载速度...")
    
                # 监控下载速度
                low_speed_count = 0
                while True:
                    current_speed = get_aria2_speed()
                    active_tasks = get_active_tasks()
                    task_count = len(active_tasks)
                    
                    current_time = time.time()
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print(f"[main] 当前下载速度: {current_speed:.2f} KB/s, 活跃任务数: {task_count}")
    
                        # 显示活跃任务信息
                        for i, task in enumerate(active_tasks):
                            task_name = task.get('files', [{}])[0].get('path', '未知文件')
                            completed = int(task.get('completedLength', 0))
                            total = int(task.get('totalLength', 0))
                            if total > 0:
                                progress = (completed / total) * 100
                            else:
                                progress = 0
                            print(f"  任务 {i + 1}: {task_name} - 进度: {progress:.1f}%")
                        
                        last_log_time = current_time
    
                    if current_speed < SPEED_THRESHOLD:
                        low_speed_count += 1
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 速度低于阈值 ({SPEED_THRESHOLD} KB/s)，计数: {low_speed_count}")
    
                        if low_speed_count >= 5:  # 连续5次低于阈值才重新开始
                            if current_time - last_log_time >= LOG_INTERVAL:
                                print("[main] 速度持续过低，重新开始获取链接...")
                            found_high_quality = False  # 重置标志
                            break
                    else:
                        low_speed_count = 0  # 重置计数器
    
                    time.sleep(5)  # 每5秒检查一次速度
            else:
                # 如果还没有找到最高质量链接，继续寻找
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 当前画质: {current_quality}，继续寻找更高质量链接...")
                time.sleep(10)  # 每10秒检查一次是否有更高质量链接
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
if __name__ == "__main__":
    try:
        # 先启动 Aria2
        start_aria2()
        time.sleep(3)

        # 运行主程序
        main()
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
    '''

    def _get_uhd_template(self):
        """获取蓝光模板 (文档4)"""
        return r'''import re
import subprocess
import time
import requests
import os
import sys
import random
import json
from datetime import datetime
import psutil
# 获取当前脚本所在目录作为基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_single_instance():
    """检查是否已有相同脚本在运行"""
    try:
        # 基于脚本路径和主播名称创建唯一标识
        script_name = os.path.basename(__file__)
        if 'SPECIFIED_NAME' in globals():
            instance_id = f"{script_name}_{SPECIFIED_NAME}"
        else:
            instance_id = script_name

        # 获取当前进程的PID
        current_pid = os.getpid()

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue

                # 检查命令行参数中是否包含实例标识
                cmdline = proc.info.get('cmdline', [])
                if instance_id in ' '.join(cmdline):
                    print(f"已经有一个实例在运行: {instance_id}")
                    sys.exit(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"检查单实例时出错: {e}")

# 配置参数
LIVE_ID = 1234567890
LIVE_URL = f"https://live.douyin.com/{LIVE_ID}"
ARIA2_BAT_PATH = "aria2.bat"  # 使用相对路径
ARIA2_RPC_URL = "http://localhost:6800/jsonrpc"
SPEED_THRESHOLD = 100  # KB/s
MAX_EMPTY_RETRIES = 3
SPECIFIED_NAME = "主播名字"  # 可以修改为您想要的名称，如果为空则使用默认命名
LOG_INTERVAL = 30  # 日志输出间隔，单位秒（将在生成时替换）
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
]

random_ua = random.choice(ua_list)

# 使用程序目录下的cookie文件
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.txt')
with open(COOKIE_FILE, 'r', encoding='utf-8') as file:
    cookies2 = file.read()

# 请求头
HEADERS = {
    "User-Agent": f"{random_ua}",
    "Cookie": f"{cookies2}",
    "Referer": f"https://live.douyin.com/{LIVE_ID}",
    "authority": "live.douyin.com",
    "method": "GET",
    "path": f"/{LIVE_ID}"
}

def get_current_datetime_string():
    """获取当前日期时间字符串，格式为YYYYMMDD_HHMMSS"""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def generate_filename(quality_suffix=""):
    """生成文件名，保存在当前工作目录下"""
    datetime_str = get_current_datetime_string()

    if SPECIFIED_NAME and SPECIFIED_NAME.strip():
        if quality_suffix:
            return f"{SPECIFIED_NAME}_{datetime_str}_{quality_suffix}.flv"  # 返回相对路径
        else:
            return f"{SPECIFIED_NAME}_{datetime_str}.flv"
    else:
        if quality_suffix:
            return f"live_{datetime_str}_{quality_suffix}.flv"
        else:
            return f"live_{datetime_str}.flv"
    

def check_aria2_running():
    """检查 Aria2 是否已经在运行"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "aria2.getVersion",
            "id": "1"
        }
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_stream_url(url: str) -> str:
    """返回第一条可用的 flv；若无 flv 则返回第一条 m3u8"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 1. 优先 flv
        flv_pattern = re.compile(r'"(https?://[^"]+\.flv[^"]*)"')
        flv_urls = flv_pattern.findall(resp.text)
        if flv_urls:
            return flv_urls[0]

        # 2. 退回 m3u8
        m3u8_pattern = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
        m3u8_urls = m3u8_pattern.findall(resp.text)
        if m3u8_urls:
            return m3u8_urls[0]

        return ""
    except Exception as e:
        print(f"[find_stream_url] 获取直播流时出错: {e}")
        return ""

def start_aria2():
    """启动 Aria2 下载器（如果未运行）"""
    # 先检查 Aria2 是否已经在运行
    if check_aria2_running():
        print("Aria2 已经在运行中，跳过启动。")
        return

    try:
        print("正在启动 Aria2...")
        subprocess.Popen([ARIA2_BAT_PATH], shell=True)
        time.sleep(5)  # 等待 Aria2 启动

        # 验证 Aria2 是否成功启动
        if check_aria2_running():
            print("Aria2 启动完成")
        else:
            print("Aria2 可能未正确启动，将继续尝试...")
    except Exception as e:
        print(f"启动 Aria2 时出错: {e}")

# 在所有录播脚本模板的 submit_to_aria2 函数中修改：

def submit_to_aria2(url, filename=None):
    headers = {'Content-Type': 'application/json'}
    
    # 先定义options
    options = {}
    if filename:
        options["out"] = filename

    # 设置下载目录为当前工作目录（EXE所在目录）
    options["dir"] = BASE_DIR

    # 添加User-Agent和其他头信息
    aria2_headers = {
        "User-Agent": random_ua,
        "Referer": f"https://live.douyin.com/{LIVE_ID}"
    }

    # 添加header选项
    header_list = []
    for key, value in aria2_headers.items():
        header_list.append(f"{key}: {value}")
    options["header"] = header_list

    # 构建参数
    params = [[url], options]

    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": "1",
        "params": params
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[submit_to_aria2] 成功添加下载任务，任务 ID: {result['result']}")
                if filename:
                    print(f"[submit_to_aria2] 文件将保存为: {os.path.join(BASE_DIR, filename)}")
                return result['result']  # 返回任务ID
            else:
                print(f"[submit_to_aria2] 添加下载任务失败: {result}")
                return None
        else:
            print(f"[submit_to_aria2] 请求失败，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[submit_to_aria2] 网络请求出错: {e}")
        # 尝试启动 Aria2 并重新提交
        start_aria2()
        time.sleep(3)
        return submit_to_aria2(url, filename)

def get_aria2_speed():
    """获取 Aria2 当前所有任务的总下载速度（KB/s）"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.getGlobalStat",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                # 下载速度是字节/秒，转换为KB/s
                download_speed = int(result['result'].get('downloadSpeed', 0)) / 1024
                return download_speed
        return 0
    except Exception as e:
        print(f"[get_aria2_speed] 获取速度时出错: {e}")
        return 0

def get_active_tasks():
    """获取活跃的下载任务列表"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.tellActive",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        return []
    except Exception as e:
        print(f"[get_active_tasks] 获取任务列表时出错: {e}")
        return []

def stop_aria2_task(gid):
    """停止指定的下载任务"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.remove",
        "id": "1",
        "params": [gid]
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[stop_aria2_task] 成功停止任务: {gid}")
                return True
        return False
    except Exception as e:
        print(f"[stop_aria2_task] 停止任务时出错: {e}")
        return False

def get_quality_from_url(url):
    """从URL中提取质量标识"""
    if "sd.flv" in url:
        return "sd"
    elif "ld.flv" in url:
        return "ld"
    elif "hd.flv" in url:
        return "hd"
    elif "md.flv" in url:
        return "md"
    elif "or4.flv" in url:
        return "or4"
    elif "uhd.flv" in url:
        return "uhd"
    else:
        return "unknown"

def is_high_quality(url):
    """判断是否为高质量链接"""
    return "uhd.flv" in url

def is_acceptable_quality(url):
    """判断是否为可接受的质量链接（保持录播完整性）"""
    return "sd.flv" in url or "ld.flv" in url or "hd.flv" in url or "uhd.flv" in url


def get_quality_priority(quality):
    """获取画质优先级，数值越大表示画质越好"""
    quality_priority = {
        "or4": 5,
        "uhd": 4,
        "hd": 3,
        "ld": 2,
        "sd": 1,
        "unknown": 0
    }
    return quality_priority.get(quality, 0)


def is_better_quality(new_quality, current_quality):
    """判断新画质是否比当前画质更好"""
    return get_quality_priority(new_quality) > get_quality_priority(current_quality)


def main():
    try:
        empty_retries = 0
        # 初始化变量
        current_task_id = None
        current_quality = ""
        found_high_quality = False
        last_log_time = 0  # 上次日志输出时间
        
        while True:
            print("[main] 开始抓取直播流链接...")
            
            # 获取直播流链接
            raw_url = find_stream_url(LIVE_URL)

            if not raw_url:
                empty_retries += 1
                print(f"[main] 第 {empty_retries} 次获取到空链接")
    
                if empty_retries >= MAX_EMPTY_RETRIES:
                    print(f"[main] 空链接超过 {MAX_EMPTY_RETRIES} 次，程序退出")
                    return
    
                time.sleep(random.uniform(3, 5))
                continue

            # 重置空链接计数器
            empty_retries = 0

            # 清洗链接：替换Unicode转义字符并去除末尾的反斜杠
            clean_url = raw_url.replace(r"\u0026", "&").rstrip('\\')
            quality = get_quality_from_url(clean_url)
            
            # 控制日志输出频率
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                print(f"[main] 获取到直播流: {clean_url} (质量: {quality})")
                last_log_time = current_time
    
            # 检查是否为可接受的质量（保持录播完整性）
            if not is_acceptable_quality(clean_url):
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 链接质量不可接受，等待重试...")
                time.sleep(random.uniform(3, 4))
                continue
    
            # 如果是第一次找到可接受质量的链接，或者找到了更高质量的链接
            if current_task_id is None or (is_better_quality(quality, current_quality) and not found_high_quality):
                # 生成文件名（包含质量标识）
                filename = generate_filename(quality)
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 生成文件名: {filename}")
    
                # 提交到 Aria2
                task_id = submit_to_aria2(clean_url, filename)
    
                if task_id:
                    # 如果之前有任务在运行，并且找到了更高质量的链接，则停止之前的任务
                    if current_task_id is not None and is_better_quality(quality, current_quality) and not found_high_quality:
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 找到更高质量链接 ({quality} > {current_quality})，停止之前的任务: {current_task_id}")
                        stop_aria2_task(current_task_id)
    
                    # 更新当前任务信息
                    current_task_id = task_id
                    current_quality = quality
    
                    # 如果是最高质量链接（or4），标记为已找到
                    if quality == "or4":
                        found_high_quality = True
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print("[main] 最高质量链接（or4）已找到并开始下载")
                else:
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print("[main] 下载任务提交失败，重新开始...")
                    time.sleep(2)
                    continue
    
            # 如果已经找到最高质量链接（or4），则只监控下载速度
            if found_high_quality:
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 最高质量链接下载中，开始监控下载速度...")
    
                # 监控下载速度
                low_speed_count = 0
                while True:
                    current_speed = get_aria2_speed()
                    active_tasks = get_active_tasks()
                    task_count = len(active_tasks)
                    
                    current_time = time.time()
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print(f"[main] 当前下载速度: {current_speed:.2f} KB/s, 活跃任务数: {task_count}")
    
                        # 显示活跃任务信息
                        for i, task in enumerate(active_tasks):
                            task_name = task.get('files', [{}])[0].get('path', '未知文件')
                            completed = int(task.get('completedLength', 0))
                            total = int(task.get('totalLength', 0))
                            if total > 0:
                                progress = (completed / total) * 100
                            else:
                                progress = 0
                            print(f"  任务 {i + 1}: {task_name} - 进度: {progress:.1f}%")
                        
                        last_log_time = current_time
    
                    if current_speed < SPEED_THRESHOLD:
                        low_speed_count += 1
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 速度低于阈值 ({SPEED_THRESHOLD} KB/s)，计数: {low_speed_count}")
    
                        if low_speed_count >= 5:  # 连续5次低于阈值才重新开始
                            if current_time - last_log_time >= LOG_INTERVAL:
                                print("[main] 速度持续过低，重新开始获取链接...")
                            found_high_quality = False  # 重置标志
                            break
                    else:
                        low_speed_count = 0  # 重置计数器
    
                    time.sleep(5)  # 每5秒检查一次速度
            else:
                # 如果还没有找到最高质量链接，继续寻找
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 当前画质: {current_quality}，继续寻找更高质量链接...")
                time.sleep(10)  # 每10秒检查一次是否有更高质量链接
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
if __name__ == "__main__":
    try:
        # 先启动 Aria2
        start_aria2()
        time.sleep(3)

        # 运行主程序
        main()
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
    '''

    def _get_hd_template(self):
        """获取超清模板 (文档3)"""
        return r'''import re
import subprocess
import time
import requests
import os
import sys
import random
import json
from datetime import datetime
import psutil
# 获取当前脚本所在目录作为基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_single_instance():
    """检查是否已有相同脚本在运行"""
    try:
        # 基于脚本路径和主播名称创建唯一标识
        script_name = os.path.basename(__file__)
        if 'SPECIFIED_NAME' in globals():
            instance_id = f"{script_name}_{SPECIFIED_NAME}"
        else:
            instance_id = script_name

        # 获取当前进程的PID
        current_pid = os.getpid()

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue

                # 检查命令行参数中是否包含实例标识
                cmdline = proc.info.get('cmdline', [])
                if instance_id in ' '.join(cmdline):
                    print(f"已经有一个实例在运行: {instance_id}")
                    sys.exit(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"检查单实例时出错: {e}")

# 配置参数
LIVE_ID = 1234567890
LIVE_URL = f"https://live.douyin.com/{LIVE_ID}"
ARIA2_BAT_PATH = "aria2.bat"  # 使用相对路径
ARIA2_RPC_URL = "http://localhost:6800/jsonrpc"
SPEED_THRESHOLD = 100  # KB/s
MAX_EMPTY_RETRIES = 3
SPECIFIED_NAME = "主播名字"  # 可以修改为您想要的名称，如果为空则使用默认命名
LOG_INTERVAL = 30  # 日志输出间隔，单位秒（将在生成时替换）
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
]

random_ua = random.choice(ua_list)

# 使用程序目录下的cookie文件
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.txt')
with open(COOKIE_FILE, 'r', encoding='utf-8') as file:
    cookies2 = file.read()

# 请求头
HEADERS = {
    "User-Agent": f"{random_ua}",
    "Cookie": f"{cookies2}",
    "Referer": f"https://live.douyin.com/{LIVE_ID}",
    "authority": "live.douyin.com",
    "method": "GET",
    "path": f"/{LIVE_ID}"
}

def get_current_datetime_string():
    """获取当前日期时间字符串，格式为YYYYMMDD_HHMMSS"""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def generate_filename(quality_suffix=""):
    """生成文件名，保存在当前工作目录下"""
    datetime_str = get_current_datetime_string()

    if SPECIFIED_NAME and SPECIFIED_NAME.strip():
        if quality_suffix:
            return f"{SPECIFIED_NAME}_{datetime_str}_{quality_suffix}.flv"  # 返回相对路径
        else:
            return f"{SPECIFIED_NAME}_{datetime_str}.flv"
    else:
        if quality_suffix:
            return f"live_{datetime_str}_{quality_suffix}.flv"
        else:
            return f"live_{datetime_str}.flv"
    
def check_aria2_running():
    """检查 Aria2 是否已经在运行"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "aria2.getVersion",
            "id": "1"
        }
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_stream_url(url: str) -> str:
    """返回第一条可用的 flv；若无 flv 则返回第一条 m3u8"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 1. 优先 flv
        flv_pattern = re.compile(r'"(https?://[^"]+\.flv[^"]*)"')
        flv_urls = flv_pattern.findall(resp.text)
        if flv_urls:
            return flv_urls[0]

        # 2. 退回 m3u8
        m3u8_pattern = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
        m3u8_urls = m3u8_pattern.findall(resp.text)
        if m3u8_urls:
            return m3u8_urls[0]

        return ""
    except Exception as e:
        print(f"[find_stream_url] 获取直播流时出错: {e}")
        return ""

def start_aria2():
    """启动 Aria2 下载器（如果未运行）"""
    # 先检查 Aria2 是否已经在运行
    if check_aria2_running():
        print("Aria2 已经在运行中，跳过启动。")
        return

    try:
        print("正在启动 Aria2...")
        subprocess.Popen([ARIA2_BAT_PATH], shell=True)
        time.sleep(5)  # 等待 Aria2 启动

        # 验证 Aria2 是否成功启动
        if check_aria2_running():
            print("Aria2 启动完成")
        else:
            print("Aria2 可能未正确启动，将继续尝试...")
    except Exception as e:
        print(f"启动 Aria2 时出错: {e}")

# 在所有录播脚本模板的 submit_to_aria2 函数中修改：

def submit_to_aria2(url, filename=None):
    headers = {'Content-Type': 'application/json'}
    
    # 先定义options
    options = {}
    if filename:
        options["out"] = filename

    # 设置下载目录为当前工作目录（EXE所在目录）
    options["dir"] = BASE_DIR

    # 添加User-Agent和其他头信息
    aria2_headers = {
        "User-Agent": random_ua,
        "Referer": f"https://live.douyin.com/{LIVE_ID}"
    }

    # 添加header选项
    header_list = []
    for key, value in aria2_headers.items():
        header_list.append(f"{key}: {value}")
    options["header"] = header_list

    # 构建参数
    params = [[url], options]

    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": "1",
        "params": params
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[submit_to_aria2] 成功添加下载任务，任务 ID: {result['result']}")
                if filename:
                    print(f"[submit_to_aria2] 文件将保存为: {os.path.join(BASE_DIR, filename)}")
                return result['result']  # 返回任务ID
            else:
                print(f"[submit_to_aria2] 添加下载任务失败: {result}")
                return None
        else:
            print(f"[submit_to_aria2] 请求失败，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[submit_to_aria2] 网络请求出错: {e}")
        # 尝试启动 Aria2 并重新提交
        start_aria2()
        time.sleep(3)
        return submit_to_aria2(url, filename)

def get_aria2_speed():
    """获取 Aria2 当前所有任务的总下载速度（KB/s）"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.getGlobalStat",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                # 下载速度是字节/秒，转换为KB/s
                download_speed = int(result['result'].get('downloadSpeed', 0)) / 1024
                return download_speed
        return 0
    except Exception as e:
        print(f"[get_aria2_speed] 获取速度时出错: {e}")
        return 0

def get_active_tasks():
    """获取活跃的下载任务列表"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.tellActive",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        return []
    except Exception as e:
        print(f"[get_active_tasks] 获取任务列表时出错: {e}")
        return []

def stop_aria2_task(gid):
    """停止指定的下载任务"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.remove",
        "id": "1",
        "params": [gid]
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[stop_aria2_task] 成功停止任务: {gid}")
                return True
        return False
    except Exception as e:
        print(f"[stop_aria2_task] 停止任务时出错: {e}")
        return False

def get_quality_from_url(url):
    """从URL中提取质量标识"""
    if "sd.flv" in url:
        return "sd"
    elif "ld.flv" in url:
        return "ld"
    elif "hd.flv" in url:
        return "hd"
    elif "md.flv" in url:
        return "md"
    elif "or4.flv" in url:
        return "or4"
    elif "uhd.flv" in url:
        return "uhd"
    else:
        return "unknown"

def is_high_quality(url):
    """判断是否为高质量链接"""
    return "hd.flv" in url

def is_acceptable_quality(url):
    """判断是否为可接受的质量链接（保持录播完整性）"""
    return "sd.flv" in url or "ld.flv" in url or "hd.flv" in url


def get_quality_priority(quality):
    """获取画质优先级，数值越大表示画质越好"""
    quality_priority = {
        "or4": 5,
        "uhd": 4,
        "hd": 3,
        "ld": 2,
        "sd": 1,
        "unknown": 0
    }
    return quality_priority.get(quality, 0)


def is_better_quality(new_quality, current_quality):
    """判断新画质是否比当前画质更好"""
    return get_quality_priority(new_quality) > get_quality_priority(current_quality)


def main():
    try:
        empty_retries = 0
        # 初始化变量
        current_task_id = None
        current_quality = ""
        found_high_quality = False
        last_log_time = 0  # 上次日志输出时间
        
        while True:
            print("[main] 开始抓取直播流链接...")
            
            # 获取直播流链接
            raw_url = find_stream_url(LIVE_URL)

            if not raw_url:
                empty_retries += 1
                print(f"[main] 第 {empty_retries} 次获取到空链接")
    
                if empty_retries >= MAX_EMPTY_RETRIES:
                    print(f"[main] 空链接超过 {MAX_EMPTY_RETRIES} 次，程序退出")
                    return
    
                time.sleep(random.uniform(3, 5))
                continue

            # 重置空链接计数器
            empty_retries = 0

            # 清洗链接：替换Unicode转义字符并去除末尾的反斜杠
            clean_url = raw_url.replace(r"\u0026", "&").rstrip('\\')
            quality = get_quality_from_url(clean_url)
            
            # 控制日志输出频率
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                print(f"[main] 获取到直播流: {clean_url} (质量: {quality})")
                last_log_time = current_time
    
            # 检查是否为可接受的质量（保持录播完整性）
            if not is_acceptable_quality(clean_url):
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 链接质量不可接受，等待重试...")
                time.sleep(random.uniform(3, 4))
                continue
    
            # 如果是第一次找到可接受质量的链接，或者找到了更高质量的链接
            if current_task_id is None or (is_better_quality(quality, current_quality) and not found_high_quality):
                # 生成文件名（包含质量标识）
                filename = generate_filename(quality)
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 生成文件名: {filename}")
    
                # 提交到 Aria2
                task_id = submit_to_aria2(clean_url, filename)
    
                if task_id:
                    # 如果之前有任务在运行，并且找到了更高质量的链接，则停止之前的任务
                    if current_task_id is not None and is_better_quality(quality, current_quality) and not found_high_quality:
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 找到更高质量链接 ({quality} > {current_quality})，停止之前的任务: {current_task_id}")
                        stop_aria2_task(current_task_id)
    
                    # 更新当前任务信息
                    current_task_id = task_id
                    current_quality = quality
    
                    # 如果是最高质量链接（or4），标记为已找到
                    if quality == "or4":
                        found_high_quality = True
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print("[main] 最高质量链接（or4）已找到并开始下载")
                else:
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print("[main] 下载任务提交失败，重新开始...")
                    time.sleep(2)
                    continue
    
            # 如果已经找到最高质量链接（or4），则只监控下载速度
            if found_high_quality:
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 最高质量链接下载中，开始监控下载速度...")
    
                # 监控下载速度
                low_speed_count = 0
                while True:
                    current_speed = get_aria2_speed()
                    active_tasks = get_active_tasks()
                    task_count = len(active_tasks)
                    
                    current_time = time.time()
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print(f"[main] 当前下载速度: {current_speed:.2f} KB/s, 活跃任务数: {task_count}")
    
                        # 显示活跃任务信息
                        for i, task in enumerate(active_tasks):
                            task_name = task.get('files', [{}])[0].get('path', '未知文件')
                            completed = int(task.get('completedLength', 0))
                            total = int(task.get('totalLength', 0))
                            if total > 0:
                                progress = (completed / total) * 100
                            else:
                                progress = 0
                            print(f"  任务 {i + 1}: {task_name} - 进度: {progress:.1f}%")
                        
                        last_log_time = current_time
    
                    if current_speed < SPEED_THRESHOLD:
                        low_speed_count += 1
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 速度低于阈值 ({SPEED_THRESHOLD} KB/s)，计数: {low_speed_count}")
    
                        if low_speed_count >= 5:  # 连续5次低于阈值才重新开始
                            if current_time - last_log_time >= LOG_INTERVAL:
                                print("[main] 速度持续过低，重新开始获取链接...")
                            found_high_quality = False  # 重置标志
                            break
                    else:
                        low_speed_count = 0  # 重置计数器
    
                    time.sleep(5)  # 每5秒检查一次速度
            else:
                # 如果还没有找到最高质量链接，继续寻找
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 当前画质: {current_quality}，继续寻找更高质量链接...")
                time.sleep(10)  # 每10秒检查一次是否有更高质量链接
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
if __name__ == "__main__":
    try:
        # 先启动 Aria2
        start_aria2()
        time.sleep(3)

        # 运行主程序
        main()
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
    '''

    def _get_ld_template(self):
        """获取高清模板 (文档2)"""
        return r'''import re
import subprocess
import time
import requests
import os
import sys
import random
import json
from datetime import datetime
import psutil
# 获取当前脚本所在目录作为基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_single_instance():
    """检查是否已有相同脚本在运行"""
    try:
        # 基于脚本路径和主播名称创建唯一标识
        script_name = os.path.basename(__file__)
        if 'SPECIFIED_NAME' in globals():
            instance_id = f"{script_name}_{SPECIFIED_NAME}"
        else:
            instance_id = script_name

        # 获取当前进程的PID
        current_pid = os.getpid()

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue

                # 检查命令行参数中是否包含实例标识
                cmdline = proc.info.get('cmdline', [])
                if instance_id in ' '.join(cmdline):
                    print(f"已经有一个实例在运行: {instance_id}")
                    sys.exit(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"检查单实例时出错: {e}")

# 配置参数
LIVE_ID = 1234567890
LIVE_URL = f"https://live.douyin.com/{LIVE_ID}"
ARIA2_BAT_PATH = "aria2.bat"  # 使用相对路径
ARIA2_RPC_URL = "http://localhost:6800/jsonrpc"
SPEED_THRESHOLD = 100  # KB/s
MAX_EMPTY_RETRIES = 3
SPECIFIED_NAME = "主播名字"  # 可以修改为您想要的名称，如果为空则使用默认命名
LOG_INTERVAL = 30  # 日志输出间隔，单位秒（将在生成时替换）
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
]

random_ua = random.choice(ua_list)

# 使用程序目录下的cookie文件
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.txt')
with open(COOKIE_FILE, 'r', encoding='utf-8') as file:
    cookies2 = file.read()

# 请求头
HEADERS = {
    "User-Agent": f"{random_ua}",
    "Cookie": f"{cookies2}",
    "Referer": f"https://live.douyin.com/{LIVE_ID}",
    "authority": "live.douyin.com",
    "method": "GET",
    "path": f"/{LIVE_ID}"
}

def get_current_datetime_string():
    """获取当前日期时间字符串，格式为YYYYMMDD_HHMMSS"""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def generate_filename(quality_suffix=""):
    """生成文件名，保存在当前工作目录下"""
    datetime_str = get_current_datetime_string()

    if SPECIFIED_NAME and SPECIFIED_NAME.strip():
        if quality_suffix:
            return f"{SPECIFIED_NAME}_{datetime_str}_{quality_suffix}.flv"  # 返回相对路径
        else:
            return f"{SPECIFIED_NAME}_{datetime_str}.flv"
    else:
        if quality_suffix:
            return f"live_{datetime_str}_{quality_suffix}.flv"
        else:
            return f"live_{datetime_str}.flv"

def check_aria2_running():
    """检查 Aria2 是否已经在运行"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "aria2.getVersion",
            "id": "1"
        }
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_stream_url(url: str) -> str:
    """返回第一条可用的 flv；若无 flv 则返回第一条 m3u8"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 1. 优先 flv
        flv_pattern = re.compile(r'"(https?://[^"]+\.flv[^"]*)"')
        flv_urls = flv_pattern.findall(resp.text)
        if flv_urls:
            return flv_urls[0]

        # 2. 退回 m3u8
        m3u8_pattern = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
        m3u8_urls = m3u8_pattern.findall(resp.text)
        if m3u8_urls:
            return m3u8_urls[0]

        return ""
    except Exception as e:
        print(f"[find_stream_url] 获取直播流时出错: {e}")
        return ""

def start_aria2():
    """启动 Aria2 下载器（如果未运行）"""
    # 先检查 Aria2 是否已经在运行
    if check_aria2_running():
        print("Aria2 已经在运行中，跳过启动。")
        return

    try:
        print("正在启动 Aria2...")
        subprocess.Popen([ARIA2_BAT_PATH], shell=True)
        time.sleep(5)  # 等待 Aria2 启动

        # 验证 Aria2 是否成功启动
        if check_aria2_running():
            print("Aria2 启动完成")
        else:
            print("Aria2 可能未正确启动，将继续尝试...")
    except Exception as e:
        print(f"启动 Aria2 时出错: {e}")

# 在所有录播脚本模板的 submit_to_aria2 函数中修改：

def submit_to_aria2(url, filename=None):
    headers = {'Content-Type': 'application/json'}
    
    # 先定义options
    options = {}
    if filename:
        options["out"] = filename

    # 设置下载目录为当前工作目录（EXE所在目录）
    options["dir"] = BASE_DIR

    # 添加User-Agent和其他头信息
    aria2_headers = {
        "User-Agent": random_ua,
        "Referer": f"https://live.douyin.com/{LIVE_ID}"
    }

    # 添加header选项
    header_list = []
    for key, value in aria2_headers.items():
        header_list.append(f"{key}: {value}")
    options["header"] = header_list

    # 构建参数
    params = [[url], options]

    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": "1",
        "params": params
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[submit_to_aria2] 成功添加下载任务，任务 ID: {result['result']}")
                if filename:
                    print(f"[submit_to_aria2] 文件将保存为: {os.path.join(BASE_DIR, filename)}")
                return result['result']  # 返回任务ID
            else:
                print(f"[submit_to_aria2] 添加下载任务失败: {result}")
                return None
        else:
            print(f"[submit_to_aria2] 请求失败，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[submit_to_aria2] 网络请求出错: {e}")
        # 尝试启动 Aria2 并重新提交
        start_aria2()
        time.sleep(3)
        return submit_to_aria2(url, filename)

def get_active_tasks():
    """获取活跃的下载任务列表"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.tellActive",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        return []
    except Exception as e:
        print(f"[get_active_tasks] 获取任务列表时出错: {e}")
        return []

def stop_aria2_task(gid):
    """停止指定的下载任务"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.remove",
        "id": "1",
        "params": [gid]
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[stop_aria2_task] 成功停止任务: {gid}")
                return True
        return False
    except Exception as e:
        print(f"[stop_aria2_task] 停止任务时出错: {e}")
        return False

def get_quality_from_url(url):
    """从URL中提取质量标识"""
    if "sd.flv" in url:
        return "sd"
    elif "ld.flv" in url:
        return "ld"
    elif "hd.flv" in url:
        return "hd"
    elif "md.flv" in url:
        return "md"
    elif "or4.flv" in url:
        return "or4"
    elif "uhd.flv" in url:
        return "uhd"
    else:
        return "unknown"

def is_high_quality(url):
    """判断是否为高质量链接"""
    return "ld.flv" in url

def is_acceptable_quality(url):
    """判断是否为可接受的质量链接（保持录播完整性）"""
    return "sd.flv" in url or "ld.flv" in url


def get_quality_priority(quality):
    """获取画质优先级，数值越大表示画质越好"""
    quality_priority = {
        "or4": 5,
        "uhd": 4,
        "hd": 3,
        "ld": 2,
        "sd": 1,
        "unknown": 0
    }
    return quality_priority.get(quality, 0)


def is_better_quality(new_quality, current_quality):
    """判断新画质是否比当前画质更好"""
    return get_quality_priority(new_quality) > get_quality_priority(current_quality)


def main():
    try:
        empty_retries = 0
        # 初始化变量
        current_task_id = None
        current_quality = ""
        found_high_quality = False
        last_log_time = 0  # 上次日志输出时间
        
        while True:
            print("[main] 开始抓取直播流链接...")
            
            # 获取直播流链接
            raw_url = find_stream_url(LIVE_URL)

            if not raw_url:
                empty_retries += 1
                print(f"[main] 第 {empty_retries} 次获取到空链接")
    
                if empty_retries >= MAX_EMPTY_RETRIES:
                    print(f"[main] 空链接超过 {MAX_EMPTY_RETRIES} 次，程序退出")
                    return
    
                time.sleep(random.uniform(3, 5))
                continue

            # 重置空链接计数器
            empty_retries = 0

            # 清洗链接：替换Unicode转义字符并去除末尾的反斜杠
            clean_url = raw_url.replace(r"\u0026", "&").rstrip('\\')
            quality = get_quality_from_url(clean_url)
            
            # 控制日志输出频率
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                print(f"[main] 获取到直播流: {clean_url} (质量: {quality})")
                last_log_time = current_time
    
            # 检查是否为可接受的质量（保持录播完整性）
            if not is_acceptable_quality(clean_url):
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 链接质量不可接受，等待重试...")
                time.sleep(random.uniform(3, 4))
                continue
    
            # 如果是第一次找到可接受质量的链接，或者找到了更高质量的链接
            if current_task_id is None or (is_better_quality(quality, current_quality) and not found_high_quality):
                # 生成文件名（包含质量标识）
                filename = generate_filename(quality)
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 生成文件名: {filename}")
    
                # 提交到 Aria2
                task_id = submit_to_aria2(clean_url, filename)
    
                if task_id:
                    # 如果之前有任务在运行，并且找到了更高质量的链接，则停止之前的任务
                    if current_task_id is not None and is_better_quality(quality, current_quality) and not found_high_quality:
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 找到更高质量链接 ({quality} > {current_quality})，停止之前的任务: {current_task_id}")
                        stop_aria2_task(current_task_id)
    
                    # 更新当前任务信息
                    current_task_id = task_id
                    current_quality = quality
    
                    # 如果是最高质量链接（or4），标记为已找到
                    if quality == "or4":
                        found_high_quality = True
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print("[main] 最高质量链接（or4）已找到并开始下载")
                else:
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print("[main] 下载任务提交失败，重新开始...")
                    time.sleep(2)
                    continue
    
            # 如果已经找到最高质量链接（or4），则只监控下载速度
            if found_high_quality:
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 最高质量链接下载中，开始监控下载速度...")
    
                # 监控下载速度
                low_speed_count = 0
                while True:
                    current_speed = get_aria2_speed()
                    active_tasks = get_active_tasks()
                    task_count = len(active_tasks)
                    
                    current_time = time.time()
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print(f"[main] 当前下载速度: {current_speed:.2f} KB/s, 活跃任务数: {task_count}")
    
                        # 显示活跃任务信息
                        for i, task in enumerate(active_tasks):
                            task_name = task.get('files', [{}])[0].get('path', '未知文件')
                            completed = int(task.get('completedLength', 0))
                            total = int(task.get('totalLength', 0))
                            if total > 0:
                                progress = (completed / total) * 100
                            else:
                                progress = 0
                            print(f"  任务 {i + 1}: {task_name} - 进度: {progress:.1f}%")
                        
                        last_log_time = current_time
    
                    if current_speed < SPEED_THRESHOLD:
                        low_speed_count += 1
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 速度低于阈值 ({SPEED_THRESHOLD} KB/s)，计数: {low_speed_count}")
    
                        if low_speed_count >= 5:  # 连续5次低于阈值才重新开始
                            if current_time - last_log_time >= LOG_INTERVAL:
                                print("[main] 速度持续过低，重新开始获取链接...")
                            found_high_quality = False  # 重置标志
                            break
                    else:
                        low_speed_count = 0  # 重置计数器
    
                    time.sleep(5)  # 每5秒检查一次速度
            else:
                # 如果还没有找到最高质量链接，继续寻找
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 当前画质: {current_quality}，继续寻找更高质量链接...")
                time.sleep(10)  # 每10秒检查一次是否有更高质量链接
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
if __name__ == "__main__":
    try:
        # 先启动 Aria2
        start_aria2()
        time.sleep(3)

        # 运行主程序
        main()
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
    '''

    def _get_sd_template(self):
        """获取标清模板 (文档1)"""
        return r'''import re
import subprocess
import time
import requests
import os
import sys
import random
import json
from datetime import datetime
import psutil
# 获取当前脚本所在目录作为基础目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def check_single_instance():
    """检查是否已有相同脚本在运行"""
    try:
        # 基于脚本路径和主播名称创建唯一标识
        script_name = os.path.basename(__file__)
        if 'SPECIFIED_NAME' in globals():
            instance_id = f"{script_name}_{SPECIFIED_NAME}"
        else:
            instance_id = script_name

        # 获取当前进程的PID
        current_pid = os.getpid()

        # 遍历所有进程
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue

                # 检查命令行参数中是否包含实例标识
                cmdline = proc.info.get('cmdline', [])
                if instance_id in ' '.join(cmdline):
                    print(f"已经有一个实例在运行: {instance_id}")
                    sys.exit(1)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except Exception as e:
        print(f"检查单实例时出错: {e}")

# 配置参数
LIVE_ID = 1234567890
LIVE_URL = f"https://live.douyin.com/{LIVE_ID}"
ARIA2_BAT_PATH = "aria2.bat"  # 使用相对路径
ARIA2_RPC_URL = "http://localhost:6800/jsonrpc"
SPEED_THRESHOLD = 100  # KB/s
MAX_EMPTY_RETRIES = 3
SPECIFIED_NAME = "主播名字"  # 可以修改为您想要的名称，如果为空则使用默认命名
LOG_INTERVAL = 30  # 日志输出间隔，单位秒（将在生成时替换）
ua_list = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
]

random_ua = random.choice(ua_list)

# 使用程序目录下的cookie文件
COOKIE_FILE = os.path.join(BASE_DIR, 'cookie.txt')
with open(COOKIE_FILE, 'r', encoding='utf-8') as file:
    cookies2 = file.read()

# 请求头
HEADERS = {
    "User-Agent": f"{random_ua}",
    "Cookie": f"{cookies2}",
    "Referer": f"https://live.douyin.com/{LIVE_ID}",
    "authority": "live.douyin.com",
    "method": "GET",
    "path": f"/{LIVE_ID}"
}

def get_current_datetime_string():
    """获取当前日期时间字符串，格式为YYYYMMDD_HHMMSS"""
    now = datetime.now()
    return now.strftime("%Y%m%d_%H%M%S")

def generate_filename(quality_suffix=""):
    """生成文件名，保存在当前工作目录下"""
    datetime_str = get_current_datetime_string()

    if SPECIFIED_NAME and SPECIFIED_NAME.strip():
        if quality_suffix:
            return f"{SPECIFIED_NAME}_{datetime_str}_{quality_suffix}.flv"  # 返回相对路径
        else:
            return f"{SPECIFIED_NAME}_{datetime_str}.flv"
    else:
        if quality_suffix:
            return f"live_{datetime_str}_{quality_suffix}.flv"
        else:
            return f"live_{datetime_str}.flv"

def check_aria2_running():
    """检查 Aria2 是否已经在运行"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "2.0",
            "method": "aria2.getVersion",
            "id": "1"
        }
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

def find_stream_url(url: str) -> str:
    """返回第一条可用的 flv；若无 flv 则返回第一条 m3u8"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # 1. 优先 flv
        flv_pattern = re.compile(r'"(https?://[^"]+\.flv[^"]*)"')
        flv_urls = flv_pattern.findall(resp.text)
        if flv_urls:
            return flv_urls[0]

        # 2. 退回 m3u8
        m3u8_pattern = re.compile(r'"(https?://[^"]+\.m3u8[^"]*)"')
        m3u8_urls = m3u8_pattern.findall(resp.text)
        if m3u8_urls:
            return m3u8_urls[0]

        return ""
    except Exception as e:
        print(f"[find_stream_url] 获取直播流时出错: {e}")
        return ""

def start_aria2():
    """启动 Aria2 下载器（如果未运行）"""
    # 先检查 Aria2 是否已经在运行
    if check_aria2_running():
        print("Aria2 已经在运行中，跳过启动。")
        return

    try:
        print("正在启动 Aria2...")
        subprocess.Popen([ARIA2_BAT_PATH], shell=True)
        time.sleep(5)  # 等待 Aria2 启动

        # 验证 Aria2 是否成功启动
        if check_aria2_running():
            print("Aria2 启动完成")
        else:
            print("Aria2 可能未正确启动，将继续尝试...")
    except Exception as e:
        print(f"启动 Aria2 时出错: {e}")

# 在所有录播脚本模板的 submit_to_aria2 函数中修改：

def submit_to_aria2(url, filename=None):
    headers = {'Content-Type': 'application/json'}
    
    # 先定义options
    options = {}
    if filename:
        options["out"] = filename

    # 设置下载目录为当前工作目录（EXE所在目录）
    options["dir"] = BASE_DIR

    # 添加User-Agent和其他头信息
    aria2_headers = {
        "User-Agent": random_ua,
        "Referer": f"https://live.douyin.com/{LIVE_ID}"
    }

    # 添加header选项
    header_list = []
    for key, value in aria2_headers.items():
        header_list.append(f"{key}: {value}")
    options["header"] = header_list

    # 构建参数
    params = [[url], options]

    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": "1",
        "params": params
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[submit_to_aria2] 成功添加下载任务，任务 ID: {result['result']}")
                if filename:
                    print(f"[submit_to_aria2] 文件将保存为: {os.path.join(BASE_DIR, filename)}")
                return result['result']  # 返回任务ID
            else:
                print(f"[submit_to_aria2] 添加下载任务失败: {result}")
                return None
        else:
            print(f"[submit_to_aria2] 请求失败，状态码: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"[submit_to_aria2] 网络请求出错: {e}")
        # 尝试启动 Aria2 并重新提交
        start_aria2()
        time.sleep(3)
        return submit_to_aria2(url, filename)

def get_aria2_speed():
    """获取 Aria2 当前所有任务的总下载速度（KB/s）"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.getGlobalStat",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                # 下载速度是字节/秒，转换为KB/s
                download_speed = int(result['result'].get('downloadSpeed', 0)) / 1024
                return download_speed
        return 0
    except Exception as e:
        print(f"[get_aria2_speed] 获取速度时出错: {e}")
        return 0

def get_active_tasks():
    """获取活跃的下载任务列表"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.tellActive",
        "id": "1"
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                return result['result']
        return []
    except Exception as e:
        print(f"[get_active_tasks] 获取任务列表时出错: {e}")
        return []

def stop_aria2_task(gid):
    """停止指定的下载任务"""
    headers = {'Content-Type': 'application/json'}
    payload = {
        "jsonrpc": "2.0",
        "method": "aria2.remove",
        "id": "1",
        "params": [gid]
    }

    try:
        response = requests.post(ARIA2_RPC_URL, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if 'result' in result:
                print(f"[stop_aria2_task] 成功停止任务: {gid}")
                return True
        return False
    except Exception as e:
        print(f"[stop_aria2_task] 停止任务时出错: {e}")
        return False

def get_quality_from_url(url):
    """从URL中提取质量标识"""
    if "sd.flv" in url:
        return "sd"
    elif "ld.flv" in url:
        return "ld"
    elif "hd.flv" in url:
        return "hd"
    elif "md.flv" in url:
        return "md"
    elif "or4.flv" in url:
        return "or4"
    elif "uhd.flv" in url:
        return "uhd"
    else:
        return "unknown"

def is_high_quality(url):
    """判断是否为高质量链接"""
    return "sd.flv" in url

def is_acceptable_quality(url):
    """判断是否为可接受的质量链接（保持录播完整性）"""
    return "sd.flv" in url


def get_quality_priority(quality):
    """获取画质优先级，数值越大表示画质越好"""
    quality_priority = {
        "or4": 5,
        "uhd": 4,
        "hd": 3,
        "ld": 2,
        "sd": 1,
        "unknown": 0
    }
    return quality_priority.get(quality, 0)


def is_better_quality(new_quality, current_quality):
    """判断新画质是否比当前画质更好"""
    return get_quality_priority(new_quality) > get_quality_priority(current_quality)



def main():
    try:
        empty_retries = 0
        # 初始化变量
        current_task_id = None
        current_quality = ""
        found_high_quality = False
        last_log_time = 0  # 上次日志输出时间
        
        while True:
            print("[main] 开始抓取直播流链接...")
            
            # 获取直播流链接
            raw_url = find_stream_url(LIVE_URL)

            if not raw_url:
                empty_retries += 1
                print(f"[main] 第 {empty_retries} 次获取到空链接")
    
                if empty_retries >= MAX_EMPTY_RETRIES:
                    print(f"[main] 空链接超过 {MAX_EMPTY_RETRIES} 次，程序退出")
                    return
    
                time.sleep(random.uniform(3, 5))
                continue

            # 重置空链接计数器
            empty_retries = 0

            # 清洗链接：替换Unicode转义字符并去除末尾的反斜杠
            clean_url = raw_url.replace(r"\u0026", "&").rstrip('\\')
            quality = get_quality_from_url(clean_url)
            
            # 控制日志输出频率
            current_time = time.time()
            if current_time - last_log_time >= LOG_INTERVAL:
                print(f"[main] 获取到直播流: {clean_url} (质量: {quality})")
                last_log_time = current_time
    
            # 检查是否为可接受的质量（保持录播完整性）
            if not is_acceptable_quality(clean_url):
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 链接质量不可接受，等待重试...")
                time.sleep(random.uniform(3, 4))
                continue
    
            # 如果是第一次找到可接受质量的链接，或者找到了更高质量的链接
            if current_task_id is None or (is_better_quality(quality, current_quality) and not found_high_quality):
                # 生成文件名（包含质量标识）
                filename = generate_filename(quality)
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 生成文件名: {filename}")
    
                # 提交到 Aria2
                task_id = submit_to_aria2(clean_url, filename)
    
                if task_id:
                    # 如果之前有任务在运行，并且找到了更高质量的链接，则停止之前的任务
                    if current_task_id is not None and is_better_quality(quality, current_quality) and not found_high_quality:
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 找到更高质量链接 ({quality} > {current_quality})，停止之前的任务: {current_task_id}")
                        stop_aria2_task(current_task_id)
    
                    # 更新当前任务信息
                    current_task_id = task_id
                    current_quality = quality
    
                    # 如果是最高质量链接（or4），标记为已找到
                    if quality == "or4":
                        found_high_quality = True
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print("[main] 最高质量链接（or4）已找到并开始下载")
                else:
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print("[main] 下载任务提交失败，重新开始...")
                    time.sleep(2)
                    continue
    
            # 如果已经找到最高质量链接（or4），则只监控下载速度
            if found_high_quality:
                if current_time - last_log_time >= LOG_INTERVAL:
                    print("[main] 最高质量链接下载中，开始监控下载速度...")
    
                # 监控下载速度
                low_speed_count = 0
                while True:
                    current_speed = get_aria2_speed()
                    active_tasks = get_active_tasks()
                    task_count = len(active_tasks)
                    
                    current_time = time.time()
                    if current_time - last_log_time >= LOG_INTERVAL:
                        print(f"[main] 当前下载速度: {current_speed:.2f} KB/s, 活跃任务数: {task_count}")
    
                        # 显示活跃任务信息
                        for i, task in enumerate(active_tasks):
                            task_name = task.get('files', [{}])[0].get('path', '未知文件')
                            completed = int(task.get('completedLength', 0))
                            total = int(task.get('totalLength', 0))
                            if total > 0:
                                progress = (completed / total) * 100
                            else:
                                progress = 0
                            print(f"  任务 {i + 1}: {task_name} - 进度: {progress:.1f}%")
                        
                        last_log_time = current_time
    
                    if current_speed < SPEED_THRESHOLD:
                        low_speed_count += 1
                        if current_time - last_log_time >= LOG_INTERVAL:
                            print(f"[main] 速度低于阈值 ({SPEED_THRESHOLD} KB/s)，计数: {low_speed_count}")
    
                        if low_speed_count >= 5:  # 连续5次低于阈值才重新开始
                            if current_time - last_log_time >= LOG_INTERVAL:
                                print("[main] 速度持续过低，重新开始获取链接...")
                            found_high_quality = False  # 重置标志
                            break
                    else:
                        low_speed_count = 0  # 重置计数器
    
                    time.sleep(5)  # 每5秒检查一次速度
            else:
                # 如果还没有找到最高质量链接，继续寻找
                if current_time - last_log_time >= LOG_INTERVAL:
                    print(f"[main] 当前画质: {current_quality}，继续寻找更高质量链接...")
                time.sleep(10)  # 每10秒检查一次是否有更高质量链接
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
if __name__ == "__main__":
    try:
        # 先启动 Aria2
        start_aria2()
        time.sleep(3)

        # 运行主程序
        main()
    except KeyboardInterrupt:
        print("\n[main] 程序被用户中断")
    except Exception as e:
        print(f"[main] 程序运行出错: {e}")
    '''

    def _get_transcode_keep_template(self):
        """获取保留原文件的转码模板 (文档6)"""
        return r'''@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 获取主程序所在目录
if defined _argv (
    :: 如果是被调用的，使用主程序目录
    set "APP_DIR=%~dp0"
) else (
    :: 如果是直接运行的，使用脚本所在目录
    for %%I in ("%~dp0.") do set "APP_DIR=%%~fI"
)

:: 确保使用正确的工作目录
cd /d "%APP_DIR%"
echo 工作目录: %APP_DIR%

:: 设置路径和文件名
set "SOURCE_DIR=%APP_DIR%"
set "TARGET_DIR=%APP_DIR%\已转码\{anchor_name}"
set "LOG_FILE=%TARGET_DIR%\converted_files.txt"
set "FFMPEG_PATH=%APP_DIR%\ffmpeg.exe"

:: 创建目标目录
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
)

:: 创建日志文件（如果不存在）
if not exist "%LOG_FILE%" (
    type nul > "%LOG_FILE%"
)

:: 遍历程序目录下所有以"主播名"开头的flv文件
for %%f in ("%SOURCE_DIR%\{anchor_name}*.flv") do (
    set "filename=%%~nf"
    set "filepath=%%f"
    set "output_path=%TARGET_DIR%\!filename!.mp4"

    :: 检查是否已经转码过
    set "converted=0"

    if exist "!output_path!" (
        set "converted=1"
        echo 跳过已存在文件: !filename!
    ) else (
        findstr /x /c:"!filename!" "%LOG_FILE%" >nul
        if !errorlevel! equ 0 (
            set "converted=1"
            echo 跳过已记录文件: !filename!
        )
    )

    :: 如果未转码，则进行转码
    if !converted! equ 0 (
        echo 正在转码: %%f
        "%FFMPEG_PATH%" -i "!filepath!" -c copy "!output_path!" -y
        if !errorlevel! equ 0 (
            echo 转码成功: !filename!
            echo !filename! >> "%LOG_FILE%"
        ) else (
            echo 转码失败: !filename!
            if exist "!output_path!" (
                del "!output_path!"
            )
        )
    )
)

echo 转码任务完成！
ping -n 10 127.0.0.1 >nul
    '''

    def _get_transcode_no_keep_template(self):
        """获取不保留原文件的转码模板 (文档7)"""
        return r'''@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 获取主程序所在目录
if defined _argv (
    :: 如果是被调用的，使用主程序目录
    set "APP_DIR=%~dp0"
) else (
    :: 如果是直接运行的，使用脚本所在目录
    for %%I in ("%~dp0.") do set "APP_DIR=%%~fI"
)

:: 确保使用正确的工作目录
cd /d "%APP_DIR%"
echo 工作目录: %APP_DIR%

:: 设置路径和文件名
set "SOURCE_DIR=%APP_DIR%"
set "TARGET_DIR=%APP_DIR%\已转码\主播名"
set "LOG_FILE=%TARGET_DIR%\converted_files.txt"
set "FFMPEG_PATH=%APP_DIR%\ffmpeg.exe"

:: 创建目标目录
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
)

:: 创建日志文件（如果不存在）
if not exist "%LOG_FILE%" (
    type nul > "%LOG_FILE%"
)

:: 遍历程序目录下所有以"主播名"开头的flv文件
for %%f in ("%SOURCE_DIR%\主播名*.flv") do (
    set "filename=%%~nf"
    set "filepath=%%f"
    set "output_path=%TARGET_DIR%\!filename!.mp4"

    :: 检查是否已经转码过
    set "converted=0"

    if exist "!output_path!" (
        set "converted=1"
        echo 跳过已存在文件: !filename!
    ) else (
        findstr /x /c:"!filename!" "%LOG_FILE%" >nul
        if !errorlevel! equ 0 (
            set "converted=1"
            echo 跳过已记录文件: !filename!
        )
    )

    :: 如果未转码，则进行转码
    if !converted! equ 0 (
        echo 正在转码: %%f
        "%FFMPEG_PATH%" -i "!filepath!" -c copy "!output_path!" -y
        if !errorlevel! equ 0 (
            echo 转码成功: !filename!
            echo !filename! >> "%LOG_FILE%"
            del "!filepath!"
            echo 已删除原始FLV文件: !filename!
        ) else (
            echo 转码失败: !filename!
            if exist "!output_path!" (
                del "!output_path!"
            )
        )
    )
)

echo 转码任务完成！
ping -n 10 127.0.0.1 >nul
    '''
    #----------------模板文件终------------------------
    def __init__(self, root_window):  # 修改参数名
        self.root = root_window  # 使用传入的窗口
        self.root.title("录播脚本生成器")
        self.root.geometry("600x550")
        self.log_messages = []  # 存储日志消息
        self.log_interval_var = tk.StringVar(value="30")  # 默认30秒

        # 画质选项映射到模板文件
        self.quality_map = {
            "原画": self._get_or4_template(),
            "蓝光": self._get_uhd_template(),
            "超清": self._get_hd_template(),
            "高清": self._get_ld_template(),
            "标清": self._get_sd_template()
        }

        # 转码模板映射
        self.transcode_templates = {
            "保留原文件": self._get_transcode_keep_template(),
            "不保留原文件": self._get_transcode_no_keep_template()
        }

        # 存储已添加的主播信息
        self.anchor_list = []
        self.current_editing_anchor = None

        # 创建界面元素 - 只调用一次，在 quality_map 定义之后
        self.create_widgets()

        # 加载已存在的主播脚本
        self.load_existing_scripts()

    def log_message(self, message, level="info"):
        """添加日志方法"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)  # 输出到控制台

        # 如果状态标签存在，更新状态显示
        if hasattr(self, 'status_label') and self.status_label:
            try:
                current_text = self.status_label.cget("text")
                # 限制显示长度，避免过长
                if len(current_text) > 200:
                    current_text = current_text[-100:]
                new_text = f"{message}\n{current_text}"
                self.status_label.config(text=new_text)
            except:
                pass

    def create_widgets(self):
        # 主播名字输入
        tk.Label(self.root, text="主播名字:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.anchor_name_entry = tk.Entry(self.root, width=30)
        self.anchor_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # 直播间号输入
        tk.Label(self.root, text="直播间号:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.live_id_entry = tk.Entry(self.root, width=30)
        self.live_id_entry.grid(row=1, column=1, padx=10, pady=10, sticky="w")

        # 画质选择
        tk.Label(self.root, text="录制画质:").grid(row=2, column=0, padx=10, pady=10, sticky="e")
        self.quality_var = tk.StringVar(value="原画")
        self.quality_combo = ttk.Combobox(self.root, textvariable=self.quality_var,
                                          values=list(self.quality_map.keys()), state="readonly")
        self.quality_combo.grid(row=2, column=1, padx=10, pady=10, sticky="w")
        # 优先保证录播完整性选项
        self.integrity_var = tk.BooleanVar(value=True)
        self.integrity_check = tk.Checkbutton(self.root, text="优先保证录播完整性",
                                              variable=self.integrity_var)
        self.integrity_check.grid(row=3, column=0, columnspan=2, pady=5, sticky="w")

        # 自动转码选项
        self.transcode_var = tk.BooleanVar(value=False)
        self.transcode_check = tk.Checkbutton(self.root, text="录播完毕后自动转码",
                                              variable=self.transcode_var,
                                              command=self.on_transcode_toggle)
        self.transcode_check.grid(row=4, column=0, columnspan=2, pady=5, sticky="w")

        # 不保留原文件选项（默认禁用）
        self.no_keep_var = tk.BooleanVar(value=False)
        self.no_keep_check = tk.Checkbutton(self.root, text="转码完成后不保留原文件",
                                            variable=self.no_keep_var,
                                            state="disabled")
        self.no_keep_check.grid(row=5, column=0, columnspan=2, pady=5, sticky="w", padx=20)

        # 按钮框架
        button_frame = tk.Frame(self.root)
        button_frame.grid(row=6, column=0, columnspan=2, pady=10)

        # 生成按钮
        self.generate_button = tk.Button(button_frame, text="生成录播脚本", command=self.generate_script)
        self.generate_button.pack(side=tk.LEFT, padx=5)

        # 更新按钮
        self.update_button = tk.Button(button_frame, text="更新录播脚本", command=self.update_script)
        self.update_button.pack(side=tk.LEFT, padx=5)

        # 删除按钮
        self.delete_button = tk.Button(button_frame, text="删除录播脚本", command=self.delete_script, bg="#ff6b6b",
                                       fg="white")
        self.delete_button.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.status_label = tk.Label(self.root, text="", fg="blue", justify=tk.LEFT, wraplength=500)
        self.status_label.grid(row=7, column=0, columnspan=2, pady=5)

        # 已添加主播列表
        tk.Label(self.root, text="已添加主播列表:").grid(row=8, column=0, columnspan=2, pady=(20, 5), sticky="w")

        # 创建列表框架
        list_frame = tk.Frame(self.root)
        list_frame.grid(row=9, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        # 创建滚动条
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 创建主播列表
        self.anchor_listbox = tk.Listbox(list_frame, width=70, height=10, yscrollcommand=scrollbar.set)
        self.anchor_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.anchor_listbox.bind('<<ListboxSelect>>', self.on_anchor_select)

        scrollbar.config(command=self.anchor_listbox.yview)

        # 配置网格权重，使列表可以扩展
        self.root.grid_rowconfigure(9, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

    def on_transcode_toggle(self):
        """当自动转码选项状态改变时的回调函数"""
        if self.transcode_var.get():
            # 启用不保留原文件选项
            self.no_keep_check.config(state="normal")
        else:
            # 禁用不保留原文件选项并重置为未选中
            self.no_keep_check.config(state="disabled")
            self.no_keep_var.set(False)

    def delete_script(self):
        if not self.current_editing_anchor:
            messagebox.showwarning("警告", "请先选择一个要删除的主播")
            return

        anchor_name = self.current_editing_anchor['name']
        filename = self.current_editing_anchor['filename']

        # 确认删除
        if not messagebox.askyesno("确认删除", f"确定要删除主播 {anchor_name} 的录播脚本吗？\n文件: {filename}"):
            return

        try:
            # 删除录播脚本文件
            if os.path.exists(filename):
                os.remove(filename)

            # 删除转码脚本文件（如果存在）
            transcode_filename = f"自动转码-{anchor_name}.bat"
            if os.path.exists(transcode_filename):
                os.remove(transcode_filename)

            # 显示删除成功信息
            self.status_label.config(text=f"脚本已删除: {filename}")
            messagebox.showinfo("成功", f"录播脚本已删除: {filename}")

            # 重新加载列表
            self.load_existing_scripts()
            self.current_editing_anchor = None

            # 清空表单
            self.anchor_name_entry.delete(0, tk.END)
            self.live_id_entry.delete(0, tk.END)
            self.quality_var.set("原画")
            self.integrity_var.set(True)
            self.transcode_var.set(False)
            self.no_keep_var.set(False)
            self.no_keep_check.config(state="disabled")

        except Exception as e:
            messagebox.showerror("错误", f"删除文件失败: {str(e)}")

    def load_existing_scripts(self):
        """加载本地已存在的录播脚本"""
        self.anchor_list = []
        self.anchor_listbox.delete(0, tk.END)

        # 查找以"开始录播"开头且不以"模板"开头的.py文件
        for filename in os.listdir("."):
            if (filename.startswith("开始录播-") and
                    filename.endswith(".py") and
                    "脚本范例" not in filename):

                # 从文件名提取主播名字
                anchor_name = filename.replace("开始录播-", "").replace(".py", "")

                try:
                    # 读取文件内容，提取画质信息
                    with open(filename, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 提取画质信息 - 改进的正则表达式
                    quality_match = re.search(r'def is_high_quality\(url\):\s*.*?return\s+"([^"]+)"\s+in\s+url',
                                              content, re.DOTALL)
                    if quality_match:
                        quality_str = quality_match.group(1)
                        # 根据画质字符串直接判断画质
                        if "or4.flv" in quality_str:
                            quality_name = "原画"
                        elif "uhd.flv" in quality_str:
                            quality_name = "蓝光"
                        elif "hd.flv" in quality_str:
                            quality_name = "超清"
                        elif "ld.flv" in quality_str:
                            quality_name = "高清"
                        elif "sd.flv" in quality_str:
                            quality_name = "标清"
                        else:
                            quality_name = "原画"  # 默认值
                    else:
                        quality_name = "原画"  # 默认值

                    # 提取直播间号
                    live_id_match = re.search(r'LIVE_ID\s*=\s*(\d+)', content)
                    live_id = live_id_match.group(1) if live_id_match else ""

                    # 提取完整性设置
                    integrity_match = re.search(r'def is_acceptable_quality\(url\):\s*(.*?)(?=\n\n|\nclass|\nif|$)',
                                                content, re.DOTALL)
                    # 提取完整性设置 - 通过比较两个函数内容是否相同来判断
                    integrity_enabled = True
                    try:
                        # 提取is_acceptable_quality函数内容
                        acceptable_quality_match = re.search(
                            r'def is_acceptable_quality\(url\):\s*(.*?)(?=\n\n|\nclass|\nif|$)',
                            content,
                            re.DOTALL
                        )

                        # 提取is_high_quality函数内容
                        high_quality_match = re.search(
                            r'def is_high_quality\(url\):\s*(.*?)(?=\n\n|\nclass|\nif|$)',
                            content,
                            re.DOTALL
                        )

                        if acceptable_quality_match and high_quality_match:
                            acceptable_quality_content = acceptable_quality_match.group(1).strip()
                            high_quality_content = high_quality_match.group(1).strip()

                            # 如果两个函数内容完全相同，则认为不保证录播完整性
                            if acceptable_quality_content == high_quality_content:
                                integrity_enabled = False
                            else:
                                integrity_enabled = True
                        else:
                            integrity_enabled = True  # 默认值

                    except Exception as e:
                        print(f"解析完整性设置时出错: {e}")
                        integrity_enabled = True  # 出错时默认开启完整性

                    # 检查是否存在转码脚本
                    transcode_enabled = False
                    no_keep_enabled = False
                    transcode_filename = f"自动转码-{anchor_name}.bat"
                    if os.path.exists(transcode_filename):
                        transcode_enabled = True
                        # 读取转码脚本判断是否不保留原文件
                        try:
                            with open(transcode_filename, 'r', encoding='utf-8') as tf:
                                transcode_content = tf.read()
                            # 精确判断：检查是否包含删除原始文件的语句
                            # 使用正则表达式匹配删除语句和删除提示
                            delete_pattern1 = r'del\s+"!filepath!"'
                            delete_pattern2 = r'echo\s+已删除原始FLV文件:\s*!filename!'

                            # 检查是否同时包含删除命令和删除提示
                            has_delete_command = bool(re.search(delete_pattern1, transcode_content, re.IGNORECASE))
                            has_delete_message = bool(re.search(delete_pattern2, transcode_content))

                            # 如果同时包含删除命令和删除提示，则认为是不保留原文件
                            if has_delete_command and has_delete_message:
                                no_keep_enabled = True
                            else:
                                no_keep_enabled = False

                        except Exception as e:
                            print(f"读取转码脚本时出错: {e}")
                            # 出错时使用备用方法：简单关键词判断
                            try:
                                with open(transcode_filename, 'r', encoding='utf-8') as tf:
                                    transcode_content = tf.read()
                                if "删除" in transcode_content or "del" in transcode_content.lower():
                                    no_keep_enabled = True
                            except:
                                pass

                    # 添加到列表
                    anchor_info = {
                        'name': anchor_name,
                        'live_id': live_id,
                        'quality': quality_name,
                        'integrity': integrity_enabled,
                        'transcode': transcode_enabled,
                        'no_keep': no_keep_enabled,
                        'filename': filename
                    }
                    self.anchor_list.append(anchor_info)

                    # 添加到列表显示
                    display_text = f"{anchor_name} (直播间: {live_id}, 画质: {quality_name}, 完整性: {'开启' if integrity_enabled else '关闭'}, 转码: {'开启' if transcode_enabled else '关闭'}, 删除原文件: {'是' if no_keep_enabled else '否'})"
                    self.anchor_listbox.insert(tk.END, display_text)

                except Exception as e:
                    print(f"读取文件 {filename} 时出错: {e}")

    def on_anchor_select(self, event):
        """当选择主播列表项时的回调函数"""
        selection = self.anchor_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.anchor_list):
                anchor_info = self.anchor_list[index]
                self.current_editing_anchor = anchor_info

                # 填充表单
                self.anchor_name_entry.delete(0, tk.END)
                self.anchor_name_entry.insert(0, anchor_info['name'])

                self.live_id_entry.delete(0, tk.END)
                self.live_id_entry.insert(0, anchor_info['live_id'])

                self.quality_var.set(anchor_info['quality'])
                self.integrity_var.set(anchor_info['integrity'])
                self.transcode_var.set(anchor_info['transcode'])
                self.no_keep_var.set(anchor_info['no_keep'])

                # 根据转码选项状态设置不保留原文件选项的可用状态
                if anchor_info['transcode']:
                    self.no_keep_check.config(state="normal")
                else:
                    self.no_keep_check.config(state="disabled")

    def generate_transcode_script(self, anchor_name):
        """生成转码脚本 - 统一命名格式"""
        if not self.transcode_var.get():
            return True  # 未勾选转码选项，直接返回成功

        try:
            # 统一命名格式：自动转码-主播名.bat
            output_filename = f"自动转码-{anchor_name}.bat"

            # 根据是否保留原文件选择模板
            if self.no_keep_var.get():
                template_content = self._get_transcode_no_keep_template()
            else:
                template_content = self._get_transcode_keep_template()

            # 替换模板中的占位符
            transcode_content = template_content.replace("{anchor_name}", anchor_name)
            transcode_content = transcode_content.replace("主播名", anchor_name)
            transcode_content = transcode_content.replace("主播名字", anchor_name)
            transcode_content = transcode_content.replace("主播名称", anchor_name)
            transcode_content = transcode_content.replace("SPECIFIED_NAME", anchor_name)

            # 保存文件
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(transcode_content)

            self.log_message(f"已生成转码脚本: {output_filename}")
            return True

        except Exception as e:
            self.log_message(f"生成转码脚本失败: {str(e)}", "error")
            return False

    def generate_script(self):
        """生成新的录播脚本"""
        anchor_name = self.anchor_name_entry.get().strip()
        live_id = self.live_id_entry.get().strip()
        quality = self.quality_var.get()
        integrity_enabled = self.integrity_var.get()

        # 验证输入
        if not self.validate_inputs(anchor_name, live_id):
            return

        # 直接读取模板内容，不再检查文件存在
        template_content = self.read_template(quality, integrity_enabled)
        if template_content is None:
            return

        # 读取并调整模板
        template_content = self.read_template(quality, integrity_enabled)
        if template_content is None:
            return

        # 替换模板中的变量
        template_content = re.sub(
            r'SPECIFIED_NAME\s*=\s*"[^"]*"',
            f'SPECIFIED_NAME = "{anchor_name}"',
            template_content
        )

        template_content = re.sub(
            r'LIVE_ID\s*=\s*\d+',
            f'LIVE_ID = {live_id}',
            template_content
        )

        # 生成输出文件名
        output_filename = f"开始录播-{anchor_name}.py"

        # 检查文件是否已存在
        if os.path.exists(output_filename):
            if not messagebox.askyesno("确认覆盖", f"文件 {output_filename} 已存在，是否覆盖？"):
                return

        # 保存录播脚本文件
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(template_content)

            # 生成转码脚本
            transcode_success = self.generate_transcode_script(anchor_name)

            if transcode_success:
                if self.transcode_var.get():
                    success_message = f"新增录制脚本成功！\n录播脚本: {output_filename}\n转码脚本: 自动转码-{anchor_name}.bat\n请添加到\"自动化任务\"使其生效"
                else:
                    success_message = f"新增录制脚本成功！\n录播脚本: {output_filename}\n请添加到\"自动化任务\"使其生效"

                self.status_label.config(text=success_message)

            # 重新加载列表
            self.load_existing_scripts()

        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")

    def update_script(self):
        """更新已存在的录播脚本"""
        if not self.current_editing_anchor:
            messagebox.showwarning("警告", "请先选择一个要修改的主播")
            return

        anchor_name = self.anchor_name_entry.get().strip()
        live_id = self.live_id_entry.get().strip()
        quality = self.quality_var.get()
        integrity_enabled = self.integrity_var.get()

        # 验证输入
        if not self.validate_inputs(anchor_name, live_id):
            return

        # 读取并调整模板
        template_content = self.read_template(quality, integrity_enabled)
        if template_content is None:
            return

        # 替换模板中的变量
        template_content = re.sub(
            r'SPECIFIED_NAME\s*=\s*"[^"]*"',
            f'SPECIFIED_NAME = "{anchor_name}"',
            template_content
        )

        template_content = re.sub(
            r'LIVE_ID\s*=\s*\d+',
            f'LIVE_ID = {live_id}',
            template_content
        )

        # 确定文件名（如果主播名字改变，需要重命名文件）
        old_filename = self.current_editing_anchor['filename']
        new_filename = f"开始录播-{anchor_name}.py"

        try:
            # 如果文件名改变，先删除旧文件
            if old_filename != new_filename and os.path.exists(old_filename):
                os.remove(old_filename)

            # 保存新文件
            with open(new_filename, 'w', encoding='utf-8') as f:
                f.write(template_content)

            # 生成转码脚本
            transcode_success = self.generate_transcode_script(anchor_name)

            if transcode_success:
                if self.transcode_var.get():
                    success_message = f"脚本已更新！\n录播脚本: {new_filename}\n转码脚本: 自动转码-{anchor_name}.bat"
                else:
                    success_message = f"脚本已更新: {new_filename}"

                self.status_label.config(text=success_message)
                messagebox.showinfo("成功", success_message)

            # 重新加载列表
            self.load_existing_scripts()
            self.current_editing_anchor = None

            # 清空表单
            self.anchor_name_entry.delete(0, tk.END)
            self.live_id_entry.delete(0, tk.END)
            self.quality_var.set("原画")
            self.integrity_var.set(True)
            self.transcode_var.set(False)
            self.no_keep_var.set(False)
            self.no_keep_check.config(state="disabled")

        except Exception as e:
            messagebox.showerror("错误", f"更新文件失败: {str(e)}")

    def read_template(self, quality, integrity_enabled):
        """读取对应画质的模板内容"""
        template_content = self.quality_map.get(quality)

        if not template_content:
            messagebox.showerror("错误", f"未找到画质 {quality} 的模板")
            return None

        # 在模板替换前确保 BASE_DIR 定义存在
        if "BASE_DIR = os.path.dirname(os.path.abspath(__file__))" not in template_content:
            # 在导入模块后插入 BASE_DIR 定义
            import_section_end = template_content.find('\n\n') + 1
            if import_section_end > 0:
                base_dir_definition = "\n# 获取当前脚本所在目录作为基础目录\nBASE_DIR = os.path.dirname(os.path.abspath(__file__))\n"
                template_content = template_content[:import_section_end] + base_dir_definition + template_content[import_section_end:]

        # 根据完整性设置调整is_acceptable_quality函数
        if integrity_enabled:
            # 勾选"优先保证录播完整性"时，保持模板原样
            pass
        else:
            # 未勾选时，使is_acceptable_quality函数与is_high_quality函数完全一样
            # 修复正则表达式匹配
            high_quality_match = re.search(
                r'def is_high_quality\(url\):\s*.*?return\s+[^"]+"([^"]+)"\s+in\s+url',
                template_content,
                re.DOTALL
            )

            if high_quality_match:
                high_quality_str = high_quality_match.group(0)
                # 创建新的is_acceptable_quality函数
                acceptable_quality_func = high_quality_str.replace('is_high_quality', 'is_acceptable_quality')

                # 替换is_acceptable_quality函数
                template_content = re.sub(
                    r'def is_acceptable_quality\(url\):\s*.*?return\s+[^"]+"([^"]+)"\s+in\s+url',
                    acceptable_quality_func,
                    template_content,
                    flags=re.DOTALL
                )

        return template_content


    def validate_inputs(self, anchor_name, live_id):
        """验证输入数据"""
        if not anchor_name:
            messagebox.showerror("错误", "请输入主播名字")
            return False

        if not live_id:
            messagebox.showerror("错误", "请输入直播间号")
            return False

        if not live_id.isdigit():
            messagebox.showerror("错误", "直播间号必须为数字")
            return False

        return True
#---------------------------------以下为录播cookie刷新--------------------------------------

class DouyinCookieRefresher:
    def __init__(self, parent=None):  # 改为可选参数
        if parent:
            self.root = tk.Toplevel(parent)  # 如果是子窗口
            self.root.transient(parent)
            self.root.grab_set()
        else:
            self.root = tk.Tk()  # 如果是独立窗口

        self.root.title("录播Cookie刷新器 v1.0")
        self.root.geometry("500x300")
        self.root.resizable(False, False)

        # 居中显示窗口
        self.center_window()

        # 变量初始化
        self.douyin_url = tk.StringVar()
        self.countdown_var = tk.StringVar(value="28")
        self.countdown_running = False
        self.driver = None
        self.cookie_file = "cookie.txt"
        self.parent = parent  # 保存父窗口引用

        self.setup_ui()

    def center_window(self):
        """窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_ui(self):
        """设置用户界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="抖音Cookie刷新器",
                                font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # 说明文字
        desc_label = ttk.Label(main_frame,
                               text="请输入正在直播的抖音直播间链接\n格式示例: https://live.douyin.com/123456789\n输入后按一次键盘的回车(Enter)键，等待一段时间后自动开始\n不要重复按回车键",
                               justify=tk.CENTER)
        desc_label.pack(pady=5)

        # 输入框框架
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=15)

        ttk.Label(input_frame, text="直播间链接:").pack(side=tk.LEFT)
        url_entry = ttk.Entry(input_frame, textvariable=self.douyin_url, width=40)
        url_entry.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

        # 倒计时显示
        countdown_frame = ttk.Frame(main_frame)
        countdown_frame.pack(pady=20)

        ttk.Label(countdown_frame, text="倒计时:").pack(side=tk.LEFT)
        countdown_label = ttk.Label(countdown_frame, textvariable=self.countdown_var,
                                    font=("Arial", 20, "bold"), foreground="red")
        countdown_label.pack(side=tk.LEFT, padx=10)
        ttk.Label(countdown_frame, text="秒").pack(side=tk.LEFT)

        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)

        self.start_btn = ttk.Button(button_frame, text="开始获取Cookie",
                                    command=self.start_cookie_refresh)
        self.start_btn.pack(side=tk.LEFT, padx=10)

        ttk.Button(button_frame, text="退出",
                   command=self.on_closing).pack(side=tk.LEFT, padx=10)

        # 状态显示
        self.status_var = tk.StringVar(value="就绪 - 请输入抖音直播间链接")
        status_label = ttk.Label(main_frame, textvariable=self.status_var,
                                 relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(fill=tk.X, pady=10)

        # 绑定回车键
        url_entry.bind('<Return>', lambda e: self.start_cookie_refresh())

        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_cookie_refresh(self):
        """开始Cookie刷新流程"""
        url = self.douyin_url.get().strip()

        if not url:
            messagebox.showerror("错误", "请输入抖音直播间链接！")
            return

        # 验证URL格式
        if not self.validate_douyin_url(url):
            messagebox.showerror("错误",
                                 "链接格式不正确！\n"
                                 "正确格式示例: https://live.douyin.com/123456789")
            return

        # 禁用开始按钮
        self.start_btn.config(state="disabled")
        self.status_var.set("正在启动浏览器...")

        # 在新线程中执行Cookie获取
        thread = threading.Thread(target=self.cookie_refresh_process, daemon=True)
        thread.start()

    def validate_douyin_url(self, url):
        """验证抖音链接格式"""
        import re
        pattern = r'^https?://live\.douyin\.com/\d+'
        return re.match(pattern, url) is not None

    def cookie_refresh_process(self):
        """Cookie刷新主流程"""
        try:
            # 启动浏览器
            if not self.start_browser():
                self.root.after(0, lambda: self.status_var.set("浏览器启动失败"))
                self.root.after(0, lambda: self.start_btn.config(state="normal"))
                return

            # 开始倒计时
            self.countdown_running = True
            self.start_countdown()

        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"错误: {str(e)}"))
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

    def start_browser(self):
        """启动浏览器"""
        try:
            self.root.after(0, lambda: self.status_var.set("正在启动Edge浏览器..."))

            # 配置浏览器选项
            options = EdgeOptions()
            options.use_chromium = True
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # 尝试启动浏览器
            self.driver = webdriver.Edge(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # 打开抖音直播间
            url = self.douyin_url.get().strip()
            self.root.after(0, lambda: self.status_var.set(f"正在打开: {url}"))
            self.driver.get(url)

            return True

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"浏览器启动失败: {str(e)}"))
            return False

    def start_countdown(self):
        """开始倒计时"""

        def update_countdown(seconds_left):
            if not self.countdown_running:
                return

            self.root.after(0, lambda: self.countdown_var.set(str(seconds_left)))
            self.root.after(0, lambda: self.status_var.set(f"倒计时: {seconds_left}秒后获取Cookie..."))

            if seconds_left > 0:
                # 每秒更新一次
                self.root.after(1000, lambda: update_countdown(seconds_left - 1))
            else:
                # 倒计时结束，获取Cookie
                self.get_cookies()

        # 开始28秒倒计时
        update_countdown(28)

    def modify_cookie_with_quality(self, cookie_str, quality):
        """修改Cookie，添加或更新画质参数"""
        # 将Cookie字符串转换为字典
        cookie_dict = {}
        if cookie_str:
            cookie_pairs = cookie_str.split("; ")
            for pair in cookie_pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    cookie_dict[key] = value

        # 添加或更新画质参数
        cookie_dict["live_local_quality"] = quality
        cookie_dict["webcast_local_quality"] = quality

        # 将字典转换回字符串
        modified_cookie = "; ".join([f"{key}={value}" for key, value in cookie_dict.items()])

        return modified_cookie

    def get_cookies(self):
        """获取并保存Cookie"""
        try:
            self.root.after(0, lambda: self.status_var.set("正在获取Cookie..."))

            # 获取所有Cookie
            cookies = self.driver.get_cookies()

            # 转换为字符串格式
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

            # 添加origin画质参数
            cookie_with_origin = self.modify_cookie_with_quality(cookie_str, "origin")

            # 保存原始Cookie到文件
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                f.write(cookie_with_origin)

            # 生成不同画质的Cookie文件
            qualities = ["uhd", "hd", "ld", "sd"]
            for quality in qualities:
                cookie_with_quality = self.modify_cookie_with_quality(cookie_str, quality)
                quality_file = f"cookie_{quality}.txt"
                with open(quality_file, "w", encoding="utf-8") as f:
                    f.write(cookie_with_quality)

            # 关闭浏览器
            if self.driver:
                self.driver.quit()
                self.driver = None

            # 更新状态
            self.root.after(0, lambda: self.status_var.set(f"Cookie获取成功！已保存到多个文件"))
            self.root.after(0, lambda: self.countdown_var.set("完成"))

            # 显示成功消息
            success_message = (
                f"Cookie获取成功！\n\n"
                f"已保存到以下文件:\n"
                f"- {os.path.abspath(self.cookie_file)} (origin画质)\n"
                f"- {os.path.abspath('cookie_uhd.txt')} (uhd画质)\n"
                f"- {os.path.abspath('cookie_hd.txt')} (hd画质)\n"
                f"- {os.path.abspath('cookie_ld.txt')} (ld画质)\n"
                f"- {os.path.abspath('cookie_sd.txt')} (sd画质)\n\n"
                f"origin画质Cookie内容已复制到剪贴板。"
            )

            self.root.after(0, lambda: messagebox.showinfo("成功", success_message))

            # 复制origin画质Cookie到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(cookie_with_origin)

            # 重新启用开始按钮
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

        except Exception as e:
            # 确保在异常情况下也关闭浏览器
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None

            self.root.after(0, lambda: self.status_var.set(f"获取Cookie失败: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"获取Cookie失败: {str(e)}"))
            self.root.after(0, lambda: self.start_btn.config(state="normal"))

    def on_closing(self):
        """程序关闭时的清理工作"""
        self.countdown_running = False

        # 确保浏览器关闭（多重保障）
        if self.driver:
            try:
                # 先尝试正常关闭
                self.driver.quit()
            except Exception as e:
                try:
                    # 如果正常关闭失败，尝试强制关闭
                    self.driver.close()
                except:
                    pass
            finally:
                self.driver = None

        self.root.destroy()
        if hasattr(self, 'parent') and self.parent:
            self.parent.focus_set()  # 焦点回到主窗口

#---------------------------------以下为主程序--------------------------------------
# selenium 相关
try:
    from selenium.webdriver import Edge
    from selenium.webdriver.edge.options import Options as EdgeOptions

    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

try:
    import aria2p

    ARIA2_OK = True
except ImportError:
    ARIA2_OK = False
    aria2p = None

# 添加录播任务创建模块
try:
    import CreateALiveRecordTask

    CREATE_TASK_OK = True
except ImportError:
    CREATE_TASK_OK = False
    CreateALiveRecordTask = None

CONFIG_FILE = "streamer_monitor_config.json"
LOG_FILE = "monitor.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# 添加一个调试用的日志方法
def log_debug(message):
    """记录调试日志"""
    if hasattr(logging, 'DEBUG'):
        logging.debug(message)



class LiveMonitorApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("直播间监控录制助手 v1.0.5[抖音和b站]")
        self.root.geometry("1020x720")

        # ===== 先初始化所有变量 =====
        self.monitoring = False
        self.monitor_thread = None
        self.last_status = {}
        self.streamers = []
        self.douyin_cookie = ""
        self.auto_cookie_var = tk.BooleanVar(value=True)
        self.aria2_process = None
        self.automations = []
        self.running_auto_tasks = []
        self.aria2_started = False  # 防止重复启动Aria2
        self.cookie_getting_started = False
        self.auto_lock = threading.Lock()
        self.running_processes = {}
        self.aria2_client = None
        self.aria2_tasks = []
        self.aria2_monitoring = False
        self.aria2_thread = None
        self.auto_start_aria2_var = tk.BooleanVar(value=False)

        # 新增状态标志
        self.cookie_getting_started = False

        # 新增变量
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.edgedriver_path = os.path.join(current_dir, "msedgedriver.exe")
        self.current_edge_version = None
        self.notification_groups = []
        self.default_notification_group = "默认组"
        self.wxpusher_enabled = tk.BooleanVar(value=True)
        self.wecom_enabled = tk.BooleanVar(value=False)
        self.wecom_webhook = tk.StringVar()
        self.download_cancelled = False
        self.progress_window = None
        self.progress_var = None
        self.progress_status = None

        # Aria2连接配置变量
        self.aria2_host = tk.StringVar(value="localhost")
        self.aria2_port = tk.StringVar(value="6800")
        self.aria2_secret = tk.StringVar()

        # ===========================

        # 界面初始化
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        self.streamer_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.streamer_tab, text="主播管理")
        self._setup_streamer_tab()

        self.notify_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.notify_tab, text="通知设置")
        self._setup_notify_tab()

        self.group_tab = ttk.Frame(self.notebook)  # 新增通知组设置标签页
        self.notebook.add(self.group_tab, text="通知组设置")
        self._setup_group_tab()

        # 新增正在录播标签页
        self.record_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.record_tab, text="正在录播")
        self._setup_record_tab()

        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="日志")
        self._setup_log_tab()

        self.auto_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.auto_tab, text="自动化任务")
        self._setup_auto_tab()

        self.status_var = tk.StringVar(value="就绪")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.set_window_icon()

        # 其余初始化
        self.load_config()
        self.root.after(100, self.async_initialization)
        self.progress_window = None
        self.progress_var = None
        self.progress_status = None
        self.download_cancelled = False
        self.start_monitoring()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def set_window_icon(self):
        """设置窗口图标 - 安全版本，不依赖log_message"""
        try:
            # 方法1: 尝试从相对路径加载
            icon_path = self.get_icon_path()

            if icon_path and os.path.exists(icon_path):
                try:
                    self.root.iconbitmap(icon_path)
                    # 使用print而不是log_message，因为log_text可能还未初始化
                    print(f"窗口图标设置成功: {icon_path}")
                    return
                except Exception as e:
                    print(f"设置窗口图标失败: {e}")

            # 方法2: 尝试使用内置图标（如果打包在EXE中）
            self.try_embedded_icon()

        except Exception as e:
            print(f"设置图标失败: {e}")

    def get_icon_path(self):
        """获取图标文件路径（适用于开发和打包环境）"""
        # 如果是打包后的EXE
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        # 尝试不同的图标文件位置
        possible_paths = [
            os.path.join(base_path, "icon.ico"),
            os.path.join(base_path, "resources", "icon.ico"),
            os.path.join(base_path, "images", "icon.ico"),
            os.path.join(base_path, "assets", "icon.ico"),
            os.path.join(base_path, "..", "icon.ico"),  # 上一级目录
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path

        return None

    def try_embedded_icon(self):
        """尝试从资源加载图标"""
        try:
            # 如果使用PyInstaller打包，尝试从临时目录加载
            if hasattr(sys, '_MEIPASS'):
                resource_dir = sys._MEIPASS
                possible_icon_paths = [
                    os.path.join(resource_dir, "icon.ico"),
                    os.path.join(resource_dir, "resources", "icon.ico"),
                    os.path.join(resource_dir, "images", "icon.ico"),
                ]

                for icon_path in possible_icon_paths:
                    if os.path.exists(icon_path):
                        self.root.iconbitmap(icon_path)
                        print(f"从资源加载图标: {icon_path}")
                        return

            print("使用系统默认图标")

        except Exception as e:
            print(f"加载内置图标失败: {e}")

    def load_icon_from_resource(self):
        """从资源加载图标（适用于打包环境）"""
        try:
            # 如果使用PyInstaller打包，可以访问临时解压目录
            if hasattr(sys, '_MEIPASS'):
                resource_dir = sys._MEIPASS
                icon_path = os.path.join(resource_dir, "icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
        except:
            pass

    def create_tray_icon(self):
        """创建系统托盘图标（可选功能）"""
        try:
            # 需要安装pystray库: pip install pystray
            import pystray
            from PIL import Image

            # 创建托盘图标
            image = Image.open(self.get_icon_path())

            def on_quit(icon, item):
                icon.stop()
                self.root.quit()

            menu = pystray.Menu(
                pystray.MenuItem('显示', lambda: self.root.deiconify()),
                pystray.MenuItem('隐藏', lambda: self.root.withdraw()),
                pystray.MenuItem('退出', on_quit)
            )

            icon = pystray.Icon("live_monitor", image, "直播间监控助手", menu)
            return icon
        except ImportError:
            print("未安装pystray库，无法创建托盘图标")
            return None

    def async_initialization(self):
        """异步执行耗时的初始化操作"""
        # 在后台线程中执行初始化
        threading.Thread(target=self._perform_initialization, daemon=True).start()

    def _perform_initialization(self):
        """执行实际的初始化操作"""
        # 加载配置
        self.load_config()

        # 初始化 Edge WebDriver（在后台进行）
        self.init_edgedriver()

        # 延迟启动监控和Aria2
        self.root.after(0, self.delayed_startup)


    def show_download_progress(self, version):
        """显示下载进度窗口"""
        # 创建进度窗口
        self.progress_window = tk.Toplevel(self.root)
        self.progress_window.title("下载 Edge WebDriver")
        self.progress_window.geometry("400x150")
        self.progress_window.transient(self.root)
        self.progress_window.grab_set()

        # 防止用户关闭窗口
        self.progress_window.protocol("WM_DELETE_WINDOW", lambda: None)

        # 添加标签
        ttk.Label(self.progress_window, text=f"正在下载 Edge WebDriver {version}...").pack(pady=10)

        # 添加进度条
        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(self.progress_window, variable=self.progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=5)

        # 添加状态标签
        self.progress_status = tk.StringVar(value="准备下载...")
        ttk.Label(self.progress_window, textvariable=self.progress_status).pack(pady=5)

        # 添加取消按钮
        ttk.Button(self.progress_window, text="取消", command=self.cancel_download).pack(pady=5)

        # 开始下载
        threading.Thread(target=self.download_edgedriver_with_progress, args=(version,), daemon=True).start()

    def download_edgedriver_with_progress(self, version):
        """带进度显示的下载方法（适用于EXE环境）"""
        try:
            # 在主线程中创建进度窗口
            if self.root and self.root.winfo_exists():
                self.root.after(0, self._create_progress_window, version)
            # 构建下载URL
            download_url = f"https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"
            self.log_message(f"下载URL: {download_url}")

            # 更新状态
            self.root.after(0, lambda: self.progress_status.set(f"下载Edge WebDriver {version}"))

            # 下载ZIP文件
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # 获取文件大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            # 创建临时目录保存文件
            temp_dir = tempfile.gettempdir()
            temp_zip = os.path.join(temp_dir, "edgedriver_temp.zip")

            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.download_cancelled:
                        self.root.after(0, lambda: self.progress_status.set("下载已取消"))
                        return False

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # 更新进度
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.root.after(0, lambda: self.progress_var.set(progress))
                            self.root.after(0, lambda: self.progress_status.set(
                                f"已下载: {downloaded / 1024 / 1024:.2f} MB / {total_size / 1024 / 1024:.2f} MB"
                            ))

            # 下载完成，关闭进度窗口
            self.root.after(0, self.progress_window.destroy)

            # 继续执行解压等操作
            self.root.after(0, lambda: self.extract_edgedriver(temp_zip, version))
            return True


        except Exception as e:
            # 安全的异常处理
            error_msg = f"下载失败: {str(e)}"
            print(error_msg)  # 确保有日志输出
            # 安全地更新进度状态
            if (hasattr(self, 'progress_status') and
                    self.progress_status is not None and
                    self.root and self.root.winfo_exists()):
                try:
                    self.root.after(0, lambda: self.progress_status.set(error_msg))
                except Exception:
                    pass  # 忽略更新失败
            # 安全关闭进度窗口
            self._safe_close_progress_window()
            return False

    def _create_progress_window(self, version):
        """创建进度窗口"""
        try:
            # 如果窗口已存在，先关闭
            if self.progress_window is not None:
                self._safe_close_progress_window()

            # 创建新窗口
            self.progress_window = tk.Toplevel(self.root)
            self.progress_window.title("下载 Edge WebDriver")
            self.progress_window.geometry("400x150")
            self.progress_window.transient(self.root)
            self.progress_window.grab_set()

            # 防止用户关闭窗口
            self.progress_window.protocol("WM_DELETE_WINDOW", lambda: None)

            # 添加标签
            ttk.Label(self.progress_window, text=f"正在下载 Edge WebDriver {version}...").pack(pady=10)

            # 添加进度条
            self.progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(self.progress_window, variable=self.progress_var, maximum=100)
            progress_bar.pack(fill=tk.X, padx=20, pady=5)

            # 添加状态标签
            self.progress_status = tk.StringVar(value="准备下载...")
            ttk.Label(self.progress_window, textvariable=self.progress_status).pack(pady=5)

            # 添加取消按钮
            ttk.Button(self.progress_window, text="取消", command=self.cancel_download).pack(pady=5)

        except Exception as e:
            print(f"创建进度窗口失败: {e}")

    def _safe_close_progress_window(self):
        """安全关闭进度窗口"""
        if (hasattr(self, 'progress_window') and
                self.progress_window is not None and
                self.root and self.root.winfo_exists()):
            try:
                self.root.after(0, self.progress_window.destroy)
                self.progress_window = None
                self.progress_var = None
                self.progress_status = None
            except Exception:
                pass  # 忽略关闭失败

    def cancel_download(self):
        """取消下载"""
        self.download_cancelled = True
        self.progress_window.destroy()

    def extract_edgedriver(self, temp_zip, version):
        """解压下载的文件（适用于EXE环境）"""
        try:
            # 获取应用程序目录
            app_dir = get_app_directory()

            # 解压ZIP文件到应用程序目录
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(app_dir)

            # 删除临时文件
            os.remove(temp_zip)

            # 检查Driver_Notes文件夹是否存在，如果存在则删除
            driver_notes_path = os.path.join(app_dir, "Driver_Notes")
            if os.path.exists(driver_notes_path):
                try:
                    shutil.rmtree(driver_notes_path)
                except Exception as e:
                    # 如果删除失败，记录警告但不中断程序
                    self.log_message(f"警告: 无法删除Driver_Notes文件夹: {e}", "warning")

            # 验证下载的文件
            edgedriver_path = os.path.join(app_dir, "msedgedriver.exe")
            if os.path.exists(edgedriver_path):
                driver_version = self.get_edgedriver_version()
                if driver_version and driver_version.split('.')[0] == version.split('.')[0]:
                    self.log_message(f"Edge WebDriver {version} 下载并解压成功")
                    return True
                else:
                    try:
                        os.remove(edgedriver_path)
                    except:
                        pass
                    self.log_message(f"版本：{version}", "error")
                    return False
            else:
                self.log_message("下载的文件中未找到msedgedriver.exe", "error")
                return False

        except Exception as e:
            self.log_message(f"解压文件失败: {e}", "error")
            return False

    # 修改 init_edgedriver 方法
    # 在LiveMonitorApp类中修改init_edgedriver方法
    def init_edgedriver(self):
        app_dir = get_app_directory()
        self.edgedriver_path = os.path.join(app_dir, "msedgedriver.exe")

        try:
            self.current_edge_version = self.get_edge_version()
            if not self.current_edge_version:
                raise Exception("无法检测Edge浏览器版本")

            # 检查EdgeDriver是否存在
            if os.path.exists(self.edgedriver_path):
                actual_version = self.get_edgedriver_version()

                if actual_version is None:
                    # 如果无法获取版本，但文件存在，可能是版本检测问题
                    self.log_message("警告：无法检测现有EdgeDriver版本，但文件存在，尝试使用现有文件", "warning")

                    # 创建备份并尝试使用现有文件
                    backup_path = self.edgedriver_path + ".bak"
                    try:
                        shutil.copy2(self.edgedriver_path, backup_path)
                        self.log_message("已创建EdgeDriver备份")
                    except:
                        pass

                    # 直接返回，使用现有文件
                    self.log_message("使用现有EdgeDriver文件（版本检测失败）")
                    return

                if actual_version == self.current_edge_version:
                    self.log_message("已存在匹配的EdgeDriver")
                    return
            else:
                actual_version = None

            # 如果版本不匹配或文件不存在，继续下载流程
            if actual_version != self.current_edge_version:
                if os.path.exists(self.edgedriver_path):
                    # 创建备份
                    backup_path = self.edgedriver_path + ".bak"
                    try:
                        shutil.copy2(self.edgedriver_path, backup_path)
                        self.log_message("已备份旧版本EdgeDriver")
                    except:
                        pass

                    # 删除旧版本
                    os.remove(self.edgedriver_path)

                # 下载新版本
                if not self.download_edgedriver_with_progress(self.current_edge_version):
                    raise Exception("下载失败")

                # 验证新版本
                new_version = self.get_edgedriver_version()
                if new_version != self.current_edge_version:
                    # 如果版本检测仍然失败，但文件存在，继续使用
                    if os.path.exists(self.edgedriver_path) and new_version is None:
                        self.log_message("警告：新下载的EdgeDriver版本检测失败，但文件存在，继续使用", "warning")
                    else:
                        raise Exception(f"版本：{self.current_edge_version}")

        except Exception as e:
            self.log_message(f"初始化EdgeDriver失败: {e}", "error")

            # 尝试恢复备份
            backup_path = self.edgedriver_path + ".bak"
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, self.edgedriver_path)
                    self.log_message("已从备份恢复EdgeDriver")
                except Exception as backup_error:
                    self.log_message(f"恢复备份失败: {backup_error}", "error")

    def delayed_startup(self):
        """延迟启动各项服务 - 修复重复启动问题"""
        # 添加启动标志，防止重复执行
        if hasattr(self, '_startup_executed') and self._startup_executed:
            return
        self._startup_executed = True

        # 启动监控
        self.start_monitoring()

        # 检查是否需要自动启动Aria2 - 只在这里启动一次
        if self.auto_start_aria2_var.get() and not self.aria2_started:
            self.log_message("检测到启用Aria2自动启动，开始启动服务...")
            self.aria2_started = True  # 添加标志防止重复启动
            # Aria2 启动放在后台线程
            threading.Thread(target=self.auto_start_aria2, daemon=True).start()
        else:
            self.log_message("Aria2自动启动未启用或已启动")

        # 其他延迟启动的任务
        self.root.after(1000, self.maybe_auto_get_douyin_cookie)

    def get_edge_version(self):
        """获取本地Edge浏览器完整版本"""
        try:
            # 方法1: 通过注册表获取完整版本
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                     r"Software\Microsoft\Edge\BLBeacon")
                version_value, _ = winreg.QueryValueEx(key, "version")
                winreg.CloseKey(key)
                if version_value:
                    return version_value
            except:
                pass

            # 方法2: 通过程序文件路径获取版本
            try:
                import win32com.client
                shell = win32com.client.Dispatch("WScript.Shell")
                edge_path = shell.RegRead(
                    r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
                return self.get_file_version(edge_path)
            except:
                pass

            # 方法3: 尝试通过命令行获取完整版本
            try:
                result = subprocess.run(["msedge", "--version"], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)", result.stdout)
                    if match:
                        return match.group(1)
            except:
                pass

            # 方法4: 检查Edge安装目录
            try:
                edge_paths = [
                    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
                    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
                ]

                for edge_path in edge_paths:
                    if os.path.exists(edge_path):
                        version = self.get_file_version(edge_path)
                        if version:
                            return version
            except:
                pass

        except Exception as e:
            self.log_message(f"获取Edge版本失败: {e}", "warning")

        return None

    def get_file_version(self, file_path):
        """获取文件的完整版本信息"""
        try:
            import win32api
            info = win32api.GetFileVersionInfo(file_path, '\\')
            ms = info['FileVersionMS']
            ls = info['FileVersionLS']
            version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
            return version
        except:
            try:
                # 备用方法：使用wmic
                info = subprocess.run(['wmic', 'datafile', 'where', f'name="{file_path}"', 'get', 'Version'],
                                      capture_output=True, text=True, timeout=10)
                lines = info.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
            except:
                pass
        return None

    def get_edgedriver_version(self):
        """获取EdgeDriver版本 - 修复EXE环境版本检测问题"""
        if not os.path.exists(self.edgedriver_path):
            return None

        try:
            # 在EXE环境中，使用更可靠的方法获取版本
            if getattr(sys, 'frozen', False):
                # EXE环境：直接读取文件版本信息
                try:
                    import win32api
                    info = win32api.GetFileVersionInfo(self.edgedriver_path, '\\')
                    ms = info['FileVersionMS']
                    ls = info['FileVersionLS']
                    version = f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
                    return version
                except ImportError:
                    # 如果没有win32api，使用备用方法
                    pass

            # 原始的命令行方法（作为备用）
            result = subprocess.run(
                [self.edgedriver_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # 多种正则表达式匹配版本
            patterns = [
                r"EdgeDriver\s+(\d+\.\d+\.\d+\.\d+)",
                r"Microsoft Edge WebDriver\s+(\d+\.\d+\.\d+\.\d+)",
                r"版本\s+(\d+\.\d+\.\d+\.\d+)",  # 中文版本
                r"(\d+\.\d+\.\d+\.\d+)\s+\(官方构建\)",
            ]

            for pattern in patterns:
                match = re.search(pattern, result.stdout)
                if match:
                    return match.group(1)

            # 如果正则匹配失败，尝试从错误输出中查找
            for pattern in patterns:
                match = re.search(pattern, result.stderr)
                if match:
                    return match.group(1)

            return None

        except Exception as e:
            self.log_message(f"获取EdgeDriver版本失败: {e}", "error")
            return None

    def download_edgedriver(self, version):
        """下载指定版本的edgedriver到本地文件夹（使用完整版本号）"""
        try:
            # 修正下载URL：添加/download/路径
            download_url = f"https://msedgedriver.microsoft.com/{version}/edgedriver_win64.zip"

            self.log_message(f"开始下载Edge WebDriver {version}到本地文件夹...")
            self.log_message(f"下载URL: {download_url}")

            # 下载ZIP文件，设置超时为30秒
            response = requests.get(download_url, timeout=30)
            response.raise_for_status()  # 如果HTTP请求返回不成功状态码，则抛出异常

            # 保存临时文件到当前目录
            temp_zip = os.path.join(os.path.dirname(self.edgedriver_path), "edgedriver_temp.zip")
            with open(temp_zip, 'wb') as f:
                f.write(response.content)

            # 解压ZIP文件到当前目录
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(os.path.dirname(self.edgedriver_path))

            # 删除临时文件
            os.remove(temp_zip)

            # 删除Driver_Notes文件夹（如果存在）
            driver_notes_path = os.path.join(os.path.dirname(self.edgedriver_path), "Driver_Notes")
            if os.path.exists(driver_notes_path):
                try:
                    shutil.rmtree(driver_notes_path)
                except Exception as e:
                    self.log_message(f"删除Driver_Notes文件夹失败: {e}", "warning")

            # 验证下载的文件
            if os.path.exists(self.edgedriver_path):
                driver_version = self.get_edgedriver_version()
                if driver_version and driver_version == version:
                    self.log_message(f"Edge WebDriver {version} 下载并解压成功到本地文件夹")
                    return True
                else:
                    # 版本不匹配，删除下载的文件
                    if os.path.exists(self.edgedriver_path):
                        os.remove(self.edgedriver_path)
                    self.log_message(f"版本不匹配: 期望{version}, 实际{driver_version}", "error")
                    return False
            else:
                self.log_message("下载的文件中未找到msedgedriver.exe", "error")
                return False

        except requests.exceptions.Timeout:
            self.log_message("下载Edge WebDriver超时，请检查网络连接", "error")
            return False
        except requests.exceptions.HTTPError as e:
            self.log_message(f"下载Edge WebDriver HTTP错误: {e}", "error")
            # 检查是否为404错误，可能是版本号不正确
            if e.response.status_code == 404:
                self.log_message(f"版本号 {version} 可能不存在，请检查Edge浏览器版本", "error")
            return False
        except requests.exceptions.RequestException as e:
            self.log_message(f"下载Edge WebDriver网络错误: {e}", "error")
            return False
        except zipfile.BadZipFile:
            self.log_message("下载的文件不是有效的ZIP文件", "error")
            return False
        except Exception as e:
            self.log_message(f"下载过程中发生错误: {e}", "error")
            return False

    def manage_config(self):
        """管理配置 - 启动内置的配置管理器"""
        try:
            # 保存当前配置
            self.save_config()

            # 创建配置管理器窗口
            config_window = tk.Toplevel(self.root)
            config_window.title("配置管理器")
            config_window.geometry("1000x700")
            config_window.transient(self.root)
            config_window.grab_set()

            # 启动配置管理器应用
            config_app = StreamerManagerApp(config_window)

            # 监听配置管理器窗口关闭事件
            def on_config_close():
                # 配置管理器关闭后刷新主程序配置
                self.log_message("配置管理器已关闭，正在刷新配置...")
                self.load_config()
                config_window.destroy()

            config_window.protocol("WM_DELETE_WINDOW", on_config_close)

            self.log_message("已启动配置管理器")

        except Exception as e:
            self.log_message(f"启动配置管理器失败: {e}", "error")
            messagebox.showerror("错误", f"启动配置管理器失败: {e}")

    def _monitor_config_manager(self, process):
        """监控配置管理工具进程"""
        try:
            # 等待配置管理工具关闭
            process.wait()

            # 配置管理工具关闭后，在主线程中刷新配置
            self.root.after(0, self._refresh_config_after_manager)
        except Exception as e:
            self.log_message(f"监控配置管理工具失败: {e}", "error")

    def _refresh_config_after_manager(self):
        """配置管理工具关闭后的配置刷新"""
        self.log_message("检测到配置管理工具已关闭，正在刷新配置...")

        # 记录当前选中的主播和自动化任务（用于恢复选中状态）
        selected_streamers = []
        selected_automations = []

        # 保存当前选中状态
        for item in self.streamer_tree.selection():
            values = self.streamer_tree.item(item, "values")
            if values:
                selected_streamers.append(values[0])  # 主播名称

        for item in self.auto_tree.selection():
            values = self.auto_tree.item(item, "values")
            if values:
                selected_automations.append(values[0])  # 任务ID

        # 重新加载配置
        self.load_config()

        # 恢复选中状态
        self._restore_selections(selected_streamers, selected_automations)

        self.log_message("配置刷新完成")

    def _restore_selections(self, streamer_names, automation_ids):
        """恢复选中状态"""
        # 恢复主播选中状态
        for item in self.streamer_tree.get_children():
            values = self.streamer_tree.item(item, "values")
            if values and values[0] in streamer_names:  # 主播名称
                self.streamer_tree.selection_add(item)

        # 恢复自动化任务选中状态
        for item in self.auto_tree.get_children():
            values = self.auto_tree.item(item, "values")
            if values and values[0] in automation_ids:  # 任务ID
                self.auto_tree.selection_add(item)

    # ------------------ 主播管理 ------------------
    def _setup_streamer_tab(self):
        add_frame = ttk.LabelFrame(self.streamer_tab, text="添加主播")
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(add_frame, text="主播名称:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.streamer_name = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.streamer_name, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="平台:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.platform = tk.StringVar()
        platform_combo = ttk.Combobox(add_frame, textvariable=self.platform, width=10, state="readonly")
        platform_combo['values'] = ('哔哩哔哩', '抖音')
        platform_combo.current(0)
        platform_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(add_frame, text="ID/URL:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.streamer_id = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.streamer_id, width=30).grid(row=0, column=5, padx=5, pady=5)

        ttk.Label(add_frame, text="通知组:").grid(row=0, column=6, padx=5, pady=5, sticky=tk.W)
        self.streamer_group = tk.StringVar(value=self.default_notification_group)
        self.group_combo = ttk.Combobox(add_frame, textvariable=self.streamer_group, width=10, state="readonly")
        self.group_combo.grid(row=0, column=7, padx=5, pady=5)

        ttk.Button(add_frame, text="添加主播", command=self.add_streamer).grid(row=0, column=8, padx=5, pady=5)
        # 第一行说明
        help_text1 = "使用说明：哔哩哔哩：需要提供主播房间ID（可在直播间URL中找到）；抖音：需要提供主播主页URL（完整URL）"
        help_label1 = ttk.Label(add_frame, text=help_text1)
        help_label1.grid(row=1, column=0, columnspan=9, padx=5, pady=2, sticky=tk.W)

        # 第二行说明
        help_text2 = "如果要正常录播，还需要自行安装Python环境（分享链接里有），将其加入到系统环境变量，并补全必要的模块"
        help_label2 = ttk.Label(add_frame, text=help_text2)
        help_label2.grid(row=2, column=0, columnspan=9, padx=5, pady=2, sticky=tk.W)

        list_frame = ttk.LabelFrame(self.streamer_tab, text="主播列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "platform", "id", "group", "status", "last_check_time")
        self.streamer_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        for col, text, width in zip(columns, ["主播名称", "平台", "ID/URL", "通知组", "状态", "上次监控时间"],
                                    [150, 80, 250, 100, 100, 120]):
            self.streamer_tree.heading(col, text=text)
            self.streamer_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.streamer_tree.yview)
        self.streamer_tree.configure(yscrollcommand=scrollbar.set)
        self.streamer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self.streamer_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_streamer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="开始监控", command=self.start_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="停止监控", command=self.stop_monitoring).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="管理配置", command=self.manage_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=5)

    def refresh_record_cookie(self):
        """启动Cookie刷新器"""
        try:
            # 检查selenium依赖
            try:
                from selenium import webdriver
            except ImportError:
                messagebox.showerror("错误",
                                     "未安装selenium库！\n\n"
                                     "请先安装: pip install selenium")
                return

            # 创建Cookie刷新器实例
            cookie_refresher = DouyinCookieRefresher(self.root)

            # 设置为主窗口的子窗口
            cookie_refresher.root.transient(self.root)  # 设置为子窗口
            cookie_refresher.root.grab_set()  # 模态窗口

            # 修改on_closing方法
            def custom_on_closing():
                cookie_refresher.on_closing()
                # 释放窗口焦点
                self.root.focus_set()

            cookie_refresher.root.protocol("WM_DELETE_WINDOW", custom_on_closing)

            self.log_message("Cookie刷新器已启动")

        except Exception as e:
            self.log_message(f"启动Cookie刷新器失败: {e}", "error")
            messagebox.showerror("错误", f"启动Cookie刷新器失败: {e}")

    # ------------------ 通知设置 ------------------
    def _setup_notify_tab(self):
        # WxPusher配置
        wx_frame = ttk.LabelFrame(self.notify_tab, text="WxPusher配置")
        wx_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(wx_frame, text="启用WxPusher通知",
                        variable=self.wxpusher_enabled).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Label(wx_frame, text="AppToken:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.app_token = tk.StringVar()
        ttk.Entry(wx_frame, textvariable=self.app_token, width=40).grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(wx_frame, text="用户UID:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.user_id = tk.StringVar()
        ttk.Entry(wx_frame, textvariable=self.user_id, width=40).grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(wx_frame, text="测试通知", command=self.test_wxpusher_notification).grid(row=2, column=2, padx=5,
                                                                                            pady=5)

        # 企业微信机器人配置
        wecom_frame = ttk.LabelFrame(self.notify_tab, text="企业微信机器人配置")
        wecom_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Checkbutton(wecom_frame, text="启用企业微信机器人通知",
                        variable=self.wecom_enabled).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Label(wecom_frame, text="Webhook URL:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        ttk.Entry(wecom_frame, textvariable=self.wecom_webhook, width=50).grid(row=1, column=1, padx=5, pady=5)

        ttk.Button(wecom_frame, text="测试通知", command=self.test_wecom_notification).grid(row=1, column=2, padx=5,
                                                                                            pady=5)

        # 其他设置
        link_frame = ttk.Frame(self.notify_tab)
        link_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(link_frame, text="还没有WxPusher账号? ").pack(side=tk.LEFT)
        link_label = ttk.Label(link_frame, text="点击这里注册", foreground="blue", cursor="hand2")
        link_label.pack(side=tk.LEFT)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://wxpusher.zjiecode.com/"))

        cookie_frame = ttk.LabelFrame(self.notify_tab, text="抖音 Cookie 设置")
        cookie_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Checkbutton(cookie_frame, text="启动时自动获取抖音 Cookie（需要 Edge 浏览器驱动）",
                        variable=self.auto_cookie_var).pack(anchor=tk.W, padx=5, pady=3)
        ttk.Label(cookie_frame, text="当前 Cookie:").pack(anchor=tk.W, padx=5, pady=3)
        self.cookie_display = tk.Text(cookie_frame, height=3, wrap=tk.WORD)
        self.cookie_display.pack(fill=tk.X, padx=5, pady=3)
        cookie_btn_frame = ttk.Frame(cookie_frame)
        cookie_btn_frame.pack(anchor=tk.W, padx=5, pady=3)
        ttk.Button(cookie_frame, text="手动填写监控Cookie", command=self.manual_input_cookie).pack(side=tk.LEFT, padx=5)
        ttk.Button(cookie_frame, text="刷新录播Cookie", command=self.refresh_record_cookie).pack(side=tk.LEFT, padx=5)
        help_frame = ttk.Frame(self.notify_tab)
        help_frame.pack(fill=tk.X, padx=10, pady=10)
        help_text = (
            "使用说明：\n"
            "1. 访问 wxpusher.zjiecode.com 注册获取AppToken\n"
            "2. 在WxPusher中绑定微信获取用户UID\n"
            "3. 添加要监控的主播\n"
            "4. 点击'开始监控'启动服务\n"
            "哔哩哔哩：需要提供主播房间ID（可在直播间URL中找到）\n"
            "抖音：需要提供主播主页URL（完整URL）\n\n"

        )
        ttk.Label(help_frame, text=help_text, justify=tk.LEFT).pack(anchor=tk.W)

    # ------------------ 通知组设置 ------------------
    def _setup_group_tab(self):
        # 在现有代码基础上添加通知方式设置
        add_frame = ttk.LabelFrame(self.group_tab, text="添加/编辑通知组")
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(add_frame, text="组名:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.group_name = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.group_name, width=20).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="默认组:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.default_group_combo = ttk.Combobox(add_frame, width=15, state="readonly")
        self.default_group_combo.grid(row=0, column=3, padx=5, pady=5)
        self.default_group_combo.set(self.default_notification_group)

        ttk.Button(add_frame, text="添加组", command=self.add_notification_group).grid(row=0, column=4, padx=5, pady=5)
        ttk.Button(add_frame, text="设为默认", command=self.set_default_group).grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(add_frame, text="管理主播", command=self.manage_group_streamers).grid(row=0, column=6, padx=5,
                                                                                         pady=5)
        ttk.Button(add_frame, text="设置通知方式", command=self.set_group_notify_methods).grid(row=0, column=7, padx=5,
                                                                                               pady=5)  # 新增按钮

        # 通知组列表（增加通知方式列）
        list_frame = ttk.LabelFrame(self.group_tab, text="通知组列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("name", "default", "streamers", "wxpusher", "wecom")
        self.group_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        for col, text, width in zip(columns, ["组名", "默认组", "包含主播数", "WxPusher", "企业微信"],
                                    [150, 80, 100, 80, 80]):
            self.group_tree.heading(col, text=text)
            self.group_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.group_tree.yview)
        self.group_tree.configure(yscrollcommand=scrollbar.set)
        self.group_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 按钮区域
        btn_frame = ttk.Frame(self.group_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="删除选中组", command=self.delete_notification_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="刷新列表", command=self.refresh_group_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="管理配置", command=self.manage_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=5)

        # 初始化组列表
        self.refresh_group_list()

    def set_group_notify_methods(self):
        """设置通知组的通知方式"""
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要设置通知方式的组")
            return

        group_name = self.group_tree.item(selected[0], "values")[0]
        group = next((g for g in self.notification_groups if g["name"] == group_name), None)

        if not group:
            messagebox.showerror("错误", "找不到选中的组")
            return

        # 创建设置窗口
        setting_window = tk.Toplevel(self.root)
        setting_window.title(f"设置组 '{group_name}' 的通知方式")
        setting_window.geometry("280x180")
        setting_window.transient(self.root)
        setting_window.grab_set()

        # 通知方式设置
        notify_frame = ttk.LabelFrame(setting_window, text="通知方式设置")
        notify_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 初始化组通知方式设置（如果不存在）
        if "notify_methods" not in group:
            group["notify_methods"] = {
                "wxpusher": True,
                "wecom": False
            }

        # WxPusher设置
        wx_var = tk.BooleanVar(value=group["notify_methods"].get("wxpusher", True))
        wx_check = ttk.Checkbutton(notify_frame, text="启用WxPusher通知", variable=wx_var)
        wx_check.pack(anchor=tk.W, padx=10, pady=10)

        # 企业微信设置
        wecom_var = tk.BooleanVar(value=group["notify_methods"].get("wecom", False))
        wecom_check = ttk.Checkbutton(notify_frame, text="启用企业微信通知", variable=wecom_var)
        wecom_check.pack(anchor=tk.W, padx=10, pady=10)

        # 按钮区域
        btn_frame = ttk.Frame(setting_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def apply_settings():
            group["notify_methods"] = {
                "wxpusher": wx_var.get(),
                "wecom": wecom_var.get()
            }
            self.log_message(f"已更新组 '{group_name}' 的通知方式设置")
            self.refresh_group_list()
            self.save_config()
            setting_window.destroy()

        ttk.Button(btn_frame, text="应用", command=apply_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=setting_window.destroy).pack(side=tk.RIGHT, padx=5)

    def add_notification_group(self):
        """添加通知组（初始化通知方式设置）"""
        group_name = self.group_name.get().strip()
        if not group_name:
            messagebox.showerror("错误", "请输入组名")
            return

        # 检查是否已存在
        if any(group["name"] == group_name for group in self.notification_groups):
            messagebox.showerror("错误", "该组名已存在")
            return

        # 添加新组，包含默认通知方式设置
        self.notification_groups.append({
            "name": group_name,
            "streamers": [],
            "notify_methods": {
                "wxpusher": True,  # 默认启用WxPusher
                "wecom": False  # 默认禁用企业微信
            }
        })
        self.log_message(f"已添加通知组: {group_name}")
        self.refresh_group_list()
        self.group_name.set("")
        self.save_config()

    def delete_notification_group(self):
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的组")
            return

        for item in selected:
            group_name = self.group_tree.item(item, "values")[0]

            # 将属于该组的主播移动到默认组
            for streamer in self.streamers:
                if streamer.get("group") == group_name:
                    streamer["group"] = self.default_notification_group

            self.notification_groups = [g for g in self.notification_groups if g["name"] != group_name]
            self.group_tree.delete(item)
            self.log_message(f"已删除通知组: {group_name}")

        # 如果删除的是默认组，则重新设置默认组
        if self.default_notification_group not in [g["name"] for g in self.notification_groups]:
            if self.notification_groups:
                self.default_notification_group = self.notification_groups[0]["name"]
            else:
                self.default_notification_group = "默认组"
                self.notification_groups.append({
                    "name": "默认组",
                    "streamers": [],
                    "notify_methods": {
                        "wxpusher": True,
                        "wecom": False
                    }
                })

        self.refresh_group_list()
        self.save_config()

    def set_default_group(self):
        group_name = self.default_group_combo.get()
        if group_name and group_name in [g["name"] for g in self.notification_groups]:
            self.default_notification_group = group_name
            self.log_message(f"已设置默认通知组: {group_name}")
            self.save_config()
        else:
            messagebox.showerror("错误", "请选择有效的通知组")

    def manage_group_streamers(self):
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要管理的组")
            return

        group_name = self.group_tree.item(selected[0], "values")[0]
        group = next((g for g in self.notification_groups if g["name"] == group_name), None)

        if not group:
            messagebox.showerror("错误", "找不到选中的组")
            return

        # 创建管理窗口
        manage_window = tk.Toplevel(self.root)
        manage_window.title(f"管理组 '{group_name}' 的主播")
        manage_window.geometry("450x400")
        manage_window.transient(self.root)
        manage_window.grab_set()

        # 主播列表
        list_frame = ttk.LabelFrame(manage_window, text="选择主播")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建滚动框架
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 主播选择变量
        streamer_vars = {}

        # 添加主播复选框
        for i, streamer in enumerate(self.streamers):
            var = tk.BooleanVar(value=streamer.get("group") == group_name)
            streamer_vars[streamer["name"]] = var

            cb = ttk.Checkbutton(
                scrollable_frame,
                text=f"{streamer['name']} ({streamer['platform']})",
                variable=var
            )
            cb.pack(anchor=tk.W, padx=5, pady=2)

        # 按钮区域
        btn_frame = ttk.Frame(manage_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        def apply_changes():
            # 更新主播所属组
            for streamer_name, var in streamer_vars.items():
                streamer = next((s for s in self.streamers if s["name"] == streamer_name), None)
                if streamer:
                    if var.get():
                        streamer["group"] = group_name
                    elif streamer.get("group") == group_name:
                        streamer["group"] = self.default_notification_group

            # 更新组的主播列表
            group["streamers"] = [s["name"] for s in self.streamers if s.get("group") == group_name]

            self.log_message(f"已更新组 '{group_name}' 的主播配置")
            self.refresh_group_list()
            self.save_config()
            manage_window.destroy()

        ttk.Button(btn_frame, text="应用更改", command=apply_changes).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="取消", command=manage_window.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_group_list(self):
        """刷新组列表显示（增加通知方式信息）"""
        self.group_tree.delete(*self.group_tree.get_children())

        for group in self.notification_groups:
            # 计算组内主播数量
            streamer_count = len([s for s in self.streamers if s.get("group") == group["name"]])
            is_default = "是" if group["name"] == self.default_notification_group else "否"

            # 获取通知方式设置
            notify_methods = group.get("notify_methods", {"wxpusher": True, "wecom": False})
            wx_status = "启用" if notify_methods.get("wxpusher", True) else "禁用"
            wecom_status = "启用" if notify_methods.get("wecom", False) else "禁用"

            self.group_tree.insert("", "end", values=(
                group["name"], is_default, streamer_count, wx_status, wecom_status
            ))

        # 更新组选择下拉框
        group_names = [g["name"] for g in self.notification_groups]
        self.group_combo['values'] = group_names
        self.default_group_combo['values'] = group_names
        self.default_group_combo.set(self.default_notification_group)

    # -----录播管理区域---------
    def start_record_guide(self):
        """开始录播引导"""
        messagebox.showinfo(
            "开始录播指引：",
            "请前往\"自动化任务\"一栏，选中要开始录制的主播，点击\"测试选中\"即可立即开始录播。\n\n"
            "提示：您需要先在自动化任务中设置好录播脚本路径。"
        )

    def _setup_record_tab(self):
        """设置录播任务管理界面"""
        # 连接设置区域
        conn_frame = ttk.LabelFrame(self.record_tab, text="Aria2连接设置")
        conn_frame.pack(fill=tk.X, padx=10, pady=5)

        # 新增：自动启动复选框
        ttk.Checkbutton(conn_frame, text="启用aria2自动启动和连接",
                        variable=self.auto_start_aria2_var).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        ttk.Label(conn_frame, text="主机:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.aria2_host = tk.StringVar(value="localhost")
        ttk.Entry(conn_frame, textvariable=self.aria2_host, width=15).grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(conn_frame, text="端口:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.aria2_port = tk.StringVar(value="6800")
        ttk.Entry(conn_frame, textvariable=self.aria2_port, width=10).grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        ttk.Label(conn_frame, text="密钥:").grid(row=1, column=4, padx=5, pady=5, sticky=tk.W)
        self.aria2_secret = tk.StringVar()
        ttk.Entry(conn_frame, textvariable=self.aria2_secret, width=20, show="*").grid(row=1, column=5, padx=5, pady=5,
                                                                                       sticky=tk.W)

        ttk.Button(conn_frame, text="启动Aria2", command=self._auto_start_aria2_thread).grid(row=1, column=6, padx=5, pady=5)
        self.aria2_connect_btn = ttk.Button(conn_frame, text="连接Aria2", command=self.connect_aria2)
        self.aria2_connect_btn.grid(row=1, column=7, padx=5, pady=5)
        ttk.Button(conn_frame, text="断开连接", command=self.disconnect_aria2).grid(row=1, column=8, padx=5, pady=5)

        # 状态显示
        self.aria2_status = tk.StringVar(value="未连接")
        status_label = ttk.Label(conn_frame, textvariable=self.aria2_status)
        status_label.grid(row=1, column=9, padx=10, pady=5, sticky=tk.W)

        # 任务操作区域
        task_frame = ttk.LabelFrame(self.record_tab, text="任务列表操作")
        task_frame.pack(fill=tk.X, padx=10, pady=5)

        # 保存按钮引用
        self.aria2_add_task_btn = ttk.Button(task_frame, text="添加录播任务", command=self.add_record_task)
        self.aria2_add_task_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.aria2_refresh_btn = ttk.Button(task_frame, text="刷新任务列表", command=self.refresh_aria2_tasks)
        self.aria2_refresh_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.aria2_auto_start_btn = ttk.Button(task_frame, text="开始自动刷新", command=self.start_aria2_monitoring)
        self.aria2_auto_start_btn.pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Button(task_frame, text="停止自动刷新", command=self.stop_aria2_monitoring).pack(side=tk.LEFT, padx=5,
                                                                                             pady=5)
        log_frame = ttk.LabelFrame(self.record_tab, text="录播日志设置")
        log_frame.pack(fill=tk.X, padx=10, pady=5)

        # 初始状态下禁用相关按钮
        self.aria2_refresh_btn.config(state=tk.DISABLED)
        self.aria2_auto_start_btn.config(state=tk.DISABLED)

        # 任务列表区域
        list_frame = ttk.LabelFrame(self.record_tab, text="Aria2任务列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = ("gid", "name", "status", "speed", "downs")
        self.aria2_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=15)

        # 设置列宽和标题
        column_config = [
            ("gid", "任务ID", 120),
            ("name", "任务名称", 250),
            ("status", "状态", 100),
            ("speed", "速度", 100),
            ("downs", "大小", 100)
        ]

        for col, text, width in column_config:
            self.aria2_tree.heading(col, text=text)
            self.aria2_tree.column(col, width=width)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.aria2_tree.yview)
        self.aria2_tree.configure(yscrollcommand=scrollbar.set)
        self.aria2_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 操作按钮区域
        op_frame = ttk.Frame(self.record_tab)
        op_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(op_frame, text="开始录播", command=self.start_record_guide).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="暂停选中", command=self.pause_selected_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="继续选中", command=self.resume_selected_tasks).pack(side=tk.LEFT, padx=5)
        ttk.Button(op_frame, text="停止并删除选中任务(保留原文件)", command=self.remove_selected_tasks).pack(
            side=tk.LEFT, padx=5)

        # 检查aria2p库是否安装
        if not ARIA2_OK:
            warning_label = ttk.Label(
                self.record_tab,
                text="警告: 未安装aria2p库，请使用 'pip install aria2p' 安装",
                foreground="red"
            )
            warning_label.pack(padx=10, pady=5)

    def auto_start_aria2(self):
        """改进的自动启动Aria2方法"""
        self.log_message("开始执行Aria2自动启动流程...")

        # 先检查是否已连接
        if self.aria2_client:
            self.log_message("Aria2已连接，跳过自动启动")
            return

        # 在后台线程中执行启动
        threading.Thread(target=self._auto_start_aria2_thread, daemon=True).start()

    def _is_aria2c_running(self):
        """检查aria2c进程是否正在运行"""
        try:
            if sys.platform == "win32":
                # Windows系统
                result = subprocess.run(['tasklist', '/fi', 'imagename eq aria2c.exe'],
                                        capture_output=True, text=True, timeout=10)
                return 'aria2c.exe' in result.stdout
            else:
                # Linux/Mac系统
                result = subprocess.run(['pgrep', '-f', 'aria2c'],
                                        capture_output=True, timeout=10)
                return result.returncode == 0
        except Exception as e:
            self.log_message(f"检查aria2c进程时出错: {e}", "debug")
            return False

    def has_active_aria2_tasks(self):
        """检查是否有活跃的aria2下载任务"""
        if not self.aria2_client:
            return False

        try:
            downloads = self.aria2_client.get_downloads()
            for task in downloads:
                status = getattr(task, 'status', '')
                # 活跃状态包括：active（下载中）、paused（暂停）、waiting（等待）
                if status in ['active', 'paused', 'waiting']:
                    return True
            return False
        except Exception as e:
            self.log_message(f"检查活跃任务时出错: {e}", "warning")
            return False

    def check_aria2_running(self):
        try:
            # 检查进程
            import psutil
            for proc in psutil.process_iter(['name']):
                if 'aria2c' in proc.info['name'].lower():
                    return True
            return False
        except:
            # 简单的端口检查
            import socket
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(('localhost', 6800))
                sock.close()
                return result == 0
            except:
                return False

    def _test_port_connection(self):
        """通过端口检测aria2服务是否在运行"""
        import socket
        try:
            host = self.aria2_host.get().strip()
            port = int(self.aria2_port.get().strip())

            # 移除协议前缀
            if host.startswith(('http://', 'https://')):
                host = host.split('://', 1)[1]

            # 测试端口连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()

            return result == 0
        except Exception as e:
            self.log_message(f"端口检测失败: {e}", "debug")
            return False

    def _test_aria2_connection(self):
        """测试aria2连接是否可用"""
        if not ARIA2_OK:
            return False

        try:
            host = self.aria2_host.get().strip()
            port = self.aria2_port.get().strip()
            secret = self.aria2_secret.get().strip()

            if not host.startswith(('http://', 'https://')):
                host = f"http://{host}"

            # 创建临时客户端测试连接
            client = aria2p.Client(
                host=host,
                port=int(port),
                secret=secret if secret else None
            )

            # 尝试获取版本信息来测试连接 - 正确处理字典返回值
            version_info = client.get_version()
            # get_version()返回的是字典，不是对象
            if isinstance(version_info, dict) and 'version' in version_info:
                self.log_message(f"检测到aria2服务已运行，版本: {version_info['version']}")
                return True
            else:
                # 如果返回的不是字典，可能是新版本的aria2p
                self.log_message(f"aria2服务检测: 响应格式异常 {type(version_info)}")
                return False

        except Exception as e:
            self.log_message(f"aria2服务检测: 未运行 ({str(e)})", "debug")
            return False

    def connect_aria2(self):
        """连接Aria2服务 - 异步版本"""
        if not ARIA2_OK:
            messagebox.showerror("错误", "未安装aria2p库，请先安装: pip install aria2p")
            return

        # 禁用连接按钮，防止重复点击
        self.aria2_connect_btn.config(state=tk.DISABLED)
        self.aria2_status.set("连接中...")

        # 在后台线程中执行连接操作
        threading.Thread(target=self._connect_aria2_thread, daemon=True).start()

    def disconnect_aria2(self):
        try:
            # 先停止监控
            self.stop_aria2_monitoring()

            # 重置客户端
            self.aria2_client = None

            # 重置UI状态
            self.aria2_status.set("未连接")
            self.aria2_tree.delete(*self.aria2_tree.get_children())

            # 关键修复：重置连接按钮状态
            self.aria2_connect_btn.config(state=tk.NORMAL)

            # 禁用相关按钮
            self.aria2_refresh_btn.config(state=tk.DISABLED)
            self.aria2_auto_start_btn.config(state=tk.DISABLED)
            self.aria2_add_task_btn.config(state=tk.DISABLED)

            self.log_message("Aria2连接已断开")

            # 注意：这里不停止aria2_process，因为用户可能只是断开连接而不是关闭程序
        except Exception as e:
            self.log_message(f"断开连接时出错: {e}", "error")

    def _connect_aria2_thread(self):
        """在后台线程中执行Aria2连接"""
        try:
            host = self.aria2_host.get().strip()
            port = self.aria2_port.get().strip()
            secret = self.aria2_secret.get().strip()

            if not host.startswith(('http://', 'https://')):
                host = f"http://{host}"

            # 创建Aria2客户端
            client = aria2p.Client(
                host=host,
                port=int(port),
                secret=secret if secret else None
            )

            # 先测试客户端连接 - 正确处理字典返回值
            try:
                version_info = client.get_version()
                # 检查版本信息是否有效
                if isinstance(version_info, dict) and 'version' in version_info:
                    version_str = version_info['version']
                else:
                    version_str = "未知版本"
            except Exception as e:
                error_msg = str(e)  # 将异常信息保存到局部变量
                self.root.after(0, lambda msg=error_msg: self._on_aria2_connect_failed(f"Aria2服务连接失败: {msg}"))
                return

            # 创建API实例
            aria2_client = aria2p.API(client)

            # 使用更兼容的方法测试
            try:
                # 尝试获取任务列表来测试功能
                downloads = aria2_client.get_downloads()
                task_count = len(downloads)
                self.root.after(0, lambda: self._on_aria2_connected(aria2_client,
                                                                    f"连接成功，版本: {version_str}，任务数: {task_count}"))
            except Exception as e:
                # 即使获取任务失败，只要连接成功也算成功
                self.root.after(0, lambda: self._on_aria2_connected(aria2_client,
                                                                    f"连接成功，版本: {version_str}（功能测试异常: {e}）"))

        except Exception as e:
            if self.root and self.root.winfo_exists():
                error_msg = str(e)  # 将异常信息保存到局部变量
                self.root.after(0, lambda msg=error_msg: self._on_aria2_connect_failed(f"连接失败: {msg}"))
            else:
                logging.error(f"Aria2连接失败: {e}")

    def _on_aria2_connected(self, client, message):
        """Aria2连接成功后的UI更新"""
        try:
            self.aria2_client = client
            self.aria2_status.set("已连接")
            self.aria2_connect_btn.config(state=tk.NORMAL)  # 确保按钮可用
            self.log_message(f"Aria2 {message}")

            # 启用相关按钮
            self.aria2_refresh_btn.config(state=tk.NORMAL)
            self.aria2_auto_start_btn.config(state=tk.NORMAL)
            self.aria2_add_task_btn.config(state=tk.NORMAL)

        except Exception as e:
            self.log_message(f"更新连接状态时出错: {e}", "error")

    def _on_aria2_connect_failed(self, error_msg):
        """Aria2连接失败后的UI更新"""
        self.aria2_status.set("连接失败")
        self.aria2_connect_btn.config(state=tk.NORMAL)

        # 确保相关按钮保持禁用状态
        self.aria2_refresh_btn.config(state=tk.DISABLED)
        self.aria2_auto_start_btn.config(state=tk.DISABLED)
        self.log_message(f"Aria2连接失败: {error_msg}", "error")
        self.root.after(0, lambda: messagebox.showerror("连接失败", f"无法连接到Aria2服务: {error_msg}"))

        # 禁用刷新按钮，防止重复点击
        self.aria2_refresh_btn.config(state=tk.DISABLED)

        # 在后台线程中执行刷新
        threading.Thread(target=self._refresh_aria2_tasks_thread, daemon=True).start()

    def _refresh_aria2_tasks_thread(self):
        """在后台线程中执行Aria2任务刷新"""
        try:
            if not self.aria2_client:
                self.root.after(0, lambda: self._on_refresh_tasks_failed("Aria2客户端未初始化"))
                return

            # 获取所有任务
            downloads = self.aria2_client.get_downloads()
            # 在主线程中更新UI
            self.root.after(0, lambda: self._update_aria2_tasks_ui(downloads))

        except Exception as e:
            self.root.after(0, lambda: self._on_refresh_tasks_failed(f"刷新失败: {str(e)}"))

    def _update_aria2_tasks_ui(self, downloads):
        """更新Aria2任务UI"""
        # 启用刷新按钮
        self.aria2_refresh_btn.config(state=tk.NORMAL)

        # 保存当前滚动位置和选中状态
        selected_items = self.aria2_tree.selection()
        selected_gids = [self.aria2_tree.item(item, "values")[0] for item in selected_items]

        # 获取第一个可见项（用于保持滚动位置）
        first_visible = None
        for item in self.aria2_tree.get_children():
            if self.aria2_tree.bbox(item):  # 如果项在视口内
                first_visible = item
                break

        # 更新任务列表（使用之前优化的不闪屏版本）
        self._update_aria2_tasks_list(downloads)

        # 恢复选中状态
        for item in self.aria2_tree.get_children():
            if self.aria2_tree.item(item, "values")[0] in selected_gids:
                self.aria2_tree.selection_add(item)

        # 滚动到之前的位置
        if first_visible and first_visible in self.aria2_tree.get_children():
            self.aria2_tree.see(first_visible)

    def _on_refresh_tasks_failed(self, error_msg):
        """刷新任务失败后的处理"""
        self.aria2_refresh_btn.config(state=tk.NORMAL)
        self.log_message(f"刷新Aria2任务失败: {error_msg}", "error")

    def _update_aria2_tasks_list(self, downloads):
        """更新Aria2任务列表（不闪屏版本）"""
        # 获取当前显示的任务GID列表
        current_displayed_gids = set()
        for item in self.aria2_tree.get_children():
            gid = self.aria2_tree.item(item, "values")[0]
            current_displayed_gids.add(gid)

        # 创建新任务GID集合
        new_gids = set()
        for task in downloads:
            try:
                gid = getattr(task, 'gid', None)
                if gid:
                    new_gids.add(gid)
            except:
                continue

        # 删除已不存在的任务
        gids_to_remove = current_displayed_gids - new_gids
        for item in self.aria2_tree.get_children():
            gid = self.aria2_tree.item(item, "values")[0]
            if gid in gids_to_remove:
                self.aria2_tree.delete(item)

        # 更新现有任务和添加新任务
        for task in downloads:
            try:
                # 安全地获取任务信息
                gid = getattr(task, 'gid', '未知')
                name = getattr(task, 'name', '未知任务') or '未知任务'
                status = getattr(task, 'status', '未知')

                # 处理速度
                speed_func = getattr(task, 'download_speed_string', lambda: '0B/s')
                speed = f"{speed_func()}"

                # 处理大小
                # size_func = getattr(task, 'total_length_string', lambda: '未知')
                # size = size_func() or '未知'

                # 处理已下载量
                try:
                    # 方法1: 直接获取 completed_length 属性
                    completed_bytes = getattr(task, 'completed_length', 0)
                    # 转换为可读格式
                    if completed_bytes >= 1024 * 1024 * 1024:  # GB
                        downs = f"{completed_bytes / (1024 * 1024 * 1024):.2f} GB"
                    elif completed_bytes >= 1024 * 1024:  # MB
                        downs = f"{completed_bytes / (1024 * 1024):.2f} MB"
                    elif completed_bytes >= 1024:  # KB
                        downs = f"{completed_bytes / 1024:.2f} KB"
                    else:
                        downs = f"{completed_bytes} B"
                except:
                    # 方法2: 使用 completed_length_string 方法
                    try:
                        downs_func = getattr(task, 'completed_length_string', lambda: '未知')
                        downs = downs_func()
                    except:
                        downs = '未知'

                # 查找是否已存在该任务
                existing_item = None
                for item in self.aria2_tree.get_children():
                    if self.aria2_tree.item(item, "values")[0] == gid:
                        existing_item = item
                        break

                if existing_item:
                    # 更新现有任务
                    current_values = self.aria2_tree.item(existing_item, "values")
                    new_values = (gid, name, status, speed, downs)

                    # 只有当值发生变化时才更新，避免不必要的刷新
                    if current_values != new_values:
                        self.aria2_tree.item(existing_item, values=new_values)
                else:
                    # 添加新任务
                    self.aria2_tree.insert("", "end", values=(
                        gid, name, status, speed, downs
                    ))

            except Exception as task_error:
                self.log_message(f"处理任务信息失败: {task_error}", "warning")
                continue

        # 记录任务数量变化
        current_count = len(self.aria2_tree.get_children())
        if hasattr(self, '_last_task_count'):
            if current_count != self._last_task_count:
                self.log_message(f"任务列表已更新，当前任务数: {current_count}")
        self._last_task_count = current_count

    # ------------分隔线-------------------------------------

    def add_record_task(self):
        """添加录播任务 - 改为启动录播脚本生成器"""
        try:
            # 创建录播脚本生成器窗口
            script_window = tk.Toplevel(self.root)
            script_window.title("录播脚本生成器")
            script_window.geometry("600x550")
            script_window.transient(self.root)
            script_window.grab_set()

            # 启动录播脚本生成器
            script_generator = ScriptGenerator(script_window)

            self.log_message("已启动录播脚本生成器")

        except Exception as e:
            self.log_message(f"启动录播脚本生成器失败: {e}", "error")
            messagebox.showerror("错误", f"启动录播脚本生成器失败: {e}")

    def start_aria2_monitoring(self):
        """开始监控Aria2任务 - 优化版本"""
        if not self.aria2_client:
            messagebox.showwarning("警告", "请先连接Aria2服务")
            return

        if self.aria2_monitoring:
            return

        self.aria2_monitoring = True
        self.aria2_auto_start_btn.config(state=tk.DISABLED)
        self.log_message("Aria2任务监控已启动")

        # 使用after方法实现定时刷新，而不是单独的线程
        self._schedule_aria2_refresh()

    def _schedule_aria2_refresh(self):
        """安排下一次Aria2刷新"""
        if not self.aria2_monitoring:
            return

        # 在后台线程中刷新任务
        threading.Thread(target=self._refresh_aria2_tasks_thread, daemon=True).start()

        # 5秒后再次刷新
        self.root.after(5000, self._schedule_aria2_refresh)

    def stop_aria2_monitoring(self):
        """停止监控Aria2任务"""
        self.aria2_monitoring = False
        self.aria2_auto_start_btn.config(state=tk.NORMAL)
        self.log_message("Aria2任务监控已停止")

    def pause_selected_tasks(self):
        """暂停选中的任务 - 异步版本"""
        if not self.aria2_client:
            messagebox.showwarning("警告", "请先连接Aria2服务")
            return

        selected = self.aria2_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要操作的任务")
            return

        # 在后台线程中执行操作
        threading.Thread(target=self._pause_selected_tasks_thread, args=(selected,), daemon=True).start()

    def _pause_selected_tasks_thread(self, selected):
        """在后台线程中暂停任务"""
        try:
            tasks_to_operate = []
            for item in selected:
                gid = self.aria2_tree.item(item, "values")[0]
                task = self.aria2_client.get_download(gid)
                tasks_to_operate.append(task)

            # 批量操作
            self.aria2_client.pause(tasks_to_operate)

            # 在主线程中更新UI
            for task in tasks_to_operate:
                self.root.after(0, lambda t=task: self.log_message(f"已暂停任务: {t.name}"))

            # 稍微延迟一下再刷新，确保操作生效
            self.root.after(100, self.refresh_aria2_tasks)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"暂停任务失败: {e}", "error"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"暂停任务失败: {e}"))

    # 同样修改resume_selected_tasks和remove_selected_tasks方法
    def resume_selected_tasks(self):
        """继续选中的任务 - 异步版本"""
        if not self.aria2_client:
            messagebox.showwarning("警告", "请先连接Aria2服务")
            return

        selected = self.aria2_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要操作的任务")
            return

        threading.Thread(target=self._resume_selected_tasks_thread, args=(selected,), daemon=True).start()

    def _resume_selected_tasks_thread(self, selected):
        """在后台线程中继续任务"""
        try:
            tasks_to_operate = []
            for item in selected:
                gid = self.aria2_tree.item(item, "values")[0]
                task = self.aria2_client.get_download(gid)
                tasks_to_operate.append(task)

            self.aria2_client.resume(tasks_to_operate)

            for task in tasks_to_operate:
                self.root.after(0, lambda t=task: self.log_message(f"已继续任务: {t.name}"))

            self.root.after(100, self.refresh_aria2_tasks)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"继续任务失败: {e}", "error"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"继续任务失败: {e}"))

    def remove_selected_tasks(self):
        """删除选中的任务 - 异步版本"""
        if not self.aria2_client:
            messagebox.showwarning("警告", "请先连接Aria2服务")
            return

        selected = self.aria2_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要操作的任务")
            return

        threading.Thread(target=self._remove_selected_tasks_thread, args=(selected,), daemon=True).start()

    def _remove_selected_tasks_thread(self, selected):
        """在后台线程中删除任务"""
        try:
            tasks_to_operate = []
            for item in selected:
                gid = self.aria2_tree.item(item, "values")[0]
                task = self.aria2_client.get_download(gid)
                tasks_to_operate.append(task)

            # 删除任务（保留文件）
            self.aria2_client.remove(tasks_to_operate, force=True)

            for task in tasks_to_operate:
                self.root.after(0, lambda t=task: self.log_message(f"已删除任务: {t.name}"))

            self.root.after(100, self.refresh_aria2_tasks)

        except Exception as e:
            self.root.after(0, lambda: self.log_message(f"删除任务失败: {e}", "error"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"删除任务失败: {e}"))

    def refresh_aria2_tasks(self):
        """刷新Aria2任务列表 - 异步版本"""

        # 禁用刷新按钮，防止重复点击
        self.aria2_refresh_btn.config(state=tk.DISABLED)

        # 在后台线程中执行刷新
        threading.Thread(target=self._refresh_aria2_tasks_thread, daemon=True).start()

    # ------------------ 日志 ------------------
    def log_message(self, message, level="info"):
        """记录日志信息到界面和文件 - 安全版本"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"

        # 记录到界面（如果log_text已初始化）
        if hasattr(self, 'log_text') and self.log_text:
            try:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, log_entry)
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
            except Exception as e:
                print(f"记录日志到界面失败: {e}")

        # 记录到文件
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)

        # 更新状态栏（如果status_var已初始化）
        if hasattr(self, 'status_var') and self.status_var:
            self.status_var.set(message)

    def _setup_log_tab(self):
        log_frame = ttk.Frame(self.log_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(self.log_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="清空日志", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="导出日志", command=self.export_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="查看日志文件", command=self.open_log_file).pack(side=tk.RIGHT, padx=5)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.log_message("界面日志已清空")

    def export_log(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".log",
                                                 filetypes=[("日志文件", "*.log"), ("所有文件", "*.*")])
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"日志已导出到: {file_path}")
            except Exception as e:
                self.log_message(f"导出日志失败: {e}", "error")

    def open_log_file(self):
        if os.path.exists(LOG_FILE):
            try:
                os.startfile(LOG_FILE)
            except:
                try:
                    subprocess.call(["open", LOG_FILE])
                except:
                    subprocess.call(["xdg-open", LOG_FILE])
        else:
            self.log_message("日志文件不存在", "warning")

    # ------------------ 自动化 ------------------
    def _setup_auto_tab(self):
        add_frame = ttk.LabelFrame(self.auto_tab, text="添加自动化任务")
        add_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(add_frame, text="选择主播:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.auto_streamer_name = tk.StringVar()
        self.auto_streamer_combo = ttk.Combobox(add_frame, textvariable=self.auto_streamer_name, width=15,
                                                state="readonly")
        self.auto_streamer_combo.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="触发条件:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.auto_trigger = tk.StringVar()
        trigger_combo = ttk.Combobox(add_frame, textvariable=self.auto_trigger, width=10, state="readonly")
        trigger_combo['values'] = ("直播中", "未开播")
        trigger_combo.current(0)
        trigger_combo.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(add_frame, text="脚本路径:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.auto_script = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.auto_script, width=35).grid(row=0, column=5, padx=5, pady=5)
        ttk.Button(add_frame, text="浏览", command=self.browse_script).grid(row=0, column=6, padx=5, pady=5)
        ttk.Button(add_frame, text="添加任务", command=self.add_automation).grid(row=0, column=7, padx=5, pady=5)

        list_frame = ttk.LabelFrame(self.auto_tab, text="自动化任务列表")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        columns = ("id", "streamer", "trigger", "script", "status")
        self.auto_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        for col, text, width in zip(columns, ["任务ID", "主播", "触发条件", "脚本路径", "状态"],
                                    [120, 120, 100, 350, 80]):
            self.auto_tree.heading(col, text=text)
            self.auto_tree.column(col, width=width)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.auto_tree.yview)
        self.auto_tree.configure(yscrollcommand=scrollbar.set)
        self.auto_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = ttk.Frame(self.auto_tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_automation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="测试选中", command=self.test_automation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="强行停止选中", command=self.force_stop_automation).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="管理配置", command=self.manage_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config).pack(side=tk.RIGHT, padx=5)

    def _update_automation_status(self, task_id, status):
        """更新自动化任务状态显示"""
        for item in self.auto_tree.get_children():
            values = self.auto_tree.item(item, "values")
            if values[0] == task_id[:8]:  # 比较短ID
                new_values = list(values)
                if len(new_values) < 5:  # 如果状态列不存在
                    new_values.append(status)
                else:
                    new_values[4] = status  # 更新状态列
                self.auto_tree.item(item, values=tuple(new_values))
                break

    def force_stop_automation(self):
        """强行停止选中的自动化任务"""
        selected = self.auto_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要停止的任务")
            return

        for item in selected:
            values = self.auto_tree.item(item, "values")
            task_id_short = values[0]  # 短ID（前8位）

            # 查找完整任务ID
            full_task_id = None
            for auto in self.automations:
                if auto["id"].startswith(task_id_short):
                    full_task_id = auto["id"]
                    break

            if full_task_id and full_task_id in self.running_processes:
                try:
                    # 确保手动停止集合存在
                    if not hasattr(self, 'manually_stopped_tasks'):
                        self.manually_stopped_tasks = set()

                    self.manually_stopped_tasks.add(full_task_id)
                    process = self.running_processes[full_task_id]

                    # 终止进程
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except:
                        process.kill()

                    # 清理进程引用
                    del self.running_processes[full_task_id]
                    self.manually_stopped_tasks.discard(full_task_id)

                    # 更新任务状态
                    self._update_automation_status(full_task_id, "已停止")
                    self.log_message(f"已强行停止自动化任务: {values[1]}")

                except Exception as e:
                    self.log_message(f"停止任务失败: {e}", "error")
                    # 确保清理进程引用
                    if full_task_id in self.running_processes:
                        del self.running_processes[full_task_id]
                    if hasattr(self, 'manually_stopped_tasks') and full_task_id in self.manually_stopped_tasks:
                        self.manually_stopped_tasks.discard(full_task_id)
            else:
                self.log_message(f"任务 {values[1]} 未在运行或找不到进程", "warning")

    # ------------------ 自动化逻辑 ------------------
    def browse_script(self):
        file_path = filedialog.askopenfilename(title="选择脚本文件",
                                               filetypes=[("Python/Bat", "*.py *.bat"), ("所有文件", "*.*")])
        if file_path:
            self.auto_script.set(file_path)

    def add_automation(self):
        streamer = self.auto_streamer_name.get()
        trigger = self.auto_trigger.get()
        script = self.auto_script.get().strip()
        if not streamer or not script:
            messagebox.showerror("错误", "请选择主播并填写脚本路径")
            return
        if len(self.automations) >= 20:
            messagebox.showwarning("警告", "最多只能创建 20 个自动化任务")
            return
        task_id = str(uuid.uuid4())
        auto = {"id": task_id, "streamer": streamer, "trigger": trigger, "script": script}
        self.automations.append(auto)
        self.auto_tree.insert("", "end", values=(task_id[:8], streamer, trigger, script, "未运行"))
        self.log_message(f"已添加自动化任务: {streamer} -> {trigger} -> {os.path.basename(script)}")
        self.save_config()

    def delete_automation(self):
        selected = self.auto_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的任务")
            return

        for item in selected:
            values = self.auto_tree.item(item, "values")
            task_id_short = values[0]

            # 查找完整任务ID并停止进程
            full_task_id = None
            for auto in self.automations:
                if auto["id"].startswith(task_id_short):
                    full_task_id = auto["id"]
                    break

            # 停止相关进程
            if full_task_id and full_task_id in self.running_processes:
                try:
                    process = self.running_processes[full_task_id]
                    process.terminate()
                    del self.running_processes[full_task_id]
                except:
                    pass

            # 删除任务
            self.automations = [a for a in self.automations if not a["id"].startswith(task_id_short)]
            self.auto_tree.delete(item)

        self.log_message("已删除选中的自动化任务")
        self.save_config()

    def test_automation(self):
        """测试自动化任务 - 修复版本"""
        selected = self.auto_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要测试的任务")
            return

        values = self.auto_tree.item(selected[0], "values")
        task_id_short = values[0]

        # 查找完整任务ID
        full_task_id = None
        auto_task = None
        for auto in self.automations:
            if auto["id"].startswith(task_id_short):
                full_task_id = auto["id"]
                auto_task = auto
                break

        if auto_task:
            # 检查脚本文件是否存在
            if not os.path.exists(auto_task["script"]):
                messagebox.showerror("错误", f"脚本文件不存在: {auto_task['script']}")
                return

            self.log_message(f"测试执行自动化任务: {auto_task['streamer']} -> {auto_task['trigger']}")
            self.run_script(auto_task["script"], auto[full_task_id])
        else:
            self.log_message("找不到对应的自动化任务", "error")

    def run_script(self, script_path, task_id):
        """执行自动化脚本 - 修复EXE环境下的执行问题"""
        try:
            # 检查脚本文件是否存在
            if not os.path.exists(script_path):
                self.log_message(f"脚本文件不存在: {script_path}", "error")
                return

            # 获取应用程序目录，确保工作目录正确
            app_dir = get_app_directory()
            # 强制设置工作目录到主程序目录
            try:
                os.chdir(app_dir)
                print(f"主程序工作目录已设置为: {app_dir}", flush=True)
            except Exception as e:
                print(f"设置工作目录失败: {e}", flush=True)
            # 检查脚本是否已经在运行（防止重复启动）
            script_basename = os.path.basename(script_path)
            for task_id_running, process in self.running_processes.items():
                try:
                    # 检查进程是否仍在运行
                    if process.poll() is None:  # 进程仍在运行
                        # 检查是否正在运行相同的脚本
                        if task_id_running != task_id and script_basename in str(process.args):
                            self.log_message(f"警告: 相同的脚本已经在运行中: {script_basename}", "warning")
                            return
                except:
                    pass

            # 判断是否在EXE环境中运行
            is_exe_environment = getattr(sys, 'frozen', False)

            # 根据脚本类型和运行环境选择执行方式
            if script_path.endswith('.py'):
                if is_exe_environment:
                    # EXE环境：直接使用系统关联执行Python脚本
                    if sys.platform == 'win32':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = 0

                        process = subprocess.Popen(
                            [script_path],  # 直接执行脚本，让系统关联处理
                            cwd=app_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            shell=True  # 使用shell执行，让系统识别文件关联
                        )
                    else:
                        process = subprocess.Popen(
                            [script_path],
                            cwd=app_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True
                        )
                    self.log_message(f"EXE环境：直接执行Python脚本: {script_path}")
                else:
                    # 开发环境：使用Python解释器执行
                    python_exe = sys.executable
                    if sys.platform == 'win32':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = 0

                        process = subprocess.Popen(
                            [python_exe, script_path],
                            cwd=app_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            startupinfo=startupinfo,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    else:
                        process = subprocess.Popen(
                            [python_exe, script_path],
                            cwd=app_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                    self.log_message(f"开发环境：使用Python解释器执行脚本: {script_path}")



            elif script_path.endswith('.bat'):
                # 使用主程序所在目录作为工作目录
                app_dir = get_app_directory()
                # 强制设置工作目录到主程序目录
                try:
                    os.chdir(app_dir)
                    print(f"主程序工作目录已设置为: {app_dir}", flush=True)
                except Exception as e:
                    print(f"设置工作目录失败: {e}", flush=True)
                if sys.platform == 'win32':
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    startupinfo.wShowWindow = 0
                    process = subprocess.Popen(
                        ['cmd.exe', '/c', script_path],
                        cwd=app_dir,  # 修改为使用主程序目录
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        startupinfo=startupinfo,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    print(f"执行BAT脚本: {script_path}, 工作目录: {app_dir}", flush=True)
                else:
                    process = subprocess.Popen(
                        ['sh', script_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
            else:
                # 其他类型脚本
                script_dir = os.path.dirname(script_path)
                process = subprocess.Popen(
                    script_path,
                    cwd=script_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True
                )

            # 保存进程引用
            self.running_processes[task_id] = process

            # 启动线程监控进程输出
            threading.Thread(target=self._monitor_script_output,
                             args=(process, script_path, task_id),
                             daemon=True).start()

            self.log_message(f"开始执行脚本: {os.path.basename(script_path)} (工作目录: {app_dir})")
            self._update_automation_status(task_id, "运行中")

        except Exception as e:
            self.log_message(f"执行脚本出错: {e}", "error")
            self._update_automation_status(task_id, "执行失败")

    def _monitor_script_output(self, process, script_path, task_id):
        """监控脚本执行输出 - 修改状态判断逻辑"""
        try:
            # 读取标准输出
            stdout_thread = threading.Thread(
                target=self._read_pipe,
                args=(process.stdout, script_path, "STDOUT"),
                daemon=True
            )
            stdout_thread.start()

            # 读取标准错误
            stderr_thread = threading.Thread(
                target=self._read_pipe,
                args=(process.stderr, script_path, "STDERR"),
                daemon=True
            )
            stderr_thread.start()

            # 等待进程结束
            return_code = process.wait()

            # 更新状态 - 检查是否手动停止
            if task_id in self.manually_stopped_tasks:
                self._update_automation_status(task_id, "已停止")
                self.manually_stopped_tasks.discard(task_id)  # 移除记录
                # 录播脚本的状态更新正常显示
                self.log_message(f"脚本被手动停止: {os.path.basename(script_path)}")
            elif return_code == 0:
                # 录播脚本的完成状态正常显示
                self.log_message(f"脚本执行完成: {os.path.basename(script_path)}")
                self._update_automation_status(task_id, "已完成")
            else:
                # 录播脚本的错误状态正常显示
                self.log_message(f"脚本执行失败，退出码: {return_code} - {os.path.basename(script_path)}", "error")
                self._update_automation_status(task_id, "执行失败")

            # 清理进程引用
            if task_id in self.running_processes:
                del self.running_processes[task_id]

        except Exception as e:
            # 检查是否手动停止
            if task_id in self.manually_stopped_tasks:
                self._update_automation_status(task_id, "已停止")
                self.manually_stopped_tasks.discard(task_id)
                # 录播脚本的状态更新正常显示
                self.log_message(f"脚本被手动停止: {os.path.basename(script_path)}")
            else:
                # 录播脚本的错误信息正常显示
                self.log_message(f"监控脚本输出出错: {e}", "error")
                self._update_automation_status(task_id, "监控失败")

    def _read_pipe(self, pipe, script_path, pipe_name):
        """读取管道输出 - 过滤录播日志"""
        try:
            for line in iter(pipe.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8', errors='ignore').strip()
                    if decoded_line:
                        # 过滤录播相关的日志（不显示到主程序日志）
                        script_basename = os.path.basename(script_path)
                        # 如果是录播脚本或转码脚本，不显示日志
                        if (script_basename.startswith("开始录播-") or
                                script_basename.startswith("自动转码-") or
                                "录播" in script_basename or
                                "转码" in script_basename):
                            # 可以选择记录到文件或完全忽略
                            # 这里我们选择完全忽略，不显示到界面
                            pass
                        else:
                            # 其他脚本的日志正常显示
                            self.log_message(f"[{script_basename} {pipe_name}] {decoded_line}")
        except Exception as e:
            # 录播脚本的错误日志也不显示
            script_basename = os.path.basename(script_path)
            if not (script_basename.startswith("开始录播-") or
                    script_basename.startswith("自动转码-")):
                self.log_message(f"读取{pipe_name}出错: {e}", "error")

    def _auto_start_aria2_thread(self):
        """在后台线程中启动Aria2 - 修复版本，优先使用vbs"""
        try:
            # 先检查是否已经连接
            if self.aria2_client:
                self.root.after(0, lambda: self.log_message("Aria2已连接，跳过启动"))
                return

            # 检查端口是否已被占用
            if self._test_port_connection():
                self.root.after(0, lambda: self.log_message("Aria2端口已被占用，尝试连接..."))
                self.root.after(0, self.connect_aria2)
                return

            # 检查Aria2 API是否可用
            if self._test_aria2_connection():
                self.root.after(0, lambda: self.log_message("检测到Aria2 API服务，尝试连接..."))
                self.root.after(0, self.connect_aria2)
                return

            self.root.after(0, lambda: self.log_message("未检测到运行的Aria2服务，开始启动..."))

            current_dir = os.path.dirname(os.path.abspath(__file__))
            vbs_path = os.path.join(current_dir, "aria2.vbs")
            bat_path = os.path.join(current_dir, "aria2.bat")

            # 检查是否已经有aria2c进程在运行
            if self._is_aria2c_running():
                self.root.after(0, lambda: self.log_message("检测到aria2c进程已在运行，跳过启动"))
                self.root.after(0, self.connect_aria2)
                return

            # 优先尝试vbs文件
            if os.path.exists(vbs_path):
                try:
                    self.root.after(0, lambda: self.log_message("尝试使用aria2.vbs启动..."))
                    # 使用绝对路径启动
                    vbs_abs_path = os.path.abspath(vbs_path)
                    self.aria2_process = subprocess.Popen(
                        ['wscript.exe', vbs_abs_path],
                        cwd=current_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.root.after(0, lambda: self.log_message("已启动aria2.vbs脚本"))

                    # 等待vbs脚本启动
                    time.sleep(3)

                except Exception as vbs_error:
                    self.root.after(0, lambda: self.log_message(f"vbs启动失败: {vbs_error}，尝试bat脚本"))
                    # vbs失败，回退到bat
                    if os.path.exists(bat_path):
                        try:
                            self.aria2_process = subprocess.Popen(
                                bat_path,
                                cwd=current_dir,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW
                            )
                            self.root.after(0, lambda: self.log_message("已启动aria2.bat脚本"))
                        except Exception as bat_error:
                            self.root.after(0, lambda: self.log_message(f"bat启动也失败: {bat_error}", "error"))
                            return
                    else:
                        self.root.after(0, lambda: self.log_message("未找到aria2.bat文件", "error"))
                        return
            elif os.path.exists(bat_path):
                # 直接使用bat文件
                try:
                    self.aria2_process = subprocess.Popen(
                        bat_path,
                        cwd=current_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    self.root.after(0, lambda: self.log_message("已启动aria2.bat脚本"))
                except Exception as bat_error:
                    self.root.after(0, lambda: self.log_message(f"bat启动失败: {bat_error}", "error"))
                    return
            else:
                self.root.after(0, lambda: self.log_message("未找到aria2启动脚本(aria2.vbs或aria2.bat)", "warning"))
                return

            # 等待服务启动
            self.root.after(0, lambda: self.log_message("等待Aria2服务启动..."))

            # 使用渐进式等待策略
            for i in range(15):  # 增加到15秒等待时间
                time.sleep(1)
                if self._test_port_connection() or self._test_aria2_connection():
                    self.root.after(0, lambda: self.log_message("Aria2服务启动成功，开始连接..."))
                    self.root.after(0, self.connect_aria2)
                    return
                self.root.after(0, lambda: self.log_message(f"等待Aria2启动... ({i + 1}/15)"))

            self.root.after(0, lambda: self.log_message("Aria2服务启动超时，但将继续尝试连接", "warning"))
            # 即使超时也尝试连接一次
            self.root.after(0, self.connect_aria2)

        except Exception as e:
            error_msg = str(e)
            self.root.after(0, lambda msg=error_msg: self.log_message(f"自动启动Aria2失败: {msg}", "error"))
            # 尝试直接连接（可能服务已由其他方式启动）
            self.root.after(0, lambda: self.log_message("尝试直接连接Aria2..."))
            self.root.after(0, self.connect_aria2)

    # ------------------ 主播管理 ------------------
    def add_streamer(self):
        name = self.streamer_name.get().strip()
        platform = self.platform.get()
        streamer_id = self.streamer_id.get().strip()
        group = self.streamer_group.get()

        if not name:
            messagebox.showerror("错误", "请输入主播名称")
            return
        if not streamer_id:
            messagebox.showerror("错误", "请输入ID或URL")
            return
        if platform == "哔哩哔哩" and not streamer_id.isdigit():
            messagebox.showerror("错误", "哔哩哔哩房间ID必须是数字")
            return
        if platform == "抖音" and not streamer_id.startswith("http"):
            messagebox.showerror("错误", "请输入有效的抖音主页URL")
            return

        streamer = {"name": name, "platform": platform, "id": streamer_id, "group": group, "status": "未开播",
                    "last_check_time": "未监控"}
        self.streamers.append(streamer)
        self.streamer_tree.insert("", "end", values=(name, platform, streamer_id, group, "未开播", "未监控"))
        self.streamer_name.set("")
        self.streamer_id.set("")
        self.log_message(f"已添加主播: {name} ({platform}) -> 通知组: {group}")
        self.update_auto_streamer_combo()
        self.refresh_group_list()  # 刷新组列表显示主播数量
        self.save_config()

    def delete_streamer(self):
        selected = self.streamer_tree.selection()
        if not selected:
            messagebox.showwarning("警告", "请先选择要删除的主播")
            return
        for item in selected:
            values = self.streamer_tree.item(item, "values")
            name = values[0]
            self.streamer_tree.delete(item)
            self.streamers = [s for s in self.streamers if s["name"] != name]
            self.log_message(f"已删除主播: {name}")
        self.update_auto_streamer_combo()
        self.refresh_group_list()  # 刷新组列表显示主播数量
        self.save_config()

    def update_auto_streamer_combo(self):
        names = [s["name"] for s in self.streamers]
        self.auto_streamer_combo["values"] = names
        if names:
            self.auto_streamer_combo.current(0)

    # ------------------ 监控 ------------------
    def start_monitoring(self):
        if self.monitoring:
            return
        stream_count = len(self.streamers)
        every_sleep = 4.5 + (0.12 * stream_count)
        squares = stream_count * 1.1
        total_cycle = 2 + (0.12 * squares)
        refer_time = round(total_cycle + (2 * every_sleep))
        self.monitoring = True
        self.log_message(f"监控已启动 (每间隔{refer_time}秒检查一次)")
        self.last_status = {s["name"]: s["status"] for s in self.streamers}
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        if not self.monitoring:
            return
        self.monitoring = False
        self.log_message("监控已停止")

    def _monitor_loop(self):
        stream_count = len(self.streamers)
        every_sleep = 4.5 + (0.12 * stream_count)
        squares = stream_count * 1.1
        total_cycle = 2 + (0.12 * squares)
        while self.monitoring:
            for streamer in self.streamers:
                try:
                    if streamer["platform"] == "哔哩哔哩":
                        is_live = self.check_bili_live(streamer["id"])
                        time.sleep(random.uniform(1, 3))
                    else:
                        is_live = self.check_douyin_live(streamer["id"])
                        time.sleep(every_sleep)
                    # 在这里添加时间更新
                    current_time = datetime.now().strftime("%H:%M:%S")
                    streamer["last_check_time"] = current_time

                    new_status = "直播中" if is_live else "未开播"
                    old_status = self.last_status.get(streamer["name"], "未开播")
                    streamer["status"] = new_status
                    # 更新Treeview
                    for item in self.streamer_tree.get_children():
                        values = self.streamer_tree.item(item, "values")
                        if values[0] == streamer["name"]:
                            self.streamer_tree.item(item, values=(
                                streamer["name"], streamer["platform"], streamer["id"],
                                streamer.get("group", self.default_notification_group), new_status, current_time))
                            break

                    if old_status != new_status:
                        self.last_status[streamer["name"]] = new_status
                        self.last_status[streamer["name"] + "_time"] = time.time()
                        if new_status == "直播中":
                            msg = (f"🎉🎉🎉🎉🎉🎉🎉🎉 你关注的{streamer['name']}在{streamer['platform']}开播啦!\n\n"
                                   f"主播名称: {streamer['name']}\n"
                                   f"直播平台: {streamer['platform']}\n"
                                   f"主播ID: {streamer['id']}\n"
                                   f"开播时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            title = f"开播提醒：{streamer['name']} 在{streamer['platform']}开播了!"
                        else:
                            msg = (f"{streamer['name']} 在{streamer['platform']}结束直播了!\n"
                                   f"结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            title = f"下播提醒：{streamer['name']} 在{streamer['platform']}结束直播了!"

                        # 发送通知（根据通知组和启用状态）
                        self.send_notifications(title, msg, streamer.get("group", self.default_notification_group))
                        self.log_message(title)
                        self._check_automation(streamer["name"], new_status)
                except Exception as e:
                    self.log_message(f"监控 {streamer['name']} 出错: {e}", "error")
            for _ in range(round(total_cycle)):
                if not self.monitoring:
                    break
                time.sleep(random.uniform(1, 2.5))

    # ------------------ 状态检查 ------------------
    def check_bili_live(self, room_id):
        try:
            api_url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={room_id}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            res = requests.get(api_url, headers=headers, timeout=10).json()
            return res.get("code") == 0 and res.get("data", {}).get("live_status") == 1
        except Exception as e:
            self.log_message(f"检查哔哩哔哩直播状态出错: {e}", "error")
            return False

    def check_douyin_live(self, url):
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cookie": self.douyin_cookie
            }
            res = requests.get(url, headers=headers, timeout=10)
            res.encoding = 'utf-8'
            m = re.search(r'"live_status":(\d)', res.text)
            if m:
                return m.group(1) == "1"
            return "直播中" in res.text
        except Exception as e:
            self.log_message(f"检查抖音直播状态出错: {e}", "error")
            return False

    # ------------------ 通知 ------------------
    def send_wxpusher_notification(self, title, content):
        """发送WxPusher通知"""
        if not self.wxpusher_enabled.get():
            return False

        app_token = self.app_token.get()
        user_id = self.user_id.get()
        if not app_token or not user_id:
            self.log_message("错误: 请先配置WxPusher信息", "error")
            return False
        try:
            api_url = "https://wxpusher.zjiecode.com/api/send/message"
            payload = {
                "appToken": app_token,
                "content": content,
                "summary": title,
                "Type": 1,
                "uids": [user_id]
            }
            res = requests.post(api_url, json=payload, timeout=10).json()
            return res.get("success", False)
        except Exception as e:
            self.log_message(f"WxPusher通知发送失败: {e}", "error")
            return False

    def send_wecom_notification(self, title, content):
        """发送企业微信机器人通知"""
        if not self.wecom_enabled.get():
            return False

        webhook_url = self.wecom_webhook.get()
        if not webhook_url:
            self.log_message("错误: 请先配置企业微信机器人Webhook", "error")
            return False
        try:
            payload = {
                "msgtype": "text",
                "text": {
                    "content": f"{title}\n\n{content}"
                }
            }
            res = requests.post(webhook_url, json=payload, timeout=10)
            return res.status_code == 200
        except Exception as e:
            self.log_message(f"企业微信机器人通知发送失败: {e}", "error")
            return False

    def send_notifications(self, title, content, group_name):
        """根据通知组设置发送通知，全局主开关优先"""
        # 查找对应的通知组
        group = next((g for g in self.notification_groups if g["name"] == group_name), None)
        if not group:
            self.log_message(f"找不到通知组 '{group_name}'，使用默认设置", "warning")
            group = {"notify_methods": {"wxpusher": True, "wecom": False}}

        # 获取组的通知方式设置
        group_methods = group.get("notify_methods", {"wxpusher": True, "wecom": False})

        # 发送通知（全局主开关优先）
        wx_success = False
        wecom_success = False

        # WxPusher通知：全局开关开启且组设置开启
        if self.wxpusher_enabled.get() and group_methods.get("wxpusher", True):
            wx_success = self.send_wxpusher_notification(title, content)
        elif group_methods.get("wxpusher", True) and not self.wxpusher_enabled.get():
            self.log_message(f"通知组 '{group_name}' 的WxPusher通知因全局开关关闭而未发送", "warning")

        # 企业微信通知：全局开关开启且组设置开启
        if self.wecom_enabled.get() and group_methods.get("wecom", False):
            wecom_success = self.send_wecom_notification(title, content)
        elif group_methods.get("wecom", False) and not self.wecom_enabled.get():
            self.log_message(f"通知组 '{group_name}' 的企业微信通知因全局开关关闭而未发送", "warning")

        # 记录发送结果
        if wx_success or wecom_success:
            self.log_message(
                f"通知组 '{group_name}' 通知发送成功（WxPusher: {'是' if wx_success else '否'}, 企业微信: {'是' if wecom_success else '否'}）")
        else:
            self.log_message(f"通知组 '{group_name}' 所有通知方式均未启用或发送失败", "error")

    def test_wxpusher_notification(self):
        if self.send_wxpusher_notification("测试通知", "这是一个来自开播监控助手的WxPusher测试消息"):
            messagebox.showinfo("成功", "WxPusher测试通知已发送，请检查微信")
        else:
            messagebox.showerror("错误", "WxPusher通知发送失败，请检查配置")

    def test_wecom_notification(self):
        if self.send_wecom_notification("测试通知", "这是一个来自开播监控助手的企业微信机器人测试消息"):
            messagebox.showinfo("成功", "企业微信机器人测试通知已发送，请检查企业微信")
        else:
            messagebox.showerror("错误", "企业微信机器人通知发送失败，请检查配置")

    # ------------------ Cookie 获取 ------------------
    def maybe_auto_get_douyin_cookie(self):
        if not self.auto_cookie_var.get():
            self.log_message("自动获取抖音 Cookie 已关闭")
            return
        if not SELENIUM_OK:
            self.log_message("未安装最新版本的selenium，跳过自动获取 Cookie")
            self.log_message("请安装最新版本的selenium(pip install selenium)以正常使用自动获取 Cookie")
            return
        threading.Thread(target=self.auto_get_douyin_cookie, daemon=True).start()

    def auto_get_douyin_cookie(self):
        try:
            self.log_message("正在自动获取抖音 Cookie...")
            options = EdgeOptions()
            options.use_chromium = True
            # 使用非Headless模式，让用户手动登录
            # options.add_argument("headless")  # 注释掉headless模式

            driver = Edge(options=options)
            # 访问抖音登录页面
            driver.get("https://www.douyin.com/user/MS4wLjABAAAA0Wk4gxp3AYFnqoqo-IBF6lbdLnrxgjy__DdhPBNBkws")
            time.sleep(15)

            # 获取登录后的Cookie
            cookies = driver.get_cookies()
            driver.quit()

            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            self.douyin_cookie = cookie_str
            self.root.after(0, lambda: self.cookie_display.delete(1.0, tk.END))
            self.root.after(0, lambda: self.cookie_display.insert(1.0, cookie_str))

            self.log_message("抖音 Cookie 获取成功")
            self.save_config()
        except Exception as e:
            self.log_message(f"自动获取抖音 Cookie 失败: {e}", "error")
            self.root.after(0, lambda: messagebox.showwarning(
                "Cookie 获取失败",
                f"自动获取抖音 Cookie 失败: {e}\n请手动填写或留空"))

    def manual_input_cookie(self):
        cookie = simpledialog.askstring("手动填写 Cookie", "请输入抖音 Cookie：")
        if cookie is not None:
            self.douyin_cookie = cookie
            self.cookie_display.delete(1.0, tk.END)
            self.cookie_display.insert(1.0, cookie)
            self.save_config()
            self.log_message("已手动更新抖音 Cookie")

    # ------------------ 配置 ------------------
    def load_config(self):
        """加载配置（兼容旧版本通知组设置）"""
        try:
            # 清空现有界面数据
            self._clear_ui_data()

            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    self.app_token.set(cfg.get("app_token", ""))
                    self.user_id.set(cfg.get("user_id", ""))
                    self.streamers = cfg.get("streamers", [])
                    self.douyin_cookie = cfg.get("douyin_cookie", "")
                    self.auto_cookie_var.set(cfg.get("auto_cookie", True))
                    self.automations = cfg.get("automations", [])

                    # 新增配置项
                    self.wxpusher_enabled.set(cfg.get("wxpusher_enabled", True))
                    self.wecom_enabled.set(cfg.get("wecom_enabled", False))
                    self.wecom_webhook.set(cfg.get("wecom_webhook", ""))

                    # 加载Aria2配置
                    self.aria2_host.set(cfg.get("aria2_host", "localhost"))
                    self.aria2_port.set(cfg.get("aria2_port", "6800"))
                    self.aria2_secret.set(cfg.get("aria2_secret", ""))
                    self.auto_start_aria2_var.set(cfg.get("auto_start_aria2", False))
                    self.current_edge_version = cfg.get("current_edge_version")

                    # 加载通知组配置（兼容旧版本）
                    self.notification_groups = cfg.get("notification_groups", [])
                    self.default_notification_group = cfg.get("default_notification_group", "默认组")

                    # 兼容旧版本配置：为旧版本的通知组添加默认通知方式设置
                    for group in self.notification_groups:
                        if "notify_methods" not in group:
                            group["notify_methods"] = {
                                "wxpusher": True,  # 旧版本默认启用WxPusher
                                "wecom": False  # 旧版本默认禁用企业微信
                            }
                        if "streamers" not in group:
                            group["streamers"] = []

                    # 兼容旧版本配置：如果没有通知组，创建默认组
                    if not self.notification_groups:
                        # 从主播数据中提取组信息
                        groups_from_streamers = set(s.get("group", "默认组") for s in self.streamers)
                        self.notification_groups = [{
                            "name": group,
                            "streamers": [],
                            "notify_methods": {
                                "wxpusher": True,
                                "wecom": False
                            }
                        } for group in groups_from_streamers]

                        # 如果没有组，创建默认组
                        if not self.notification_groups:
                            self.notification_groups = [{
                                "name": "默认组",
                                "streamers": [],
                                "notify_methods": {
                                    "wxpusher": True,
                                    "wecom": False
                                }
                            }]

                    # 重新填充界面数据
                    self._refresh_ui_data()

        except Exception as e:
            self.log_message(f"加载配置出错: {e}", "error")

    def _clear_ui_data(self):
        """清空界面数据"""
        # 清空主播列表
        for item in self.streamer_tree.get_children():
            self.streamer_tree.delete(item)

        # 清空自动化任务列表
        for item in self.auto_tree.get_children():
            self.auto_tree.delete(item)

        # 清空Cookie显示
        self.cookie_display.delete(1.0, tk.END)

    def _refresh_ui_data(self):
        """刷新界面数据"""
        # 加载主播数据（包含通知组）
        for s in self.streamers:
            if "last_check_time" not in s:
                s["last_check_time"] = "从未监控"

            group = s.get("group", self.default_notification_group)
            status = s.get("status", "未开播")
            last_check_time = s.get("last_check_time", "未监控")

            self.streamer_tree.insert("", "end", values=(
                s["name"], s["platform"], s["id"], group, status, last_check_time
            ))

        # 加载自动化任务
        for a in self.automations:
            # 检查任务是否正在运行
            status = "未运行"
            if a["id"] in self.running_processes:
                status = "运行中"

            self.auto_tree.insert("", "end", values=(
                a["id"][:8], a["streamer"], a["trigger"], a["script"], status
            ))

        self.update_auto_streamer_combo()
        self.cookie_display.insert(1.0, self.douyin_cookie)
        self.refresh_group_list()

    def save_config(self):
        try:
            cfg = {
                "app_token": self.app_token.get(),
                "user_id": self.user_id.get(),
                "streamers": self.streamers,
                "douyin_cookie": self.douyin_cookie,
                "auto_cookie": self.auto_cookie_var.get(),
                "automations": self.automations,
                "current_edge_version": self.current_edge_version,
                "aria2_host": self.aria2_host.get(),
                "aria2_port": self.aria2_port.get(),
                "aria2_secret": self.aria2_secret.get(),

                # 新增配置项
                "wxpusher_enabled": self.wxpusher_enabled.get(),
                "wecom_enabled": self.wecom_enabled.get(),
                "wecom_webhook": self.wecom_webhook.get(),
                "notification_groups": self.notification_groups,
                "default_notification_group": self.default_notification_group,
                "auto_start_aria2": self.auto_start_aria2_var.get()
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            self.log_message("配置保存成功")
            return True
        except Exception as e:
            self.log_message(f"保存配置出错: {e}", "error")
            return False

    def on_closing(self):
        """程序关闭时的处理 - 确保所有资源正确释放"""
        try:
            # 检查是否有活跃的录播任务
            has_active_tasks = False
            if self.aria2_client:
                try:
                    downloads = self.aria2_client.get_downloads()
                    for task in downloads:
                        status = getattr(task, 'status', '')
                        # 活跃状态包括：active（下载中）、paused（暂停）、waiting（等待）
                        if status in ['active', 'paused', 'waiting']:
                            has_active_tasks = True
                            break
                except Exception as e:
                    self.log_message(f"检查活跃任务时出错: {e}", "warning")

            # 如果有活跃任务，弹出确认对话框
            if has_active_tasks:
                confirm = messagebox.askyesno(
                    "确认退出",
                    "检测到有正在录播的任务！\n\n退出程序会导致正在录播的任务停止。\n\n确定要退出程序吗？",
                    icon="warning"
                )
                if not confirm:
                    self.log_message("用户取消退出程序")
                    return  # 用户取消退出，直接返回

            # 停止监控
            self.monitoring = False

            # 停止Aria2监控
            self.stop_aria2_monitoring()

            # 停止所有自动化任务
            self._stop_all_automation_tasks()

            # 停止由本程序启动的aria2进程
            if hasattr(self, 'aria2_process') and self.aria2_process:
                try:
                    self.log_message("正在停止aria2服务...")
                    self.aria2_process.terminate()

                    # 等待进程结束，最多等待5秒
                    for i in range(50):
                        if self.aria2_process.poll() is not None:
                            self.log_message("aria2服务已正常停止")
                            break
                        time.sleep(0.1)
                    else:
                        # 如果进程没有正常终止，强制杀死
                        self.aria2_process.kill()
                        self.log_message("aria2服务已被强制停止")

                except Exception as e:
                    self.log_message(f"停止aria2服务时出错: {e}", "warning")

            # 额外措施：强制终止所有aria2c进程（确保完全关闭）
            try:
                self._kill_all_aria2c_processes()
            except Exception as e:
                self.log_message(f"强制终止aria2c进程时出错: {e}", "warning")

            # 保存配置
            self.save_config()

            # 等待一小段时间确保资源释放
            time.sleep(0.5)

            # 强制退出程序
            self.log_message("程序正在退出...")

            # 使用os._exit确保程序完全退出
            import os
            os._exit(0)

        except Exception as e:
            self.log_message(f"关闭过程中发生错误: {e}", "error")
            # 无论如何都要尝试退出
            try:
                import os
                os._exit(1)
            except:
                pass

        except Exception as e:
            self.log_message(f"关闭过程中发生错误: {e}", "error")
            # 无论如何都要尝试退出
            try:
                import os
                os._exit(1)
            except:
                pass

    def _stop_all_automation_tasks(self):
        """停止所有自动化任务"""
        try:
            if hasattr(self, 'running_processes'):
                for task_id, process in list(self.running_processes.items()):
                    try:
                        process.terminate()
                        process.wait(timeout=3)
                    except:
                        try:
                            process.kill()
                        except:
                            pass
                self.running_processes.clear()
            self.log_message("所有自动化任务已停止")
        except Exception as e:
            self.log_message(f"停止自动化任务时出错: {e}", "warning")

    def _kill_all_aria2c_processes(self):
        """强制终止所有aria2c进程"""
        try:
            if sys.platform == "win32":
                # Windows系统
                subprocess.run(['taskkill', '/f', '/im', 'aria2c.exe'],
                               capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
                self.log_message("已强制终止所有aria2c进程")
            else:
                # Linux/Mac系统
                subprocess.run(['pkill', '-f', 'aria2c'],
                               capture_output=True, timeout=10)
                self.log_message("已强制终止所有aria2c进程")
        except Exception as e:
            self.log_message(f"强制终止aria2c进程失败: {e}", "warning")


    # ------------------ 自动化触发 ------------------
    def _check_automation(self, streamer_name, new_status):
        now = time.time()
        with self.auto_lock:
            for auto in self.automations:
                if auto["streamer"] != streamer_name or auto["trigger"] != new_status:
                    continue
                self.running_auto_tasks.append(auto)
                threading.Thread(target=self._execute_auto_tasks, daemon=True).start()
                break

    def _execute_auto_tasks(self):
        while True:
            with self.auto_lock:
                if not self.running_auto_tasks:
                    break
                auto = self.running_auto_tasks.pop(0)

            self.log_message(f"触发自动化任务: {auto['streamer']} -> {auto['trigger']}")
            self.run_script(auto["script"], auto["id"])

            self.send_notifications(
                "自动化任务触发",
                f"主播 {auto['streamer']} 状态变为 {auto['trigger']}，已执行脚本 {os.path.basename(auto['script'])}",
                "默认组"
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = LiveMonitorApp(root)
    root.mainloop()
