import fcntl
import socket
import struct
import time

import paramiko
import corosync_cmds
import utils
import re
import sys
import timeout_decorator


class Connect(object):
    """
    通过ssh连接节点，生成连接对象的列表
    """
    list_ssh = []
    list_hostname = []

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            Connect._instance = super().__new__(cls)
            Connect._instance.conf_file = utils.ConfFile()
            Connect._instance.cluster = Connect._instance.conf_file.config
            Connect.get_ssh_conn(Connect._instance)
        return Connect._instance

    def get_ssh_conn(self):
        local_ip = utils.get_host_ip()
        # for node in self.cluster.get('node', []):
        #     if local_ip:
        self.list_ssh.append(None)
        #     else:
        #         ssh_conn = utils.SSHConn(host=node.get('heartbeat_line')[0], username=node.get('username', ''), password=node.get('password', ''))
        #         self.list_ssh.append(ssh_conn)

class CorosyncConsole(object):
    def __init__(self):
        self.conf_file = utils.ConfFile()

    def sync_time(self):
        # for ssh in self.conn.list_ssh:
        result = corosync_cmds.sync_time(None)
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        if "no server" in result:
            print(result)
            sys.exit()

    def set_remote_node(self):
        nodes = self.conf_file.get_nodes_info()  # 获取节点信息

        # 获取当前节点的所有 IP 地址
        current_node_ips = self.get_local_ip_addresses()

        # 定义一个数组来存储所有的 nodeid
        node_ids = []
        for node in nodes:
            node_ip = node.get('heartbeat_line')[0]
            # print(f"node_ip: {node_ip}")
            if node_ip in current_node_ips:
                # 跳过当前节点
                continue
            node_id = node.get('id')
            node_ids.append(node_id)  # 将 nodeid 添加到数组中

        node_ids.sort()  # 将 nodeid 从小到大排序
        # print(f"node_ids: {node_ids}")

        try:
            for node in nodes:
                node_name = node.get('name')
                node_ip = node.get('heartbeat_line')[0]  # 假设使用第一个 IP 进行连接

                if node_ip in current_node_ips:
                    # 跳过当前节点
                    continue
            
                # 创建SSH客户端
                ssh_client = paramiko.SSHClient()
                ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                # 连接远程节点
                ssh_client.connect(node_ip, username='root')
                
                # """使用SSH连接远程节点，将本地配置文件复制到所有节点"""
                # # 读取本地配置文件内容
                # with open(local_file, 'r', encoding='utf-8') as f:
                #     local_config_content = f.read()

                # # 将本地配置文件内容写入远程节点配置文件
                # remote_file = f'/data/corosync-config-tool/{local_file}'  # 远程节点配置文件路径
                # with ssh_client.open_sftp().file(remote_file, 'w') as remote_f:
                #     remote_f.write(local_config_content)

                """使用SSH连接远程节点，备份远程节点的 corosync.conf 文件"""
                if node_ids:
                    # print("111111")
                    backup_file = f'/etc/corosync/corosync_{"_".join(map(str, node_ids))}.conf.vsds.bak'

                    # 执行备份命令
                    cmd = f'cp /etc/corosync/corosync.conf {backup_file}'
                    stdin, stdout, stderr = ssh_client.exec_command(cmd)
                    exit_status = stdout.channel.recv_exit_status()

                    if exit_status == 0:
                        log_data = f"{node_name}: Backup completed on {node_name} ({node_ip})"
                        utils.Log().logger.info(log_data)
                    else:
                        log_data = f"{node_name}: Failed to backup on {node_name} ({node_ip}). Error: {stderr.read().decode()}"
                        utils.Log().logger.info(log_data)

                log_data = f"{node_name}: Config file copied to {node_name} ({node_ip}) successfully."
                utils.Log().logger.info(log_data)
                print(f'{node_name}: Start to set up corosync')

                """在远程节点上修改corosync配置文件"""
                # 在本地获取配置数据
                cluster_name = self.conf_file.get_cluster_name()
                bindnetaddr = self.conf_file.get_bindnetaddr()
                bindnetaddr_list = self.conf_file.get_bindnetaddr_list()
                interface = self.conf_file.get_interface()
                nodelist_2 = self.conf_file.get_nodelist_2()
                nodelist_3 = self.conf_file.get_nodelist_3()
                
                # 在远程节点上执行相应的配置修改
                if bindnetaddr is None:
                    corosync_cmds.change_corosync3_conf(
                        cluster_name=cluster_name,
                        nodelist=nodelist_3,
                        ssh_conn=ssh_client,  # 传递 SSH 客户端到远程修改方法
                    )
                    
                elif bindnetaddr is not None:
                    corosync_cmds.change_corosync2_conf(
                        cluster_name=cluster_name,
                        bindnetaddr_list=bindnetaddr_list,
                        bindnetaddr=bindnetaddr,
                        interface=interface,
                        nodelist=nodelist_2,
                        ssh_conn=ssh_client,  # 传递 SSH 客户端到远程修改方法
                    )

                print(f'{node_name}: Start to restart corosync')

                self.restart_corosync(ssh_client)
                self.print_corosync(ssh_client)

                # 关闭连接
                ssh_client.close()

        except Exception as e:
            print(f"Failed to execute on {node_name} ({node_ip}): {str(e)}")
    
    def get_local_ip_addresses(self):
        """获取本地所有 IP 地址"""
        ip_addresses = []
        try:
            # 获取所有网络接口的名称
            ifnames = [i[1] for i in socket.if_nameindex()]

            for ifname in ifnames:
                try:
                    # 获取指定接口的 IP 地址
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    ifaddr = fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s', ifname[:15].encode('utf-8')))
                    ip_addresses.append(socket.inet_ntoa(struct.unpack('4s', ifaddr[20:24])[0]))
                except Exception:
                    pass
        except Exception:
            pass

        return ip_addresses

    def corosync_conf_change(self):
        cluster_name = self.conf_file.get_cluster_name()
        bindnetaddr = self.conf_file.get_bindnetaddr()
        bindnetaddr_list = self.conf_file.get_bindnetaddr_list()
        interface = self.conf_file.get_interface()
        nodelist_2 = self.conf_file.get_nodelist_2()
        nodelist_3 = self.conf_file.get_nodelist_3()

        # for ssh in self.conn.list_ssh:
        corosync_cmds.backup_corosync()
            # result = corosync_cmds.check_corosync(ssh)
            # if isinstance(result, bytes):
            #     result = result.decode('utf-8')
            # match = re.search(r'\d+', result)
            # version = match.group(0)
        if bindnetaddr == None:
            corosync_cmds.change_corosync3_conf(
                cluster_name=cluster_name,
                nodelist=nodelist_3,
            )
        elif bindnetaddr is not None:
            corosync_cmds.change_corosync2_conf(
                cluster_name=cluster_name,
                bindnetaddr_list=bindnetaddr_list,
                bindnetaddr=bindnetaddr,
                interface=interface,
                nodelist=nodelist_2,
            )

    def restart_corosync(self, ssh_conn=None):
        try:
            time.sleep(5)
            corosync_cmds.restart_corosync(ssh_conn)
        except timeout_decorator.timeout_decorator.TimeoutError:
            print('Restarting corosync service timed out')
            sys.exit()

    def print_corosync(self, ssh_conn=None):
        time.sleep(5)
        # for ssh in self.conn.list_ssh:
        result = corosync_cmds.check_corosync_config(ssh_conn)
        print("-----------------------------")
        if ssh_conn:
            # 提取标准输出
            stdout_data = result[1].read().decode('utf-8')
            utils.Log().logger.info(stdout_data)
        else:
            print(result)
