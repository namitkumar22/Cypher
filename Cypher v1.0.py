import cv2
import numpy as np
import face_recognition
from datetime import datetime
import os

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
    with open("Attendence.csv", 'r+') as f:
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