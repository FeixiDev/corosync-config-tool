import utils

corosync_conf_path = '/etc/corosync/corosync.conf'
original_attr = {'cluster_name': 'debian',
                 'bindnetaddr': '127.0.0.1'}
interface_pos = 'crypto_hash: none'
nodelist_pos = "logging {"
quorum_pos = "        provider: corosync_votequorum"


def check_corosync(ssh_conn=None):
    cmd = f'corosync -v'
    result = utils.exec_cmd(cmd, ssh_conn)
    return result


def check_corosync_config(ssh_conn=None):
    cmd = f'corosync-cfgtool -s'
    result = utils.exec_cmd(cmd, ssh_conn)
    return result


def restart_corosync(ssh_conn=None):
    if ssh_conn is None:
        return

    cmd = f'systemctl restart corosync'
    result = utils.exec_cmd(cmd, ssh_conn)
    return result


def backup_corosync(ssh_conn=None):
    cmd = f'cp /etc/corosync/corosync.conf /etc/corosync/corosync.confbak'
    result = utils.exec_cmd(cmd, ssh_conn)
    return result


def sync_time(ssh_conn=None):
    cmd = 'sudo ntpdate -u cn.ntp.org.cn'
    result = utils.exec_cmd(cmd, ssh_conn)
    return result


def change_corosync2_conf(cluster_name, bindnetaddr, bindnetaddr_list, interface, nodelist, ssh_conn=None):
    logging_content = '''
        syslog_facility: daemon
        timestamp: on
    '''
    quorum_content = '        expected_votes: 2'
    editor = utils.FileEdit(corosync_conf_path) 
    editor.replace_data(f"cluster_name: {original_attr['cluster_name']}", f"cluster_name: {cluster_name}")
    editor.replace_data(f"bindnetaddr: {original_attr['bindnetaddr']}", f"bindnetaddr: {bindnetaddr}")
    interface_content = f'''
        interface {{
            ringnumber: 0
            bindnetaddr: {bindnetaddr}
            mcastport: 5405
            ttl: 1
        }}
    '''
    if "interface" not in editor.data:
        editor.replace_data(f"crypto_hash: none", f"crypto_hash: none\n{interface_content}")

    # editor.insert_data(interface, anchor=interface_pos, type='under')
    
    editor.insert_data(nodelist, anchor=nodelist_pos, type='above')
    if len(bindnetaddr_list) > 1:
        editor.insert_data(f'\trrp_mode: passive', anchor='        # also set rrp_mode.', type='under')

    # 移动 syslog_facility: daemon 和 timestamp: on 到 logging 部分
    if logging_content not in editor.data:
        editor.replace_data(f"to_syslog: yes", f"to_syslog: yes\n{logging_content}")

    # 移动 expected_votes: 2 到 quorum 部分
    if quorum_content not in editor.data:
        editor.replace_data(f"provider: corosync_votequorum", f"provider: corosync_votequorum\n{quorum_content}")

    utils.exec_cmd(f'echo "{editor.data}" > {corosync_conf_path}', ssh_conn)


def change_corosync3_conf(cluster_name, nodelist, ssh_conn=None):
    editor = utils.FileEdit(corosync_conf_path)

    editor.replace_data(f"cluster_name: {original_attr['cluster_name']}", f"cluster_name: {cluster_name}")
    editor.insert_data("        expected_votes: 2", anchor=quorum_pos, type='under')
    editor.insert_data(nodelist, anchor=nodelist_pos, type='above')

    utils.exec_cmd(f'echo "{editor.data}" > {corosync_conf_path}', ssh_conn)

