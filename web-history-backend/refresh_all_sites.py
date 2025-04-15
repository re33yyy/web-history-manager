# refresh_all_sites.py
import os
import sys
import importlib.util

# Function to run a Python script by name
def run_script(script_name):
    print(f"\n======= Running {script_name} =======")
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    
    # Import and execute the script
    try:
        spec = importlib.util.spec_from_file_location(script_name, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"Successfully ran {script_name}")
    except Exception as e:
        print(f"Error running {script_name}: {e}")

# Run all the site crawler scripts
if __name__ == "__main__":
    scripts = [
        "save_verge_articles.py",
        "save_hackernews_articles.py",
        "save_bbc_articles.py"
    ]
    
    for script in scripts:
        run_script(script)
    
    print("\nAll sites refreshed successfully!")