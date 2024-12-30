import sqlite3
from adafruit_fingerprint import Adafruit_Fingerprint
import serial

# Initialize the serial connection
uart = serial.Serial("/dev/ttyS1", baudrate=57600, timeout=1)
finger = Adafruit_Fingerprint(uart)  # Initialize with the serial connection

# Function to enroll the fingerprint
def enroll_fingerprint():
    for attempt in range(1, 3):
        print(f"Attempt {attempt}: Place your finger on the sensor...")
        while True:
            if finger.get_image() == Adafruit_Fingerprint.OK:
                print("Image captured.")
                break

        if finger.image_2_tz(attempt) != Adafruit_Fingerprint.OK:
            print("Failed to convert image to template.")
            return False

        if attempt == 1:
            print("Remove your finger and place it again.")
            while finger.get_image() != Adafruit_Fingerprint.NOFINGER:
                pass

    print("Creating model...")
    if finger.create_model() != Adafruit_Fingerprint.OK:
        print("Failed to create fingerprint model.")
        return False

    slot = find_empty_slot(finger)
    if slot is None:
        print("No available slots.")
        return False

    if finger.store_model(slot) != Adafruit_Fingerprint.OK:
        print("Failed to store fingerprint.")
        return False

    return slot

# Function to find an empty slot for fingerprint storage
def find_empty_slot(finger):
    if finger.read_templates() == Adafruit_Fingerprint.OK:
        all_slots = set(range(0, finger.library_size))  # All possible slots
        used_slots = set(finger.templates)  # Occupied slots
        free_slots = all_slots - used_slots
        return min(free_slots) if free_slots else None  # Return the first available slot
    else:
        return None

# Function to add admin to the database
def add_admin_to_db(first_name, last_name, pin, slot):
    db = sqlite3.connect('attendance.db')
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO users (first_name, last_name, pin, fingerprint_id, user_type) 
        VALUES (?, ?, ?, ?, ?)
    """, (first_name, last_name, pin, slot, 'admin'))  # 'admin' is the user_type

    db.commit()
    db.close()

# Main function to run the process
def main():
    first_name = input("Enter admin's first name: ")
    last_name = input("Enter admin's last name: ")
    pin = input("Enter admin's PIN: ")

    # Enroll fingerprint
    slot = enroll_fingerprint()
    if slot:
        # Add admin to the database
        add_admin_to_db(first_name, last_name, pin, slot)
        print(f"Admin {first_name} {last_name} added successfully with fingerprint ID {slot}.")
    else:
        print("Fingerprint enrollment failed.")

if __name__ == "__main__":
    main()
