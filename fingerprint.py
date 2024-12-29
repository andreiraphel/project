import serial
import adafruit_fingerprint

class FingerprintManager:
    def __init__(self, port="/dev/ttyS1", baudrate=57600):
        self.uart = serial.Serial(port, baudrate=baudrate, timeout=1)
        self.finger = adafruit_fingerprint.Adafruit_Fingerprint(self.uart)

    def find_empty_slot(sensor):
        if sensor.read_templates() == adafruit_fingerprint.OK:
            all_slots = set(range(0, sensor.library_size))  # All possible slots
            used_slots = set(sensor.templates)  # Occupied slots
            free_slots = all_slots - used_slots
            return min(free_slots) if free_slots else None  # Return the first available slot
        else:
            return None

    def enroll_fingerprint(self):
        """
        Enroll a fingerprint for a given ID. This requires capturing the fingerprint twice.
        """
        # Check if the fingerprint is already enrolled
        print("Place your finger on the sensor to check if it's already enrolled...")
        if self.get_fingerprint_image():
            if self.finger.finger_search() == adafruit_fingerprint.OK:
                print(f"Fingerprint already enrolled with ID: {self.finger.finger_id}")
                return False

        for attempt in range(1, 3):  # Enroll requires two consistent reads
            print(f"Attempt {attempt}: Place your finger on the sensor...")
            while True:
                if self.finger.get_image() == adafruit_fingerprint.OK:
                    print("Image captured.")
                    break
            if self.finger.image_2_tz(attempt) != adafruit_fingerprint.OK:
                print("Failed to convert image to template.")
                return False
            if attempt == 1:
                print("Remove your finger and place it again.")
                while self.finger.get_image() != adafruit_fingerprint.NO_FINGER:
                    pass

        # Create a model for the fingerprint
        print("Creating model...")
        if self.finger.create_model() != adafruit_fingerprint.OK:
            print("Failed to create fingerprint model.")
            return False

        slot = self.find_empty_slot(self.finger)
        # Store the model in the given slot
        print(f"Storing fingerprint at ID {slot}...")
        if self.finger.store_model(slot) != adafruit_fingerprint.OK:
            print("Failed to store fingerprint.")
            return False

        print("Fingerprint enrollment successful.")
        return True

    def search_fingerprint(self):
        """
        Search the sensor for a fingerprint match.
        Returns the fingerprint ID if found, or None if not found.
        """
        print("Place your finger on the sensor for verification...")
        if self.get_fingerprint_image():
            print("Searching for fingerprint match...")
            if self.finger.finger_search() == adafruit_fingerprint.OK:
                print(f"Fingerprint found! ID: {self.finger.finger_id}")
                return self.finger.finger_id
            else:
                print("No matching fingerprint found.")
        return None

    def delete_fingerprint(self, finger_id):
        """
        Delete a fingerprint from a specific ID slot.
        """
        print(f"Deleting fingerprint at ID {finger_id}...")
        if self.finger.delete_model(finger_id) == adafruit_fingerprint.OK:
            print("Fingerprint deleted successfully.")
            return True
        print("Failed to delete fingerprint.")
        return False


    def list_fingerprints(self):
        """List all stored fingerprints."""
        if self.finger.read_templates() == adafruit_fingerprint.OK:
            print("Stored Fingerprints:", self.finger.templates)
        else:
            print("Failed to read templates.")

    def clear_all_fingerprints(self):
        """Clear all fingerprints from the library."""
        print("Clearing all fingerprints from the library...")
        if self.finger.empty_library() == adafruit_fingerprint.OK:
            print("All fingerprints have been successfully deleted.")
            return True
        else:
            print("Failed to clear fingerprints. Please try again.")
            return False

if __name__ == "__main__":
    manager = FingerprintManager(port="COM3")  # Adjust the port as needed

    while True:
        print("\nFingerprint Manager")
        print("1. Enroll Fingerprint")
        print("2. Search Fingerprint")
        print("3. Delete Fingerprint")
        print("4. List Fingerprints")
        print("5. Clear All Fingerprints")
        print("6. Exit")
        choice = input("Enter your choice: ")

        if choice == '1':
            manager.enroll_fingerprint()
        elif choice == '2':
            manager.search_fingerprint()
        elif choice == '3':
            finger_id = int(input("Enter Fingerprint ID to delete: "))
            manager.delete_fingerprint(finger_id)
        elif choice == '4':
            manager.list_fingerprints()
        elif choice == '5':
            manager.clear_all_fingerprints()
        elif choice == '6':
            break
        else:
            print("Invalid choice. Please try again.")