import threading
import asyncio
import customtkinter
import sqlite3
from CTkMessagebox import CTkMessagebox
from datetime import datetime
import os
from functools import partial
import json
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry
from PIL import Image, ImageTk
import io
import queue
import cv2
import numpy as np
import csv

from registration import RegistrationPage


customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("blue")



# Global queues for thread-safe camera frame updates (4 cameras)
camera_frame_queues = {
    'camera_1': queue.Queue(maxsize=1),
    'camera_2': queue.Queue(maxsize=1),
    'camera_3': queue.Queue(maxsize=1),
    'camera_4': queue.Queue(maxsize=1),
}

# Camera configurations (IP addresses/indices)
CAMERA_CONFIG = {
    'camera_1': 0,      # Local webcam - Primary camera
    'camera_2': 1,      # Change to different camera IP or index (e.g., 1, 2, or 'http://192.168.1.100:8080/video')
    'camera_3': 2,      # Change to different camera IP or index
    'camera_4': 3,      # Change to different camera IP or index
}


def DefaultCamera(frame_queue, camera_id):
    import cv2
    import numpy as np
    import face_recognition
    from datetime import datetime
    import os
    from pytz import timezone
    import time
    import sqlite3

    # Add delay to prevent all cameras from starting simultaneously
    time.sleep(2)

    try:
        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()

        cur.execute("CREATE TABLE IF NOT EXISTS AllStudentAttendanceData (Name text not null, date text not null, time text not null, ID integer not null, Attendance text, Period integer);")
        cur.execute("CREATE TABLE IF NOT EXISTS AuthenticationData (Name text not null, Role text not null, ID integer primary key, Password text not null, phone_number integer not null);")

        path = 'Images'
        images = []
        classNames = []

        if not os.path.exists(path):
            print(f"{camera_id}: Images folder not found")
            return

        myList = os.listdir(path)
        print(f"{camera_id}: Found {len(myList)} images")

        for cls in myList:
            curImg = cv2.imread(f'{path}/{cls}')
            if curImg is not None:
                images.append(curImg)
                classNames.append(os.path.splitext(cls)[0])

        if not classNames:
            print(f"{camera_id}: No valid images found")
            return

        print(f"{camera_id} Class Names: {classNames}")

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
                if duration.total_seconds() > 5:  # 5 seconds minimum
                    query = f"SELECT * from AllStudentAttendanceData WHERE ID = ? and date = ? and Period = ?;"
                    cur.execute(query, (StudentID, datestring, period))
                    existing_entry = cur.fetchone()
                    if existing_entry == None:
                        try:
                            print(f"{camera_id}: Marking attendance for {realName}")
                            cur.execute("INSERT INTO AllStudentAttendanceData (Name, date, time, ID, Attendance, Period) VALUES (?, ?, ?, ?, 'P', ?);", (realName, datestring, time_now, StudentID, period))
                            conn.commit()
                        except Exception as e:
                            print(f"{camera_id}: Error marking attendance - {str(e)}")
                            conn.rollback()
                    else:
                        print(f"{camera_id}: Attendance already marked for {realName} in period {period}")

        encodeListKnownFaces = findEncoding(images)
        print(f'{camera_id}: Encoding Done - {len(encodeListKnownFaces)} faces encoded')

        cap = cv2.VideoCapture(CAMERA_CONFIG[camera_id])
        
        # Set camera properties with error handling
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 100)     # Increase brightness
        cap.set(cv2.CAP_PROP_CONTRAST, 50)        # Increase contrast
        cap.set(cv2.CAP_PROP_SATURATION, 50)      # Increase saturation
        cap.set(cv2.CAP_PROP_FPS, 30)

        if not cap.isOpened():
            print(f"Error: {camera_id} - Camera index {CAMERA_CONFIG[camera_id]} not available")
            print(f"{camera_id}: Available camera indices are typically 0, 1, 2, etc.")
            print(f"{camera_id}: For IP cameras, use format: 'rtsp://ip:port/stream' or 'http://ip:port/video'")
            return

        print(f"{camera_id}: Camera opened successfully")

        # Add initialization delay to let camera warm up
        time.sleep(1)
        
        # Discard initial frames that might be grey/corrupted
        for _ in range(5):
            ret, _ = cap.read()
            if not ret:
                break

        recognized_faces = {}
        frame_count = 0
        reconnect_attempts = 0
        max_reconnect_attempts = 3

        while True:
            try:
                success, img = cap.read()
                if not success or img is None:
                    print(f"{camera_id}: Failed to read frame")
                    reconnect_attempts += 1
                    
                    if reconnect_attempts > max_reconnect_attempts:
                        print(f"{camera_id}: Max reconnection attempts reached. Stopping camera.")
                        break
                    
                    time.sleep(0.5)
                    continue

                reconnect_attempts = 0
                frame_count += 1
                if frame_count % 3 != 0:
                    continue

                # Increase brightness in post-processing
                img = cv2.convertScaleAbs(img, alpha=1.2, beta=30)

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
                        print(f"{camera_id}: {name}")

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

                # Send frame to GUI
                try:
                    frame_queue.put_nowait(img)
                except queue.Full:
                    pass

            except Exception as e:
                print(f"{camera_id}: Error in frame processing - {str(e)}")
                time.sleep(0.5)
                continue

            ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
            hour = int(ind_time[:2])
            minute = int(ind_time[3:5])

            # if (hour == 11 and minute >= 45) or (hour == 12 and minute <= 40): # Here set lunch timing or college off timing as per your schedule
            #     print("Lunch Break")
            #     time.sleep(3300)
            if hour >= 17:
                mark_absent_students()
                print("College is not opened yet")
                time.sleep(57600)

        cap.release()
        conn.close()

    except Exception as e:
        print(f"{camera_id}: Fatal error - {str(e)}")
        import traceback
        traceback.print_exc()
  
            

async def timemethod(admin_gui=None):
    from pytz import timezone 
    from datetime import datetime
    import time

    last_absent_mark_date = None

    while True:     
        ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        current_date = datetime.now(timezone("Asia/Kolkata")).strftime('%d:%m:%Y')
        
        hour = int(ind_time[:2])
        minute = int(ind_time[3:5])

        # Start camera at 9:10 AM
        if hour == 9 and minute >= 10:
            try:
                print(f"✅ Starting camera feed at {ind_time}")
                DefaultCamera(camera_frame_queues['camera_1'], 'camera_1')
            except Exception as e:
                print(f"❌ Camera error: {str(e)}")
                await asyncio.sleep(1)
        
        # Mark absent at 5:00 PM (17:00) - ONLY ONCE PER DAY
        elif hour == 17 and minute == 0:
            if last_absent_mark_date != current_date:
                try:
                    print(f"🔔 Marking absent students at {ind_time}")
                    mark_absent_students()
                    last_absent_mark_date = current_date
                except Exception as e:
                    print(f"❌ Error marking absent: {str(e)}")
            await asyncio.sleep(60)  # Wait 1 minute to avoid duplicate execution
        
        else:
            await asyncio.sleep(1)


def get_all_enrolled_students():
    """
    Get all students from AuthenticationData table where Role = 'Student'
    Returns: List of tuples [(ID, Name), ...]
    """
    try:
        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()
        
        # Get all students (Role = 'Student')
        cur.execute("SELECT ID, Name FROM AuthenticationData WHERE Role = 'Student'")
        students = cur.fetchall()
        
        conn.close()
        
        if students:
            print(f"📋 Found {len(students)} enrolled students")
        else:
            print(f"⚠️  No students found with Role='Student'")
        
        return students
        
    except Exception as e:
        print(f"❌ Error getting enrolled students: {e}")
        import traceback
        traceback.print_exc()
        return []

def mark_absent_students():
    """
    Mark students absent for all periods if not marked present on current date.
    Runs automatically at 5 PM when college closes.
    
    Logic:
    - Gets ALL students from AuthenticationData (Role = 'Student')
    - For each student, checks each period (1-8)
    - If no attendance record exists OR record is not 'P', marks as 'A'
    - This ensures students who didn't show up get marked absent for ALL periods
    """

    from pytz import timezone
    try:
        conn = sqlite3.connect("MainDataBase.db")
        cur = conn.cursor()

        # Get current date in IST
        ist = timezone("Asia/Kolkata")
        current_datetime = datetime.now(ist)
        current_date = current_datetime.strftime('%d:%m:%Y')
        current_time = current_datetime.strftime('%H:%M:%S')
        
        # All periods in a day (1-8)
        all_periods = list(range(1, 9))

        print(f"\n{'='*60}")
        print(f"🕐 Auto-Absent Marking Started at {current_time}")
        print(f"📅 Date: {current_date}")
        print(f"{'='*60}\n")

        # Get ALL enrolled students from AuthenticationData
        all_students = get_all_enrolled_students()

        if not all_students:
            print(f"⚠️  No students found in AuthenticationData table!")
            print(f"💡 Tip: Make sure students are registered with Role='Student'")
            conn.close()
            return

        total_students = len(all_students)
        absent_marked = 0
        students_fully_absent = 0
        students_partially_present = 0

        for student_id, student_name in all_students:
            student_absent_count = 0
            student_present_count = 0
            
            for period in all_periods:
                # Check if attendance record exists for this student, date, and period
                cur.execute(
                    """SELECT Attendance FROM AllStudentAttendanceData 
                       WHERE ID = ? AND date = ? AND Period = ?""",
                    (student_id, current_date, period)
                )
                record = cur.fetchone()

                if record is None:
                    # No record exists - student didn't attend this period
                    # Insert absent record
                    try:
                        cur.execute(
                            """INSERT INTO AllStudentAttendanceData 
                               (Name, date, time, ID, Attendance, Period) 
                               VALUES (?, ?, ?, ?, 'A', ?)""",
                            (student_name, current_date, current_time, student_id, period)
                        )
                        absent_marked += 1
                        student_absent_count += 1
                    except sqlite3.IntegrityError:
                        # Record might have been inserted by another process
                        pass
                    
                elif record[0] != 'P':
                    # Record exists but not marked present - ensure it's marked absent
                    cur.execute(
                        """UPDATE AllStudentAttendanceData 
                           SET Attendance = 'A', time = ? 
                           WHERE ID = ? AND date = ? AND Period = ?""",
                        (current_time, student_id, current_date, period)
                    )
                    absent_marked += 1
                    student_absent_count += 1
                else:
                    # Student was present for this period
                    student_present_count += 1

            # Check if student was absent for all periods (whole day absent)
            if student_absent_count == len(all_periods):
                students_fully_absent += 1
                print(f"   🔴 {student_name} ({student_id}) - Absent ALL DAY (0/{len(all_periods)} periods)")
            elif student_present_count > 0:
                students_partially_present += 1
                print(f"   🟡 {student_name} ({student_id}) - Present {student_present_count}/{len(all_periods)} periods, Absent {student_absent_count}/{len(all_periods)}")

        conn.commit()
        conn.close()

        # Print summary
        print(f"\n{'='*60}")
        print(f"✅ Absent Marking Completed Successfully!")
        print(f"{'='*60}")
        print(f"📊 Summary:")
        print(f"   • Total Students: {total_students}")
        print(f"   • Students Fully Present: {total_students - students_fully_absent - students_partially_present}")
        print(f"   • Students Partially Present: {students_partially_present}")
        print(f"   • Students Absent All Day: {students_fully_absent}")
        print(f"   • Total Absent Records Created: {absent_marked}")
        print(f"   • Date: {current_date}")
        print(f"   • Time: {current_time}")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"❌ Error in mark_absent_students: {str(e)}")
        import traceback
        traceback.print_exc()


def LoginFunction():
    global LoginScreen, conn_global

    try:
        conn_global = sqlite3.connect("MainDataBase.db")
        cur = conn_global.cursor()

        # Create tables WITHOUT dropping existing data
        cur.execute("""
            CREATE TABLE IF NOT EXISTS AllStudentAttendanceData (
                Name text not null,
                date text not null,
                time text not null,
                ID integer not null,
                Attendance text,
                Period integer,
                UNIQUE(ID, date, Period)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS AuthenticationData (
                Name text not null,
                Role text not null,
                ID integer primary key,
                Password text not null,
                phone_number integer not null
            );
        """)

        conn_global.commit()

        user_id = input_ID.get().strip()
        password = input_password.get().strip()

        if not user_id or not password:
            CTkMessagebox(master=LoginScreen, title="Cypher", message="Please fill all fields!", icon="warning", option_1="Ok")
            return

        query = "SELECT * FROM AuthenticationData WHERE ID = ? AND Password = ?;"
        cur.execute(query, (user_id, password))
        global loginresult
        loginresult = cur.fetchone()

        if loginresult == None:
            CTkMessagebox(master=LoginScreen, title="Cypher", message="Invalid credentials!", icon="warning", option_1="Ok")
            return

        if loginresult[1].upper() == 'ADMIN':
            LoginScreen.destroy()
            admin_gui = CypherGUIAdmin()
            admin_gui.mainloop()
            
        elif loginresult[1].upper() == 'STUDENT':
            print(loginresult)
            LoginScreen.destroy()
            student_gui = CypherGUIStudent(loginresult[2], loginresult[0])
            student_gui.mainloop()

    except Exception as e:
        CTkMessagebox(master=LoginScreen, title="Error", message=f"Login Error: {str(e)}", icon="warning", option_1="Ok")
    finally:
        pass

def LoginPage():
    global LoginScreen
    LoginScreen = customtkinter.CTk()

    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("blue") 
    LoginScreen.title("Cypher - Login")

    window_width = 500
    window_height = 500
    LoginScreen.geometry(f"{window_width}x{window_height}")
    LoginScreen.resizable(False, False)

    # Title
    title_label = customtkinter.CTkLabel(
        master=LoginScreen, 
        text="CYPHER", 
        font=customtkinter.CTkFont(size=36, weight="bold"),
        text_color="#00D4FF"
    )
    title_label.pack(pady=(40, 5), padx=10)

    subtitle = customtkinter.CTkLabel(
        master=LoginScreen,
        text="🎓 Smart Attendance System",
        font=customtkinter.CTkFont(size=15, weight="bold"),
        text_color="#888888"
    )
    subtitle.pack(pady=(0, 40), padx=10)

    label_ID = customtkinter.CTkLabel(master=LoginScreen, text="👤 Admin or Student ID", font=customtkinter.CTkFont(size=13, weight="bold"))
    global input_ID
    input_ID = customtkinter.CTkEntry(master=LoginScreen, width=300, height=45, placeholder_text="Enter Your ID", font=customtkinter.CTkFont(size=12))
    label_password = customtkinter.CTkLabel(master=LoginScreen, text="🔐 Password", font=customtkinter.CTkFont(size=13, weight="bold"))
    global input_password
    input_password = customtkinter.CTkEntry(master=LoginScreen, width=300, height=45, placeholder_text="Enter Your Password", show="•", font=customtkinter.CTkFont(size=12))
    button_login = customtkinter.CTkButton(
        master=LoginScreen, 
        text="🔓 Login", 
        command=LoginFunction,
        font=customtkinter.CTkFont(size=14, weight="bold"),
        height=45,
        fg_color="#00D4FF",
        text_color="black"
    )
    btn = customtkinter.CTkButton(
        master=LoginScreen, 
        text="Exit", 
        command=MainExitFunc,
        font=customtkinter.CTkFont(size=12),
        height=40,
        fg_color="#FF6B6B"
    )

    label_ID.pack(pady=(20,5), padx=10)
    input_ID.pack(pady=(0, 15), padx=10)
    label_password.pack(pady=(0, 5), padx=10)
    input_password.pack(pady=(0, 20), padx=10)
    button_login.pack(pady=15, padx=10, fill="x")
    btn.pack(pady=10, padx=10, fill="x")

    LoginScreen.mainloop()

def MainExitFunc():
    exit(0)



class CypherGUIAdmin(customtkinter.CTk):

    def __init__(self):
        super().__init__()

        self.title("Cypher - Admin Dashboard")
        
        # Set to fullscreen
        self.state('zoomed')  # For Windows
        
        # Color scheme
        self.primary_color = "#00D4FF"
        self.secondary_color = "#1E1E2E"
        self.accent_color = "#FF6B6B"
        self.success_color = "#00FF00"
        self.warning_color = "#FFD700"

        # Grid configuration - Better layout
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ==== TOP HEADER ====
        self.header_frame = customtkinter.CTkFrame(self, height=80, fg_color="#0F0F1E", corner_radius=0)
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_propagate(False)

        header_title = customtkinter.CTkLabel(
            self.header_frame,
            text="🎓 Cypher - By Data Minds",
            font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color=self.primary_color
        )
        header_title.pack(side="left", padx=30, pady=20)

        welcome_info = customtkinter.CTkLabel(
            self.header_frame,
            text=f"Welcome: {loginresult[0]} | {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
            font=customtkinter.CTkFont(size=11),
            text_color="#888888"
        )
        welcome_info.pack(side="right", padx=30, pady=20)

        # ==== LEFT SIDEBAR ====
        self.sidebar_frame = customtkinter.CTkFrame(self, width=200, corner_radius=0, fg_color=self.secondary_color)
        self.sidebar_frame.grid(row=1, column=0, padx=0, pady=10, rowspan=1, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        self.logo_label = customtkinter.CTkLabel(
            self.sidebar_frame, 
            text="CYPHER", 
            font=customtkinter.CTkFont(size=24, weight="bold"),
            text_color=self.primary_color
        )
        self.logo_label.pack(pady=(20, 40), padx=15)

        self.sidebar_button_1 = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="📊 Check Attendance", 
            command=self.CheckAttendanceAdmin,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        self.sidebar_button_1.pack(padx=10, pady=8, fill="x")

        self.sidebar_button_2 = customtkinter.CTkButton(
            self.sidebar_frame,
            text="✏️ Update Attendance", 
            command=self.UpdateAttendanceAdmin,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        self.sidebar_button_2.pack(padx=10, pady=8, fill="x")

        self.sidebar_button_3 = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="➕ Add Student", 
            command=self.AddDataAdmin,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        self.sidebar_button_3.pack(padx=10, pady=8, fill="x")

        self.sidebar_button_5 = customtkinter.CTkButton(
            self.sidebar_frame,
            text="💾 Export Report",
            command=self.ExportAttendance,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        self.sidebar_button_5.pack(padx=10, pady=8, fill="x")

        self.appearance_mode_label = customtkinter.CTkLabel(self.sidebar_frame, text="Theme", anchor="w", font=customtkinter.CTkFont(size=11, weight="bold"))
        self.appearance_mode_label.pack(padx=10, pady=(30, 5), fill="x")
        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
            font=customtkinter.CTkFont(size=10),
            height=40
        )
        self.appearance_mode_optionemenu.pack(padx=10, pady=(0, 10), fill="x")

        self.exit_button = customtkinter.CTkButton(
            self.sidebar_frame, 
            text="🚪 Exit", 
            command=MainExitFunc,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.accent_color,
            text_color="white",
            height=45
        )
        self.exit_button.pack(padx=10, pady=(20, 20), fill="x")

        # ==== MAIN CONTENT AREA ====
        self.main_frame = customtkinter.CTkFrame(self, fg_color=self.secondary_color, corner_radius=0)
        self.main_frame.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Create scrollable frame for cameras
        self.camera_scroll_frame = customtkinter.CTkScrollableFrame(
            self.main_frame,
            fg_color=self.secondary_color,
            corner_radius=0
        )
        self.camera_scroll_frame.pack(fill="both", expand=True, padx=0, pady=0)
        self.camera_scroll_frame.grid_columnconfigure(0, weight=1)
        self.camera_scroll_frame.grid_columnconfigure(1, weight=1)

        # Camera title
        cameras_title = customtkinter.CTkLabel(
            self.camera_scroll_frame,
            text="📹 LIVE CAMERA FEEDS",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=self.primary_color
        )
        cameras_title.grid(row=0, column=0, columnspan=2, padx=15, pady=15, sticky="w")

        # Create 4 camera frames in grid (2x2) with 1920x1080 display
        self.camera_canvases = {}
        self.camera_frames = {}
        self.camera_photo_refs = {}
        
        camera_positions = [
            (1, 0, "Camera 1 - A-102", "⭐"),
            (1, 1, "Camera 2 - A-103", "⭐"),
            (2, 0, "Camera 3 - A-104", "⭐"),
            (2, 1, "Camera 4 - Net Lab", "🥼"),
        ]

        for row, col, label, icon in camera_positions:
            camera_key = f"camera_{(row-1)*2 + col + 1}"
            
            # Camera frame container - FIXED SIZE
            cam_frame = customtkinter.CTkFrame(self.camera_scroll_frame, corner_radius=12, fg_color="#2A2A3E", border_width=2, border_color=self.primary_color, width=520, height=580)
            cam_frame.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")
            cam_frame.grid_propagate(False)  # Prevent frame from expanding
            
            # Set equal weights for square layout
            self.camera_scroll_frame.grid_rowconfigure(row, weight=1)
            self.camera_scroll_frame.grid_columnconfigure(col, weight=1)

            # Camera header with title and status
            header_frame = customtkinter.CTkFrame(cam_frame, fg_color="#1E1E2E", corner_radius=10)
            header_frame.pack(pady=8, padx=8, fill="x")

            # Title and icon
            title_frame = customtkinter.CTkFrame(header_frame, fg_color="transparent")
            title_frame.pack(side="left", padx=10, pady=8, fill="x", expand=True)

            cam_title = customtkinter.CTkLabel(
                title_frame,
                text=f"{icon} {label}",
                font=customtkinter.CTkFont(size=12, weight="bold"),
                text_color=self.primary_color
            )
            cam_title.pack(side="left")

            # Status indicator
            status_label = customtkinter.CTkLabel(
                header_frame,
                text="🟢 ACTIVE",
                font=customtkinter.CTkFont(size=9, weight="bold"),
                text_color=self.success_color
            )
            status_label.pack(side="right", padx=10, pady=8)

            # Camera canvas - FIXED 480x480 SQUARE
            canvas = tk.Canvas(
                cam_frame,
                bg="#1A1A1A",
                width=480,
                height=480,
                highlightthickness=3,
                highlightbackground=self.primary_color,
                cursor="crosshair"
            )
            canvas.pack(pady=10, padx=10, fill="none", expand=False)

            # FPS counter
            fps_label = customtkinter.CTkLabel(
                cam_frame,
                text="FPS: 30 | Source: Live",
                font=customtkinter.CTkFont(size=9),
                text_color="#888888"
            )
            fps_label.pack(pady=(5, 10), padx=10, fill="x")

            self.camera_canvases[camera_key] = canvas
            self.camera_frames[camera_key] = (cam_frame, status_label)
            self.camera_photo_refs[camera_key] = None

        self.update_camera_feed()

    def update_camera_feed(self):
        camera_keys = ['camera_1', 'camera_2', 'camera_3', 'camera_4']
        
        for camera_key in camera_keys:
            try:
                frame = camera_frame_queues[camera_key].get_nowait()
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # Resize to EXACT square 480x480
                frame_resized = cv2.resize(frame_rgb, (480, 480), interpolation=cv2.INTER_LINEAR)
                image = Image.fromarray(frame_resized)
                photo = ImageTk.PhotoImage(image=image)
                
                canvas = self.camera_canvases[camera_key]
                canvas.delete("all")
                canvas.create_image(240, 240, image=photo, anchor="center")
                self.camera_photo_refs[camera_key] = photo
            except queue.Empty:
                pass
        
        self.after(30, self.update_camera_feed)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def ExportAttendance(self):
        try:
            import csv
            
            conn = sqlite3.connect("MainDataBase.db")
            cur = conn.cursor()
            
            current_date = datetime.now().strftime('%d_%m_%Y')
            filename = f"Cypher_Attendance_{current_date}.csv"
            
            cur.execute("SELECT Name, date, time, ID, Attendance, Period FROM AllStudentAttendanceData ORDER BY date DESC, ID, Period;")
            records = cur.fetchall()
            
            if not records:
                CTkMessagebox(title="Info", message="✅ No attendance records to export", icon="info", option_1="Ok")
                conn.close()
                return
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Name', 'Date', 'Time', 'ID', 'Attendance', 'Period'])
                writer.writerows(records)
            
            CTkMessagebox(title="Success", message=f"✅ Report exported as\n{filename}", icon="check", option_1="Ok")
            conn.close()
        except Exception as e:
            CTkMessagebox(title="Error", message=f"❌ Export Error: {str(e)}", icon="warning", option_1="Ok")

    def CheckAttendanceAdmin(self):
        checkWindow = customtkinter.CTkToplevel(self)
        checkWindow.title("Check Attendance - Cypher")
        checkWindow.geometry("950x650")
        checkWindow.resizable(True, True)

        header = customtkinter.CTkFrame(checkWindow, fg_color="#0F0F1E", height=65, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        title = customtkinter.CTkLabel(header, text="📊 CHECK ATTENDANCE RECORDS", font=customtkinter.CTkFont(size=15, weight="bold"), text_color="#00D4FF")
        title.pack(pady=18, padx=10)

        input_frame = customtkinter.CTkFrame(checkWindow, fg_color="#1E1E2E", height=50, corner_radius=8)
        input_frame.pack(fill="x", padx=12, pady=10)
        input_frame.pack_propagate(False)

        customtkinter.CTkLabel(input_frame, text="🔍 ID", font=customtkinter.CTkFont(size=10, weight="bold")).pack(side="left", padx=8)
        input_id = customtkinter.CTkEntry(input_frame, width=120, height=35, placeholder_text="Student ID", font=customtkinter.CTkFont(size=9))
        input_id.pack(side="left", padx=3)

        customtkinter.CTkLabel(input_frame, text="📅 Date", font=customtkinter.CTkFont(size=10, weight="bold")).pack(side="left", padx=8)
        input_date = customtkinter.CTkEntry(input_frame, width=120, height=35, placeholder_text="DD:MM:YYYY (Optional)", font=customtkinter.CTkFont(size=9))
        input_date.pack(side="left", padx=3)

        def open_calendar():
            try:
                cal_window = tk.Toplevel(checkWindow)
                cal_window.title("📅 Select Date")
                cal_window.geometry("400x320")
                cal_window.resizable(False, False)
                
                # Set window to appear on top
                cal_window.attributes('-topmost', True)
                
                # Main frame with white background for visibility
                main_frame = tk.Frame(cal_window, bg="#FFFFFF", relief=tk.SUNKEN, bd=2)
                main_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Title frame
                title_frame = tk.Frame(main_frame, bg="#00D4FF")
                title_frame.pack(fill="x", padx=5, pady=5)
                
                title_label = tk.Label(title_frame, text="Select Date", font=("Arial", 14, "bold"), bg="#00D4FF", fg="#000000")
                title_label.pack(pady=5)
                
                # Calendar with minimal styling
                try:
                    from tkcalendar import Calendar
                    cal = Calendar(
                        main_frame,
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day,
                        font=("Arial", 10),
                        headersforground="black",
                        normalbackground="white",
                        normalforeground="black",
                        weekendforeground="red",
                        otherforeground="gray",
                        selectforeground="white",
                        selectbackground="#00D4FF"
                    )
                    cal.pack(fill="both", expand=True, padx=5, pady=5)
                except:
                    # Fallback if styling fails
                    cal = Calendar(main_frame, year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                    cal.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Button frame
                button_frame = tk.Frame(main_frame, bg="#FFFFFF")
                button_frame.pack(fill="x", padx=5, pady=10)
                
                def select_date():
                    try:
                        selected = cal.selection_get()
                        input_date.delete(0, tk.END)
                        input_date.insert(0, selected.strftime("%d:%m:%Y"))
                    except:
                        pass
                    cal_window.destroy()
                
                select_btn = tk.Button(
                    button_frame,
                    text="✓ SELECT DATE",
                    command=select_date,
                    bg="#00D4FF",
                    fg="#000000",
                    font=("Arial", 11, "bold"),
                    padx=30,
                    pady=8,
                    relief=tk.RAISED,
                    bd=2
                )
                select_btn.pack(fill="x")
                
                # Center window on parent
                cal_window.transient(checkWindow)
                cal_window.grab_set()
                
            except Exception as e:
                CTkMessagebox(
                    master=checkWindow,
                    title="Error",
                    message=f"Calendar widget error.\n\nPlease enter date manually in DD:MM:YYYY format.\n\nError: {str(e)}",
                    icon="warning",
                    option_1="Ok"
                )

        cal_btn = customtkinter.CTkButton(
            input_frame,
            text="📆 Pick Date",
            command=open_calendar,
            width=100,
            height=35,
            fg_color="#00D4FF",
            text_color="black",
            font=customtkinter.CTkFont(size=10, weight="bold"),
            hover_color="#00B8D4"
        )
        cal_btn.pack(side="left", padx=3)

        def search_attendance():
            student_id = input_id.get().strip()
            date_str = input_date.get().strip()

            if not student_id:
                CTkMessagebox(master=checkWindow, title="Error", message="Please enter Student ID", icon="warning", option_1="Ok")
                return

            try:
                conn = sqlite3.connect("MainDataBase.db")
                cur = conn.cursor()

                if date_str:
                    query = "SELECT Name, date, Period, Attendance, time FROM AllStudentAttendanceData WHERE ID = ? AND date = ? ORDER BY Period;"
                    cur.execute(query, (student_id, date_str))
                else:
                    query = "SELECT Name, date, Period, Attendance, time FROM AllStudentAttendanceData WHERE ID = ? ORDER BY date DESC, Period;"
                    cur.execute(query, (student_id,))

                records = cur.fetchall()
                conn.close()

                for item in tree.get_children():
                    tree.delete(item)

                if not records:
                    CTkMessagebox(master=checkWindow, title="Info", message="No records found for this student", icon="info", option_1="Ok")
                    return

                # Insert all records - including multiple entries per date for different periods
                for record in records:
                    tree.insert('', 'end', values=record)

            except Exception as e:
                CTkMessagebox(master=checkWindow, title="Error", message=f"Error: {str(e)}", icon="warning", option_1="Ok")

        search_btn = customtkinter.CTkButton(input_frame, text="🔎 Search", command=search_attendance, fg_color="#00D4FF", text_color="black", font=customtkinter.CTkFont(size=10, weight="bold"), height=35, width=80)
        search_btn.pack(side="left", padx=5)

        # Info label
        info_label = customtkinter.CTkLabel(
            checkWindow,
            text="💡 Tip: Leave date field empty to view all attendance records",
            font=customtkinter.CTkFont(size=9),
            text_color="#888888"
        )
        info_label.pack(padx=12, pady=(5, 10), anchor="w")

        # Create Treeview
        tree_frame = customtkinter.CTkFrame(checkWindow, fg_color="#1E1E2E")
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        columns = ('Name', 'Date', 'Period', 'Attendance', 'Time')
        tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Name", anchor=tk.W, width=180)
        tree.column("Date", anchor=tk.CENTER, width=110)
        tree.column("Period", anchor=tk.CENTER, width=80)
        tree.column("Attendance", anchor=tk.CENTER, width=110)
        tree.column("Time", anchor=tk.CENTER, width=120)

        tree.heading("#0", text="")
        tree.heading("Name", text="Student Name")
        tree.heading("Date", text="Date")
        tree.heading("Period", text="Period")
        tree.heading("Attendance", text="Status")
        tree.heading("Time", text="Time")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#2A2A3E", foreground="#FFFFFF", fieldbackground="#2A2A3E", font=("Arial", 9))
        style.configure("Treeview.Heading", background="#0F0F1E", foreground="#00D4FF", font=("Arial", 9, "bold"))

        tree.pack(fill="both", expand=True)

    def UpdateAttendanceAdmin(self):
        updateWindow = customtkinter.CTkToplevel(self)
        updateWindow.title("Update Attendance - Cypher")
        updateWindow.geometry("600x600")

        header = customtkinter.CTkFrame(updateWindow, fg_color="#0F0F1E", height=70, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        title = customtkinter.CTkLabel(header, text="✏️ UPDATE ATTENDANCE", font=customtkinter.CTkFont(size=16, weight="bold"), text_color="#00D4FF")
        title.pack(pady=20, padx=10)

        content = customtkinter.CTkScrollableFrame(updateWindow, fg_color="#1E1E2E")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # Student ID
        customtkinter.CTkLabel(content, text="👤 Student ID", font=customtkinter.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(10, 5))
        input_id = customtkinter.CTkEntry(content, width=300, height=40, placeholder_text="Enter Student ID", font=customtkinter.CTkFont(size=10))
        input_id.pack(fill="x", pady=(0, 15))

        # Date with Calendar
        customtkinter.CTkLabel(content, text="📅 Date (DD:MM:YYYY)", font=customtkinter.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(10, 5))
        date_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        date_frame.pack(fill="x", pady=(0, 15))
        
        input_date = customtkinter.CTkEntry(date_frame, width=250, height=40, placeholder_text="Select Date", font=customtkinter.CTkFont(size=10))
        input_date.pack(side="left", padx=(0, 10))

        def open_calendar():
            try:
                cal_window = tk.Toplevel(updateWindow)
                cal_window.title("📅 Select Date")
                cal_window.geometry("400x320")
                cal_window.resizable(False, False)
                
                # Set window to appear on top
                cal_window.attributes('-topmost', True)
                
                # Main frame with white background for visibility
                main_frame = tk.Frame(cal_window, bg="#FFFFFF", relief=tk.SUNKEN, bd=2)
                main_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Title frame
                title_frame = tk.Frame(main_frame, bg="#00D4FF")
                title_frame.pack(fill="x", padx=5, pady=5)
                
                title_label = tk.Label(title_frame, text="Select Date", font=("Arial", 14, "bold"), bg="#00D4FF", fg="#000000")
                title_label.pack(pady=5)
                
                # Calendar with minimal styling
                try:
                    from tkcalendar import Calendar
                    cal = Calendar(
                        main_frame,
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day,
                        font=("Arial", 10),
                        headersforground="black",
                        normalbackground="white",
                        normalforeground="black",
                        weekendforeground="red",
                        otherforeground="gray",
                        selectforeground="white",
                        selectbackground="#00D4FF"
                    )
                    cal.pack(fill="both", expand=True, padx=5, pady=5)
                except:
                    # Fallback if styling fails
                    cal = Calendar(main_frame, year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                    cal.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Button frame
                button_frame = tk.Frame(main_frame, bg="#FFFFFF")
                button_frame.pack(fill="x", padx=5, pady=10)
                
                def select_date():
                    try:
                        selected = cal.selection_get()
                        input_date.delete(0, tk.END)
                        input_date.insert(0, selected.strftime("%d:%m:%Y"))
                    except:
                        pass
                    cal_window.destroy()
                
                select_btn = tk.Button(
                    button_frame,
                    text="✓ SELECT DATE",
                    command=select_date,
                    bg="#00D4FF",
                    fg="#000000",
                    font=("Arial", 11, "bold"),
                    padx=30,
                    pady=8,
                    relief=tk.RAISED,
                    bd=2
                )
                select_btn.pack(fill="x")
                
                # Center window on parent
                cal_window.transient(updateWindow)
                cal_window.grab_set()
                
            except Exception as e:
                CTkMessagebox(
                    master=updateWindow,
                    title="Error",
                    message=f"Calendar widget error.\n\nPlease enter date manually in DD:MM:YYYY format.\n\nError: {str(e)}",
                    icon="warning",
                    option_1="Ok"
                )

        cal_btn = customtkinter.CTkButton(
            date_frame,
            text="📆 Pick Date",
            command=open_calendar,
            width=100,
            height=40,
            fg_color="#00D4FF",
            text_color="black",
            font=customtkinter.CTkFont(size=10, weight="bold"),
            hover_color="#00B8D4"
        )
        cal_btn.pack(side="left")

        # Period
        customtkinter.CTkLabel(content, text="🕐 Period (1-8)", font=customtkinter.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(10, 5))
        input_period = customtkinter.CTkComboBox(
            content,
            values=["1", "2", "3", "4", "5", "6", "7", "8"],
            width=300,
            height=40,
            font=customtkinter.CTkFont(size=10),
            state="readonly"
        )
        input_period.pack(fill="x", pady=(0, 15))

        # Attendance
        customtkinter.CTkLabel(content, text="✓ Attendance Status", font=customtkinter.CTkFont(size=11, weight="bold")).pack(anchor="w", pady=(10, 5))
        input_attendance = customtkinter.CTkComboBox(
            content,
            values=["P - Present", "A - Absent"],
            width=300,
            height=40,
            font=customtkinter.CTkFont(size=10),
            state="readonly"
        )
        input_attendance.pack(fill="x", pady=(0, 20))

        def update_record():
            student_id = input_id.get().strip()
            date_str = input_date.get().strip()
            period = input_period.get().strip()
            attendance_val = input_attendance.get().strip()

            if not all([student_id, date_str, period, attendance_val]):
                CTkMessagebox(master=updateWindow, title="Error", message="❌ Please fill all fields", icon="warning", option_1="Ok")
                return

            # Extract just P or A from the dropdown
            attendance = attendance_val[0].upper() if attendance_val else ""

            if attendance not in ['P', 'A']:
                CTkMessagebox(master=updateWindow, title="Error", message="❌ Invalid attendance status", icon="warning", option_1="Ok")
                return

            # Validate date format
            try:
                from datetime import datetime as dt
                dt.strptime(date_str, "%d:%m:%Y")
            except:
                CTkMessagebox(master=updateWindow, title="Error", message="❌ Invalid date format. Use DD:MM:YYYY", icon="warning", option_1="Ok")
                return

            try:
                conn = sqlite3.connect("MainDataBase.db")
                cur = conn.cursor()
                cur.execute("UPDATE AllStudentAttendanceData SET Attendance = ? WHERE ID = ? AND date = ? AND Period = ?;", (attendance, student_id, date_str, period))
                conn.commit()
                
                if cur.rowcount > 0:
                    CTkMessagebox(master=updateWindow, title="Success", message="✅ Attendance Updated Successfully", icon="check", option_1="Ok")
                    # Clear form
                    input_id.delete(0, tk.END)
                    input_date.delete(0, tk.END)
                    input_period.set("")
                    input_attendance.set("")
                else:
                    CTkMessagebox(master=updateWindow, title="Info", message="❌ No Record Found to Update", icon="info", option_1="Ok")
                
                conn.close()
            except Exception as e:
                CTkMessagebox(master=updateWindow, title="Error", message=f"❌ Database Error: {str(e)}", icon="warning", option_1="Ok")

        update_btn = customtkinter.CTkButton(
            content,
            text="💾 Update Record",
            command=update_record,
            fg_color="#00D4FF",
            text_color="black",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            height=40,
            hover_color="#00B8D4"
        )
        update_btn.pack(fill="x", pady=10)

    def AddDataAdmin(self):
        try:
            # Save current state
            admin_name = loginresult[0]
            
            # Destroy current admin window
            self.destroy()
            
            # Open registration page
            from registration import RegistrationPage
            reg_app = RegistrationPage()
            reg_app.run()
            
            # Recreate admin window after registration closes
            admin_gui = CypherGUIAdmin()
            admin_gui.mainloop()
        
        except Exception as e:
            print(f"Error opening registration: {str(e)}")
            import traceback
            traceback.print_exc()

    def ExitApp(self):
        exit(0)

class CypherGUIStudent(customtkinter.CTk):
    def __init__(self, student_id, student_name):
        super().__init__()
        self.student_id = student_id
        self.student_name = student_name

        self.title("Cypher - Student Dashboard")
        self.state('zoomed')  # For Windows

        # Color scheme
        self.primary_color = "#00D4FF"
        self.secondary_color = "#1E1E2E"
        self.accent_color = "#FF6B6B"
        self.success_color = "#00FF00"
        self.warning_color = "#FFD700"

        # Period timings
        self.period_times = {
            1: ((9, 0), (9, 55)),
            2: ((9, 55), (10, 50)),
            3: ((10, 50), (11, 45)),
            4: ((11, 45), (12, 40)),
            5: ((12, 40), (13, 35)),
            6: ((13, 35), (14, 30)),
            7: ((14, 30), (15, 25)),
            8: ((15, 25), (16, 20)),
        }

        # Grid configuration - RESPONSIVE
        self.grid_columnconfigure(0, weight=0, minsize=200)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        # ==== TOP HEADER ==== (OPTIMIZED)
        self.header_frame = customtkinter.CTkFrame(
            self,
            fg_color="#0F0F1E",
            corner_radius=0
        )
        self.header_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        self.header_frame.grid_propagate(False)

        # Inner header container for responsive padding
        header_container = customtkinter.CTkFrame(
            self.header_frame,
            fg_color="#0F0F1E",
            corner_radius=0
        )
        header_container.pack(fill="both", expand=True, padx=20, pady=12)

        # Left side - Title
        header_title = customtkinter.CTkLabel(
            header_container,
            text="🎓 CYPHER - STUDENT DASHBOARD",
            font=customtkinter.CTkFont(size=18, weight="bold"),
            text_color=self.primary_color
        )
        header_title.pack(side="left", expand=True, anchor="w")

        # Right side - Welcome info
        welcome_info = customtkinter.CTkLabel(
            header_container,
            text=f"Welcome: {self.student_name} | {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}",
            font=customtkinter.CTkFont(size=10),
            text_color="#888888"
        )
        welcome_info.pack(side="right", anchor="e", padx=(20, 0))

        # Set appropriate header height
        self.header_frame.update_idletasks()
        self.header_frame.configure(height=60)

        # ==== LEFT SIDEBAR ==== (RESPONSIVE)
        self.sidebar_frame = customtkinter.CTkFrame(
            self,
            corner_radius=0,
            fg_color=self.secondary_color
        )
        self.sidebar_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.sidebar_frame.grid_propagate(False)

        logo_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="CYPHER",
            font=customtkinter.CTkFont(size=24, weight="bold"),
            text_color=self.primary_color
        )
        logo_label.pack(pady=(15, 25), padx=15)

        dashboard_btn = customtkinter.CTkButton(
            self.sidebar_frame,
            text="📊 Dashboard",
            command=self.show_dashboard,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        dashboard_btn.pack(padx=10, pady=6, fill="x")

        attendance_btn = customtkinter.CTkButton(
            self.sidebar_frame,
            text="📋 Attendance Records",
            command=self.show_attendance_records,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        attendance_btn.pack(padx=10, pady=6, fill="x")

        profile_btn = customtkinter.CTkButton(
            self.sidebar_frame,
            text="👤 My Profile",
            command=self.show_profile,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.primary_color,
            text_color="black",
            height=50
        )
        profile_btn.pack(padx=10, pady=6, fill="x")

        self.appearance_mode_label = customtkinter.CTkLabel(
            self.sidebar_frame,
            text="Theme",
            anchor="w",
            font=customtkinter.CTkFont(size=11, weight="bold")
        )
        self.appearance_mode_label.pack(padx=10, pady=(25, 5), fill="x")

        self.appearance_mode_optionemenu = customtkinter.CTkOptionMenu(
            self.sidebar_frame,
            values=["Light", "Dark", "System"],
            command=self.change_appearance_mode_event,
            font=customtkinter.CTkFont(size=10),
            height=40
        )
        self.appearance_mode_optionemenu.pack(padx=10, pady=(0, 10), fill="x")

        exit_button = customtkinter.CTkButton(
            self.sidebar_frame,
            text="🚪 Logout",
            command=self.exit_app,
            font=customtkinter.CTkFont(size=11, weight="bold"),
            fg_color=self.accent_color,
            text_color="white",
            height=45
        )
        exit_button.pack(padx=10, pady=(15, 15), fill="x", side="bottom")

        # ==== MAIN CONTENT AREA ==== (RESPONSIVE)
        self.main_frame = customtkinter.CTkFrame(
            self,
            fg_color=self.secondary_color,
            corner_radius=0
        )
        self.main_frame.grid(row=1, column=1, padx=0, pady=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        # Show dashboard by default
        self.show_dashboard()

    def clear_main_frame(self):
        """Clear all widgets from main frame"""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        """Display dashboard with stats and recent attendance"""
        self.clear_main_frame()

        content = customtkinter.CTkScrollableFrame(
            self.main_frame,
            fg_color=self.secondary_color,
            corner_radius=0
        )
        content.pack(fill="both", expand=True, padx=0, pady=0)
        content.grid_columnconfigure(0, weight=1)

        # Title
        title = customtkinter.CTkLabel(
            content,
            text="📊 Dashboard Overview",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color=self.primary_color
        )
        title.pack(anchor="w", padx=20, pady=(20, 30))

        # Fetch statistics
        try:
            conn = sqlite3.connect("MainDataBase.db")
            cur = conn.cursor()

            # Total records
            cur.execute("SELECT COUNT(*) FROM AllStudentAttendanceData WHERE ID = ?", (self.student_id,))
            total_records = cur.fetchone()[0]

            # Present count
            cur.execute("SELECT COUNT(*) FROM AllStudentAttendanceData WHERE ID = ? AND Attendance = 'P'", (self.student_id,))
            present_count = cur.fetchone()[0]

            # Absent count
            cur.execute("SELECT COUNT(*) FROM AllStudentAttendanceData WHERE ID = ? AND Attendance = 'A'", (self.student_id,))
            absent_count = cur.fetchone()[0]

            # Calculate percentage
            percentage = (present_count / total_records * 100) if total_records > 0 else 0

            conn.close()
        except Exception as e:
            total_records = present_count = absent_count = percentage = 0

        # Stat cards frame
        stats_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=(0, 30))
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # Card 1: Total Records
        card1 = customtkinter.CTkFrame(stats_frame, fg_color="#2A2A3E", corner_radius=12, border_width=2, border_color=self.primary_color)
        card1.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        customtkinter.CTkLabel(card1, text="📝 Total Records", font=customtkinter.CTkFont(size=10, weight="bold"), text_color="#888888").pack(pady=(10, 5))
        customtkinter.CTkLabel(card1, text=str(total_records), font=customtkinter.CTkFont(size=20, weight="bold"), text_color=self.primary_color).pack(pady=(0, 10))

        # Card 2: Present
        card2 = customtkinter.CTkFrame(stats_frame, fg_color="#2A2A3E", corner_radius=12, border_width=2, border_color=self.success_color)
        card2.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        customtkinter.CTkLabel(card2, text="✓ Present", font=customtkinter.CTkFont(size=10, weight="bold"), text_color="#888888").pack(pady=(10, 5))
        customtkinter.CTkLabel(card2, text=str(present_count), font=customtkinter.CTkFont(size=20, weight="bold"), text_color=self.success_color).pack(pady=(0, 10))

        # Card 3: Absent
        card3 = customtkinter.CTkFrame(stats_frame, fg_color="#2A2A3E", corner_radius=12, border_width=2, border_color=self.accent_color)
        card3.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        customtkinter.CTkLabel(card3, text="✗ Absent", font=customtkinter.CTkFont(size=10, weight="bold"), text_color="#888888").pack(pady=(10, 5))
        customtkinter.CTkLabel(card3, text=str(absent_count), font=customtkinter.CTkFont(size=20, weight="bold"), text_color=self.accent_color).pack(pady=(0, 10))

        # Card 4: Percentage
        card4 = customtkinter.CTkFrame(stats_frame, fg_color="#2A2A3E", corner_radius=12, border_width=2, border_color=self.warning_color)
        card4.grid(row=0, column=3, padx=10, pady=10, sticky="nsew")
        customtkinter.CTkLabel(card4, text="% Attendance", font=customtkinter.CTkFont(size=10, weight="bold"), text_color="#888888").pack(pady=(10, 5))
        customtkinter.CTkLabel(card4, text=f"{percentage:.1f}%", font=customtkinter.CTkFont(size=20, weight="bold"), text_color=self.warning_color).pack(pady=(0, 10))

        # Recent attendance section
        recent_title = customtkinter.CTkLabel(
            content,
            text="📅 Recent Attendance (Last 10 Records)",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            text_color=self.primary_color
        )
        recent_title.pack(anchor="w", padx=20, pady=(20, 15))

        # Recent records table
        tree_frame = customtkinter.CTkFrame(content, fg_color="#1E1E2E", corner_radius=8)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        columns = ('Date', 'Period', 'Time', 'Status')
        tree = ttk.Treeview(tree_frame, columns=columns, height=10)
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Date", anchor=tk.CENTER, width=120)
        tree.column("Period", anchor=tk.CENTER, width=80)
        tree.column("Time", anchor=tk.CENTER, width=150)
        tree.column("Status", anchor=tk.CENTER, width=100)

        tree.heading("#0", text="")
        tree.heading("Date", text="Date")
        tree.heading("Period", text="Period")
        tree.heading("Time", text="Time")
        tree.heading("Status", text="Status")

        # Style treeview
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#2A2A3E", foreground="#FFFFFF", fieldbackground="#2A2A3E", font=("Arial", 9))
        style.configure("Treeview.Heading", background="#0F0F1E", foreground="#00D4FF", font=("Arial", 9, "bold"))

        # Fetch recent records
        try:
            conn = sqlite3.connect("MainDataBase.db")
            cur = conn.cursor()
            cur.execute("SELECT date, Period, time, Attendance FROM AllStudentAttendanceData WHERE ID = ? ORDER BY date DESC LIMIT 10", (self.student_id,))
            records = cur.fetchall()
            conn.close()

            for record in records:
                date_str, period, time_str, attendance = record
                status_display = "✓ Present" if attendance == 'P' else "✗ Absent"
                period_times = self.period_times.get(int(period), ((0, 0), (0, 0)))
                time_display = f"{period_times[0][0]:02d}:{period_times[0][1]:02d} - {period_times[1][0]:02d}:{period_times[1][1]:02d}"
                tree.insert('', 'end', values=(date_str, f"Period {period}", time_display, status_display))
        except Exception as e:
            pass

        tree.pack(fill="both", expand=True)

    def show_attendance_records(self):
        """Display attendance records with calendar date picker"""
        self.clear_main_frame()

        content = customtkinter.CTkScrollableFrame(
            self.main_frame,
            fg_color=self.secondary_color,
            corner_radius=0
        )
        content.pack(fill="both", expand=True, padx=0, pady=0)
        content.grid_columnconfigure(0, weight=1)

        # Title
        title = customtkinter.CTkLabel(
            content,
            text="📋 Attendance Records",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color=self.primary_color
        )
        title.pack(anchor="w", padx=20, pady=(20, 20))

        # Filter section
        filter_frame = customtkinter.CTkFrame(content, fg_color="#1E1E2E", corner_radius=8)
        filter_frame.pack(fill="x", padx=20, pady=(0, 20))

        customtkinter.CTkLabel(filter_frame, text="📅 Select Date:", font=customtkinter.CTkFont(size=10, weight="bold")).pack(side="left", padx=10, pady=10)

        date_entry = customtkinter.CTkEntry(filter_frame, width=150, height=35, placeholder_text="DD:MM:YYYY", font=customtkinter.CTkFont(size=9))
        date_entry.pack(side="left", padx=5, pady=10)

        def open_calendar():
            try:
                cal_window = tk.Toplevel(self)
                cal_window.title("Select Date")
                cal_window.geometry("400x320")
                cal_window.resizable(False, False)
                cal_window.attributes('-topmost', True)

                main_frame_cal = tk.Frame(cal_window, bg="#FFFFFF", relief=tk.SUNKEN, bd=2)
                main_frame_cal.pack(fill="both", expand=True, padx=5, pady=5)

                title_frame_cal = tk.Frame(main_frame_cal, bg="#00D4FF")
                title_frame_cal.pack(fill="x", padx=5, pady=5)

                title_label = tk.Label(title_frame_cal, text="Select Date", font=("Arial", 14, "bold"), bg="#00D4FF", fg="#000000")
                title_label.pack(pady=5)

                try:
                    from tkcalendar import Calendar
                    cal = Calendar(
                        main_frame_cal,
                        year=datetime.now().year,
                        month=datetime.now().month,
                        day=datetime.now().day,
                        font=("Arial", 10),
                        headersforground="black",
                        normalbackground="white",
                        normalforeground="black",
                        weekendforeground="red",
                        otherforeground="gray",
                        selectforeground="white",
                        selectbackground="#00D4FF"
                    )
                    cal.pack(fill="both", expand=True, padx=5, pady=5)
                except:
                    cal = Calendar(main_frame_cal, year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
                    cal.pack(fill="both", expand=True, padx=5, pady=5)

                button_frame_cal = tk.Frame(main_frame_cal, bg="#FFFFFF")
                button_frame_cal.pack(fill="x", padx=5, pady=10)

                def select_date():
                    try:
                        selected = cal.selection_get()
                        date_entry.delete(0, tk.END)
                        date_entry.insert(0, selected.strftime("%d:%m:%Y"))
                        load_records()
                    except:
                        pass
                    cal_window.destroy()

                select_btn = tk.Button(
                    button_frame_cal,
                    text="SELECT DATE",
                    command=select_date,
                    bg="#00D4FF",
                    fg="#000000",
                    font=("Arial", 11, "bold"),
                    padx=30,
                    pady=8
                )
                select_btn.pack(fill="x")

                cal_window.transient(self)
                cal_window.grab_set()
            except Exception as e:
                CTkMessagebox(title="Error", message=f"Calendar error: {str(e)}", icon="warning", option_1="Ok")

        cal_btn = customtkinter.CTkButton(
            filter_frame,
            text="📆 Pick Date",
            command=open_calendar,
            width=100,
            height=35,
            fg_color="#00D4FF",
            text_color="black",
            font=customtkinter.CTkFont(size=10, weight="bold")
        )
        cal_btn.pack(side="left", padx=5, pady=10)

        clear_btn = customtkinter.CTkButton(
            filter_frame,
            text="Clear",
            command=lambda: (date_entry.delete(0, tk.END), load_records()),
            width=80,
            height=35,
            fg_color="#888888",
            text_color="white",
            font=customtkinter.CTkFont(size=10, weight="bold")
        )
        clear_btn.pack(side="left", padx=5, pady=10)

        # Records table
        tree_frame = customtkinter.CTkFrame(content, fg_color="#1E1E2E", corner_radius=8)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        columns = ('Date', 'Period', 'Time', 'Status')
        tree = ttk.Treeview(tree_frame, columns=columns, height=20)
        tree.column("#0", width=0, stretch=tk.NO)
        tree.column("Date", anchor=tk.CENTER, width=120)
        tree.column("Period", anchor=tk.CENTER, width=80)
        tree.column("Time", anchor=tk.CENTER, width=150)
        tree.column("Status", anchor=tk.CENTER, width=100)

        tree.heading("#0", text="")
        tree.heading("Date", text="Date")
        tree.heading("Period", text="Period")
        tree.heading("Time", text="Time")
        tree.heading("Status", text="Status")

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", background="#2A2A3E", foreground="#FFFFFF", fieldbackground="#2A2A3E", font=("Arial", 9))
        style.configure("Treeview.Heading", background="#0F0F1E", foreground="#00D4FF", font=("Arial", 9, "bold"))

        def load_records():
            for item in tree.get_children():
                tree.delete(item)

            date_filter = date_entry.get().strip()

            try:
                conn = sqlite3.connect("MainDataBase.db")
                cur = conn.cursor()

                if date_filter:
                    query = "SELECT date, Period, time, Attendance FROM AllStudentAttendanceData WHERE ID = ? AND date = ? ORDER BY Period"
                    cur.execute(query, (self.student_id, date_filter))
                else:
                    query = "SELECT date, Period, time, Attendance FROM AllStudentAttendanceData WHERE ID = ? ORDER BY date DESC, Period"
                    cur.execute(query, (self.student_id,))

                records = cur.fetchall()
                conn.close()

                if not records:
                    CTkMessagebox(title="Info", message="No records found", icon="info", option_1="Ok")
                    return

                for record in records:
                    date_str, period, time_str, attendance = record
                    status_display = "✓ Present" if attendance == 'P' else "✗ Absent"
                    period_times = self.period_times.get(int(period), ((0, 0), (0, 0)))
                    time_display = f"{period_times[0][0]:02d}:{period_times[0][1]:02d} - {period_times[1][0]:02d}:{period_times[1][1]:02d}"
                    tree.insert('', 'end', values=(date_str, f"Period {period}", time_display, status_display))
            except Exception as e:
                CTkMessagebox(title="Error", message=f"Error: {str(e)}", icon="warning", option_1="Ok")

        # Load initial records
        load_records()
        tree.pack(fill="both", expand=True)

    def show_profile(self):
        """Display student profile from AuthenticationData table"""
        self.clear_main_frame()

        content = customtkinter.CTkScrollableFrame(
            self.main_frame,
            fg_color=self.secondary_color,
            corner_radius=0
        )
        content.pack(fill="both", expand=True, padx=0, pady=0)

        # Title
        title = customtkinter.CTkLabel(
            content,
            text="👤 My Profile",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color=self.primary_color
        )
        title.pack(anchor="w", padx=20, pady=(20, 30))

        # Profile card
        profile_card = customtkinter.CTkFrame(content, fg_color="#1E1E2E", corner_radius=12)
        profile_card.pack(fill="x", padx=20, pady=(0, 20))

        try:
            conn = sqlite3.connect("MainDataBase.db")
            cur = conn.cursor()

            cur.execute("SELECT Name, ID, Role, phone_number FROM AuthenticationData WHERE ID = ?", (self.student_id,))
            profile_data = cur.fetchone()
            conn.close()

            if profile_data:
                name, student_id, role, phone = profile_data

                # Create profile info rows
                rows_data = [
                    ("Name", name),
                    ("Student ID", str(student_id)),
                    ("Role", role),
                    ("Phone", str(phone))
                ]

                for label, value in rows_data:
                    row_frame = customtkinter.CTkFrame(profile_card, fg_color="transparent")
                    row_frame.pack(fill="x", padx=15, pady=10)

                    label_widget = customtkinter.CTkLabel(
                        row_frame,
                        text=f"{label}:",
                        font=customtkinter.CTkFont(size=11, weight="bold"),
                        text_color="#888888",
                        width=100,
                        anchor="w"
                    )
                    label_widget.pack(side="left", padx=(0, 20))

                    value_widget = customtkinter.CTkLabel(
                        row_frame,
                        text=value,
                        font=customtkinter.CTkFont(size=11),
                        text_color=self.primary_color
                    )
                    value_widget.pack(side="left")
            else:
                error_label = customtkinter.CTkLabel(
                    profile_card,
                    text="Profile not found",
                    font=customtkinter.CTkFont(size=11),
                    text_color=self.accent_color
                )
                error_label.pack(pady=20)
        except Exception as e:
            error_label = customtkinter.CTkLabel(
                profile_card,
                text=f"Error loading profile: {str(e)}",
                font=customtkinter.CTkFont(size=11),
                text_color=self.accent_color
            )
            error_label.pack(pady=20)

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode)

    def exit_app(self):
        self.destroy()



def start_async_tasks(loop):
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(timemethod()))

if __name__ == "__main__":
    conn_global = None
    loop = asyncio.new_event_loop()
    threading.Thread(target=start_async_tasks, args=(loop,), daemon=True).start()
    
    for idx, cam_key in enumerate(['camera_1', 'camera_2', 'camera_3', 'camera_4']):
        if idx == 0:
            threading.Thread(
                target=lambda c=cam_key: DefaultCamera(camera_frame_queues[c], c),
                daemon=True,
                name=f"Camera-{cam_key}"
            ).start()
    
    LoginPage()