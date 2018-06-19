from remotelogin.oper_sys.linux.shellcommands import LinuxShellCmds

# TODO: implement base64 upload of base64.sh or write of file on system

class BusyBoxCmds(LinuxShellCmds):

    HAS_BASE64 = False

    def base64(self, file):
        raise NotImplementedError

    def base64_encode_to_file(self, file_decoded, base64file):
        raise NotImplementedError

    def base64_decode_to_file(self, base64file, file_decoded):
        raise NotImplementedError

    def netstat(self, protocol='tcp', family=''):
        proto = ' -t t' if protocol == 'tcp' else ' -t u' if protocol == 'udp' else ''
        return 'netstat -an' + proto

    def restart(self, **kwargs):
        return 'sync; sync; sync; busybox reboot'

    def snoop(selfself, *args):
        return "/sdcard_ddr/util/tcpdump " + ' '.join(str(a) for a in args)

    def find_process(self, process_name):
        return "ps | grep {} | grep -v grep | awk '{{print $1}}'".format(process_name)

    def kill_process(self, process_name):
        return self.find_process(process_name) + " | xargs kill -9"

    def get_ps_with_args(self):
        return 'ps'

    def get_pid_and_cmd_from_ps(self):
        return 'ps | ' + self.get_fields_from_text(first=5, fields=(1,))

    def list_file(self, file_path):
        return "ls -le {}".format(file_path)


Instance = None


def get_instance():
    global Instance
    if Instance is None:
        Instance = BusyBoxCmds()
    return Instance