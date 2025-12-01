import customtkinter
import sqlite3
import re
import os
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox
import shutil

class RegistrationPage:
    def __init__(self):
        self.app = customtkinter.CTk()
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        
        self.app.title("Student Registration System")
        
        # Responsive window sizing
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        window_width = min(700, int(screen_width * 0.6))
        window_height = min(800, int(screen_height * 0.85))
        
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.app.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.app.minsize(600, 700)
        
        # Image variables
        self.selected_image_path = None
        self.image_label_widget = None
        
        # Create Images folder if not exists
        if not os.path.exists("Images"):
            os.makedirs("Images")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = customtkinter.CTkFrame(self.app, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Title
        title = customtkinter.CTkLabel(
            main_frame, 
            text="Student Registration",
            font=customtkinter.CTkFont(size=32, weight="bold"),
            text_color=("#1f6aa5", "#3a8dd1")
        )
        title.pack(pady=(0, 10))
        
        subtitle = customtkinter.CTkLabel(
            main_frame,
            text="Please fill in all required information",
            font=customtkinter.CTkFont(size=13),
            text_color=("gray60", "gray50")
        )
        subtitle.pack(pady=(0, 25))
        
        # Scrollable frame for form fields
        scroll_frame = customtkinter.CTkScrollableFrame(
            main_frame,
            fg_color=("gray90", "gray15"),
            corner_radius=15
        )
        scroll_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Image upload section
        image_frame = customtkinter.CTkFrame(scroll_frame, fg_color="transparent")
        image_frame.pack(pady=15, padx=20, fill="x")
        
        image_title = customtkinter.CTkLabel(
            image_frame,
            text="Profile Picture",
            font=customtkinter.CTkFont(size=15, weight="bold")
        )
        image_title.pack(anchor="w", pady=(0, 10))
        
        # Image preview
        self.image_preview_frame = customtkinter.CTkFrame(
            image_frame,
            width=150,
            height=150,
            fg_color=("gray80", "gray25"),
            corner_radius=10
        )
        self.image_preview_frame.pack(pady=(0, 10))
        self.image_preview_frame.pack_propagate(False)
        
        self.image_label_widget = customtkinter.CTkLabel(
            self.image_preview_frame,
            text="No Image\nSelected",
            font=customtkinter.CTkFont(size=12),
            text_color=("gray50", "gray60")
        )
        self.image_label_widget.pack(expand=True)
        
        upload_btn = customtkinter.CTkButton(
            image_frame,
            text="📷 Upload Image",
            command=self.upload_image,
            height=40,
            corner_radius=8,
            font=customtkinter.CTkFont(size=13, weight="bold")
        )
        upload_btn.pack()
        
        # Form fields
        self.create_form_field(scroll_frame, "Full Name", "name")
        self.create_form_field(scroll_frame, "Student/Admin ID", "id")
        self.create_form_field(scroll_frame, "Password", "password", show="*")
        self.create_form_field(scroll_frame, "Role (Student/Admin)", "role")
        self.create_form_field(scroll_frame, "Phone Number", "phone")
        
        # Register button
        register_btn = customtkinter.CTkButton(
            main_frame,
            text="Register Account",
            command=self.register_user,
            height=50,
            corner_radius=10,
            font=customtkinter.CTkFont(size=16, weight="bold"),
            fg_color=("#1f6aa5", "#3a8dd1"),
            hover_color=("#184d7a", "#2d7ab8")
        )
        register_btn.pack(fill="x")
        
    def create_form_field(self, parent, label_text, field_name, show=None):
        container = customtkinter.CTkFrame(parent, fg_color="transparent")
        container.pack(pady=12, padx=20, fill="x")
        
        label = customtkinter.CTkLabel(
            container,
            text=label_text,
            font=customtkinter.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        label.pack(anchor="w", pady=(0, 5))
        
        if show:
            entry = customtkinter.CTkEntry(
                container,
                height=45,
                corner_radius=8,
                border_width=2,
                font=customtkinter.CTkFont(size=13),
                show=show
            )
        else:
            entry = customtkinter.CTkEntry(
                container,
                height=45,
                corner_radius=8,
                border_width=2,
                font=customtkinter.CTkFont(size=13)
            )
        entry.pack(fill="x")
        
        setattr(self, f"input_{field_name}", entry)
        
    def upload_image(self):
        file_path = filedialog.askopenfilename(
            title="Select Profile Picture",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Load and resize image for preview
                img = Image.open(file_path)
                img.thumbnail((140, 140), Image.Resampling.LANCZOS)
                
                photo = customtkinter.CTkImage(light_image=img, dark_image=img, size=(140, 140))
                
                self.image_label_widget.configure(image=photo, text="")
                self.image_label_widget.image = photo
                
                self.selected_image_path = file_path
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def validate_inputs(self, name, user_id, password, role, phone):
        # Validate name
        if not name or len(name.strip()) < 2:
            messagebox.showerror("Validation Error", "Name must be at least 2 characters long")
            return False
        
        if not re.match(r"^[a-zA-Z\s]+$", name):
            messagebox.showerror("Validation Error", "Name should only contain letters and spaces")
            return False
        
        # Validate ID
        if not user_id:
            messagebox.showerror("Validation Error", "ID is required")
            return False
        
        try:
            user_id_int = int(user_id)
            if user_id_int <= 0:
                messagebox.showerror("Validation Error", "ID must be a positive number")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "ID must be a valid number")
            return False
        
        # Validate password
        if not password or len(password) < 6:
            messagebox.showerror("Validation Error", "Password must be at least 6 characters long")
            return False
        
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            messagebox.showerror("Validation Error", "Password must contain both letters and numbers")
            return False
        
        # Validate role
        if not role:
            messagebox.showerror("Validation Error", "Role is required")
            return False
        
        if role.lower() not in ["student", "admin"]:
            messagebox.showerror("Validation Error", "Role must be either 'Student' or 'Admin'")
            return False
        
        # Validate phone
        if not phone:
            messagebox.showerror("Validation Error", "Phone number is required")
            return False
        
        # Remove spaces and hyphens
        phone_clean = phone.replace(" ", "").replace("-", "")
        
        if not phone_clean.isdigit():
            messagebox.showerror("Validation Error", "Phone number must contain only digits")
            return False
        
        if len(phone_clean) < 10 or len(phone_clean) > 15:
            messagebox.showerror("Validation Error", "Phone number must be between 10 and 15 digits")
            return False
        
        return True
    
    def register_user(self):
        name = self.input_name.get().strip()
        user_id = self.input_id.get().strip()
        password = self.input_password.get()
        role = self.input_role.get().strip().capitalize()
        phone = self.input_phone.get().strip()
        
        # Validate all inputs
        if not self.validate_inputs(name, user_id, password, role, phone):
            return
        
        user_id_int = int(user_id)
        phone_clean = phone.replace(" ", "").replace("-", "")
        phone_int = int(phone_clean)
        
        try:
            conn = sqlite3.connect("MainDataBase.db")
            cur = conn.cursor()
            
            # Fixed SQL syntax: "primary key" not "primar key"
            cur.execute("""
                CREATE TABLE IF NOT EXISTS AuthenticationData (
                    ID INTEGER PRIMARY KEY,
                    Name TEXT NOT NULL,
                    Role TEXT NOT NULL,
                    Password TEXT NOT NULL,
                    phone_number INTEGER NOT NULL
                )
            """)
            
            # Check if ID already exists
            cur.execute("SELECT ID FROM AuthenticationData WHERE ID = ?", (user_id_int,))
            if cur.fetchone():
                messagebox.showerror("Registration Error", "This ID is already registered")
                conn.close()
                return
            
            # Handle image saving
            if self.selected_image_path:
                try:
                    # Create filename: name[student_id].ext
                    ext = os.path.splitext(self.selected_image_path)[1]
                    filename = f"{name}[{user_id_int}]{ext}"
                    destination = os.path.join("Images", filename)
                    
                    # Copy image to Images folder
                    shutil.copy2(self.selected_image_path, destination)
                except Exception as e:
                    messagebox.showwarning("Image Error", f"Failed to save image: {str(e)}\nRegistration will continue without image.")
            
            # Insert data
            query = """
                INSERT INTO AuthenticationData (ID, Name, Role, Password, phone_number)
                VALUES (?, ?, ?, ?, ?)
            """
            cur.execute(query, (user_id_int, name, role, password, phone_int))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Success", f"Registration successful!\nWelcome, {name}!")
            
            # Clear all fields
            self.clear_form()
            
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"An error occurred: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
    
    def clear_form(self):
        self.input_name.delete(0, 'end')
        self.input_id.delete(0, 'end')
        self.input_password.delete(0, 'end')
        self.input_role.delete(0, 'end')
        self.input_phone.delete(0, 'end')
        
        # Reset image
        self.selected_image_path = None
        self.image_label_widget.configure(image=None, text="No Image\nSelected")
        
    def run(self):
        self.app.mainloop()


if __name__ == "__main__":
    app = RegistrationPage()
    app.run()