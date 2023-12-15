import time
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
        #for node in self.cluster['node']:
        #    if local_ip == node['ip']:
        self.list_ssh.append(None)
        #    else:
                # ssh_conn = utils.SSHConn(host=node['ip'], password=node['ssh_password'])
        #        self.list_ssh.append(None)

class CorosyncConsole(object):
    def __init__(self):
        self.conn = Connect()

    def sync_time(self):
        for ssh in self.conn.list_ssh:
            result = corosync_cmds.sync_time(ssh)
            if isinstance(result, bytes):
                result = result.decode('utf-8')
            if "no server" in result:
                print(result)
                sys.exit()

    def corosync_conf_change(self):
        cluster_name = self.conn.conf_file.get_cluster_name()
        bindnetaddr = self.conn.conf_file.get_bindnetaddr()
        bindnetaddr_list = self.conn.conf_file.get_bindnetaddr_list()
        interface = self.conn.conf_file.get_interface()
        nodelist_2 = self.conn.conf_file.get_nodelist_2()
        nodelist_3 = self.conn.conf_file.get_nodelist_3()

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

    def restart_corosync(self):
        try:
            for ssh in self.conn.list_ssh:
                corosync_cmds.restart_corosync(ssh)
        except timeout_decorator.timeout_decorator.TimeoutError:
            print('Restarting corosync service timed out')
            sys.exit()

    def print_corosync(self):
        time.sleep(5)
        for ssh in self.conn.list_ssh:
            result = corosync_cmds.check_corosync_config(ssh)
            print("-----------------------------")
            print(f"{result}")
