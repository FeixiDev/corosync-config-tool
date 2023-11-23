import argparse
import control

def main():
    parser = argparse.ArgumentParser(description="corosync_configuration_tool")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")

    args = parser.parse_args()

    if args.version:
        print("corosync-config-tool version: v1.0.0")
        return

    corosync_config = control.CorosyncConsole()
    print('Start to synchronised time')
    corosync_config.sync_time()
    print('Start to set up corosync')
    corosync_config.corosync_conf_change()
    print('Start to restart corosync')
    corosync_config.restart_corosync()
    corosync_config.print_corosync()

if __name__ == "__main__":
    main()
