import control

corosync_config = control.CorosyncConsole()
print('Start to synchronised time')
corosync_config.sync_time()
print('Start to set up corosync')
corosync_config.corosync_conf_change()
print('Start to restart corosync')
corosync_config.restart_corosync()
corosync_config.print_corosync()
