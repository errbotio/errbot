import os
import paramiko

path_to_priv_key_file = ''
log_filename = ''
server = ''
username = ''

privkey = paramiko.RSAKey.from_private_key_file(path_to_priv_key_file)
ssh = paramiko.SSHClient()
paramiko.util.log_to_file(log_filename)
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# In case the server's key is unknown,
# we will be adding it automatically to the list of known hosts
ssh.load_host_keys(os.path.expanduser(os.path.join("~", ".ssh", "known_hosts")))
# Loads the user's local known host file.
ssh.connect(server, username=username, pkey=privkey)
ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command('ls /tmp')
print("output", ssh_stdout.read())
error = ssh_stderr.read()
print("err", error, len(error))

# Transfering files to and from the remote machine
# sftp = ssh.open_sftp()
# sftp.get(remote_path, local_path)
# sftp.put(local_path, remote_path)
# sftp.close()
ssh.close()
