import json
import random
import os
from pynput import keyboard
from dotenv import load_dotenv
import threading

load_dotenv()

class MinecraftControlChanger:
    def __init__(self):
        self.keys_to_change = [
            "key_key.jump",
            "key_key.sneak",
            "key_key.sprint",
            "key_key.left",
            "key_key.right",
            "key_key.back",
            "key_key.forward",
            "key_key.attack",
            "key_key.pickItem",
            "key_key.use",
            "key_key.drop",
            "key_key.hotbar.1",
            "key_key.hotbar.2",
            "key_key.hotbar.3",
            "key_key.hotbar.4",
            "key_key.hotbar.5",
            "key_key.hotbar.6",
            "key_key.hotbar.7",
            "key_key.hotbar.8",
            "key_key.hotbar.9",
            "key_key.inventory",
            "key_key.swapOffhand",
            "key_key.screenshot",
            "key_key.smoothCamera",
            "key_key.togglePerspective",
        ]
        
        # available keys for randomization (excluding some problematic ones)
        self.available_keys = [
            "key.keyboard.q", "key.keyboard.w", "key.keyboard.e", "key.keyboard.r", 
            "key.keyboard.t", "key.keyboard.y", "key.keyboard.u", "key.keyboard.i", 
            "key.keyboard.o", "key.keyboard.p", "key.keyboard.a", "key.keyboard.s", 
            "key.keyboard.d", "key.keyboard.f", "key.keyboard.g", "key.keyboard.h", 
            "key.keyboard.j", "key.keyboard.k", "key.keyboard.l", "key.keyboard.z", 
            "key.keyboard.x", "key.keyboard.c", "key.keyboard.v", "key.keyboard.b", 
            "key.keyboard.n", "key.keyboard.m", "key.keyboard.space", 
            "key.keyboard.left.shift", "key.keyboard.right.shift", 
            "key.keyboard.left.control", "key.keyboard.right.control", 
            "key.keyboard.left.alt", "key.keyboard.right.alt", 
            "key.keyboard.tab", "key.keyboard.capslock", "key.keyboard.f1", 
            "key.keyboard.f2", "key.keyboard.f3", "key.keyboard.f4", 
            "key.keyboard.f5", "key.keyboard.f6", "key.keyboard.f7", 
            "key.keyboard.f8", "key.keyboard.f9", "key.keyboard.f10", 
            "key.keyboard.f12", "key.keyboard.1", "key.keyboard.2", 
            "key.keyboard.3", "key.keyboard.4", "key.keyboard.5", 
            "key.keyboard.6", "key.keyboard.7", "key.keyboard.8", 
            "key.keyboard.9", "key.keyboard.0", "key.keyboard.insert", 
            "key.keyboard.home", "key.keyboard.pageup", 
            "key.keyboard.pagedown", "key.mouse.left", "key.mouse.right", 
            "key.mouse.middle", "key.mouse.4", "key.mouse.5"
        ]
        
        self.config_path = os.getenv("DIRECTORY_PATH")
        self.is_changing = False
    
    def get_random_key_mapping(self):
        """Generate random key mappings"""
        mapping = self.available_keys
        random.shuffle(mapping)
        
        return mapping[:len(self.keys_to_change)]
    
    def load_current_settings(self):
        """Load current settings from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as file:
                    return json.load(file)
            else:
                print(f"Warning: Config file not found at {self.config_path}")
        except json.JSONDecodeError:
            print("Error: Config file is not valid JSON.")
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def change_controls(self, new_mapping=[]):
        """Change all movement controls"""
        if self.is_changing:
            print("Already changing controls, please wait...")
            return
        
        self.is_changing = True
        
        try:
            print("\n" + "="*50)
            print("Changing Minecraft controls, please wait..")
            print("="*50)
            
            # load ALL current settings
            standard_settings = self.load_current_settings()
            
            # get new random mappings
            new_mapping = self.get_random_key_mapping()
            
            with open("controls.txt", "w") as txt:
                txt.write("="*50)
                txt.write("\nMINECRAFT CONTROLS\n")
                txt.write("="*50)
                txt.write("\n\n")
            
            # change controls
            success_count = 0
            for i, current_key in enumerate(self.keys_to_change):
                if i < len(new_mapping):
                    new_key = new_mapping[i]
                    standard_settings[current_key] = new_key
                    print(f"Changing {current_key} to {new_key}")
                    success_count += 1
                    
                    with open("controls.txt", "a") as txt:
                        txt.write(f"{current_key[8:]}: {new_key[4:]}\n")
                    
            # write ALL settings back to file
            with open(self.config_path, "w", encoding='utf-8') as file:
                json.dump(standard_settings, file, indent=2)
                file.flush()  # ensure data is written immediately
            
            print(f"\n✓ Successfully changed {success_count}/{len(self.keys_to_change)} controls! You can now run Minecraft.")
            print("Press F2 again to change controls!")
            
        except Exception as e:
            print(f"Error during control change: {e}")
            
        finally:
            self.is_changing = False

def main():
    print("="*60)
    print("MINECRAFT 1.16.1 CONTROL CHANGER - BUTTON TRIGGERED")
    print("="*60)
    print("INSTRUCTIONS:")
    print("1. Locate your 'standardsettings.json' file (can be somewhere in ../.minecraft/config/)")
    print("2. Copy the file path to 'standardsettings.json' (e.g., ../.minecraft/.config/standardsettings.json)")
    print("3. Paste the file path to the 'DIRECTORY_PATH' variable in .env")
    print("4. Make sure your Minecraft is CLOSED before running the script")
    print("="*60)
    
    changer = MinecraftControlChanger()
    
    def on_press(key):
        """Handle key presses"""
        try:
            if key == keyboard.Key.f2:
                # start control change in a separate thread to not block key listener
                if not changer.is_changing:
                    threading.Thread(target=changer.change_controls, daemon=True).start()
                    
            elif key == keyboard.Key.f3:
                # exit program
                print("\nExiting Minecraft 1.16.1 Control Changer...")
                return False  # this will stop the listener
                
        except AttributeError:
            pass
    
    # start listening for key presses
    with keyboard.Listener(on_press=on_press) as listener:
        print("\nHotkeys active:")
        print("F2 - Randomize controls")
        print("F3 - Exit program")
        print("\nWaiting for key presses...")
        
        listener.join()

if __name__ == "__main__":
    # check if required packages are installed
    try:
        import pynput
        import dotenv
    except ImportError:
        print("Error: Required packages not installed.")
        print("Please install them with: pip install -r requirements.txt")
        exit(1)
    
    main()