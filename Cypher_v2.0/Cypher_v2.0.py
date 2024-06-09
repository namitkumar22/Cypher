import threading

def startmakingattendence():
    import cv2
    import numpy as np
    import face_recognition
    from datetime import datetime
    import os
    from datetime import datetime
    from pytz import timezone 
    import time

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
            encode = face_recognition.face_encodings(img)[0]
            encodedlist.append(encode)

        return encodedlist


    def markAttendence(name):
        with open("Attendance.csv", 'r+') as f:
            mydatalist = f.readlines()
            nameList = []
        
            for line in mydatalist:
                entry = line.split(',')
                nameList.append(entry[0])

            if name not in nameList:
                now = datetime.now()
                datestring = now.strftime('%A:%B:%Y %H:%M:%S')
                f.writelines(f'\n{name}, {datestring}')



    encodeListKnownFaces = findEncoding(images)
    print('Encoding Done')

    cap = cv2.VideoCapture(0)

    while True:
        success, img = cap.read()
        imgs = cv2.resize(img, (0,0), None, 0.25, 0.25)
        imgs = cv2.cvtColor(imgs, cv2.COLOR_BGR2RGB)
        faceCurrent = face_recognition.face_locations(imgs)
        encode = face_recognition.face_encodings(imgs, faceCurrent)

        for encodeface, facelocation in  zip(encode, faceCurrent):
            matches = face_recognition.compare_faces(encodeListKnownFaces, encodeface)
            facedistance = face_recognition.face_distance(encodeListKnownFaces, encodeface)
            print(facedistance)
            matchIndex = np.argmin(facedistance)

            if matches[matchIndex]:
                name = classNames[matchIndex].upper()
                print(name)
                y1, x2, y2, x1 = facelocation
                y1, x2, y2, x1 = y1*4, x2*4, y2*4, x1*4
                cv2.rectangle(img, (x1,y1), (x2, y2), (0, 255, 255), 1)
                cv2.rectangle(img, (x1,y2-25), (x2, y2), (0, 255, 255), cv2.FILLED)
                cv2.putText(img, name, (x1+6, y2-6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 1)

                markAttendence(name)
            
        cv2.imshow('webcam', img)
        cv2.waitKey(1)


        # Note "hour" is 24 hour clock (00,01,02,...., 23)
        ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        hour = ind_time[:2]
        minute = ind_time[3:5]
        seconds = ind_time[6:]

        hour = int(hour)
        minute = int(minute)
        seconds = int(seconds)

        print(ind_time)

        # These are time stamps for a particular time table. Feel free to change this time stamps accoring to your school time table
        if hour == 9 and minute >= 10 and minute <= 50:
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif hour == 10 and minute >= 5 and minute <= 45:
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif hour == 11 and minute >= 00 and minute <= 40:
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif (hour == 11 and minute >= 55) or (hour == 12 and minute <= 35):
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif (hour == 12 and minute >= 50) or (hour == 13 and minute <= 30):
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif (hour == 13 and minute >= 45) or (hour == 14 and minute <= 25):
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif (hour == 14 and minute >= 40) or (hour == 15 and minute <= 20):
            print("Putting Cypher on sleep")
            time.sleep(2400)

        elif (hour >= 15 and minute >= 35):
            print("College if not opened yet")
            time.sleep(54000)
            
            



def timemethod():
    from pytz import timezone 
    from datetime import datetime

    while True:     
        ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S')
        print(ind_time)
            
        hour = ind_time[:2]
        minute = ind_time[3:5]
        seconds = ind_time[6:]

        if str(hour) == '19' and str(minute) == '21':
            while True:
                ind_time = datetime.now(timezone("Asia/Kolkata")).strftime('%H:%M:%S') # This is start time of Cypher. Feel free to change it as your school start time
                hour = ind_time[:2]
                minute = ind_time[3:5]
                seconds = ind_time[6:]
                startmakingattendence()
        else:
            continue


if __name__ =="__main__":
    t2 = threading.Thread(target=timemethod)
    t2.start()
    t2.join()