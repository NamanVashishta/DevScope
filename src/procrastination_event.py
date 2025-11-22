import tkinter as tk
from tkinter import messagebox
import threading
import sys


class ProcrastinationEvent:
    def show_popup(self, ai_message, pledge_message):
        # Suppress Tcl async errors by ensuring proper cleanup
        try:
            root = tk.Tk()
            root.withdraw()  # Hide initially to avoid flicker
            
            # Create popup (this sets up geometry and everything)
            app = FocusPopup(root, ai_message, pledge_message)
            
            # Show and focus
            root.deiconify()
            root.lift()
            root.attributes('-topmost', True)
            root.focus_force()
            
            # Try grab_set but don't let it block clicks
            try:
                root.grab_set_global()  # Global grab might work better
            except:
                try:
                    root.grab_set()  # Fallback to normal grab
                except:
                    pass  # If grab doesn't work, that's okay
            
            root.mainloop()
            
            # Cleanup
            try:
                root.grab_release()
            except:
                pass
            try:
                root.quit()
            except:
                pass
            try:
                root.destroy()
            except:
                pass
        except Exception as e:
            print(f"Error showing popup: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: just print the message
            print(f"\n{'='*60}")
            print(f"AURA ALERT: {ai_message}")
            if pledge_message:
                print(f"PLEDGE: {pledge_message}")
            print(f"{'='*60}\n")

    def play_countdown(self, count, brief_message="You have 10 seconds to close it."):
        try:
            root = tk.Tk()
            root.title("Aura - Countdown")
            root.attributes('-topmost', True)
            root.configure(bg='#0a0a15')
            root.resizable(False, False)

            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()

            # Modern compact countdown window
            window_width = 500
            window_height = 350

            position_top = int(screen_height / 2 - window_height / 2)
            position_right = int(screen_width / 2 - window_width / 2)

            root.geometry(f'{window_width}x{window_height}+{position_right}+{position_top}')

            # Main container with modern design
            container = tk.Frame(root, bg='#0a0a15')
            container.pack(expand=True, fill=tk.BOTH, padx=30, pady=30)

            # Top section - Aura branding
            top_frame = tk.Frame(container, bg='#0a0a15')
            top_frame.pack(fill=tk.X)

            aura_label = tk.Label(
                top_frame,
                text="⚡ AURA",
                font=('Arial', 24, 'bold'),
                fg='#4a9eff',
                bg='#0a0a15'
            )
            aura_label.pack()

            # Message label
            message_label = tk.Label(
                container, 
                text=brief_message, 
                font=('Arial', 14), 
                fg='#d1d5db', 
                bg='#0a0a15',
                wraplength=400,
                justify=tk.CENTER
            )
            message_label.pack(pady=20)

            # Countdown number - large and prominent
            count_frame = tk.Frame(container, bg='#0a0a15')
            count_frame.pack(expand=True, fill=tk.BOTH)

            count_label = tk.Label(
                count_frame, 
                text=str(count),
                font=('Arial', 120, 'bold'), 
                fg='#ef4444', 
                bg='#0a0a15'
            )
            count_label.pack(expand=True)

            # Progress indicator bar
            progress_frame = tk.Frame(container, bg='#1f2937', height=8)
            progress_frame.pack(fill=tk.X, pady=10)
            progress_frame.pack_propagate(False)

            progress_bar = tk.Frame(progress_frame, bg='#ef4444', height=8)
            progress_bar.pack(side=tk.LEFT)

            def countdown(start_count):
                if start_count > 0:
                    # Update count
                    count_label['text'] = start_count
                    
                    # Update progress bar
                    progress_width = int((count - start_count + 1) / count * window_width)
                    progress_bar.config(width=progress_width)
                    
                    # Change color as time runs out
                    if start_count <= 3:
                        count_label['fg'] = '#ff6666'
                        progress_bar.config(bg='#ff6666')
                    
                    root.after(1000, countdown, start_count - 1)
                else:
                    count_label['text'] = "TIME'S UP!"
                    count_label['fg'] = '#ef4444'
                    count_label['font'] = ('Arial', 48, 'bold')
                    progress_bar.config(bg='#ef4444', width=window_width)
                    root.after(800, root.destroy)  # Auto-close after showing "Time's Up"

            countdown(count)
            root.mainloop()
            root.quit()
            root.destroy()
        except Exception as e:
            print(f"Error showing countdown: {e}")
            import traceback
            traceback.print_exc()
            # Fallback: just print countdown
            import time
            for i in range(count, 0, -1):
                print(f"⏰ {i} seconds remaining...")
                time.sleep(1)
            print("⏰ Time's Up!")


class FocusPopup:
    def __init__(self, master, ai_message, pledge_message):
        self.master = master
        self.master.title("Aura - Focus Reminder")
        
        # Make it a centered modal window instead of fullscreen
        self.master.attributes('-topmost', True)
        self.master.configure(bg='#0a0a15')
        self.master.resizable(False, False)
        
        # Center the window on screen
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        window_width = 900
        window_height = 700
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.master.geometry(f'{window_width}x{window_height}+{x}+{y}')
        
        # Main container with padding
        main_container = tk.Frame(master, bg='#0a0a15')
        main_container.pack(expand=True, fill=tk.BOTH, padx=40, pady=40)
        
        # Top section - AURA branding
        top_section = tk.Frame(main_container, bg='#0a0a15')
        top_section.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            top_section,
            text="⚡ AURA",
            font=("Arial", 48, "bold"),
            bg='#0a0a15',
            fg='#4a9eff'
        )
        title_label.pack()

        subtitle_label = tk.Label(
            top_section,
            text="Focus Reminder",
            font=("Arial", 20),
            bg='#0a0a15',
            fg='#9ca3af'
        )
        subtitle_label.pack(pady=(10, 0))

        # Divider
        divider = tk.Frame(main_container, bg='#1f2937', height=2)
        divider.pack(fill=tk.X, pady=25)

        # AI message section
        message_section = tk.Frame(main_container, bg='#0a0a15')
        message_section.pack(fill=tk.BOTH, expand=True, pady=20)
        
        self.ai_message_label = tk.Label(
            message_section,
            text=ai_message if ai_message else "You are procrastinating. Please focus on your work.",
            font=("Arial", 16),
            bg='#0a0a15',
            fg='#ffffff',
            wraplength=800,
            justify=tk.CENTER,
            padx=20
        )
        self.ai_message_label.pack(pady=20)

        # Middle section - message and pledge
        middle_section = tk.Frame(main_container, bg='#0a0a15')
        middle_section.pack(fill=tk.BOTH, expand=True, pady=20)

        # Pledge message (shown in a card)
        pledge_text = pledge_message.strip() if pledge_message else "I will focus on my work."
        if len(pledge_text) > 100:
            pledge_text = pledge_text[:100] + "..."
        
        if pledge_text:
            pledge_frame = tk.Frame(middle_section, bg='#16213e', relief=tk.FLAT)
            pledge_frame.pack(fill=tk.X, pady=(0, 30))
            
            pledge_label = tk.Label(
                pledge_frame, 
                text=f'"{pledge_text}"', 
                font=("Arial", 13, "italic"), 
                bg='#16213e', 
                fg='#9ca3af',
                wraplength=750,
                padx=20
            )
            pledge_label.pack(pady=15)

        # Bottom section with button - separate and clearly visible
        button_section = tk.Frame(main_container, bg='#0a0a15')
        button_section.pack(side=tk.BOTTOM, fill=tk.X, pady=(30, 0))

        # Instruction text - make it visible
        instruction_label = tk.Label(
            button_section, 
            text="Press ENTER, ESC, SPACE, or click the button to continue", 
            font=("Arial", 13), 
            bg='#0a0a15', 
            fg='#d1d5db'
        )
        instruction_label.pack(pady=(0, 20))

        # Button - Create it with explicit click handler
        self.acknowledge_button = tk.Button(
            button_section,
            text="✓ I UNDERSTAND - CONTINUE",
            font=("Arial", 22, "bold"),
            bg='#4a9eff',
            fg='#ffffff',
            activebackground='#5ab0ff',
            activeforeground='#ffffff',
            relief=tk.RAISED,
            bd=6,
            padx=60,
            pady=35,
            cursor='hand2',
            command=self.acknowledge,
            borderwidth=6,
            width=28,
            height=2,
            highlightthickness=3,
            highlightbackground='#ffffff',
            highlightcolor='#ffffff',
            takefocus=1
        )
        
        # Explicit click binding BEFORE packing
        def on_button_click(event=None):
            print("Button clicked!")
            self.acknowledge()
        
        self.acknowledge_button.config(command=on_button_click)
        self.acknowledge_button.pack(pady=(0, 15))
        
        # Bind all possible click events
        self.acknowledge_button.bind('<Button-1>', on_button_click)
        self.acknowledge_button.bind('<ButtonRelease-1>', on_button_click)
        self.acknowledge_button.bind('<Button-3>', on_button_click)  # Right click too
        
        # Hover effects
        self.acknowledge_button.bind('<Enter>', lambda e: self.acknowledge_button.config(bg='#5ab0ff', relief=tk.SUNKEN))
        self.acknowledge_button.bind('<Leave>', lambda e: self.acknowledge_button.config(bg='#4a9eff', relief=tk.RAISED))
        
        # Bind keys - these should always work
        self.master.bind('<Return>', lambda e: (print("Enter pressed"), self.acknowledge(e)))
        self.master.bind('<Escape>', lambda e: (print("Escape pressed"), self.acknowledge(e)))
        self.master.bind('<space>', lambda e: (print("Space pressed"), self.acknowledge(e)))
        self.master.bind_all('<Return>', lambda e: self.acknowledge(e))
        self.master.bind_all('<Escape>', lambda e: self.acknowledge(e))
        self.master.bind_all('<space>', lambda e: self.acknowledge(e))
        
        # Force all updates and ensure button is on top
        self.master.update_idletasks()
        button_section.update_idletasks()
        self.acknowledge_button.update_idletasks()
        self.acknowledge_button.lift()
        self.acknowledge_button.focus_set()
        self.master.update()
        self.master.focus_force()

    def acknowledge(self, event=None):
        """Simplified - just acknowledge and continue"""
        print("Acknowledged - closing popup")
        try:
            self.master.quit()
        except:
            pass
        try:
            self.master.destroy()
        except:
            pass


if __name__ == "__main__":
    procrastination_event = ProcrastinationEvent()
    procrastination_event.show_popup("You are procrastinating. Please focus on your work.", "I will focus on my work.")
    procrastination_event.play_countdown(10)
