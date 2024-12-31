import customtkinter as ctk
import adafruit_fingerprint
import serial
import time
#from PIL import ImageTk, Image
import sqlite3
import threading

uart = serial.Serial("/dev/ttyS1", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Dao Attendance System")
        self.geometry("800x480")
        self.resizable(False, False)
        self.attributes("-fullscreen", True)
        self.config(cursor="none")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.start_font_size = 100
        self.font_size = self.start_font_size
        self.start_opacity = 1.0  # Fully visible
        self.opacity = self.start_opacity


        #self.img1 = ctk.CTkImage(light_image=Image.open("C:\\Users\\andre\\project\\background\\pattern1.jpg"),
        #                          dark_image=Image.open("C:\\Users\\andre\\project\\background\\pattern1.jpg"),
        #                          size=(800, 480))

        self.time_label = ctk.CTkLabel(self, font=("Arial", 20, "bold"), fg_color="transparent")
        self.time_label.place(relx=0.98, rely=0.02, anchor='ne')
        self.update_time()

        self.title_frame = TitleFrame(self, font_size=self.start_font_size)
        self.login_frame = LoginFrame(self)
        self.title_frame.place(relx=0.5, rely=0.45, anchor='center')

        # Schedule the animation to start after 1.5 second
        self.after(1500, self.start_animation)

# ---------------------- Methods ----------------------

    def start_animation(self):
        # Start the fade-out animation process
        self.animate_opacity()

    def animate_opacity(self):
        if self.opacity > 0.1:  # Fade out until 10% visible
            self.opacity -= 0.01
            self.title_frame.update_opacity(self.opacity)
            self.after(5, self.animate_opacity)
        else:
            # After fading out, update the text, reposition, and change font size
            self.title_frame.title_label.configure(text="Please ENTER PIN or\nuse FINGERPRINT to login:", font=("Figtree", 24, "bold"))
            self.login_frame.place(relx=0.5, rely=0.57, anchor='center')
            self.title_frame.place(relx=0.5, rely=0.1, anchor='center')
            self.fade_in()

    def fade_in(self):
        if self.opacity < 1.0:
            self.opacity += 0.01
            self.title_frame.update_opacity(self.opacity)
            self.after(5, self.fade_in)

    def update_time(self):
        current_time = time.strftime("%I:%M %p")
        self.time_label.configure(text=current_time)
        self.after(100, self.update_time)

# ---------------------------------------------------------------

class TitleFrame(ctk.CTkFrame):
    def __init__(self, master, font_size):
        super().__init__(master)
        self.configure(fg_color="transparent")
        self.title_label = ctk.CTkLabel(self, text="WELCOME!", font=("Figtree", font_size, "bold"), text_color="#FFFFFF")
        self.title_label.pack()

    def update_opacity(self, alpha):
        # Simulate opacity by blending between white (#FFFFFF) and black (#000000)
        intensity = int(alpha * 255)
        color = f"#{intensity:02X}{intensity:02X}{intensity:02X}"
        self.title_label.configure(text_color=color)


class LoginFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="transparent")

        self.pin_entry = ctk.CTkEntry(
            self, font=("Figtree", 50, "bold"), width=320, justify='center', show='*', fg_color="transparent"
        )
        self.pin_entry.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        self.create_keypad()

        # Thread control
        self.stop_fingerprint_thread = threading.Event()
        self.fingerprint_thread = threading.Thread(target=self.scan_fingerprint_thread, daemon=True)
        self.fingerprint_thread.start()

    def create_keypad(self):
        self.enter_button = None
        keypad_frame = ctk.CTkFrame(self)
        keypad_frame.grid(row=1, column=0, columnspan=3, pady=(5, 0))

        keypad = [
            "1", "2", "3",
            "4", "5", "6",
            "7", "8", "9",
            "DELETE", "0", "ENTER"
        ]

        for i, key in enumerate(keypad):
            button = ctk.CTkButton(
                keypad_frame,
                text=key,
                font=("Figtree", 30, "bold"),
                fg_color=("#c0392b" if key == "DELETE" else "#009432" if key == "ENTER" else "#95a5a6"),
                text_color="#000000",
                command=lambda k=key: self.append_pin(k)
            )
            button.grid(row=i // 3, column=i % 3, padx=5, pady=5, ipadx=10, ipady=5)
            if key == "ENTER":
                self.enter_button = button
                self.enter_button.configure(state="disabled")  # Disable initially

    def append_pin(self, value):
        current_pin = self.pin_entry.get()
        if value == "DELETE":
            self.pin_entry.delete(len(current_pin) - 1)
        elif value == "ENTER":
            self.enter()
        else:
            if len(current_pin) < 6:
                self.pin_entry.insert('end', value)

        # Enable or disable the enter button based on pin length
        self.enter_button.configure(state="normal" if len(self.pin_entry.get()) == 6 else "disabled")

    def enter(self):
        self.stop_fingerprint_thread.set()
        self.fingerprint_thread.join()
        pin = self.pin_entry.get()
        db = Database()

        try:
            user = db.fetch_one("SELECT id, first_name, last_name, user_type FROM users WHERE pin = ?", (pin,))
        except Exception as e:
            self.master.title_frame.title_label.configure(text="Database Error.", font=("Figtree", 24, "bold"))
            print(f"Error: {e}")
            return
        finally:
            db.close()

        if user:
            user_id, first_name, last_name, user_type = user
            full_name = f"{first_name} {last_name}"
            if user_type == "admin":
                self.master.title_frame.title_label.configure(
                    text=f"Admin {full_name} logged in", font=("Figtree", 24, "bold")
                )
                self.place_forget()
                self.pin_entry.delete(0, 'end')
                AdminFrame(self.master, user_id)
            else:
                self.master.title_frame.title_label.configure(
                    text=f"Welcome {full_name}!", font=("Figtree", 24, "bold")
                )
                self.place_forget()
                self.pin_entry.delete(0, 'end')
                UserFrame(self.master, user_id)
        else:
            self.master.title_frame.title_label.configure(
                text="Invalid PIN. Try again.", font=("Figtree", 24, "bold")
            )
            self.pin_entry.delete(0, 'end')

    def scan_fingerprint_thread(self):
        while not self.stop_fingerprint_thread.is_set():
            fingerprint_id = self.get_fingerprint()
            if fingerprint_id is not None:
                self.master.after(0, self.process_fingerprint, fingerprint_id)

    def get_fingerprint(self):
        try:
            if finger.get_image() == adafruit_fingerprint.OK:
                if finger.image_2_tz(1) == adafruit_fingerprint.OK:
                    if finger.finger_search() == adafruit_fingerprint.OK:
                        return finger.finger_id
        except Exception as e:
            print(f"Fingerprint error: {e}")
        return None

    def process_fingerprint(self, fingerprint_id):

        self.stop_fingerprint_thread.set()
        self.fingerprint_thread.join()

        user_details = self.get_user_by_fingerprint(fingerprint_id)
        if user_details:
            full_name = f"{user_details['first_name']} {user_details['last_name']}"
            if user_details["user_type"] == "admin":
                self.master.title_frame.title_label.configure(
                    text=f"Admin {full_name} logged in", font=("Figtree", 24, "bold")
                )
                self.place_forget()
                AdminFrame(self.master, user_details["id"])
            else:
                self.master.title_frame.title_label.configure(
                    text=f"Welcome {full_name}!", font=("Figtree", 24, "bold")
                )
                self.place_forget()
                UserFrame(self.master, user_details["id"])
        else:
            self.master.title_frame.title_label.configure(
                text="Fingerprint not recognized. Try again.", font=("Figtree", 24, "bold")
            )

    def get_user_by_fingerprint(self, fingerprint_id):
        db = Database()
        try:
            user = db.fetch_one("SELECT * FROM users WHERE finger_id = ?", (fingerprint_id,))
        except Exception as e:
            print(f"Error fetching user by fingerprint: {e}")
            return None
        finally:
            db.close()

        if user:
            return {
                "id": user[0],
                "finger_id": user[1],
                "pin": user[2],
                "first_name": user[3],
                "last_name": user[4],
                "user_type": user[5],
            }
        return None


class AdminFrame(ctk.CTkFrame):
    def __init__(self, master, user_id):
        super().__init__(master)
        self.user_id = user_id  # Store the current user's ID
        self.configure(fg_color="transparent")
        self.create_buttons()
        self.place(relx=0.5, rely=0.55, anchor='center')

    def create_buttons(self):
        self.rowconfigure(0, weight=1)

        buttons = [
            ("Time In", lambda: self.handle_time_action("time-in")),
            ("Time Out", lambda: self.handle_time_action("time-out")),
            ("Log Out", self.log_out),
            ("Admin\nOptions", self.admin_options),
        ]

        for i, (text, command) in enumerate(buttons):
            button = ctk.CTkButton(
                self,
                text=text,
                font=("Figtree", 30, "bold"),
                fg_color="#3498db",
                command=command,
                height=150,
                width=150,
                corner_radius=10,
            )
            button.grid(row=i // 2, column=i % 2, padx=10, pady=10, ipadx=20, ipady=5)

    def handle_time_action(self, action):
        """Handles time-in and time-out actions with interval enforcement."""
        db = Database()
        cursor = db.connection.cursor()

        # Check the last attendance record for this user
        last_record =  cursor.execute(
            """
            SELECT timestamp, type FROM attendance
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (self.user_id,),
        )
        #last_record = cursor.fetchone()
        current_time = datetime.now()

        # Enforce interval if there is a previous record
        if last_record:
            last_timestamp = datetime.fromisoformat(last_record[0])
            last_action = last_record[1]
            time_diff = (current_time - last_timestamp).total_seconds() / 60  # In minutes

            if last_action == action:
                self.master.title_frame.title_label.configure(
                    text=f"You already performed {action.replace('-', ' ')}.\nPlease wait before retrying.",
                    font=("Figtree", 24, "bold"),
                )
                db.close()
                return
            elif time_diff < 5:  # Minimum interval of 5 minutes
                self.master.title_frame.title_label.configure(
                    text=f"Too soon to {action.replace('-', ' ')} again.\nPlease wait {5 - int(time_diff)} minutes.",
                    font=("Figtree", 24, "bold"),
                )
                db.close()
                return

        # Insert the new attendance record
        cursor.execute(
            """
            INSERT INTO attendance (user_id, timestamp, type)
            VALUES (?, ?, ?)
            """,
            (self.user_id, current_time, action),
        )
        db.connection.commit()
        db.close()

        # Update the title to indicate success
        action_text = "Timed in at" if action == "time-in" else "Timed out at"
        self.master.title_frame.title_label.configure(
            text=f"Thank you! {action_text}: \n{current_time.strftime('%Y-%m-%d %I:%M %p')}",
            font=("Figtree", 50, "bold"),
        )
        self.master.title_frame.place(relx=0.5, rely=0.5, anchor='center')
        self.place_forget()
        self.after(3000, self.log_out)  # Automatically log out after 3 seconds

    def log_out(self):
        """Logs out the admin and returns to the login frame."""
        self.master.title_frame.title_label.configure(
            text="Please ENTER PIN or\nuse FINGERPRINT to login:", font=("Figtree", 24, "bold")
        )
        self.master.login_frame.place(relx=0.5, rely=0.57, anchor='center')
        self.master.title_frame.place(relx=0.5, rely=0.1, anchor='center')
        self.place_forget()

        # Restart fingerprint scanning thread
        self.master.login_frame.stop_fingerprint_thread.clear()  # Reset the stop event
        self.master.login_frame.fingerprint_thread = threading.Thread(
            target=self.master.login_frame.scan_fingerprint_thread, daemon=True
        )
        self.master.login_frame.fingerprint_thread.start()


    def admin_options(self):
        """Navigates to the admin options frame."""
        try:
            self.place_forget()
            AdminOptions(self.master)  # Ensure AdminOptions is properly initialized
        except Exception as e:
            self.master.title_frame.title_label.configure(
                text="Error opening Admin Options.", font=("Figtree", 24, "bold")
            )
            print(f"AdminOptions Error: {e}")

class AdminOptions(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="transparent")
        self.create_buttons()
        self.place(relx=0.5, rely=0.55, anchor='center')
        
    def create_buttons(self):
        self.rowconfigure(0, weight=1)

        buttons = [
            ("Enroll", self.enroll),
            ("Delete", self.delete),
            ("Back", self.back),
        ]
    
        for i, (text, command) in enumerate(buttons):
            button = ctk.CTkButton(
                self,
                text=text,
                font=("Figtree", 30, "bold"),
                fg_color="#3498db",
                command=command,
                height=150,
                width=150, 
                corner_radius=10,
            )
            button.grid(row=0, column=i, padx=10, pady=10, ipadx=20, ipady=5)
    
    def enroll(self):
        self.master.title_frame.title_label.configure(text="Enroll New User", font=("Figtree", 24, "bold"))
        self.place_forget()
        EnrollFrame(self.master)

    def delete(self):
        self.master.title_frame.title_label.configure(text="Delete User", font=("Figtree", 24, "bold"))
        self.place_forget()
        DeleteUserFrame(self.master)

    def back(self):
        self.place_forget()
        AdminFrame(self.master)

class UserFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="transparent")
        self.create_buttons()
        self.place(relx=0.5, rely=0.55, anchor='center')
        
    def create_buttons(self):
        self.rowconfigure(0, weight=1)

        buttons = [
            ("Time In", lambda: self.handle_time_action("time-in")),
            ("Time Out", lambda: self.handle_time_action("time-out")),
            ("Log Out", self.log_out),
        ]
    
        for i, (text, command) in enumerate(buttons):
            button = ctk.CTkButton(
                self,
                text=text,
                font=("Figtree", 30, "bold"),
                fg_color="#3498db",
                command=command,
                height=150,
                width=150, 
                corner_radius=10,
            )
            button.grid(row=0, column=i, padx=10, pady=10, ipadx=20, ipady=5)
    
    def handle_time_action(self, action):
        """Handles time-in and time-out actions with interval enforcement."""
        db = Database()
        cursor = db.connection.cursor()

        # Check the last attendance record for this user
        cursor.execute(
            """
            SELECT timestamp, type FROM attendance
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (self.user_id,),
        )
        last_record = cursor.fetchone()
        current_time = datetime.now()

        # Enforce interval if there is a previous record
        if last_record:
            last_timestamp = datetime.fromisoformat(last_record[0])
            last_action = last_record[1]
            time_diff = (current_time - last_timestamp).total_seconds() / 60  # In minutes

            if last_action == action:
                self.master.title_frame.title_label.configure(
                    text=f"You already performed {action.replace('-', ' ')}.\nPlease wait before retrying.",
                    font=("Figtree", 24, "bold"),
                )
                db.close()
                return
            elif time_diff < 5:  # Minimum interval of 5 minutes
                self.master.title_frame.title_label.configure(
                    text=f"Too soon to {action.replace('-', ' ')} again.\nPlease wait {5 - int(time_diff)} minutes.",
                    font=("Figtree", 24, "bold"),
                )
                db.close()
                return

        # Insert the new attendance record
        cursor.execute(
            """
            INSERT INTO attendance (user_id, timestamp, type)
            VALUES (?, ?, ?)
            """,
            (self.user_id, current_time, action),
        )
        db.connection.commit()
        db.close()

        # Update the title to indicate success
        action_text = "Timed in at" if action == "time-in" else "Timed out at"
        self.master.title_frame.title_label.configure(
            text=f"Thank you! {action_text}: \n{current_time.strftime('%Y-%m-%d %I:%M %p')}",
            font=("Figtree", 50, "bold"),
        )
        self.master.title_frame.place(relx=0.5, rely=0.5, anchor='center')
        self.place_forget()
        self.after(3000, self.log_out)  # Automatically log out after 3 seconds

    def log_out(self):
        """Logs out the admin and returns to the login frame."""
        self.master.title_frame.title_label.configure(
            text="Please ENTER PIN or\nuse FINGERPRINT to login:", font=("Figtree", 24, "bold")
        )
        self.master.login_frame.place(relx=0.5, rely=0.57, anchor='center')
        self.master.title_frame.place(relx=0.5, rely=0.1, anchor='center')
        self.place_forget()

        # Restart fingerprint scanning thread
        self.master.login_frame.stop_fingerprint_thread.clear()  # Reset the stop event
        self.master.login_frame.fingerprint_thread = threading.Thread(
            target=self.master.login_frame.scan_fingerprint_thread, daemon=True
        )
        self.master.login_frame.fingerprint_thread.start()


class EnrollFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(fg_color="transparent")
        self.is_admin = None

        self.create_entry_frame()
        self.create_input_frames()  # Create keypad and keyboard frames at initialization
        self.place(relx=0.5, rely=0.6, anchor='center')

    def create_entry_frame(self):
        self.entry_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.entry_frame.grid(row=0, column=0, columnspan=2, pady=10, padx=10)

        self.first_name_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="First Name", width=300, height=50, fg_color="transparent")
        self.last_name_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Last Name", width=300, height=50, fg_color="transparent")
        self.pin_entry = ctk.CTkEntry(self.entry_frame, placeholder_text="Enter 6 Digit PIN", width=300, height=50, fg_color="transparent", show='*')
        self.verify_pin = ctk.CTkEntry(self.entry_frame, placeholder_text="Verify 6 Digit PIN", width=300, height=50, fg_color="transparent", show='*')

        seelf.check_var = ctk.Stringvar(value="off")
        self.admin_checkbox = ctk.CTkCheckBox(self.entry_frame, text="Admin", command=checkbox_event,
                                                variable=self.check_var, onvalue="on", offvalue="off")

        # Bind focus events to track the active entry
        for entry in [self.first_name_entry, self.last_name_entry, self.pin_entry, self.verify_pin]:
            entry.bind("<FocusIn>", self.set_active_entry)
        
        # Grid positioning
        self.first_name_entry.grid(row=0, column=0, pady=5, padx=10)
        self.last_name_entry.grid(row=0, column=1, pady=5, padx=10)
        self.pin_entry.grid(row=1, column=0, pady=5, padx=10)
        self.verify_pin.grid(row=1, column=1, pady=5, padx=10)

        self.admin_checkbox.grid(row=2, column=1, pady=5, padx=10)
        self.submit_button = ctk.CTkButton(self.entry_frame, text="Submit", command=self.submit)
        self.submit_button.grid(row=2, column=0, pady=10, padx=10)
    
    def checkbox_event():
        if self.check_var.get() == "on":
            self.is_admin == 'admin'
        else:
            self.is_admin == 'normal'


    def create_input_frames(self):
        # Frame for input options (keypad and keyboard)
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=3, column=0, columnspan=2, pady=10, padx=10)

        # Keyboard frame
        self.keyboard_frame = ctk.CTkFrame(self.input_frame)
        self.create_keyboard(self.keyboard_frame)

        # Keypad frame
        self.keypad_frame = ctk.CTkFrame(self.input_frame)
        self.create_keypad(self.keypad_frame)

        # Show keyboard by default
        self.keyboard_frame.grid(row=0, column=0)
        self.keypad_frame.grid_remove()  # Hide keypad initially

    def create_keyboard(self, parent):
        self.configure(fg_color="transparent")
        keys = [
            'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P',
            'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L',
            'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'Space', 'Backspace'
        ]

        row, col = 0, 0
        for key in keys:
            if key == "Space":
                button = ctk.CTkButton(parent, text="Space", width=100, height=50, font=("Figtree", 30, "bold"), command=lambda k=" ": self.type_key(k))
                button.grid(row=row, column=col, columnspan=2, padx=2, pady=2, sticky="nsew")
                col += 2
            elif key == "Backspace":
                button = ctk.CTkButton(parent, text="Backspace", width=100, height=50, font=("Figtree", 30, "bold"), command=self.backspace_key)
                button.grid(row=row, column=col, columnspan=2, padx=2, pady=2, sticky="nsew")
                col += 2
            else:
                button = ctk.CTkButton(parent, text=key, width=70, height=50, font=("Figtree", 30, "bold"), command=lambda k=key: self.type_key(k))
                button.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                col += 1
                if col > 9:  # Adjust number of columns as needed
                    col = 0
                    row += 1

    def create_keypad(self, parent):
        self.configure(fg_color="transparent")
        keys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'Backspace']

        row, col = 0, 0
        for key in keys:
            if key == '':
                col += 1  # Skip one column to center '0'
                continue
            if key == 'Backspace':
                button = ctk.CTkButton(parent, text=key, width=100, height=40, font=("Figtree", 30, "bold"), command=self.backspace_key)
                button.grid(row=row, column=1, columnspan=2, padx=2, pady=2, sticky="nsew")
                col += 2  # Skip the next column
            else:
                button = ctk.CTkButton(parent, text=key, width=100, height=40, font=("Figtree", 30, "bold"), command=lambda k=key: self.type_key(k))
                button.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                col += 1
            if col > 2:  # Adjust number of columns as needed
                col = 0
                row += 1

        # Add '0' in the center
        button = ctk.CTkButton(parent, text='0', width=100, height=40, font=("Figtree", 30, "bold"), command=lambda k='0': self.type_key(k))
        button.grid(row=row, column=0, padx=2, pady=2, sticky="nsew")

    def set_active_entry(self, event):
        self.active_entry = event.widget
        print(f"Active entry set to: {self.active_entry}")

        if str(self.active_entry) in [str(self.pin_entry._entry), str(self.verify_pin._entry)]:
            self.keyboard_frame.grid_remove()
            self.keypad_frame.grid()
        else:
            self.keypad_frame.grid_remove()
            self.keyboard_frame.grid()

    def submit(self):
        first_name = self.first_name_entry.get()
        last_name = self.last_name_entry.get()
        pin = self.pin_entry.get()
        verify_pin = self.verify_pin.get()
        is_admin = self.is_admin

        if pin == verify_pin and len(pin) == 6:
            print(f"Enrolled {first_name} {last_name} with PIN {pin}")
            self.master.title_frame.title_label.configure(text="Place your finger on the sensor...", font=("Figtree", 24, "bold"))
            self.place_forget()
            GetFingerprintFrame(self.master, first_name, last_name, pin, is_admin)
        else:
            print("PINs do not match or are not 6 digits")
            self.master.title_frame.title_label.configure(text="Enrollment Failed", font=("Figtree", 24, "bold"))

    def type_key(self, key):
        if hasattr(self, "active_entry") and self.active_entry:
            if str(self.active_entry) in [str(self.pin_entry._entry), str(self.verify_pin._entry)]:
                if len(self.active_entry.get()) < 6:
                    self.active_entry.insert('end', key)
            else:
                self.active_entry.insert('end', key)
        else:
            print("No active entry is set!")

    def backspace_key(self):
        if hasattr(self, "active_entry") and self.active_entry:
            current_text = self.active_entry.get()
            print(f"Backspace on: {self.active_entry}, Current text: '{current_text}'")
            self.active_entry.delete(0, 'end')
            self.active_entry.insert(0, current_text[:-1])
        else:
            print("No active entry is set!")

class GetFingerprintFrame(ctk.CTkFrame):
    def __init__(self, master, first_name, last_name, pin, is_admin):
        super().__init__(master)

        self.finger = finger
        self.first_name = first_name
        self.last_name = last_name
        self.pin = pin
        self.is_admin = is_admin

        for attempt in range(1, 3):  # Enroll requires two consistent reads
            self.master.title_frame.title_label.configure(text=f" Attempt {attempt}:Place your finger on the sensor...", font=("Figtree", 24, "bold"))
            while True:
                if self.finger.get_image() == adafruit_fingerprint.OK:
                    print("Image captured.")
                    break

            if self.finger.image_2_tz(attempt) != adafruit_fingerprint.OK:
                print("Failed to convert image to template.")
                return False

            if attempt == 1:
                self.master.title_frame.title_label.configure(text="Remove your finger and place it again.", font=("Figtree", 24, "bold"))
                while self.finger.get_image() != adafruit_fingerprint.NOFINGER:
                    pass

                # Create a model for the fingerprint
        print("Creating model...")
        if self.finger.create_model() != adafruit_fingerprint.OK:
            self.master.title_frame.title_label.configure(text="Failed to create fingerprint model", font=("Figtree", 24, "bold"))
            self.place_forget()     
            self.after(2000, lambda: GetFingerprintFrame(self.master))
            return False

        slot = self.find_empty_slot()
        # Store the model in the given slot
        print(f"Storing fingerprint at ID {slot}...")
        if self.finger.store_model(slot) != adafruit_fingerprint.OK:
            self.master.title_frame.title_label.configure(text="Failed to store fingerprint.", font=("Figtree", 24, "bold"))
            self.place_forget()     
            self.after(2000, lambda: GetFingerprintFrame(self.master))
            return False

        db.Database()
        db.execute_query("""
            INSERT INTO users (first_name, last_name, pin, fingerprint_id, user_type) 
            VALUES (?, ?, ?, ?, ?)
        """, (self.first_name, self.last_name, self.pin, slot, self.is_admin))

        self.master.title_frame.title_label.configure(text="Fingerprint enrollment successful.", font=("Figtree", 24, "bold"))
        self.master.title_frame.place(relx=0.5, rely=0.5, anchor='center')  
        self.place_forget()     
        self.after(3000, AdminFrame(self.master))

    def find_empty_slot():
        if self.finger.read_templates() == adafruit_fingerprint.OK:
            all_slots = set(range(0, self.finger.library_size))  # All possible slots
            used_slots = set(self.finger.templates)  # Occupied slots
            free_slots = all_slots - used_slots
            return min(free_slots) if free_slots else None  # Return the first available slot
        else:
            return None

class DeleteUserFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        self.configure(fg_color="transparent")
        self.create_widgets()
        self.place(relx=0.5, rely=0.55, anchor='center')

    def create_widgets(self):
        self.label = ctk.CTkLabel(self, text="Enter User ID to Delete:", font=("Figtree", 24, "bold"))
        self.label.grid(row=0, column=0, pady=10, padx=10)

        self.user_id_entry = ctk.CTkEntry(self, width=300, height=50, fg_color="transparent")
        self.user_id_entry.grid(row=1, column=0, pady=10, padx=10)

        self.delete_button = ctk.CTkButton(self, text="Delete", command=self.delete_user)
        self.delete_button.grid(row=2, column=0, pady=10, padx=10)

        self.back_button = ctk.CTkButton(self, text="Back", command=self.back)
        self.back_button.grid(row=3, column=0, pady=10, padx=10)

    def delete_user(self):
        user_id = self.user_id_entry.get()
        if user_id:
            db = Database()
            user = db.fetch_one("SELECT finger_id FROM users WHERE id = ?", (user_id,))
            if user:
                finger_id = user[0]
                if finger.delete_model(finger_id) == adafruit_fingerprint.OK:
                    db.execute_query("DELETE FROM users WHERE id = ?", (user_id,))
                    self.master.title_frame.title_label.configure(text="User and fingerprint deleted successfully.", font=("Figtree", 24, "bold"))
                else:
                    self.master.title_frame.title_label.configure(text="Failed to delete fingerprint from sensor.", font=("Figtree", 24, "bold"))
            else:
                self.master.title_frame.title_label.configure(text="User ID not found.", font=("Figtree", 24, "bold"))
            db.close()
            self.place_forget()
            self.after(3000, AdminFrame(self.master))
        else:
            self.master.title_frame.title_label.configure(text="Please enter a valid User ID.", font=("Figtree", 24, "bold"))
            self.user_id_entry.delete(0, 'end')

    def back(self):
        self.place_forget()
        AdminOptions(self.master)

class Database:
    def __init__(self, db_name="attendance.db"):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def execute_query(self, query, params=()):
        self.cursor.execute(query, params)
        self.connection.commit()

    def fetch_one(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchone()

    def fetch_all(self, query, params=()):
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()

app = App()
app.mainloop()