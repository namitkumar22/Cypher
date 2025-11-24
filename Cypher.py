import threading
import asyncio
import customtkinter
import sqlite3
from CTkMessagebox import CTkMessagebox
from datetime import datetime
import os
from functools import partial
import json
from datetime import datetime
import tkinter as tk


customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")



def MainExitFunc():
        exit(0)


def DefaultCamera():
    import cv2
    import numpy as np
    import face_recognition
    from datetime import datetime
    import os
    from pytz import timezone
    import time
    import sqlite3

    conn = sqlite3.connect("MainDataBase.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS AllStudentAttendanceData (Name text not null, date text not null, time text not null, ID integer not null, Attendance text, Period integer);")
    cur.execute("CREATE TABLE IF NOT EXISTS AuthenticationData (Name text not null, Role text not null, ID integer primary key, Password text not null, phone_number integer not null);")

    path = 'Images'
    images = []
    classNames = []

    myList = os.listdir(path)
    print(myList)

    for cls in myList:
        curImg = cv2.imread(f'{path}/{cls}')
        images.append(curImg)
        classNames.append(os.path.splitext(cls)[0])

    print(classNames)

    def findEncoding(images):
        encodedlist = []
        for img in images:
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            try:
                encode = face_recognition.face_encodings(img)[0]
            except IndexError:
                continue
            encodedlist.append(encode)
        return encodedlist

    def getCurrentPeriod(hour, minute):
        period_times = {                    # These are lecture timings set them as per your Schedule
            1: ((9, 0), (9, 55)),
            2: ((9, 55), (10, 50)),
            3: ((10, 50), (11, 45)),
            4: ((11, 45), (12, 40)),
            5: ((12, 40), (13, 35)),
            6: ((13, 35), (14, 30)),
            7: ((14, 30), (15, 25)),
            8: ((15, 25), (16, 20)),
        }
        for period, (start, end) in period_times.items():
            if (hour == start[0] and minute >= start[1]) or (hour == end[0] and minute <= end[1]):
                return period
        return None # Change here if you want to mark attendance outside lecture timings

    def markAttendance(name, start_time=None, end_time=None):
        now = datetime.now()
        datestring = now.strftime('%d:%m:%Y')
        time_now = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')

        start_index = name.find('[') + 1
        end_index = name.find(']', start_index)
        realName = name.split('[')[0]
        realName = realName.replace('_', ' ')
        StudentID = name[start_index:end_index]

        current_hour = now.hour
        current_minute = now.minute

        period = getCurrentPeriod(current_hour, current_minute)
        if not period:
            return

        if start_time and end_time:
            duration = datetime.strptime(end_time, '%H:%M:%S') - datetime.strptime(start_time, '%H:%M:%S')
            if duration.total_seconds() > 5:  # 300 seconds = 5 minutes [Face detection time for making attendace] [1800 = 30 minutes]
                query = f"SELECT * from AllStudentAttendanceData WHERE ID = ? and date = ? and Period = ?;"
                cur.execute(query, (StudentID, datestring, period))
                existing_entry = cur.fetchone()
                if existing_entry == None:
                    print(existing_entry)
                    cur.execute("INSERT INTO AllStudentAttendanceData (Name, date, time, ID, Attendance, Period) VALUES (?, ?, ?, ?, 'P', ?);", (realName, datestring, time_now, StudentID, period))
        conn.commit()

    encodeListKnownFaces = findEncoding(images)
    print('Encoding Done')

    cap = cv2.VideoCapture(0)        # Put the ip of your camera you using here in place of '0'
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    if not cap.isOpened():
        print("Error: Camera not opened.")
        return

    # Add initialization delay to let camera warm up
    time.sleep(1)
    
    # Discard initial frames that might be grey/corrupted
    for _ in range(5):
        cap.read()

    recognized_faces = {}
    frame_count = 0
    window_created = False

    while True:
        success, img = cap.read()
        if not success or img is None:
            print("Failed to read frame, retrying...")
            time.sleep(0.1)
            continue

        frame_count += 1
        if frame_count % 3 != 0:
            continue

        current_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_small = cv2.resize(img_rgb, (0, 0), fx=0.25, fy=0.25)
        face_locations = face_recognition.face_locations(img_small) # put model="cnn" for better accuracy but requires more processing power
        encodings = face_recognition.face_encodings(img_small, face_locations)

        for encode_face, face_location in zip(encodings, face_locations):
            matches = face_recognition.compare_faces(encodeListKnownFaces, encode_face)
            face_distance = face_recognition.face_distance(encodeListKnownFaces, encode_face)
            match_index = np.argmin(face_distance)

            if matches[match_index] and face_distance[match_index] < 0.6:
                name = classNames[match_index].upper()
                print(name)

                if name not in recognized_faces:
                    recognized_faces[name] = {'start_time': current_time, 'last_seen': current_time}
                else:
                    recognized_faces[name]['last_seen'] = current_time

                y1, x2, y2, x1 = [v * 4 for v in face_location]

                main_color = (255, 182, 193)  # Light purple
                corner_color = (128, 0, 128)  # Dark purple
                thickness = 2
                corner_thickness = 6 

                cv2.rectangle(img, (x1, y1), (x2, y2), main_color, thickness)

                corner_length = 30
                cv2.line(img, (x1, y1), (x1 + corner_length, y1), corner_color, corner_thickness)
                cv2.line(img, (x1, y1), (x1, y1 + corner_length), corner_color, corner_thickness)
                cv2.line(img, (x2, y1), (x2 - corner_length, y1), corner_color, corner_thickness)
                cv2.line(img, (x2, y1), (x2, y1 + corner_length), corner_color, corner_thickness)
                cv2.line(img, (x1, y2), (x1 + corner_length, y2), corner_color, corner_thickness)
                cv2.line(img, (x1, y2), (x1, y2 - corner_length), corner_color, corner_thickness)
                cv2.line(img, (x2, y2), (x2 - corner_length, y2), corner_color, corner_thickness)
                cv2.line(img, (x2, y2), (x2, y2 - corner_length), corner_color, corner_thickness)

                cv2.rectangle(img, (x1, y2 - 35), (x2, y2), main_color, cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                font_scale = 0.8
                font_thickness = 1 
                cv2.putText(img, name, (x1 + 6, y2 - 6), font, font_scale, (255, 255, 255), font_thickness)

                start_time_obj = datetime.strptime(recognized_faces[name]['start_time'], '%H:%M:%S')
                current_time_obj = datetime.strptime(current_time, '%H:%M:%S')

                if (current_time_obj - start_time_obj).total_seconds() > 5:  # 300 seconds = 5 minutes
                    markAttendance(name, recognized_faces[name]['start_time'], current_time)
                    del recognized_faces[name]

        for name in list(recognized_faces.keys()):
            if recognized_faces[name]['last_seen'] != current_time:
                markAttendance(name, recognized_faces[name]['start_time'], recognized_faces[name]['last_seen'])
                del recognized_faces[name]

        # Only create and show window after first valid frame
        if not window_created:
            cv2.namedWindow('webcam', cv2.WINDOW_NORMAL)
            window_created = True
        
        cv2.imshow('webcam', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        hour = int(ind_time[:2])
        minute = int(ind_time[3:5])

        if (hour == 11 and minute >= 45) or (hour == 12 and minute <= 40): # Here set lunch timing or college off timing as per your schedule
            print("Lunch Break")
            time.sleep(3300)
        # elif hour >= 17:
        #     mark_absent_students()
        #     print("College is not opened yet")
        #     time.sleep(57600)

    cap.release()
    cv2.destroyAllWindows()
  
            

async def timemethod():
    from pytz import timezone 
    from datetime import datetime

    while True:     
        ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        print(ind_time)
            
        hour = ind_time[:2]
        minute = ind_time[3:5]
        seconds = ind_time[6:]

        if str(hour) == '9' and str(minute) == '10':  # This is the automatic start timing, set as per your schedule
            while True:
                ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
                hour = ind_time[:2]
                minute = ind_time[3:5]
                seconds = ind_time[6:]
                DefaultCamera()

        await asyncio.sleep(1)

def mark_absent_students():
        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()

        current_date = datetime.now().strftime('%d:%m:%Y')
        periods = [i for i in range(1, 9)]

        cur.execute("SELECT DISTINCT ID, Name FROM AllStudentAttendanceData;")
        students = cur.fetchall()

        for student in students:
            student_id, student_name = student


            cur.execute("SELECT DISTINCT Period FROM AllStudentAttendanceData WHERE ID = ? AND date = ? AND Attendance = 'P';",
                        (student_id, current_date))
            present_periods = [result[0] for result in cur.fetchall()]

            for period in periods:
                if period not in present_periods:

                    cur.execute("INSERT INTO AllStudentAttendanceData (Name, date, time, ID, Attendance, Period) VALUES (?, ?, ?, ?, 'A', ?);",
                                (student_name, current_date, "17:00:00", student_id, period))

        conn.commit()
        conn.close()

        print("Absent students marked for the day")
    

def LoginPage():
    global LoginScreen
    LoginScreen = customtkinter.CTk()

    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("green") 
    LoginScreen.title("Login")

    window_width = 400
    window_height = 300
    LoginScreen.geometry(f"{window_width}x{window_height}")

    label_ID = customtkinter.CTkLabel(master=LoginScreen, text="Admin or Student ID")
    global input_ID
    input_ID = customtkinter.CTkEntry(master=LoginScreen, width=300, height=35)
    label_password = customtkinter.CTkLabel(master=LoginScreen, text="Password")
    global input_password
    input_password = customtkinter.CTkEntry(master=LoginScreen, width=300, height=35, show="*")
    button_login = customtkinter.CTkButton(master=LoginScreen, text="Login", command=LoginFunction)
    btn = customtkinter.CTkButton(master=LoginScreen, text="Exit", command = MainExitFunc)


    label_ID.pack(pady=(20,0), padx=10)
    input_ID.pack(pady=(0, 10), padx=10)
    label_password.pack(pady=0, padx=10)
    input_password.pack(pady=(0,10), padx=10)
    button_login.pack(pady=10, padx=10)
    btn.pack(pady = 8)

    LoginScreen.mainloop()



def LoginFunction():
    global LoginScreen

    conn = sqlite3.connect("MainDataBase.db")
    cur = conn.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS AllStudentAttendanceData (Name text not null, date text not null, time text not null, ID integer primary key, Attendance text, Period integer);")

    cur.execute("CREATE TABLE IF NOT EXISTS AuthenticationData (Name text not null, Role text not null, ID integer primary key, Password text not null, phone_number integer not null);")

    user_id = input_ID.get()
    password = input_password.get()


    query = "SELECT * FROM AuthenticationData WHERE ID = ? AND Password = ?;"
    cur.execute(query, (user_id, password))
    global loginresult
    loginresult = cur.fetchone()

    if loginresult == None:
        CTkMessagebox(master= LoginScreen, title="Cypher", message= "No Record Found!", icon="warning", option_1= "Ok")

    if loginresult[1].upper() == 'ADMIN':
        LoginScreen.destroy()
        CypherGUIAdmin()
        CypherGUIAdmin().mainloop()
        
    if loginresult[1].upper() == 'STUDENT':
        LoginScreen.destroy()
        print("Student")
        LoginScreen.destroy()
        



class CypherGUIAdmin(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.title("Cypher 3.0")
        self.geometry(f"{1300}x{600}")

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure((2, 3), weight=0)
        self.grid_rowconfigure((0, 1, 2), weight=1)

        self.sidebar_frame = customtkinter.CTkFrame(self, width=140, corner_radius=10)
        self.sidebar_frame.grid(row=0, column=0, padx=(10, 0), pady=(10, 10), rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.sidebar_frame2 = customtkinter.CTkFrame(self, width=140, corner_radius=10)
        self.sidebar_frame2.grid(row=0, column=1, padx=(10, 0), pady=(10, 10), rowspan=4, sticky="nsew")
        self.sidebar_frame2.grid_rowconfigure(4, weight=1)

        self.sidebar_frame3 = customtkinter.CTkScrollableFrame(self, width=140, corner_radius=10)
        self.sidebar_frame3.grid(row=0, column=4, padx=(0, 10), pady=(10, 10), rowspan=3, sticky="nsew")
        self.sidebar_frame3.grid_rowconfigure(4, weight=1)

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Cypher", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        self.sidebar_button_1 = customtkinter.CTkButton(self.sidebar_frame, text="Check Attendance", command=self.CheckAttendanceAdmin)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        self.sidebar_button_2 = customtkinter.CTkButton(self.sidebar_frame,text="Update Attendance", command=self.UpdateAttendanceAdmin)
        self.sidebar_button_2.grid(row=2, column=0, padx=20, pady=10)
        self.sidebar_button_3 = customtkinter.CTkButton(self.sidebar_frame, text="Add Student Data", command=self.AddDataAdmin)
        self.sidebar_button_3.grid(row=3, column=0, padx=20, pady=10)




        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Theme", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],command=self.change_appearance_mode_event)
        
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))

        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text=f"Wecome {loginresult[0]}", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=7, column=0, padx=20, pady=(20, 10))

        self.exit_button_1 = customtkinter.CTkButton(master=self, fg_color="transparent", text="Exit", border_width=2, text_color=("gray10", "#DCE4EE"), command=MainExitFunc)
        self.exit_button_1.grid(row=3, column=4, padx=(20, 20), pady=(20, 20), sticky="nsew")

        global Cameraview

        self.Cameraview = customtkinter.CTkScrollableFrame(self, width=650, height=600)
        self.Cameraview.grid(row=0, column=3, padx=(10, 10), pady=(10, 10), sticky="nsew")

        self.labels = []

        

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def change_scaling_event(self, new_scaling: str):
        new_scaling_float = int(new_scaling.replace("%", "")) / 100
        customtkinter.set_widget_scaling(new_scaling_float)

    def CheckAttendanceAdmin(self):
        global rootCheckAttendance
        rootCheckAttendance = customtkinter.CTk()

        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("green") 
        rootCheckAttendance.title("Cypher 3.0")

        window_width = 400
        window_height = 300
        rootCheckAttendance.geometry(f"{window_width}x{window_height}")

        label_ID = customtkinter.CTkLabel(master=rootCheckAttendance, text="Student ID")
        global input_idchatt
        input_idchatt = customtkinter.CTkEntry(master=rootCheckAttendance, width=300, height=35)

        label_Date = customtkinter.CTkLabel(master=rootCheckAttendance, text="Date")
        global input_datechatt
        input_datechatt = customtkinter.CTkEntry(master=rootCheckAttendance, width=300, height=35, placeholder_text="28:04:2024 [Leave Empty for all Dates Data]")


        button_login = customtkinter.CTkButton(master=rootCheckAttendance, text="Submit", command= self.CheckStudentAttendance)
        btn = customtkinter.CTkButton(master=rootCheckAttendance, text="Back", command= rootCheckAttendance.destroy)

        label_ID.pack(pady=0, padx=10)
        input_idchatt.pack(pady=(0,10), padx=10)

        label_Date.pack()
        input_datechatt.pack()

        

        button_login.pack(pady=10, padx=10)
        btn.pack(pady = 8)

        rootCheckAttendance.mainloop()

    

    def CheckStudentAttendance(self):
        from pytz import timezone 
        now = datetime.now()
        datestring = now.strftime('%d:%m:%Y')
        time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')

        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS AllStudentAttendanceData (Name text not null, date text not null, time text not null, ID integer primary key, Attendance text, Period integer);")

        cur.execute("CREATE TABLE IF NOT EXISTS AuthenticationData (Name text not null, Role text not null, ID integer primary key, Password text not null, phone_number integer not null);")

        user_idchatt = input_idchatt.get()
        user_date = input_datechatt.get()

        if user_idchatt == '':
            CTkMessagebox(master=rootCheckAttendance, title="Cypher", message="Please Enter a Proper ID", icon="info", option_1="Ok")
            return
        
        elif user_date == '':
            Exceptional_query = f"SELECT * FROM AllStudentAttendanceData WHERE ID = {user_idchatt};"
            cur.execute(Exceptional_query)
            Exception_Result = cur.fetchall()
            print(Exception_Result)

            for label in self.labels:
                label.destroy()
            self.labels.clear()
            
            Exception_Result_sorted = sorted(Exception_Result, key=lambda x: (x[1], x[5]))  # Sort by date (index 1) and then by period (index 5)

            current_date = None
            for i in range(len(Exception_Result_sorted)):
                date = Exception_Result_sorted[i][1]

                if date != current_date:
                    if current_date is not None:
                        # Add a ruler between different dates
                        self.ruler = tk.Frame(self.sidebar_frame3, height=2, bd=1, relief='sunken')
                        self.ruler.grid(row=len(self.labels), column=0, columnspan=1, sticky='we', pady=(5, 10))
                        self.labels.append(self.ruler)

                    # Display date as a heading
                    self.date_heading = customtkinter.CTkLabel(self.sidebar_frame3, text=f"{date}", font=customtkinter.CTkFont(size=17, weight="bold"), fg_color="purple", bg_color="white")
                    self.date_heading.grid(row=len(self.labels), column=0, pady=(10, 10), sticky='w')
                    self.labels.append(self.date_heading)

                    current_date = date

                # Display attendance data
                self.Data_label = customtkinter.CTkLabel(self.sidebar_frame3, text=f"Lecture {Exception_Result_sorted[i][5]} -----> {Exception_Result_sorted[i][4]}", font=customtkinter.CTkFont(size=15, weight="bold"))
                self.Data_label.grid(row=len(self.labels), column=0, pady=(0, 10), sticky='w')
                self.labels.append(self.Data_label)

        else:
            query = f"SELECT * FROM AllStudentAttendanceData WHERE ID = ? AND date = ?;"
            cur.execute(query, (user_idchatt, user_date))
            result = cur.fetchall()

            for label in self.labels:
                label.destroy()
            self.labels.clear()

            if result:
                # Sort result by period (index 5)
                result_sorted = sorted(result, key=lambda x: x[5])

                # Show the name once
                self.name_label = customtkinter.CTkLabel(self.sidebar_frame3, text=f"{result_sorted[0][0]}", font=customtkinter.CTkFont(size=20, weight="bold"))
                self.name_label.grid(row=0, column=0, padx=(10, 10), pady=(10, 10), sticky='w')
                self.labels.append(self.name_label)

                current_date = None
                for i in range(len(result_sorted)):
                    date = result_sorted[i][1]
                    if date != current_date:
                        if current_date is not None:
                            # Add a ruler between different dates
                            self.ruler = tk.Frame(self.sidebar_frame3, height=2, bd=1, relief='sunken')
                            self.ruler.grid(row=len(self.labels), column=0, columnspan=3, sticky='we', pady=(5, 10))
                            self.labels.append(self.ruler)

                        # Display date as a heading
                        self.date_heading = customtkinter.CTkLabel(self.sidebar_frame3, text=f"{date}", font=customtkinter.CTkFont(size=17, weight="bold"), fg_color="purple", bg_color="white")
                        self.date_heading.grid(row=len(self.labels), column=0, pady=(10, 10), sticky='w')
                        self.labels.append(self.date_heading)

                        current_date = date

                    # Display attendance data
                    self.Data_label = customtkinter.CTkLabel(self.sidebar_frame3, text=f"Lecture {result_sorted[i][5]} -----> {result_sorted[i][4]}", font=customtkinter.CTkFont(size=15, weight="bold"))
                    self.Data_label.grid(row=len(self.labels), column=0, pady=(0, 10), sticky='w')
                    self.labels.append(self.Data_label)

        
    def display_info(self, name, start_time_obj, current_time_obj):

            time_diff = (current_time_obj - start_time_obj).total_seconds()
        
            self.ruler = tk.Frame(self.Cameraview, height=2, bd=1, relief='sunken')
            self.ruler.grid(row=len(self.labels), column=0, columnspan=2, sticky='we', pady=(5, 10))
            self.labels.append(self.ruler)

            self.date_heading = customtkinter.CTkLabel(self.Cameraview, text=f"Name: {name} | CT: {current_time_obj} | SDT: {start_time_obj} | SCD: {time_diff}", font=customtkinter.CTkFont(size=14, weight="bold"), fg_color="black", bg_color="white")
            self.date_heading.grid(row=len(self.labels), column=0, pady=(10, 10), sticky='w')
            self.labels.append(self.date_heading)

            self.ruler = tk.Frame(self.Cameraview, height=2, bd=1, relief='sunken')
            self.ruler.grid(row=len(self.labels), column=0, columnspan=2, sticky='we', pady=(5, 10))
            self.labels.append(self.ruler)
   

    def UpdateAttendanceAdmin(self):
        global rootUpdateAttendance
        rootUpdateAttendance = customtkinter.CTk()

        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("green")
        rootUpdateAttendance.title("Cypher 3.0")

        window_width = 600
        window_height = 500
        rootUpdateAttendance.geometry(f"{window_width}x{window_height}")

        label_ID = customtkinter.CTkLabel(master=rootUpdateAttendance, text="Student ID")
        global input_idupatt
        input_idupatt = customtkinter.CTkEntry(master=rootUpdateAttendance, width=300, height=35)

        label_Date = customtkinter.CTkLabel(master=rootUpdateAttendance, text="Date")
        global input_dateupatt
        input_dateupatt = customtkinter.CTkEntry(master=rootUpdateAttendance, width=300, height=35, placeholder_text="28:04:2024")

        label_Period = customtkinter.CTkLabel(master=rootUpdateAttendance, text="Period")
        global input_periodupatt
        input_periodupatt = customtkinter.CTkEntry(master=rootUpdateAttendance, width=300, height=35)

        label_Attendance = customtkinter.CTkLabel(master=rootUpdateAttendance, text="Attendance")
        global input_attendanceupatt
        input_attendanceupatt = customtkinter.CTkEntry(master=rootUpdateAttendance, width=300, height=35)

        button_submit = customtkinter.CTkButton(master=rootUpdateAttendance, text="Submit", command=self.UpdateStudentAttendance)
        button_back = customtkinter.CTkButton(master=rootUpdateAttendance, text="Back", command=rootUpdateAttendance.destroy)

        label_ID.pack(pady=5)
        input_idupatt.pack(pady=5)

        label_Date.pack(pady=5)
        input_dateupatt.pack(pady=5)

        label_Period.pack(pady=5)
        input_periodupatt.pack(pady=5)

        label_Attendance.pack(pady=5)
        input_attendanceupatt.pack(pady=5)

        button_submit.pack(pady=10)
        button_back.pack(pady=10)

        rootUpdateAttendance.mainloop()

    def UpdateStudentAttendance(self):
        user_idupatt = input_idupatt.get()
        user_date = input_dateupatt.get()
        user_period = input_periodupatt.get()
        user_attendance = input_attendanceupatt.get()

        if not user_idupatt or not user_date or not user_period or not user_attendance:
            CTkMessagebox(master=rootUpdateAttendance, title="Cypher", message="Please fill all fields", icon="warning", option_1="Ok")
            return

        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()

        query = f"UPDATE AllStudentAttendanceData SET Attendance = ? WHERE ID = ? AND date = ? AND Period = ?;"
        cur.execute(query, (user_attendance, user_idupatt, user_date, user_period))
        conn.commit()

        if cur.rowcount > 0:
            CTkMessagebox(master=rootUpdateAttendance, title="Cypher", message="Attendance Updated Successfully", icon="check", option_1="Ok")
        else:
            CTkMessagebox(master=rootUpdateAttendance, title="Cypher", message="No Record Found to Update", icon="warning", option_1="Ok")

        conn.close()
    
    def AddDataAdmin(self):
        print("Under Development")

    def ExitApp(self):
        exit(0)



def start_async_tasks(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(timemethod()))

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    threading.Thread(target=start_async_tasks, args=(loop,), daemon=True).start()
    LoginPage()