## About Cypher

Cypher is a Automated Attendance System for School, Colleges and Universities and etc. It uses cnn model to recognize face and put attendance in real time automatically.

## Cypher validations

It uses validation for recognizing faces like The attendance will only mark if a student face will detect for more than 30 minutes means if a student attended class for more than 30 minutes then only it mark the attendance, it solves various issues like marking attendance of a student by his/her image because its not possible to hold a image in front of camera for 30 minutes

## Features in version 3
<hr>
<b>1</b> [Major Update] Added user friendly modern GUI
<b>2</b> Facility to Check Attendance of any student
<b>3</b> Facility to update Attendance of any student
<b>4</b> Automatic current lecture detection 
<b>5</b> Increased capability to detect face upto 8 meters
<b>6</b> Light and Dark Themes added
<b>7</b> Automatic Starting Time and sleeping time to save resources
<hr>

## How to use [Admin]
<hr>
<b>step 1</b> : Run "registration.py" and Register as admin 
<b>step 1</b> : Set your Scholl or University Timing as per your schedule in the code [you will find comments in the code for changes]
<b>step 1</b> : Add a folder with name "Images" in the directory in which you are running Cypher<br>
<b>step 2</b> : Add the images of the student in the same folder "Images" you created in step 1<br>
<b>step 2</b> : Make sure the images name should be in format [name[id of student] for example [namit[12].png]]<br>
<b>step 1</b> : Run "Cypher_v3.0.py"
<b>step 1</b> : Login with your credentials
<b>step 1</b> : And you will find the camera is opened simultaneously
<hr>

When the student face is in the camera for 30 minutes then it will automatically mark the attendance of the student in the database. You can also change these 30 minutes as per your requirements just find comments in the code and make changes

I hope you will find this software usefull

## Note

Please Ignore the "Add Camera" Button and "camera_info.json", they are currently under development