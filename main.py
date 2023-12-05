import argparse
import control
import sys

def main():
    parser = argparse.ArgumentParser(description=" vsdscoroconf")
    parser.add_argument("-v", "--version", action="store_true", help="Show version information")

    args = parser.parse_args()

    if args.version:
        print("vsdscoroconf version: v1.0.0")
        sys.exit()

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
