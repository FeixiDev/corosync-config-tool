import datetime
import logging
import socket
import sys
# import paramiko
import subprocess
import yaml
# import time
import json
import re
import os

# class SSHConn(object):
#     def __init__(self, host, port=22, username="root", password=None, timeout=8):
#         self._host = host
#         self._port = port
#         self._username = username
#         self._password = password
#         self.timeout = timeout
#         self.ssh_connection = None
#         self.ssh_conn()

#     def ssh_conn(self):
#         """
#         SSH连接
#         """
#         try:
#            conn = paramiko.SSHClient()
#            conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#            conn.connect(hostname=self._host,
#                         username=self._username,
#                         port=self._port,
#                         password=self._password,
#                         timeout=self.timeout,
#                         look_for_keys=False,
#                         allow_agent=False)
#            self.ssh_connection = conn
#        except paramiko.AuthenticationException:
#            print(f" Error SSH connection message of {self._host}")
#        except Exception as e:
#            print(f" Failed to connect {self._host}")

#     def exec_cmd(self, command):
#        """
#        命令执行
#        """
#        if self.ssh_connection:
#            stdin, stdout, stderr = self.ssh_connection.exec_command(command)
#            result = stdout.read()
#            result = result.decode() if isinstance(result, bytes) else result
#            if result is not None:
#                return {"st": True, "rt": result}

#            err = stderr.read()
#            if err is not None:
#                return {"st": False, "rt": err}


def local_cmd(command):
    """
    命令执行
    """
    sub_conn = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    if sub_conn.returncode == 0:
        result = sub_conn.stdout
        return {"st": True, "rt": result}
    else:
        print(f"Can't to execute command: {command}")
        err = sub_conn.stderr
        print(f"Error message:{err}")
        return {"st": False, "rt": err}


def get_host_ip():
    """
    查询本机ip地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    finally:
        s.close()
    return ip


def exec_cmd(cmd, conn=None):
    if conn:
        result = conn.exec_cmd(cmd)
    else:
        result = local_cmd(cmd)
    result_str = result['rt'].decode() if isinstance(result['rt'], bytes) else result
    log_data = f"{get_host_ip()} - {cmd} - {result_str}"
    Log().logger.info(log_data)
    if result['st']:
        pass
    if result['st'] is False:
        sys.exit()

    return result_str


class Log(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.logger = logging.getLogger()
            cls._instance.logger.setLevel(logging.INFO)
            cls._instance.set_handler()
        return cls._instance

    def set_handler(self):
        now_date = datetime.datetime.now().strftime('%Y-%m-%d')
        existing_log_files = [file for file in os.listdir('.') if file.startswith(f"vsdscoroconf_{now_date}")]

        if existing_log_files:
            file_name = existing_log_files[0]
        else:
            file_name = f"vsdscoroconf_{now_date}.log"

        fh = logging.FileHandler(file_name, mode='a')
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)


class FileEdit(object):
    def __init__(self, path):
        self.path = path
        self.data = self.read_file()

    def read_file(self):
        with open(self.path) as f:
            data = f.read()
        return data

    def replace_data(self, old, new):
        if not old in self.data:
            print(f'The content does not exist\n{old}')
            return
        self.data = self.data.replace(old, new)
        return self.data
    
    def remove_nodelist(self):
        pattern = 'provider: corosync_votequorum'  # 要查找的模式
        lines = self.data.split('\n')
        found_pattern = False
        start_index = None
        middle_index = None

        for index, line in enumerate(lines):
            if pattern in line:
                middle_index = index
                break  # 找到模式后退出循环

        if middle_index is not None:
            for index in range(middle_index, len(lines)):
                line = lines[index]
                if "}" in line:
                    found_pattern = True
                    start_index = index
                    break  # 找到大括号后退出循环
            

        if found_pattern and start_index is not None:
            # 删除找到的内容
            del lines[start_index + 1:]

            # 更新数据
            self.data = '\n'.join(lines)
            return True  # 表示成功删除内容
        else:
            return False  # 表示未找到要删除的内容

    def insert_data(self, content, anchor=None, type=None):
        """
        在定位字符串anchor的上面或者下面插入数据，上面和下面由type决定（under/above）
        anchor可以是多行数据，但必须完整
        :param anchor: 定位字符串
        :param type: under/above
        :return:
        """
        list_data = self.data.splitlines()
        list_add = (content + '\n').splitlines()
        pos = len(list_data)
        lst = []

        if anchor:
            if not anchor in self.data:
                return

            list_anchor = anchor.splitlines()
            len_anchor = len(list_anchor)

            for n in range(len(list_data)):
                match_num = 0
                for m in range(len_anchor):
                    if not list_anchor[m] == list_data[n + m]:
                        break
                    match_num += 1

                if match_num == len_anchor:
                    if type == 'under':
                        pos = n + len_anchor
                    else:
                        pos = n
                    break

        lst.extend(list_data[:pos])
        lst.extend(list_add)
        lst.extend(list_data[pos:])
        self.data = '\n'.join(lst)

        return self.data
    
    def add_interface_to_totem(self, interface_content):   # 21
        """
        在 totem 配置块中添加 interface
        :param interface_content: 要添加的 interface 内容
        """
        totem_block = re.search(r"totem\s*{([^}]*)}", self.data, re.DOTALL)
        if totem_block:
            updated_totem = totem_block.group(0).strip()  # 获取 totem 块内容并去除首尾空格

            # 添加 interface 内容到 totem 块中
            updated_totem += f"\n{interface_content}"

            # 替换原始的 totem 块内容为更新后的内容
            self.data = re.sub(r"totem\s*{([^}]*)}", updated_totem, self.data, flags=re.DOTALL)

            return self.data
        else:
            return "totem block not found in the configuration data"

    @staticmethod
    def add_data_to_head(text, data_add):
        text_list = text.splitlines()
        for i in range(len(text_list)):
            if text_list[i] != '\n':
                text_list[i] = f'{data_add}{text_list[i]}'

        return '\n'.join(text_list)

    @staticmethod
    def remove_comma(text):
        text_list = text.splitlines()
        for i in range(len(text_list)):
            text_list[i] = text_list[i].rstrip(',')
        return '\n'.join(text_list)


class ConfFile(object):
    def __init__(self):
        self.yaml_file = 'corosync_config.yaml'
        self.config = self.read_yaml()
        self.nodelist_generated = False  # 添加标记

    def read_yaml(self):
        """读YAML文件"""
        try:
            with open(self.yaml_file, 'r', encoding='utf-8') as f:
                yaml_dict = yaml.safe_load(f)
            return yaml_dict
        except FileNotFoundError:
            print("Please check the file name:", self.yaml_file)
            sys.exit()
        except TypeError:
            print("Error in the type of file name.")
            sys.exit()

    def update_yaml(self):
        """更新文件内容"""
        with open(self.yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False)

    # def get_ssh_conn_data(self):
    #     list_ssh = []
    #     for node in self.config['node']:
    #         list_ssh.append([node['heartbeat_line'][0], 22, node['name'], node['ssh_password']])
    #     return list_ssh

    def get_cluster_name(self):
        # noontime = time.strftime('%y%m%d')
        return self.config['cluster']

    def get_bindnetaddr_list(self):
        node = self.config['node'][0]
        ips = node['heartbeat_line']
        lst = []
        for ip in ips:
            ip_list = ip.split(".")
            lst.append(f"{'.'.join(ip_list[:3])}.0")
        return lst

    def get_bindnetaddr(self):
        bindnetaddr = self.config['bindnetaddr']
        return bindnetaddr

    def get_interface(self):
        bindnetaddr_list = self.get_bindnetaddr_list()
        interface_list = []
        ringnumber = 1
        for bindnetaddr in bindnetaddr_list[1:]:
            interface = "interface {\n\tringnumber: %s\n\tbindnetaddr: %s\n\tmcastport: 5407\n\tttl: 1\n}" % (
                ringnumber, bindnetaddr)
            interface = FileEdit.add_data_to_head(interface, '\t')
            interface_list.append(interface)
            ringnumber += 1
        return "\n".join(interface_list)

    def get_nodelist_2(self):
        str_node_all = ""
        hostname_list = []
        id_list = []
        for hostname in self.config['node']:
            hostname_list.append(hostname['name'])
            id_list.append(hostname['id'])
        for node, hostname, name_id in zip(self.config['node'], hostname_list, id_list):
            dict_node = {}
            str_node = "node "
            index = 0
            for ip in node["heartbeat_line"]:
                dict_node.update({f"ring{index}_addr": ip})
                index += 1
            dict_node.update({'name': hostname})
            dict_node.update({'nodeid': name_id})
            str_node += json.dumps(dict_node, indent=4, separators=(',', ': '))
            str_node = FileEdit.remove_comma(str_node)
            str_node_all += str_node + '\n'      #####
        str_node_all = FileEdit.add_data_to_head(str_node_all, '\t')
        str_nodelist = "nodelist {\n%s\n}" % str_node_all
        return str_nodelist

    def get_nodelist_3(self):
        str_node_all = ""
        hostname_list = []
        id_list = []
        for hostname in self.config['node']:
            hostname_list.append(hostname['name'])
            id_list.append(hostname['id'])
        for node, hostname, name_id in zip(self.config['node'], hostname_list, id_list):
            dict_node = {}
            str_node = "node "
            index = 0
            for ip in node["heartbeat_line"]:
                dict_node.update({f"ring{index}_addr": ip})
                index += 1
            dict_node.update({'name': hostname})
            dict_node.update({'nodeid': name_id})
            str_node += json.dumps(dict_node, indent=4, separators=(',', ': '))
            str_node = FileEdit.remove_comma(str_node)
            str_node_all += str_node + '\n'
        str_node_all = FileEdit.add_data_to_head(str_node_all, '\t')
        str_nodelist = "nodelist {\n%s\n}" % str_node_all
        return str_nodelist
