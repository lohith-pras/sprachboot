import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path
import shutil

def print_step(msg):
    print(f"\n🚀 {msg}")

def check_command(command, name, install_url):
    if not shutil.which(command):
        print(f"❌ Error: '{name}' is not installed.")
        print(f"   Please install it from: {install_url}")
        return False
    return True

def main():
    root_dir = Path(__file__).parent.absolute()
    env_file = root_dir / ".env"
    env_example = root_dir / ".env.example"
    
    # 1. First-time setup / Environment Variables
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            print_step("First run — created .env from .env.example.")
            print("   No need to edit it: you'll enter your OpenRouter API key")
            print("   in the app's onboarding screen on first launch.")
        else:
            print("❌ Error: .env.example not found.")
            sys.exit(1)
            
    # Always keep frontend/.env.local in sync with root .env
    frontend_env = root_dir / "frontend" / ".env.local"
    shutil.copy(env_file, frontend_env)
        
    # 2. Check Prerequisites
    print_step("Checking prerequisites...")
    ready = True
    ready &= check_command("node", "Node.js", "https://nodejs.org/")
    ready &= check_command("npm", "npm", "https://nodejs.org/")
    ready &= check_command("uv", "uv", "https://docs.astral.sh/uv/getting-started/installation/ (or simply run 'pip install uv')")
    
    if not ready:
        sys.exit(1)
        
    print("✅ All prerequisites installed.")

    # 3. Sync backend dependencies using uv
    print_step("Syncing backend dependencies...")
    backend_dir = root_dir / "backend"
    subprocess.run(["uv", "sync"], cwd=backend_dir, check=True)

    # 4. Install frontend dependencies if needed
    frontend_dir = root_dir / "frontend"
    if not (frontend_dir / "node_modules").exists():
        print_step("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    else:
        print_step("Frontend dependencies already installed.")

    # 5. Start Servers
    print_step("Starting Frontend and Backend servers...")
    
    try:
        backend_process = subprocess.Popen(
            ["uv", "run", "python", "run_server.py"],
            cwd=backend_dir
        )
        
        frontend_process = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=frontend_dir
        )
        
        print_step("Waiting for servers to start...")
        time.sleep(4)
        
        print_step("Opening browser to http://localhost:3000...")
        webbrowser.open("http://localhost:3000")
        
        print("\n✅ SprachBoot is running!")
        print("Press Ctrl+C in this terminal to stop both servers.\n")
        
        # Keep the script running to hold the processes
        backend_process.wait()
        frontend_process.wait()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("Goodbye!")

if __name__ == "__main__":
    main()
