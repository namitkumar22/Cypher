import customtkinter
import sqlite3

def RegistrationPage():
    RegistrationScreen = customtkinter.CTk()

    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("blue") 
    RegistrationScreen.title("Registration")

    window_width = 550
    window_height = 450
    RegistrationScreen.geometry(f"{window_width}x{window_height}")

    label_AdminName = customtkinter.CTkLabel(master=RegistrationScreen, text="Admin or Student Name")
    global input_AdminName
    input_AdminName = customtkinter.CTkEntry(master=RegistrationScreen, width=300, height=35)
    label_AdminID = customtkinter.CTkLabel(master=RegistrationScreen, text="Admin or Student ID")
    global input_AdminID
    input_AdminID = customtkinter.CTkEntry(master=RegistrationScreen, width=300, height=35)
    label_password = customtkinter.CTkLabel(master=RegistrationScreen, text="Password")
    global input_password
    input_password = customtkinter.CTkEntry(master=RegistrationScreen, width=300, height=35, show="*")
    button_login = customtkinter.CTkButton(master=RegistrationScreen, text="Register", command=RegisterFunction)

    role_label = customtkinter.CTkLabel(master=RegistrationScreen, text="Role")
    global user_role
    user_role = customtkinter.CTkEntry(master=RegistrationScreen, width=300, height=35)
    phone_label = customtkinter.CTkLabel(master=RegistrationScreen, text="Phone Number")
    global user_phone
    user_phone = customtkinter.CTkEntry(master=RegistrationScreen, width=300, height=35)



    label_AdminName.pack(pady=(20,0), padx=10)
    input_AdminName.pack(pady=(0, 10), padx=10)
    label_AdminID.pack(pady=0, padx=10)
    input_AdminID.pack(pady=(0,10), padx=10)
    label_password.pack(pady=0, padx=10)
    input_password.pack(pady=(0,10), padx=10)
    role_label.pack(pady=0, padx=10)
    user_role.pack(pady=(0, 10), padx=10)
    phone_label.pack(pady=0, padx=10)
    user_phone.pack(pady=(0, 10), padx=10)
    button_login.pack(pady=10, padx=10)

    RegistrationScreen.mainloop()



def RegisterFunction():
    user_name = input_AdminName.get()
    user_id = input_AdminID.get()
    user_id = int(user_id)
    password = input_password.get()
    role = user_role.get()
    phone = user_phone.get()
    phone = int(phone)

    conn = sqlite3.connect("MainDataBase.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS AuthenticationData (Name text not null, Role text not null, ID integer primar key, Password text not null, phone_number integer not null);")

    query = "INSERT INTO AuthenticationData (Name, Role, ID, Password, phone_number) VALUES (?, ?, ?, ?, ?)"

    cur.execute(query, (user_name, role, user_id, password, phone))

    conn.commit()

    role = cur.fetchone()

    print("Done")


if __name__ == "__main__":
    RegistrationPage()
